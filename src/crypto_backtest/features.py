import json
from dataclasses import dataclass

import numpy as np
import polars as pl


@dataclass
class FeatureConfig:
    lookback_window: int = 20
    ma_periods: list[int] | None = None
    rsi_period: int = 14
    atr_period: int = 14
    bb_period: int = 20
    bb_std: float = 2.0


def compute_rsi(close: pl.Series, period: int = 14) -> pl.Series:
    delta = close.diff()
    gain = delta.clip(lower_bound=0)
    loss = (-delta).clip(lower_bound=0)
    
    avg_gain = gain.rolling_mean(window_size=period)
    avg_loss = loss.rolling_mean(window_size=period)
    
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_atr(high: pl.Series, low: pl.Series, close: pl.Series, period: int = 14) -> pl.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pl.max_horizontal(tr1, tr2, tr3)
    atr = tr.rolling_mean(window_size=period)
    return atr


def compute_bollinger_bands(
    close: pl.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pl.Series, pl.Series, pl.Series]:
    middle = close.rolling_mean(window_size=period)
    std = close.rolling_std(window_size=period)
    
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    
    return upper, middle, lower


def compute_macd(
    close: pl.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pl.Series, pl.Series, pl.Series]:
    ema_fast = close.ewm_mean(span=fast)
    ema_slow = close.ewm_mean(span=slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm_mean(span=signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def compute_stochastic(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pl.Series, pl.Series]:
    lowest_low = low.rolling_min(window_size=k_period)
    highest_high = high.rolling_max(window_size=k_period)
    
    denom = highest_high - lowest_low
    denom = denom.fill_null(1e-10).replace(0, 1e-10)
    
    k = 100 * (close - lowest_low) / denom
    d = k.rolling_mean(window_size=d_period)
    
    return k, d


def compute_adx(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    period: int = 14,
) -> pl.Series:
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    
    plus_dm = (high - prev_high).clip(lower_bound=0)
    minus_dm = (prev_low - low).clip(lower_bound=0)
    
    tr = pl.max_horizontal(
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    )
    
    atr = tr.rolling_mean(window_size=period)
    plus_di = 100 * plus_dm.rolling_mean(window_size=period) / atr.replace(0, 1e-10)
    minus_di = 100 * minus_dm.rolling_mean(window_size=period) / atr.replace(0, 1e-10)
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-10)
    adx = dx.rolling_mean(window_size=period)
    
    return adx


def compute_williams_r(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    period: int = 14,
) -> pl.Series:
    highest_high = high.rolling_max(window_size=period)
    lowest_low = low.rolling_min(window_size=period)
    
    denom = highest_high - lowest_low
    denom = denom.fill_null(1e-10).replace(0, 1e-10)
    
    wr = -100 * (highest_high - close) / denom
    return wr


def compute_obv(close: pl.Series, volume: pl.Series) -> pl.Series:
    direction = close.diff().sign().fill_null(0)
    obv = (direction * volume).cum_sum()
    return obv


def compute_vwap(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    volume: pl.Series,
) -> pl.Series:
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cum_sum() / volume.cum_sum().replace(0, 1e-10)
    return vwap


def compute_cci(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    period: int = 20,
) -> pl.Series:
    typical_price = (high + low + close) / 3
    sma = typical_price.rolling_mean(window_size=period)
    mean_dev = (typical_price - sma).abs().rolling_mean(window_size=period)
    cci = (typical_price - sma) / (0.015 * mean_dev.replace(0, 1e-10))
    return cci


def compute_mfi(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    volume: pl.Series,
    period: int = 14,
) -> pl.Series:
    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume
    
    tp_diff = typical_price.diff()
    pos_flow = pl.when(tp_diff > 0).then(raw_money_flow).otherwise(0)
    neg_flow = pl.when(tp_diff < 0).then(raw_money_flow).otherwise(0)
    
    pos_sum = pos_flow.rolling_sum(window_size=period)
    neg_sum = neg_flow.rolling_sum(window_size=period)
    
    mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, 1e-10)))
    return mfi


