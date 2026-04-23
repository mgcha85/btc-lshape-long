from dataclasses import dataclass, field
from pathlib import Path

import polars as pl


MA_PERIODS = [25, 50, 100, 200, 400]


@dataclass
class BacktestConfig:
    data_path: Path
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    
    ma_periods: list[int] = field(default_factory=lambda: MA_PERIODS.copy())
    resistance_ma: int = 25
    half_close_pct: float = 1.0
    breakeven_after_half: bool = True
    take_profit_pct: float = 2.0
    stop_loss_pct: float = 2.0
    
    start_date: str | None = None
    end_date: str | None = None


BINANCE_KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "num_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]


def load_minute_data(data_path: Path, symbol: str = "BTCUSDT") -> pl.LazyFrame:
    import glob
    
    pattern = str(data_path / symbol / "1m" / "**" / "*.csv")
    files = sorted(glob.glob(pattern, recursive=True))
    
    if not files:
        raise FileNotFoundError(f"No CSV files found matching {pattern}")
    
    frames = []
    for f in files:
        with open(f, "r") as fp:
            first_line = fp.readline()
        
        has_header = first_line.startswith("open_time")
        
        try:
            df = pl.read_csv(
                f,
                has_header=has_header,
                new_columns=None if has_header else BINANCE_KLINE_COLUMNS,
                schema_overrides={
                    "open_time": pl.Int64,
                    "open": pl.Float64,
                    "high": pl.Float64,
                    "low": pl.Float64,
                    "close": pl.Float64,
                    "volume": pl.Float64,
                    "close_time": pl.Int64,
                    "quote_volume": pl.Float64,
                    "ignore": pl.Int64,
                },
                ignore_errors=True,
            )
            
            if "count" in df.columns:
                df = df.rename({"count": "num_trades"})
            if "taker_buy_volume" in df.columns:
                df = df.rename({"taker_buy_volume": "taker_buy_base_volume"})
            
            df = df.select([c for c in BINANCE_KLINE_COLUMNS if c in df.columns])
            frames.append(df)
        except Exception:
            continue
    
    if not frames:
        raise ValueError("No valid data loaded")
    
    combined = pl.concat(frames)
    return combined.lazy()


def resample_to_hourly(df: pl.LazyFrame) -> pl.LazyFrame:
    return (
        df.with_columns(
            pl.from_epoch("open_time", time_unit="ms").alias("datetime"),
        )
        .with_columns(
            pl.col("datetime").dt.truncate("1h").alias("hour"),
        )
        .group_by("hour")
        .agg(
            pl.col("open").first().alias("open"),
            pl.col("high").max().alias("high"),
            pl.col("low").min().alias("low"),
            pl.col("close").last().alias("close"),
            pl.col("volume").sum().alias("volume"),
            pl.col("quote_volume").sum().alias("quote_volume"),
            pl.col("num_trades").sum().alias("num_trades"),
        )
        .sort("hour")
        .rename({"hour": "datetime"})
    )


def resample_to_5min(df: pl.LazyFrame) -> pl.LazyFrame:
    return (
        df.with_columns(
            pl.from_epoch("open_time", time_unit="ms").alias("datetime"),
        )
        .with_columns(
            pl.col("datetime").dt.truncate("5m").alias("bar"),
        )
        .group_by("bar")
        .agg(
            pl.col("open").first().alias("open"),
            pl.col("high").max().alias("high"),
            pl.col("low").min().alias("low"),
            pl.col("close").last().alias("close"),
            pl.col("volume").sum().alias("volume"),
            pl.col("quote_volume").sum().alias("quote_volume"),
            pl.col("num_trades").sum().alias("num_trades"),
        )
        .sort("bar")
        .rename({"bar": "datetime"})
    )


def add_indicators(df: pl.LazyFrame, ma_periods: list[int] | None = None) -> pl.LazyFrame:
    if ma_periods is None:
        ma_periods = MA_PERIODS
    
    ma_columns = [
        pl.col("close").rolling_mean(window_size=period).alias(f"ma_{period}")
        for period in ma_periods
    ]
    
    return df.with_columns(
        *ma_columns,
        pl.col("close").shift(1).alias("prev_close"),
        pl.col("high").shift(1).alias("prev_high"),
        pl.col("low").shift(1).alias("prev_low"),
    )


