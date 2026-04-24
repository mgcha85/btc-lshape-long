#!/usr/bin/env python3
"""
Enhanced Rules Parametric Study - Optimized version
Pre-computes all signals once, then varies only TP/SL/HC for backtest.
"""

import itertools
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

import numpy as np
import polars as pl
from tqdm import tqdm


def load_eth_hourly() -> pl.DataFrame:
    df = pl.read_parquet('/mnt/data/finance/cryptocurrency/ETHUSDT/*/*.parquet')
    df = df.with_columns(pl.col('open_time').cast(pl.Datetime('ms')))
    df = df.sort('open_time')
    df = df.with_columns(pl.col('open_time').dt.truncate('1h').alias('hour'))
    df = df.group_by('hour').agg([
        pl.col('open').first(),
        pl.col('high').max(),
        pl.col('low').min(),
        pl.col('close').last(),
        pl.col('volume').sum(),
    ]).sort('hour').rename({'hour': 'open_time'})
    
    for period in [25, 50, 100, 200]:
        df = df.with_columns(
            pl.col('close').rolling_mean(window_size=period).alias(f'ma_{period}')
        )
    
    return df


def run_backtest_numpy(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    signal_indices: list[int],
    tp: float,
    sl: float,
    hc: float,
) -> dict:
    """Numpy-optimized backtest."""
    n = len(close)
    profits = []
    
    for entry_idx in signal_indices:
        if entry_idx >= n - 1:
            continue
            
        entry_price = close[entry_idx]
        half_closed = False
        current_sl = sl
        
        for i in range(entry_idx + 1, min(entry_idx + 200, n)):
            pnl_low = (low[i] - entry_price) / entry_price * 100
            pnl_high = (high[i] - entry_price) / entry_price * 100
            
            if pnl_low <= -current_sl:
                profit = hc / 2 if half_closed else -sl
                profits.append(profit)
                break
            
            if not half_closed and pnl_high >= hc:
                half_closed = True
                current_sl = 0.0
            
            if pnl_high >= tp:
                profit = (hc / 2 + tp / 2) if half_closed else tp
                profits.append(profit)
                break
        else:
            end_idx = min(entry_idx + 199, n - 1)
            pnl = (close[end_idx] - entry_price) / entry_price * 100
            profit = (hc / 2 + pnl / 2) if half_closed else pnl
            profits.append(profit)
    
    if not profits:
        return {'trades': 0, 'win_rate': 0, 'profit': 0, 'mdd': 0, 'pf': 0}
    
    wins = sum(1 for p in profits if p > 0)
    total = sum(profits)
    
    cumsum = np.cumsum(profits)
    peak = np.maximum.accumulate(cumsum)
    mdd = np.max(peak - cumsum)
    
    win_sum = sum(p for p in profits if p > 0)
    loss_sum = abs(sum(p for p in profits if p < 0))
    pf = win_sum / loss_sum if loss_sum > 0 else float('inf')
    
    return {
        'trades': len(profits),
        'win_rate': wins / len(profits) * 100,
        'profit': total,
        'mdd': mdd,
        'pf': pf,
    }


def detect_all_configs(df: pl.DataFrame):
    """Pre-detect signals for all detector config combinations."""
    from crypto_backtest.detection.enhanced_rules.detector import (
        EnhancedLShapeDetector,
        EnhancedDetectorConfig,
    )
    
    drop_atr_mults = [1.5, 2.0, 2.5, 3.0]
    consol_atr_mults = [0.8, 1.0, 1.5, 2.0]
    flatness_thresholds = [0.3, 0.35, 0.4, 0.5]
    volume_required_opts = [True, False]
    min_confidences = [0.5, 0.6, 0.7]
    
    detection_configs = list(itertools.product(
        drop_atr_mults,
        consol_atr_mults,
        flatness_thresholds,
        volume_required_opts,
        min_confidences,
    ))
    
    print(f"Pre-computing signals for {len(detection_configs)} detector configs...")
    
    signals_cache = {}
    
    for (drop_atr, consol_atr, flat_thresh, vol_req, min_conf) in tqdm(detection_configs, desc="Detecting"):
        config = EnhancedDetectorConfig(
            drop_atr_multiplier=drop_atr,
            consolidation_atr_multiplier=consol_atr,
            flatness_threshold=flat_thresh,
            volume_decline_required=vol_req,
            min_confidence=min_conf,
        )
        
        detector = EnhancedLShapeDetector(config)
        detections = detector.detect_batch_vectorized(df, ma_column='ma_50', min_idx=200)
        
        key = (drop_atr, consol_atr, flat_thresh, vol_req, min_conf)
        signals_cache[key] = [d[0] for d in detections]
    
    return signals_cache