def compute_roc(close: pl.Series, period: int = 10) -> pl.Series:
    prev_close = close.shift(period)
    roc = (close - prev_close) / prev_close.replace(0, 1e-10) * 100
    return roc


def compute_momentum(close: pl.Series, period: int = 10) -> pl.Series:
    return (close / close.shift(period).replace(0, 1e-10) - 1) * 100


def compute_trix(close: pl.Series, period: int = 15) -> pl.Series:
    ema1 = close.ewm_mean(span=period)
    ema2 = ema1.ewm_mean(span=period)
    ema3 = ema2.ewm_mean(span=period)
    trix = (ema3 - ema3.shift(1)) / ema3.shift(1).replace(0, 1e-10) * 100
    return trix


def compute_ultimate_oscillator(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    period1: int = 7,
    period2: int = 14,
    period3: int = 28,
) -> pl.Series:
    prev_close = close.shift(1)
    bp = close - pl.min_horizontal(low, prev_close)
    tr = pl.max_horizontal(high, prev_close) - pl.min_horizontal(low, prev_close)
    
    avg1 = bp.rolling_sum(window_size=period1) / tr.rolling_sum(window_size=period1).replace(0, 1e-10)
    avg2 = bp.rolling_sum(window_size=period2) / tr.rolling_sum(window_size=period2).replace(0, 1e-10)
    avg3 = bp.rolling_sum(window_size=period3) / tr.rolling_sum(window_size=period3).replace(0, 1e-10)
    
    uo = 100 * ((4 * avg1) + (2 * avg2) + avg3) / 7
    return uo


def add_all_indicators(df: pl.DataFrame, config: FeatureConfig | None = None) -> pl.DataFrame:
    if config is None:
        config = FeatureConfig()
    
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    
    rsi = compute_rsi(close, config.rsi_period)
    atr = compute_atr(high, low, close, config.atr_period)
    bb_upper, bb_middle, bb_lower = compute_bollinger_bands(close, config.bb_period, config.bb_std)
    macd, macd_signal, macd_hist = compute_macd(close)
    stoch_k, stoch_d = compute_stochastic(high, low, close)
    adx = compute_adx(high, low, close)
    williams_r = compute_williams_r(high, low, close)
    obv = compute_obv(close, volume)
    vwap = compute_vwap(high, low, close, volume)
    
    cci = compute_cci(high, low, close)
    mfi = compute_mfi(high, low, close, volume)
    roc = compute_roc(close)
    momentum = compute_momentum(close)
    trix = compute_trix(close)
    uo = compute_ultimate_oscillator(high, low, close)
    
    bb_width = (bb_upper - bb_lower) / bb_middle.replace(0, 1e-10) * 100
    bb_pct = (close - bb_lower) / (bb_upper - bb_lower).replace(0, 1e-10)
    bb_upper_dist = (close - bb_upper) / close.replace(0, 1e-10) * 100
    bb_lower_dist = (close - bb_lower) / close.replace(0, 1e-10) * 100
    bb_middle_dist = (close - bb_middle) / close.replace(0, 1e-10) * 100
    
    atr_pct = atr / close.replace(0, 1e-10) * 100
    
    vwap_dist_pct = (close - vwap) / close.replace(0, 1e-10) * 100
    
    price_change = close.pct_change() * 100
    price_change_3 = (close - close.shift(3)) / close.shift(3).replace(0, 1e-10) * 100
    price_change_5 = (close - close.shift(5)) / close.shift(5).replace(0, 1e-10) * 100
    price_change_10 = (close - close.shift(10)) / close.shift(10).replace(0, 1e-10) * 100
    price_change_20 = (close - close.shift(20)) / close.shift(20).replace(0, 1e-10) * 100
    
    vol_change = volume.pct_change() * 100
    vol_ma_ratio = volume / volume.rolling_mean(window_size=20).replace(0, 1e-10)
    
    rsi_slope = rsi.diff(5)
    macd_slope = macd.diff(3)
    adx_slope = adx.diff(5)
    
    high_low_range_pct = (high - low) / close.replace(0, 1e-10) * 100
    
    highest_20 = high.rolling_max(window_size=20)
    lowest_20 = low.rolling_min(window_size=20)
    donchian_pct = (close - lowest_20) / (highest_20 - lowest_20).replace(0, 1e-10)
    dist_from_high_20 = (close - highest_20) / close.replace(0, 1e-10) * 100
    dist_from_low_20 = (close - lowest_20) / close.replace(0, 1e-10) * 100
    
    volatility_20 = close.rolling_std(window_size=20) / close.rolling_mean(window_size=20).replace(0, 1e-10) * 100
    
    return df.with_columns(
        rsi.alias("rsi"),
        rsi_slope.alias("rsi_slope"),
        atr_pct.alias("atr_pct"),
        bb_width.alias("bb_width"),
        bb_pct.alias("bb_pct"),
        bb_upper_dist.alias("bb_upper_dist"),
        bb_lower_dist.alias("bb_lower_dist"),
        bb_middle_dist.alias("bb_middle_dist"),
        macd_slope.alias("macd_slope"),
        stoch_k.alias("stoch_k"),
        stoch_d.alias("stoch_d"),
        adx.alias("adx"),
        adx_slope.alias("adx_slope"),
        williams_r.alias("williams_r"),
        cci.alias("cci"),
        mfi.alias("mfi"),
        roc.alias("roc"),
        momentum.alias("momentum"),
        trix.alias("trix"),
        uo.alias("ultimate_osc"),
        vwap_dist_pct.alias("vwap_dist_pct"),
        price_change.alias("price_change_1"),
        price_change_3.alias("price_change_3"),
        price_change_5.alias("price_change_5"),
        price_change_10.alias("price_change_10"),
        price_change_20.alias("price_change_20"),
        vol_change.alias("vol_change"),
        vol_ma_ratio.alias("vol_ma_ratio"),
        high_low_range_pct.alias("high_low_range_pct"),
        donchian_pct.alias("donchian_pct"),
        dist_from_high_20.alias("dist_from_high_20"),
        dist_from_low_20.alias("dist_from_low_20"),
        volatility_20.alias("volatility_20"),
    )