def load_hourly_data(config: BacktestConfig) -> pl.DataFrame:
    minute_data = load_minute_data(config.data_path, config.symbol)
    hourly_data = resample_to_hourly(minute_data)
    with_indicators = add_indicators(hourly_data, config.ma_periods)
    
    result = with_indicators.collect()
    
    if config.start_date:
        result = result.filter(pl.col("datetime") >= pl.lit(config.start_date).str.to_datetime())
    if config.end_date:
        result = result.filter(pl.col("datetime") <= pl.lit(config.end_date).str.to_datetime())
    
    return result


def load_5min_data(config: BacktestConfig) -> pl.DataFrame:
    minute_data = load_minute_data(config.data_path, config.symbol)
    data_5m = resample_to_5min(minute_data)
    with_indicators = add_indicators(data_5m, config.ma_periods)
    
    result = with_indicators.collect()
    
    if config.start_date:
        result = result.filter(pl.col("datetime") >= pl.lit(config.start_date).str.to_datetime())
    if config.end_date:
        result = result.filter(pl.col("datetime") <= pl.lit(config.end_date).str.to_datetime())
    
    return result


def load_parquet_data(data_path: Path, symbol: str = "BTCUSDT") -> pl.LazyFrame:
    """Load 1-minute data from hive-partitioned parquet files."""
    parquet_path = data_path / symbol
    
    if not parquet_path.exists():
        raise FileNotFoundError(f"No parquet data found at {parquet_path}")
    
    df = pl.scan_parquet(
        str(parquet_path / "**/*.parquet"),
        hive_partitioning=True,
    )
    
    return df


def resample_to_15min(df: pl.LazyFrame) -> pl.LazyFrame:
    return (
        df.with_columns(
            (pl.col("open_time") * 1000).cast(pl.Datetime("us")).alias("datetime"),
        )
        .with_columns(
            pl.col("datetime").dt.truncate("15m").alias("bar"),
        )
        .group_by("bar")
        .agg(
            pl.col("open").first().alias("open"),
            pl.col("high").max().alias("high"),
            pl.col("low").min().alias("low"),
            pl.col("close").last().alias("close"),
            pl.col("volume").sum().alias("volume"),
            pl.col("quote_volume").sum().alias("quote_volume"),
            pl.col("trades").sum().alias("num_trades"),
        )
        .sort("bar")
        .rename({"bar": "datetime"})
    )


def resample_to_4h(df: pl.LazyFrame) -> pl.LazyFrame:
    return (
        df.with_columns(
            (pl.col("open_time") * 1000).cast(pl.Datetime("us")).alias("datetime"),
        )
        .with_columns(
            pl.col("datetime").dt.truncate("4h").alias("bar"),
        )
        .group_by("bar")
        .agg(
            pl.col("open").first().alias("open"),
            pl.col("high").max().alias("high"),
            pl.col("low").min().alias("low"),
            pl.col("close").last().alias("close"),
            pl.col("volume").sum().alias("volume"),
            pl.col("quote_volume").sum().alias("quote_volume"),
            pl.col("trades").sum().alias("num_trades"),
        )
        .sort("bar")
        .rename({"bar": "datetime"})
    )


def load_15min_data(config: BacktestConfig) -> pl.DataFrame:
    """Load and resample data to 15-minute bars from parquet."""
    minute_data = load_parquet_data(config.data_path, config.symbol)
    data_15m = resample_to_15min(minute_data)
    with_indicators = add_indicators(data_15m, config.ma_periods)
    
    result = with_indicators.collect()
    
    if config.start_date:
        result = result.filter(pl.col("datetime") >= pl.lit(config.start_date).str.to_datetime())
    if config.end_date:
        result = result.filter(pl.col("datetime") <= pl.lit(config.end_date).str.to_datetime())
    
    return result


def load_4h_data(config: BacktestConfig) -> pl.DataFrame:
    """Load and resample data to 4-hour bars from parquet."""
    minute_data = load_parquet_data(config.data_path, config.symbol)
    data_4h = resample_to_4h(minute_data)
    with_indicators = add_indicators(data_4h, config.ma_periods)
    
    result = with_indicators.collect()
    
    if config.start_date:
        result = result.filter(pl.col("datetime") >= pl.lit(config.start_date).str.to_datetime())
    if config.end_date:
        result = result.filter(pl.col("datetime") <= pl.lit(config.end_date).str.to_datetime())
    
    return result
