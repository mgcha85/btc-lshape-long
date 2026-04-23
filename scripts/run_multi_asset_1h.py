#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import polars as pl
from tqdm import tqdm
import itertools

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_backtest.data_loader import BacktestConfig, load_1h_parquet_data
from crypto_backtest.long_strategy import LongStrategyConfig, LongBacktestEngine
from crypto_backtest.storage import calculate_stats

DATA_PATH = Path("/mnt/data/finance/cryptocurrency")
OUTPUT_DIR = Path(__file__).parent.parent / "docs"

SYMBOLS = ["ETHUSDT", "SOLUSDT", "XRPUSDT", "ORDIUSDT", "RENDERUSDT", "GMTUSDT", "CETUSUSDT"]


def run_single_coin_study(symbol: str, data: pl.DataFrame) -> dict:
    ma_periods = [25, 50, 100]
    consolidation_bars_list = [3, 5, 7]
    consolidation_range_list = [3.0, 5.0]
    drop_threshold_list = [3.0, 5.0]
    take_profit_pcts = [5.0, 7.0, 10.0]
    stop_loss_pcts = [2.0, 3.0, 5.0]
    
    combinations = list(itertools.product(
        ma_periods,
        consolidation_bars_list,
        consolidation_range_list,
        drop_threshold_list,
        take_profit_pcts,
        stop_loss_pcts,
    ))
    
    results = []
    
    for ma, cons_bars, cons_range, drop_thresh, tp, sl in combinations:
        strategy_config = LongStrategyConfig(
            data_path=DATA_PATH,
            symbol=symbol,
            timeframe="1h",
            breakout_ma=ma,
            consolidation_bars=cons_bars,
            consolidation_range_pct=cons_range,
            drop_threshold_pct=drop_thresh,
            take_profit_pct=tp,
            stop_loss_pct=sl,
            half_close_enabled=False,
        )
        
        engine = LongBacktestEngine(strategy_config)
        engine.run(data)
        trades_df = engine.get_trades_df()
        
        if trades_df.is_empty():
            continue
        
        stats = calculate_stats(trades_df)
        
        winning = [p for p in trades_df["profit_pct"].to_list() if p > 0]
        losing = [p for p in trades_df["profit_pct"].to_list() if p <= 0]
        profit_factor = abs(sum(winning) / sum(losing)) if losing and sum(losing) != 0 else float("inf")
        
        results.append({
            "ma": ma,
            "cons_bars": cons_bars,
            "cons_range": cons_range,
            "drop_thresh": drop_thresh,
            "take_profit": tp,
            "stop_loss": sl,
            "trades": stats["total_trades"],
            "win_rate": stats["win_rate"],
            "total_profit": stats["total_profit_pct"],
            "max_dd": stats["max_drawdown_pct"],
            "profit_factor": profit_factor,
        })
    
    if not results:
        return None
    
    df = pl.DataFrame(results).sort("total_profit", descending=True)
    best = df.head(1).to_dicts()[0]
    
    best_with_hc = run_half_close_test(symbol, data, best)
    
    return {
        "symbol": symbol,
        "candles": len(data),
        "date_range": f"{data['datetime'].min()} ~ {data['datetime'].max()}",
        "best_config": best,
        "best_with_hc": best_with_hc,
        "profitable_configs": len(df.filter(pl.col("total_profit") > 0)),
        "total_configs": len(df),
    }


def run_half_close_test(symbol: str, data: pl.DataFrame, best_config: dict) -> dict:
    half_close_pcts = [2.0, 3.0, 5.0]
    
    best_result = None
    best_ratio = 0
    
    for hc in half_close_pcts:
        strategy_config = LongStrategyConfig(
            data_path=DATA_PATH,
            symbol=symbol,
            timeframe="1h",
            breakout_ma=best_config["ma"],
            consolidation_bars=best_config["cons_bars"],
            consolidation_range_pct=best_config["cons_range"],
            drop_threshold_pct=best_config["drop_thresh"],
            take_profit_pct=best_config["take_profit"],
            stop_loss_pct=best_config["stop_loss"],
            half_close_enabled=True,
            half_close_pct=hc,
        )
        
        engine = LongBacktestEngine(strategy_config)
        engine.run(data)
        trades_df = engine.get_trades_df()
        
        if trades_df.is_empty():
            continue
        
        stats = calculate_stats(trades_df)
        ratio = stats["total_profit_pct"] / stats["max_drawdown_pct"] if stats["max_drawdown_pct"] > 0 else 0
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_result = {
                "half_close_pct": hc,
                "trades": stats["total_trades"],
                "win_rate": stats["win_rate"],
                "total_profit": stats["total_profit_pct"],
                "max_dd": stats["max_drawdown_pct"],
                "profit_to_mdd": ratio,
            }
    
    return best_result


def run_multi_asset_study():
    print("=" * 60)
    print("Multi-Asset 1H Parametric Study")
    print("=" * 60)
    
    all_results = []
    
    for symbol in tqdm(SYMBOLS, desc="Coins"):
        print(f"\n{'='*40}")
        print(f"Processing {symbol}...")
        print(f"{'='*40}")
        
        try:
            config = BacktestConfig(
                data_path=DATA_PATH,
                symbol=symbol,
                timeframe="1h",
                ma_periods=[25, 50, 100, 200, 400],
            )
            data = load_1h_parquet_data(config)
            print(f"  Loaded {len(data):,} candles")
            print(f"  Date range: {data['datetime'].min()} to {data['datetime'].max()}")
            
            result = run_single_coin_study(symbol, data)
            if result:
                all_results.append(result)
                print(f"  Best profit: {result['best_config']['total_profit']:.2f}%")
                print(f"  Best MDD: {result['best_config']['max_dd']:.2f}%")
                if result['best_with_hc']:
                    print(f"  With HC: {result['best_with_hc']['total_profit']:.2f}% profit, {result['best_with_hc']['max_dd']:.2f}% MDD")
            else:
                print(f"  No profitable configurations found")
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    summary_data = []
    for r in all_results:
        summary_data.append({
            "symbol": r["symbol"],
            "candles": r["candles"],
            "best_profit": r["best_config"]["total_profit"],
            "best_mdd": r["best_config"]["max_dd"],
            "best_ma": r["best_config"]["ma"],
            "best_tp": r["best_config"]["take_profit"],
            "best_sl": r["best_config"]["stop_loss"],
            "trades": r["best_config"]["trades"],
            "win_rate": r["best_config"]["win_rate"],
            "hc_profit": r["best_with_hc"]["total_profit"] if r["best_with_hc"] else None,
            "hc_mdd": r["best_with_hc"]["max_dd"] if r["best_with_hc"] else None,
            "hc_ratio": r["best_with_hc"]["profit_to_mdd"] if r["best_with_hc"] else None,
            "profitable_configs": r["profitable_configs"],
            "total_configs": r["total_configs"],
        })
    
    summary_df = pl.DataFrame(summary_data).sort("best_profit", descending=True)
    print(summary_df)
    
    summary_csv_path = OUTPUT_DIR / "multi_asset_1h_results.csv"
    summary_df.write_csv(summary_csv_path)
    print(f"\nResults saved to: {summary_csv_path}")
    
    json_path = OUTPUT_DIR / "multi_asset_1h_details.json"
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"Details saved to: {json_path}")
    
    return all_results


if __name__ == "__main__":
    run_multi_asset_study()