def run_parametric_study():
    print("Loading ETHUSDT hourly data...")
    df = load_eth_hourly()
    print(f"Loaded {len(df)} bars ({df.row(0, named=True)['open_time']} ~ {df.row(-1, named=True)['open_time']})")
    
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    
    signals_cache = detect_all_configs(df)
    
    tp_pcts = [5.0, 7.0, 10.0, 15.0]
    sl_pcts = [2.0, 3.0, 5.0]
    hc_pcts = [3.0, 5.0]
    
    exit_combos = list(itertools.product(tp_pcts, sl_pcts, hc_pcts))
    
    print(f"\nBacktesting {len(signals_cache)} signal sets × {len(exit_combos)} exit configs = {len(signals_cache) * len(exit_combos)} combinations...")
    
    results = []
    
    for key, signal_indices in tqdm(signals_cache.items(), desc="Backtesting"):
        if len(signal_indices) < 3:
            continue
        
        drop_atr, consol_atr, flat_thresh, vol_req, min_conf = key
        
        for tp, sl, hc in exit_combos:
            stats = run_backtest_numpy(high, low, close, signal_indices, tp, sl, hc)
            
            if stats['trades'] < 3:
                continue
            
            profit_mdd = stats['profit'] / stats['mdd'] if stats['mdd'] > 0 else 0
            
            results.append({
                'drop_atr': drop_atr,
                'consol_atr': consol_atr,
                'flatness': flat_thresh,
                'vol_req': vol_req,
                'min_conf': min_conf,
                'tp': tp,
                'sl': sl,
                'hc': hc,
                'trades': stats['trades'],
                'win_rate': stats['win_rate'],
                'profit': stats['profit'],
                'mdd': stats['mdd'],
                'pf': stats['pf'],
                'profit_mdd': profit_mdd,
            })
    
    return results


def analyze_results(results: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(results)


if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')
    
    results = run_parametric_study()
    
    if not results:
        print("No valid results found!")
        exit(1)
    
    df = analyze_results(results)
    
    print("\n" + "="*100)
    print("TOP 20 BY PROFIT/MDD RATIO")
    print("="*100)
    top_by_ratio = df.sort('profit_mdd', descending=True).head(20)
    print(top_by_ratio)
    
    print("\n" + "="*100)
    print("TOP 20 BY TOTAL PROFIT")
    print("="*100)
    top_by_profit = df.sort('profit', descending=True).head(20)
    print(top_by_profit)
    
    print("\n" + "="*100)
    print("TOP 20 BY WIN RATE (min 20 trades)")
    print("="*100)
    top_by_wr = df.filter(pl.col('trades') >= 20).sort('win_rate', descending=True).head(20)
    print(top_by_wr)
    
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    print(f"Total combinations tested: {len(results)}")
    print(f"Profitable: {df.filter(pl.col('profit') > 0).height}")
    
    if len(df) > 0:
        best = df.sort('profit_mdd', descending=True).head(1).to_dicts()[0]
        print(f"\nBest config (by Profit/MDD):")
        print(f"  drop_atr={best['drop_atr']}, consol_atr={best['consol_atr']}")
        print(f"  flatness={best['flatness']}, vol_req={best['vol_req']}, min_conf={best['min_conf']}")
        print(f"  Trades: {best['trades']}, Win Rate: {best['win_rate']:.1f}%")
        print(f"  Profit: {best['profit']:.1f}%, MDD: {best['mdd']:.1f}%")
        print(f"  Profit/MDD: {best['profit_mdd']:.2f}")
    
    output_path = Path('outputs/enhanced_parametric_study.parquet')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)
    print(f"\nSaved results to {output_path}")