def extract_candle_features(df: pl.DataFrame) -> pl.DataFrame:
    open_col = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    body = close - open_col
    body_abs = body.abs()
    range_hl = high - low
    
    body_pct = body_abs / range_hl.replace(0, 1e-10)
    
    upper_shadow = high - pl.max_horizontal(open_col, close)
    lower_shadow = pl.min_horizontal(open_col, close) - low
    
    upper_shadow_pct = upper_shadow / range_hl.replace(0, 1e-10)
    lower_shadow_pct = lower_shadow / range_hl.replace(0, 1e-10)
    
    is_bullish = (close > open_col).cast(pl.Int32)
    is_doji = body_pct < 0.1
    is_hammer = (lower_shadow_pct > 0.6) & (upper_shadow_pct < 0.1)
    is_shooting_star = (upper_shadow_pct > 0.6) & (lower_shadow_pct < 0.1)
    
    return df.with_columns(
        body.alias("candle_body"),
        body_pct.alias("candle_body_pct"),
        upper_shadow_pct.alias("upper_shadow_pct"),
        lower_shadow_pct.alias("lower_shadow_pct"),
        is_bullish.alias("is_bullish"),
        is_doji.cast(pl.Int32).alias("is_doji"),
        is_hammer.cast(pl.Int32).alias("is_hammer"),
        is_shooting_star.cast(pl.Int32).alias("is_shooting_star"),
    )


