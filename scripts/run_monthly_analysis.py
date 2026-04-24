"""
Monthly Returns Analysis for L-Shape Long Strategy

Generates monthly breakdown of returns, win rates, and trade statistics.
"""

import json
from datetime import datetime
from pathlib import Path

import polars as pl

from crypto_backtest.data_loader import BacktestConfig, load_hourly_data
from crypto_backtest.long_strategy import LongBacktestEngine, LongStrategyConfig


def run_monthly_analysis(
    data_path: Path,
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    config_overrides: dict | None = None,
) -> dict:
    """Run backtest and aggregate results by month."""
    
    default_config = {
        "breakout_ma": 50,
        "consolidation_bars": 5,
        "consolidation_range_pct": 3.0,
        "drop_threshold_pct": 3.0,
        "take_profit_pct": 10.0,
        "stop_loss_pct": 3.0,
        "half_close_enabled": True,
        "half_close_pct": 5.0,
    }
    
    if config_overrides:
        default_config.update(config_overrides)
    
    config = LongStrategyConfig(
        data_path=data_path,
        symbol=symbol,
        timeframe=timeframe,
        **default_config,
    )
    
    backtest_config = BacktestConfig(
        data_path=data_path,
        symbol=symbol,
        timeframe=timeframe,
    )
    
    if timeframe == "1h":
        data = load_hourly_data(backtest_config)
    else:
        from crypto_backtest.data_loader import load_timeframe_data
        data = load_timeframe_data(backtest_config)
    
    engine = LongBacktestEngine(config)
    engine.run(data)
    trades_df = engine.get_trades_df()
    
    if trades_df.is_empty():
        return {"error": "No trades generated"}
    
    trades_df = trades_df.with_columns([
        pl.col("open_time").dt.year().alias("year"),
        pl.col("open_time").dt.month().alias("month"),
        pl.col("open_time").dt.strftime("%Y-%m").alias("year_month"),
    ])
    
    monthly_stats = (
        trades_df.group_by("year_month")
        .agg([
            pl.col("profit_pct").sum().alias("total_profit"),
            pl.col("profit_pct").count().alias("trades"),
            (pl.col("profit_pct") > 0).sum().alias("wins"),
            (pl.col("profit_pct") <= 0).sum().alias("losses"),
            pl.col("profit_pct").mean().alias("avg_profit"),
            pl.col("profit_pct").max().alias("best_trade"),
            pl.col("profit_pct").min().alias("worst_trade"),
        ])
        .sort("year_month")
    )
    
    monthly_stats = monthly_stats.with_columns([
        (pl.col("wins") / pl.col("trades") * 100).alias("win_rate"),
    ])
    
    yearly_stats = (
        trades_df.with_columns([
            pl.col("open_time").dt.year().alias("year"),
        ])
        .group_by("year")
        .agg([
            pl.col("profit_pct").sum().alias("total_profit"),
            pl.col("profit_pct").count().alias("trades"),
            (pl.col("profit_pct") > 0).sum().alias("wins"),
            pl.col("profit_pct").mean().alias("avg_profit"),
        ])
        .sort("year")
    )
    
    yearly_stats = yearly_stats.with_columns([
        (pl.col("wins") / pl.col("trades") * 100).alias("win_rate"),
    ])
    
    cumulative = trades_df.sort("open_time").select([
        "open_time",
        "profit_pct",
        pl.col("profit_pct").cum_sum().alias("cumulative_profit"),
    ])
    
    peak = 0.0
    max_dd = 0.0
    for row in cumulative.iter_rows(named=True):
        cum = row["cumulative_profit"]
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    
    total_profit = trades_df.select(pl.col("profit_pct").sum()).item()
    total_trades = len(trades_df)
    win_trades = trades_df.filter(pl.col("profit_pct") > 0).height
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "config": default_config,
        "summary": {
            "total_profit": round(total_profit, 2),
            "max_drawdown": round(max_dd, 2),
            "profit_to_mdd": round(total_profit / max_dd, 2) if max_dd > 0 else 0,
            "total_trades": total_trades,
            "win_rate": round(win_trades / total_trades * 100, 2),
        },
        "monthly": monthly_stats.to_dicts(),
        "yearly": yearly_stats.to_dicts(),
    }


