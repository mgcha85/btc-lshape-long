import itertools
from dataclasses import dataclass
from pathlib import Path

import polars as pl
from tqdm import tqdm

from .data_loader import BacktestConfig, load_hourly_data
from .long_strategy import LongStrategyConfig, LongBacktestEngine
from .storage import calculate_stats


@dataclass
class LongStudyResult:
    breakout_ma: int
    consolidation_bars: int
    consolidation_range_pct: float
    drop_threshold_pct: float
    take_profit_pct: float
    stop_loss_pct: float
    total_trades: int
    win_rate: float
    total_profit_pct: float
    avg_profit_pct: float
    max_drawdown_pct: float
    profit_factor: float
    sl_rate: float


def run_long_parametric_study(
    data_path: Path,
    symbol: str = "BTCUSDT",
    ma_periods: list[int] | None = None,
    consolidation_bars_list: list[int] | None = None,
    consolidation_range_list: list[float] | None = None,
    drop_threshold_list: list[float] | None = None,
    take_profit_pcts: list[float] | None = None,
    stop_loss_pcts: list[float] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[LongStudyResult]:
    
    if ma_periods is None:
        ma_periods = [25, 50, 100]
    if consolidation_bars_list is None:
        consolidation_bars_list = [5]
    if consolidation_range_list is None:
        consolidation_range_list = [3.0, 5.0]
    if drop_threshold_list is None:
        drop_threshold_list = [5.0]
    if take_profit_pcts is None:
        take_profit_pcts = [3.0, 5.0, 7.0, 10.0]
    if stop_loss_pcts is None:
        stop_loss_pcts = [2.0, 3.0, 5.0]
    
    all_ma_periods = list(set(ma_periods + [25, 50, 100, 200, 400]))
    
    base_config = BacktestConfig(
        data_path=data_path,
        symbol=symbol,
        ma_periods=all_ma_periods,
        start_date=start_date,
        end_date=end_date,
    )
    
    print("Loading data...")
    data = load_hourly_data(base_config)
    print(f"Loaded {len(data)} candles")
    
    combinations = list(itertools.product(
        ma_periods,
        consolidation_bars_list,
        consolidation_range_list,
        drop_threshold_list,
        take_profit_pcts,
        stop_loss_pcts,
    ))
    
    print(f"Running {len(combinations)} parameter combinations...")
    
    results = []
    
    for ma, cons_bars, cons_range, drop_thresh, tp, sl in tqdm(combinations, desc="Backtesting"):
        config = LongStrategyConfig(
            data_path=data_path,
            symbol=symbol,
            breakout_ma=ma,
            consolidation_bars=cons_bars,
            consolidation_range_pct=cons_range,
            drop_threshold_pct=drop_thresh,
            take_profit_pct=tp,
            stop_loss_pct=sl,
            start_date=start_date,
            end_date=end_date,
        )
        
        engine = LongBacktestEngine(config)
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
        
        result = LongStudyResult(
            breakout_ma=ma,
            consolidation_bars=cons_bars,
            consolidation_range_pct=cons_range,
            drop_threshold_pct=drop_thresh,
            take_profit_pct=tp,
            stop_loss_pct=sl,
            total_trades=stats["total_trades"],
            win_rate=stats["win_rate"],
            total_profit_pct=stats["total_profit_pct"],
            avg_profit_pct=stats["avg_profit_pct"],
            max_drawdown_pct=stats["max_drawdown_pct"],
            profit_factor=profit_factor,
            sl_rate=sl_rate,
        )
        results.append(result)
    
    return results


def analyze_long_results(results: list[LongStudyResult]) -> pl.DataFrame:
    data = []
    for r in results:
        data.append({
            "ma": r.breakout_ma,
            "cons_bars": r.consolidation_bars,
            "cons_range": r.consolidation_range_pct,
            "drop_thresh": r.drop_threshold_pct,
            "take_profit": r.take_profit_pct,
            "stop_loss": r.stop_loss_pct,
            "trades": r.total_trades,
            "win_rate": r.win_rate,
            "total_profit": r.total_profit_pct,
            "avg_profit": r.avg_profit_pct,
            "max_dd": r.max_drawdown_pct,
            "profit_factor": r.profit_factor,
            "sl_rate": r.sl_rate,
        })
    
    df = pl.DataFrame(data)
    return df.sort("total_profit", descending=True)


def print_long_top_results(df: pl.DataFrame, top_n: int = 20) -> None:
    print(f"\n{'='*100}")
    print(f"TOP {top_n} PARAMETER COMBINATIONS BY TOTAL PROFIT")
    print(f"{'='*100}\n")
    
    top = df.head(top_n)
    print(top)
    
    print(f"\n{'='*100}")
    print("SUMMARY STATISTICS")
    print(f"{'='*100}\n")
    
    profitable_count = df.filter(pl.col("total_profit") > 0).height
    total_count = len(df)
    print(f"Profitable combinations: {profitable_count}/{total_count} ({profitable_count/total_count*100:.1f}%)")
    
    if profitable_count > 0:
        profitable = df.filter(pl.col("total_profit") > 0)
        avg_profit_profitable = profitable["total_profit"].mean()
        print(f"Avg profit (profitable only): {avg_profit_profitable:.2f}%")
        
        best = profitable.head(1).to_dicts()[0]
        print(f"\nBest config:")
        print(f"  MA: {best['ma']}, TP: {best['take_profit']}%, SL: {best['stop_loss']}%")
        print(f"  Total profit: {best['total_profit']:.2f}%")
        print(f"  Win rate: {best['win_rate']:.2f}%")
        print(f"  Profit factor: {best['profit_factor']:.2f}")
    
    print(f"\nBy MA period:")
    ma_summary = df.group_by("ma").agg([
        pl.col("total_profit").mean().alias("avg_profit"),
        pl.col("trades").mean().alias("avg_trades"),
        (pl.col("total_profit") > 0).sum().alias("profitable_count"),
    ]).sort("avg_profit", descending=True)
    print(ma_summary)