def add_ma_features(df: pl.DataFrame, ma_periods: list[int] | None = None) -> pl.DataFrame:
    if ma_periods is None:
        ma_periods = [25, 50, 100, 200, 400]
    
    close = df["close"]
    
    features = []
    for period in ma_periods:
        ma_col = f"ma_{period}"
        if ma_col in df.columns:
            ma = df[ma_col]
        else:
            ma = close.rolling_mean(window_size=period)
            features.append(ma.alias(ma_col))
        
        dist_pct = (close - ma) / close.replace(0, 1e-10) * 100
        features.append(dist_pct.alias(f"ma_{period}_dist_pct"))
        
        slope = (ma - ma.shift(5)) / ma.shift(5).replace(0, 1e-10) * 100
        features.append(slope.alias(f"ma_{period}_slope"))
        
        above_ma = (close > ma).cast(pl.Int32)
        features.append(above_ma.alias(f"above_ma_{period}"))
    
    for i, short_ma in enumerate(ma_periods[:-1]):
        for long_ma in ma_periods[i+1:]:
            short_col = f"ma_{short_ma}"
            long_col = f"ma_{long_ma}"
            
            if short_col in df.columns and long_col in df.columns:
                short_val = df[short_col]
                long_val = df[long_col]
            else:
                short_val = close.rolling_mean(window_size=short_ma)
                long_val = close.rolling_mean(window_size=long_ma)
            
            cross_dist = (short_val - long_val) / close.replace(0, 1e-10) * 100
            features.append(cross_dist.alias(f"ma_{short_ma}_{long_ma}_cross_pct"))
    
    if features:
        df = df.with_columns(features)
    
    return df