def analyze_detection_quality(
    data_path: Path,
    symbol: str = "BTCUSDT",
) -> dict:
    """Analyze L-shape pattern detection quality."""
    
    config = LongStrategyConfig(
        data_path=data_path,
        symbol=symbol,
        breakout_ma=50,
        consolidation_bars=5,
        consolidation_range_pct=3.0,
        drop_threshold_pct=3.0,
        take_profit_pct=10.0,
        stop_loss_pct=3.0,
        half_close_enabled=True,
        half_close_pct=5.0,
    )
    
    backtest_config = BacktestConfig(data_path=data_path, symbol=symbol)
    data = load_hourly_data(backtest_config)
    
    engine = LongBacktestEngine(config)
    engine.run(data)
    trades_df = engine.get_trades_df()
    
    if trades_df.is_empty():
        return {"error": "No trades"}
    
    tp_trades = trades_df.filter(pl.col("result") == "TP")
    sl_trades = trades_df.filter(pl.col("result") == "SL")
    
    total = len(trades_df)
    tp_count = len(tp_trades)
    sl_count = len(sl_trades)
    
    tp_profits = tp_trades.select(pl.col("profit_pct").sum()).item() if len(tp_trades) > 0 else 0
    sl_losses = abs(sl_trades.select(pl.col("profit_pct").sum()).item()) if len(sl_trades) > 0 else 0
    
    profit_factor = tp_profits / sl_losses if sl_losses > 0 else float('inf')
    
    half_closed = trades_df.filter(pl.col("half_closed") == True)
    half_closed_wins = half_closed.filter(pl.col("profit_pct") > 0).height
    
    return {
        "symbol": symbol,
        "total_signals": total,
        "take_profit": {
            "count": tp_count,
            "rate": round(tp_count / total * 100, 2),
            "total_profit": round(tp_profits, 2),
        },
        "stop_loss": {
            "count": sl_count,
            "rate": round(sl_count / total * 100, 2),
            "total_loss": round(sl_losses, 2),
        },
        "profit_factor": round(profit_factor, 2),
        "half_close": {
            "triggered": len(half_closed),
            "win_rate": round(half_closed_wins / len(half_closed) * 100, 2) if len(half_closed) > 0 else 0,
        },
        "signal_quality": {
            "precision": round(tp_count / total * 100, 2),
            "avg_win": round(tp_trades.select(pl.col("profit_pct").mean()).item(), 2) if len(tp_trades) > 0 else 0,
            "avg_loss": round(sl_trades.select(pl.col("profit_pct").mean()).item(), 2) if len(sl_trades) > 0 else 0,
        },
    }


def run_multi_symbol_monthly(
    data_path: Path,
    symbols: list[str],
) -> list[dict]:
    """Run monthly analysis for multiple symbols."""
    results = []
    for symbol in symbols:
        try:
            result = run_monthly_analysis(data_path, symbol)
            results.append(result)
        except Exception as e:
            results.append({"symbol": symbol, "error": str(e)})
    return results


def load_parquet_data(data_path: Path, symbol: str) -> pl.DataFrame:
    """Load data from hive-partitioned parquet files."""
    symbol_path = data_path / symbol
    
    df = pl.scan_parquet(
        str(symbol_path / "**/*.parquet"),
        hive_partitioning=True,
    ).collect()
    
    if "open_time" in df.columns:
        df = df.with_columns(
            pl.from_epoch("open_time", time_unit="ms").alias("datetime")
        )
    elif "datetime" not in df.columns:
        raise ValueError("No datetime column found")
    
    df = df.sort("datetime")
    
    for ma in [25, 50, 100, 200]:
        df = df.with_columns(
            pl.col("close").rolling_mean(window_size=ma).alias(f"ma_{ma}")
        )
    
    return df


