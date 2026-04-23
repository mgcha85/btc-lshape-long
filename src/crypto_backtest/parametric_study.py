import itertools
from dataclasses import dataclass
from pathlib import Path

import polars as pl
from tqdm import tqdm

from .backtest_engine import BacktestEngine
from .data_loader import BacktestConfig, load_hourly_data
from .storage import calculate_stats


@dataclass
class ParameterSet:
    resistance_ma: int
    half_close_pct: float
    take_profit_pct: float
    stop_loss_pct: float


@dataclass
class StudyResult:
    params: ParameterSet
    total_trades: int
    win_rate: float
    total_profit_pct: float
    avg_profit_pct: float
    max_drawdown_pct: float
    profit_factor: float
    sl_rate: float


def run_parametric_study(
    data_path: Path,
    symbol: str = "BTCUSDT",
    ma_periods: list[int] | None = None,
    half_close_pcts: list[float] | None = None,
    take_profit_pcts: list[float] | None = None,
    stop_loss_pcts: list[float] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[StudyResult]:
    if ma_periods is None:
        ma_periods = [25, 50, 100, 200]
    if half_close_pcts is None:
        half_close_pcts = [0.5, 1.0, 1.5]
    if take_profit_pcts is None:
        take_profit_pcts = [1.5, 2.0, 2.5, 3.0]
    if stop_loss_pcts is None:
        stop_loss_pcts = [1.0, 1.5, 2.0, 2.5]
    
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
        half_close_pcts,
        take_profit_pcts,
        stop_loss_pcts,
    ))
    
    print(f"Running {len(combinations)} parameter combinations...")
    
    results = []
    
    for ma, half, tp, sl in tqdm(combinations, desc="Backtesting"):
        config = BacktestConfig(
            data_path=data_path,
            symbol=symbol,
            ma_periods=all_ma_periods,
            resistance_ma=ma,
            half_close_pct=half,
            take_profit_pct=tp,
            stop_loss_pct=sl,
            start_date=start_date,
            end_date=end_date,
        )
        
        engine = BacktestEngine(config)
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
        
        result = StudyResult(
            params=ParameterSet(ma, half, tp, sl),
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


def analyze_results(results: list[StudyResult]) -> pl.DataFrame:
    data = []
    for r in results:
        data.append({
            "ma": r.params.resistance_ma,
            "half_close": r.params.half_close_pct,
            "take_profit": r.params.take_profit_pct,
            "stop_loss": r.params.stop_loss_pct,
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


def print_top_results(df: pl.DataFrame, top_n: int = 20) -> None:
    print(f"\n{'='*80}")
    print(f"TOP {top_n} PARAMETER COMBINATIONS BY TOTAL PROFIT")
    print(f"{'='*80}\n")
    
    top = df.head(top_n)
    print(top)
    
    print(f"\n{'='*80}")
    print("BEST BY METRIC")
    print(f"{'='*80}\n")
    
    best_profit = df.sort("total_profit", descending=True).head(1)
    print("Best Total Profit:")
    print(best_profit)
    
    profitable = df.filter(pl.col("total_profit") > 0)
    if not profitable.is_empty():
        best_pf = profitable.sort("profit_factor", descending=True).head(1)
        print("\nBest Profit Factor (among profitable):")
        print(best_pf)
        
        best_wr = profitable.sort("win_rate", descending=True).head(1)
        print("\nBest Win Rate (among profitable):")
        print(best_wr)
    
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}\n")
    
    profitable_count = df.filter(pl.col("total_profit") > 0).height
    total_count = len(df)
    print(f"Profitable combinations: {profitable_count}/{total_count} ({profitable_count/total_count*100:.1f}%)")
    
    if profitable_count > 0:
        avg_profit_profitable = df.filter(pl.col("total_profit") > 0)["total_profit"].mean()
        print(f"Avg profit (profitable only): {avg_profit_profitable:.2f}%")
    
    print(f"\nBy MA period:")
    ma_summary = df.group_by("ma").agg([
        pl.col("total_profit").mean().alias("avg_profit"),
        pl.col("trades").mean().alias("avg_trades"),
        (pl.col("total_profit") > 0).sum().alias("profitable_count"),
    ]).sort("avg_profit", descending=True)
    print(ma_summary)


def generate_heatmap_data(df: pl.DataFrame) -> dict:
    heatmaps = {}
    
    for ma in df["ma"].unique().to_list():
        ma_df = df.filter(pl.col("ma") == ma)
        
        pivot_data = {}
        for row in ma_df.to_dicts():
            key = (row["take_profit"], row["stop_loss"])
            if key not in pivot_data:
                pivot_data[key] = []
            pivot_data[key].append(row["total_profit"])
        
        heatmaps[ma] = pivot_data
    
    return heatmaps