def prepare_ml_features(
    df: pl.DataFrame,
    trades_df: pl.DataFrame,
    lookback: int = 20,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    df = add_all_indicators(df)
    df = extract_candle_features(df)
    df = add_ma_features(df)
    
    feature_cols = [
        "rsi", "rsi_slope", "atr_pct", 
        "bb_width", "bb_pct", "bb_upper_dist", "bb_lower_dist", "bb_middle_dist",
        "macd_slope", "stoch_k", "stoch_d", 
        "adx", "adx_slope", "williams_r",
        "cci", "mfi", "roc", "momentum", "trix", "ultimate_osc",
        "vwap_dist_pct", 
        "price_change_1", "price_change_3", "price_change_5", "price_change_10", "price_change_20",
        "vol_change", "vol_ma_ratio",
        "high_low_range_pct", "donchian_pct", "dist_from_high_20", "dist_from_low_20",
        "volatility_20",
        "candle_body_pct", "upper_shadow_pct", "lower_shadow_pct",
        "is_bullish", "is_doji", "is_hammer", "is_shooting_star",
        "ma_25_dist_pct", "ma_50_dist_pct", "ma_100_dist_pct", "ma_200_dist_pct", "ma_400_dist_pct",
        "ma_25_slope", "ma_50_slope", "ma_100_slope", "ma_200_slope", "ma_400_slope",
        "above_ma_25", "above_ma_50", "above_ma_100", "above_ma_200", "above_ma_400",
        "ma_25_50_cross_pct", "ma_25_100_cross_pct", "ma_50_100_cross_pct", "ma_100_200_cross_pct",
    ]
    
    available_cols = [c for c in feature_cols if c in df.columns]
    
    X_list = []
    y_list = []
    
    df_dict = {col: df[col].to_numpy() for col in available_cols + ["datetime"]}
    datetime_arr = df_dict["datetime"]
    
    for trade in trades_df.to_dicts():
        open_time = trade["open_time"]
        is_sl = trade["is_sl"]
        
        mask = datetime_arr <= open_time
        idx = np.sum(mask) - 1
        
        if idx < lookback:
            continue
        
        features = []
        for col in available_cols:
            arr = df_dict[col]
            window = arr[idx - lookback + 1 : idx + 1]
            
            if len(window) == lookback:
                features.extend([
                    np.nanmean(window),
                    np.nanstd(window),
                    window[-1] if not np.isnan(window[-1]) else 0,
                ])
        
        if len(features) == len(available_cols) * 3:
            X_list.append(features)
            y_list.append(1 if is_sl else 0)
    
    expanded_cols = []
    for col in available_cols:
        expanded_cols.extend([f"{col}_mean", f"{col}_std", f"{col}_last"])
    
    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    
    return X, y, expanded_cols


def create_candle_sequences(
    df: pl.DataFrame,
    trades_df: pl.DataFrame,
    sequence_length: int = 50,
) -> tuple[np.ndarray, np.ndarray]:
    ohlcv_cols = ["open", "high", "low", "close", "volume"]
    
    df_normalized = df.with_columns([
        ((pl.col(c) - pl.col(c).rolling_mean(window_size=50)) / 
         pl.col(c).rolling_std(window_size=50).replace(0, 1e-10)).alias(f"{c}_norm")
        for c in ohlcv_cols
    ])
    
    norm_cols = [f"{c}_norm" for c in ohlcv_cols]
    
    X_list = []
    y_list = []
    
    data_dict = {col: df_normalized[col].to_numpy() for col in norm_cols + ["datetime"]}
    datetime_arr = data_dict["datetime"]
    
    for trade in trades_df.to_dicts():
        open_time = trade["open_time"]
        is_sl = trade["is_sl"]
        
        mask = datetime_arr <= open_time
        idx = np.sum(mask) - 1
        
        if idx < sequence_length:
            continue
        
        sequence = np.zeros((sequence_length, len(norm_cols)), dtype=np.float32)
        for i, col in enumerate(norm_cols):
            arr = data_dict[col]
            sequence[:, i] = arr[idx - sequence_length + 1 : idx + 1]
        
        if not np.any(np.isnan(sequence)):
            X_list.append(sequence)
            y_list.append(1 if is_sl else 0)
    
    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    
    return X, y


def candle_to_image(
    ohlcv_sequence: np.ndarray,
    image_size: tuple[int, int] = (64, 64),
) -> np.ndarray:
    seq_len, n_features = ohlcv_sequence.shape
    img = np.zeros((*image_size, 3), dtype=np.float32)
    
    h, w = image_size
    candle_width = max(1, w // seq_len)
    
    o, hi, lo, c, v = ohlcv_sequence.T
    
    price_min = np.min([o.min(), lo.min(), c.min()])
    price_max = np.max([o.max(), hi.max(), c.max()])
    price_range = price_max - price_min
    if price_range < 1e-10:
        price_range = 1e-10
    
    def price_to_y(price):
        return int((1 - (price - price_min) / price_range) * (h - 1))
    
    for i in range(seq_len):
        x_start = i * candle_width
        x_end = min(x_start + candle_width, w)
        
        y_open = price_to_y(o[i])
        y_close = price_to_y(c[i])
        y_high = price_to_y(hi[i])
        y_low = price_to_y(lo[i])
        
        is_green = c[i] >= o[i]
        color = (0, 1, 0) if is_green else (1, 0, 0)
        
        wick_x = (x_start + x_end) // 2
        for y in range(min(y_high, y_low), max(y_high, y_low) + 1):
            if 0 <= y < h and 0 <= wick_x < w:
                img[y, wick_x] = (0.5, 0.5, 0.5)
        
        body_top = min(y_open, y_close)
        body_bottom = max(y_open, y_close)
        for y in range(body_top, body_bottom + 1):
            for x in range(x_start, x_end):
                if 0 <= y < h and 0 <= x < w:
                    img[y, x] = color
    
    return img


def create_candle_images(
    df: pl.DataFrame,
    trades_df: pl.DataFrame,
    sequence_length: int = 50,
    image_size: tuple[int, int] = (64, 64),
) -> tuple[np.ndarray, np.ndarray]:
    ohlcv_cols = ["open", "high", "low", "close", "volume"]
    
    X_list = []
    y_list = []
    
    data_dict = {col: df[col].to_numpy() for col in ohlcv_cols + ["datetime"]}
    datetime_arr = data_dict["datetime"]
    
    for trade in trades_df.to_dicts():
        open_time = trade["open_time"]
        is_sl = trade["is_sl"]
        
        mask = datetime_arr <= open_time
        idx = np.sum(mask) - 1
        
        if idx < sequence_length:
            continue
        
        sequence = np.zeros((sequence_length, len(ohlcv_cols)), dtype=np.float32)
        for i, col in enumerate(ohlcv_cols):
            arr = data_dict[col]
            sequence[:, i] = arr[idx - sequence_length + 1 : idx + 1]
        
        if not np.any(np.isnan(sequence)):
            img = candle_to_image(sequence, image_size)
            X_list.append(img)
            y_list.append(1 if is_sl else 0)
    
    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    
    X = np.transpose(X, (0, 3, 1, 2))
    
    return X, y