def run_monthly_analysis_parquet(
    data_path: Path,
    symbol: str = "BTCUSDT",
    config_overrides: dict | None = None,
) -> dict:
    """Run backtest using parquet data and aggregate results by month."""
    
    default_config = {
        "breakout_ma": 50,
        "consolidation_bars": 5,
        "consolidation_range_pct": 3.0,
        "drop_threshold_pct": 3.0,
        "take_profit_pct": 10.0,
        "stop_loss_pct": 3.0,
        "half_close_enabled": True,
        "half_close_pct": 5.0,
    }
    
    if config_overrides:
        default_config.update(config_overrides)
    
    config = LongStrategyConfig(
        data_path=data_path,
        symbol=symbol,
        **default_config,
    )
    
    data = load_parquet_data(data_path, symbol)
    
    hourly = (
        data.group_by_dynamic("datetime", every="1h")
        .agg([
            pl.col("open").first(),
            pl.col("high").max(),
            pl.col("low").min(),
            pl.col("close").last(),
            pl.col("volume").sum(),
        ])
    )
    
    for ma in [25, 50, 100, 200]:
        hourly = hourly.with_columns(
            pl.col("close").rolling_mean(window_size=ma).alias(f"ma_{ma}")
        )
    
    engine = LongBacktestEngine(config)
    engine.run(hourly)
    trades_df = engine.get_trades_df()
    
    if trades_df.is_empty():
        return {"error": "No trades generated", "symbol": symbol}
    
    trades_df = trades_df.with_columns([
        pl.col("open_time").dt.year().alias("year"),
        pl.col("open_time").dt.month().alias("month"),
        pl.col("open_time").dt.strftime("%Y-%m").alias("year_month"),
    ])
    
    monthly_stats = (
        trades_df.group_by("year_month")
        .agg([
            pl.col("profit_pct").sum().alias("total_profit"),
            pl.col("profit_pct").count().alias("trades"),
            (pl.col("profit_pct") > 0).sum().alias("wins"),
            (pl.col("profit_pct") <= 0).sum().alias("losses"),
            pl.col("profit_pct").mean().alias("avg_profit"),
            pl.col("profit_pct").max().alias("best_trade"),
            pl.col("profit_pct").min().alias("worst_trade"),
        ])
        .sort("year_month")
    )
    
    monthly_stats = monthly_stats.with_columns([
        (pl.col("wins") / pl.col("trades") * 100).alias("win_rate"),
    ])
    
    yearly_stats = (
        trades_df.group_by("year")
        .agg([
            pl.col("profit_pct").sum().alias("total_profit"),
            pl.col("profit_pct").count().alias("trades"),
            (pl.col("profit_pct") > 0).sum().alias("wins"),
            pl.col("profit_pct").mean().alias("avg_profit"),
        ])
        .sort("year")
    )
    
    yearly_stats = yearly_stats.with_columns([
        (pl.col("wins") / pl.col("trades") * 100).alias("win_rate"),
    ])
    
    cumulative = trades_df.sort("open_time").select([
        "open_time",
        "profit_pct",
        pl.col("profit_pct").cum_sum().alias("cumulative_profit"),
    ])
    
    peak = 0.0
    max_dd = 0.0
    for row in cumulative.iter_rows(named=True):
        cum = row["cumulative_profit"]
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    
    total_profit = trades_df.select(pl.col("profit_pct").sum()).item()
    total_trades = len(trades_df)
    win_trades = trades_df.filter(pl.col("profit_pct") > 0).height
    
    tp_trades = trades_df.filter(pl.col("result") == "TP")
    sl_trades = trades_df.filter(pl.col("result") == "SL")
    tp_sum = tp_trades.select(pl.col("profit_pct").sum()).item() if len(tp_trades) > 0 else 0
    sl_sum = abs(sl_trades.select(pl.col("profit_pct").sum()).item()) if len(sl_trades) > 0 else 0
    profit_factor = tp_sum / sl_sum if sl_sum > 0 else 0
    
    return {
        "symbol": symbol,
        "config": default_config,
        "summary": {
            "total_profit": round(total_profit, 2),
            "max_drawdown": round(max_dd, 2),
            "profit_to_mdd": round(total_profit / max_dd, 2) if max_dd > 0 else 0,
            "total_trades": total_trades,
            "win_rate": round(win_trades / total_trades * 100, 2),
            "profit_factor": round(profit_factor, 2),
        },
        "monthly": monthly_stats.to_dicts(),
        "yearly": yearly_stats.to_dicts(),
    }


if __name__ == "__main__":
    data_path = Path("/mnt/data/finance/cryptocurrency")
    
    symbols = ["BTCUSDT", "ETHUSDT"]
    
    all_results = {}
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Analyzing {symbol}")
        print('='*60)
        
        try:
            monthly = run_monthly_analysis_parquet(data_path, symbol)
            all_results[symbol] = monthly
            
            print(f"\nSummary for {symbol}:")
            print(f"  Total Profit: {monthly['summary']['total_profit']}%")
            print(f"  Max Drawdown: {monthly['summary']['max_drawdown']}%")
            print(f"  Profit/MDD: {monthly['summary']['profit_to_mdd']}")
            print(f"  Win Rate: {monthly['summary']['win_rate']}%")
            print(f"  Total Trades: {monthly['summary']['total_trades']}")
            print(f"  Profit Factor: {monthly['summary']['profit_factor']}")
            
            print(f"\nYearly Breakdown:")
            for yr in monthly['yearly']:
                print(f"  {yr['year']}: {yr['total_profit']:.1f}% ({yr['trades']} trades, {yr['win_rate']:.1f}% WR)")
                
        except Exception as e:
            print(f"  Error: {e}")
            all_results[symbol] = {"error": str(e)}
    
    output_path = Path("docs/monthly_analysis_results.json")
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nResults saved to {output_path}")
