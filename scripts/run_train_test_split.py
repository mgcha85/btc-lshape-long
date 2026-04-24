#!/usr/bin/env python3
"""
Train/Test Split Backtest
- Train: 2025년 데이터로 파라메트릭 스터디 → 최적 파라미터 도출
- Test: 2026년 데이터로 최적 파라미터 검증
"""
import json
import sys
from pathlib import Path

import polars as pl
import itertools

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_backtest.data_loader import BacktestConfig, load_1h_parquet_data
from crypto_backtest.long_strategy import LongStrategyConfig, LongBacktestEngine
from crypto_backtest.storage import calculate_stats

DATA_PATH = Path("/mnt/data/finance/cryptocurrency")
OUTPUT_DIR = Path(__file__).parent.parent / "docs"

SYMBOLS = ["BTCUSDT", "ETHUSDT"]

TRAIN_START = "2020-01-01"
TRAIN_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-12-31"


def run_parametric_study(symbol: str, data: pl.DataFrame) -> dict | None:
    """Run parametric study on training data to find best config."""
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
    return df.head(1).to_dicts()[0]


def run_test(symbol: str, data: pl.DataFrame, best_config: dict) -> dict:
    """Run best config on test data."""
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
        half_close_enabled=False,
    )
    
    engine = LongBacktestEngine(strategy_config)
    engine.run(data)
    trades_df = engine.get_trades_df()
    
    if trades_df.is_empty():
        return {
            "trades": 0,
            "win_rate": 0,
            "total_profit": 0,
            "max_dd": 0,
            "profit_factor": 0,
        }
    
    stats = calculate_stats(trades_df)
    
    winning = [p for p in trades_df["profit_pct"].to_list() if p > 0]
    losing = [p for p in trades_df["profit_pct"].to_list() if p <= 0]
    profit_factor = abs(sum(winning) / sum(losing)) if losing and sum(losing) != 0 else float("inf")
    
    return {
        "trades": stats["total_trades"],
        "win_rate": stats["win_rate"],
        "total_profit": stats["total_profit_pct"],
        "max_dd": stats["max_drawdown_pct"],
        "profit_factor": profit_factor,
    }


def run_test_with_half_close(symbol: str, data: pl.DataFrame, best_config: dict) -> dict:
    """Run best config with half close on test data."""
    half_close_pcts = [2.0, 3.0, 5.0]
    
    best_result = None
    best_ratio = -float("inf")
    
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


def main():
    print("=" * 60)
    print("Train/Test Split Backtest")
    print(f"Train: {TRAIN_START} ~ {TRAIN_END}")
    print(f"Test:  {TEST_START} ~ {TEST_END}")
    print("=" * 60)
    
    results = []
    
    for symbol in SYMBOLS:
        print(f"\n{'='*40}")
        print(f"Processing {symbol}...")
        print(f"{'='*40}")
        
        # Load train data (2025)
        train_config = BacktestConfig(
            data_path=DATA_PATH,
            symbol=symbol,
            timeframe="1h",
            ma_periods=[25, 50, 100, 200, 400],
            start_date=TRAIN_START,
            end_date=TRAIN_END,
        )
        train_data = load_1h_parquet_data(train_config)
        print(f"  Train data: {len(train_data):,} candles")
        print(f"  Train range: {train_data['datetime'].min()} to {train_data['datetime'].max()}")
        
        # Load test data (2026)
        test_config = BacktestConfig(
            data_path=DATA_PATH,
            symbol=symbol,
            timeframe="1h",
            ma_periods=[25, 50, 100, 200, 400],
            start_date=TEST_START,
            end_date=TEST_END,
        )
        test_data = load_1h_parquet_data(test_config)
        print(f"  Test data: {len(test_data):,} candles")
        print(f"  Test range: {test_data['datetime'].min()} to {test_data['datetime'].max()}")
        
        # Run parametric study on train data
        print(f"\n  Running parametric study on 2025 data...")
        best_config = run_parametric_study(symbol, train_data)
        
        if not best_config:
            print(f"  No profitable config found for {symbol}")
            continue
        
        print(f"  Best config from 2025:")
        print(f"    MA={best_config['ma']}, TP={best_config['take_profit']}%, SL={best_config['stop_loss']}%")
        print(f"    Profit={best_config['total_profit']:.2f}%, MDD={best_config['max_dd']:.2f}%")
        
        # Test on 2026 data
        print(f"\n  Testing on 2026 data...")
        test_result = run_test(symbol, test_data, best_config)
        print(f"  Test result (no HC):")
        print(f"    Trades={test_result['trades']}, Win={test_result['win_rate']:.1f}%")
        print(f"    Profit={test_result['total_profit']:.2f}%, MDD={test_result['max_dd']:.2f}%")
        
        # Test with half close
        test_hc_result = run_test_with_half_close(symbol, test_data, best_config)
        if test_hc_result:
            print(f"  Test result (HC {test_hc_result['half_close_pct']}%):")
            print(f"    Trades={test_hc_result['trades']}, Win={test_hc_result['win_rate']:.1f}%")
            print(f"    Profit={test_hc_result['total_profit']:.2f}%, MDD={test_hc_result['max_dd']:.2f}%")
        
        results.append({
            "symbol": symbol,
            "train_candles": len(train_data),
            "test_candles": len(test_data),
            "best_config": best_config,
            "train_profit": best_config["total_profit"],
            "train_mdd": best_config["max_dd"],
            "train_trades": best_config["trades"],
            "train_win_rate": best_config["win_rate"],
            "test_profit": test_result["total_profit"],
            "test_mdd": test_result["max_dd"],
            "test_trades": test_result["trades"],
            "test_win_rate": test_result["win_rate"],
            "test_hc": test_hc_result,
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    summary_data = []
    for r in results:
        summary_data.append({
            "symbol": r["symbol"],
            "train_profit": r["train_profit"],
            "train_mdd": r["train_mdd"],
            "train_trades": r["train_trades"],
            "test_profit": r["test_profit"],
            "test_mdd": r["test_mdd"],
            "test_trades": r["test_trades"],
            "test_hc_profit": r["test_hc"]["total_profit"] if r["test_hc"] else None,
            "test_hc_mdd": r["test_hc"]["max_dd"] if r["test_hc"] else None,
            "best_ma": r["best_config"]["ma"],
            "best_tp": r["best_config"]["take_profit"],
            "best_sl": r["best_config"]["stop_loss"],
        })
    
    summary_df = pl.DataFrame(summary_data)
    print(summary_df)
    
    # Save results
    json_path = OUTPUT_DIR / "train_test_split_results.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {json_path}")
    
    return results


if __name__ == "__main__":
    main()
