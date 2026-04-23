#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import polars as pl
from tqdm import tqdm
import itertools

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_backtest.data_loader import BacktestConfig, load_15min_data
from crypto_backtest.long_strategy import LongStrategyConfig, LongBacktestEngine
from crypto_backtest.storage import calculate_stats

DATA_PATH = Path("/mnt/data/finance/cryptocurrency")
OUTPUT_DIR = Path(__file__).parent.parent / "docs"


def run_parametric_study():
    print("=" * 60)
    print("15분봉 Parametric Study")
    print("=" * 60)
    
    ma_periods = [25, 50, 100]
    consolidation_bars_list = [4, 8, 12]
    consolidation_range_list = [2.0, 3.0, 4.0]
    drop_threshold_list = [2.0, 3.0, 4.0]
    take_profit_pcts = [3.0, 5.0, 7.0]
    stop_loss_pcts = [1.5, 2.0, 3.0]
    
    all_ma_periods = list(set(ma_periods + [25, 50, 100, 200, 400]))
    
    print("\n[1/3] Loading 15-minute data...")
    config = BacktestConfig(
        data_path=DATA_PATH,
        symbol="BTCUSDT",
        timeframe="15m",
        ma_periods=all_ma_periods,
    )
    data = load_15min_data(config)
    print(f"  Loaded {len(data):,} candles")
    print(f"  Date range: {data['datetime'].min()} to {data['datetime'].max()}")
    
    combinations = list(itertools.product(
        ma_periods,
        consolidation_bars_list,
        consolidation_range_list,
        drop_threshold_list,
        take_profit_pcts,
        stop_loss_pcts,
    ))
    
    print(f"\n[2/3] Running {len(combinations)} parameter combinations...")
    
    results = []
    
    for ma, cons_bars, cons_range, drop_thresh, tp, sl in tqdm(combinations, desc="Backtesting"):
        strategy_config = LongStrategyConfig(
            data_path=DATA_PATH,
            symbol="BTCUSDT",
            timeframe="15m",
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
        
        sl_count = trades_df.filter(pl.col("is_sl") == True).height
        sl_rate = sl_count / len(trades_df) * 100 if len(trades_df) > 0 else 0
        
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
            "avg_profit": stats["avg_profit_pct"],
            "max_dd": stats["max_drawdown_pct"],
            "profit_factor": profit_factor,
            "sl_rate": sl_rate,
        })
    
    print(f"\n[3/3] Analyzing results...")
    
    df = pl.DataFrame(results).sort("total_profit", descending=True)
    
    print("\n" + "=" * 60)
    print("TOP 20 PARAMETER COMBINATIONS (By Total Profit)")
    print("=" * 60)
    print(df.head(20))
    
    csv_path = OUTPUT_DIR / "15min_parametric_results.csv"
    df.write_csv(csv_path)
    print(f"\nResults saved to: {csv_path}")
    
    print("\n" + "=" * 60)
    print("ANALYSIS BY MA PERIOD")
    print("=" * 60)
    ma_summary = df.group_by("ma").agg([
        pl.col("total_profit").mean().alias("avg_profit"),
        pl.col("trades").mean().alias("avg_trades"),
        pl.col("max_dd").mean().alias("avg_mdd"),
        (pl.col("total_profit") > 0).sum().alias("profitable_count"),
        pl.len().alias("total_configs"),
    ]).sort("avg_profit", descending=True)
    print(ma_summary)
    
    print("\n" + "=" * 60)
    print("ANALYSIS BY TP/SL")
    print("=" * 60)
    tpsl_summary = df.group_by(["take_profit", "stop_loss"]).agg([
        pl.col("total_profit").mean().alias("avg_profit"),
        pl.col("win_rate").mean().alias("avg_win_rate"),
        pl.col("max_dd").mean().alias("avg_mdd"),
    ]).sort("avg_profit", descending=True)
    print(tpsl_summary)
    
    profitable = df.filter(pl.col("total_profit") > 0)
    print(f"\nProfitable configs: {len(profitable)}/{len(df)} ({len(profitable)/len(df)*100:.1f}%)")
    
    if len(profitable) > 0:
        best = df.head(1).to_dicts()[0]
        print(f"\nBest configuration:")
        print(f"  MA: {best['ma']}")
        print(f"  Consolidation: {best['cons_bars']} bars, {best['cons_range']}% range")
        print(f"  Drop threshold: {best['drop_thresh']}%")
        print(f"  TP/SL: {best['take_profit']}% / {best['stop_loss']}%")
        print(f"  Total profit: {best['total_profit']:.2f}%")
        print(f"  Win rate: {best['win_rate']:.2f}%")
        print(f"  Max DD: {best['max_dd']:.2f}%")
        print(f"  Profit factor: {best['profit_factor']:.2f}")
        print(f"  Trades: {best['trades']}")
    
    return df


def run_half_close_study(best_config: dict):
    print("\n" + "=" * 60)
    print("HALF CLOSE STUDY")
    print("=" * 60)
    
    config = BacktestConfig(
        data_path=DATA_PATH,
        symbol="BTCUSDT",
        timeframe="15m",
        ma_periods=[25, 50, 100, 200, 400],
    )
    data = load_15min_data(config)
    
    half_close_pcts = [1.0, 2.0, 3.0]
    
    results = []
    
    for hc in half_close_pcts:
        strategy_config = LongStrategyConfig(
            data_path=DATA_PATH,
            symbol="BTCUSDT",
            timeframe="15m",
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
        
        winning = [p for p in trades_df["profit_pct"].to_list() if p > 0]
        losing = [p for p in trades_df["profit_pct"].to_list() if p <= 0]
        profit_factor = abs(sum(winning) / sum(losing)) if losing and sum(losing) != 0 else float("inf")
        
        results.append({
            "half_close_pct": hc,
            "trades": stats["total_trades"],
            "win_rate": stats["win_rate"],
            "total_profit": stats["total_profit_pct"],
            "max_dd": stats["max_drawdown_pct"],
            "profit_factor": profit_factor,
            "profit_to_mdd": stats["total_profit_pct"] / stats["max_drawdown_pct"] if stats["max_drawdown_pct"] > 0 else float("inf"),
        })
    
    hc_df = pl.DataFrame(results)
    print(hc_df)
    
    hc_csv_path = OUTPUT_DIR / "15min_half_close_results.csv"
    hc_df.write_csv(hc_csv_path)
    print(f"\nHalf close results saved to: {hc_csv_path}")
    
    return hc_df


if __name__ == "__main__":
    results_df = run_parametric_study()
    
    if len(results_df) > 0:
        best = results_df.head(1).to_dicts()[0]
        run_half_close_study(best)
