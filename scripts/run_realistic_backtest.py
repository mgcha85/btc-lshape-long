#!/usr/bin/env python3
"""
Realistic Compound Backtest with Fees and Funding Rate

Includes:
1. Maker/Taker fees
2. Funding rate (8-hour)
3. Multiple timeframes (1H, 15M, 5M)
4. Three risk profiles (Conservative, Balanced, Aggressive)
"""

import itertools
from dataclasses import dataclass
from pathlib import Path
from datetime import timedelta

import numpy as np
import polars as pl
from tqdm import tqdm


@dataclass
class FeeConfig:
    maker_fee: float = 0.0002  # 0.02%
    taker_fee: float = 0.0005  # 0.05%
    funding_rate_8h: float = 0.0001  # 0.01% per 8h (average)
    use_limit_orders: bool = False  # True = maker, False = taker


@dataclass 
class StrategyProfile:
    name: str
    position_size: float
    leverage: float
    tp_pct: float
    sl_pct: float
    hc_pct: float


PROFILES = {
    'conservative': StrategyProfile('Conservative', 0.10, 5.0, 15.0, 2.0, 5.0),
    'balanced': StrategyProfile('Balanced', 0.20, 10.0, 15.0, 2.0, 5.0),
    'aggressive': StrategyProfile('Aggressive', 0.30, 10.0, 15.0, 2.0, 5.0),
}


@dataclass
class BacktestResult:
    profile_name: str
    timeframe: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    calmar_ratio: float
    total_trades: int
    win_rate: float
    total_fees_paid: float
    total_funding_paid: float
    avg_holding_hours: float
    bankruptcy: bool


def load_data(timeframe: str) -> pl.DataFrame:
    df = pl.read_parquet('/mnt/data/finance/cryptocurrency/ETHUSDT/*/*.parquet')
    df = df.with_columns(pl.col('open_time').cast(pl.Datetime('ms')))
    df = df.sort('open_time')
    
    if timeframe == '1h':
        df = df.with_columns(pl.col('open_time').dt.truncate('1h').alias('period'))
    elif timeframe == '15m':
        df = df.with_columns(pl.col('open_time').dt.truncate('15m').alias('period'))
    elif timeframe == '5m':
        df = df.with_columns(pl.col('open_time').dt.truncate('5m').alias('period'))
    else:
        raise ValueError(f"Unknown timeframe: {timeframe}")
    
    df = df.group_by('period').agg([
        pl.col('open').first(),
        pl.col('high').max(),
        pl.col('low').min(),
        pl.col('close').last(),
        pl.col('volume').sum(),
    ]).sort('period').rename({'period': 'open_time'})
    
    for period in [25, 50, 100, 200]:
        df = df.with_columns(
            pl.col('close').rolling_mean(window_size=period).alias(f'ma_{period}')
        )
    
    return df


def detect_signals(df: pl.DataFrame, timeframe: str) -> list[int]:
    from crypto_backtest.detection.enhanced_rules.detector import (
        EnhancedLShapeDetector,
        EnhancedDetectorConfig,
    )
    
    if timeframe == '1h':
        config = EnhancedDetectorConfig(
            drop_atr_multiplier=2.5,
            consolidation_atr_multiplier=1.5,
            flatness_threshold=0.4,
            volume_decline_required=False,
            min_confidence=0.6,
        )
    elif timeframe == '15m':
        config = EnhancedDetectorConfig(
            drop_atr_multiplier=2.0,
            consolidation_atr_multiplier=1.2,
            flatness_threshold=0.45,
            volume_decline_required=False,
            min_confidence=0.5,
        )
    else:  # 5m
        config = EnhancedDetectorConfig(
            drop_atr_multiplier=1.5,
            consolidation_atr_multiplier=1.0,
            flatness_threshold=0.5,
            volume_decline_required=False,
            min_confidence=0.5,
        )
    
    detector = EnhancedLShapeDetector(config)
    detections = detector.detect_batch_vectorized(df, ma_column='ma_50', min_idx=200)
    return [d[0] for d in detections]


def calculate_funding_periods(entry_idx: int, exit_idx: int, timeframe: str) -> int:
    """Calculate how many 8-hour funding periods the position spans."""
    if timeframe == '1h':
        hours = exit_idx - entry_idx
    elif timeframe == '15m':
        hours = (exit_idx - entry_idx) * 0.25
    else:  # 5m
        hours = (exit_idx - entry_idx) * (5/60)
    
    return int(hours // 8)


def run_realistic_backtest(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    timestamps: list,
    signal_indices: list[int],
    profile: StrategyProfile,
    fee_config: FeeConfig,
    timeframe: str,
    initial_capital: float = 10000.0,
) -> BacktestResult:
    
    n = len(close)
    capital = initial_capital
    peak_capital = initial_capital
    max_dd = 0.0
    
    trade_returns = []
    total_fees = 0.0
    total_funding = 0.0
    total_holding_bars = 0
    bankruptcy = False
    
    tp = profile.tp_pct
    sl = profile.sl_pct
    hc = profile.hc_pct
    
    entry_fee_rate = fee_config.taker_fee if not fee_config.use_limit_orders else fee_config.maker_fee
    exit_fee_rate = fee_config.taker_fee  # usually taker on exit
    
    for entry_idx in signal_indices:
        if entry_idx >= n - 1 or capital <= 0:
            if capital <= 0:
                bankruptcy = True
            break
        
        entry_price = close[entry_idx]
        half_closed = False
        current_sl = sl
        exit_idx = entry_idx
        
        trade_pnl_pct = 0.0
        
        for i in range(entry_idx + 1, min(entry_idx + 200, n)):
            pnl_low = (low[i] - entry_price) / entry_price * 100
            pnl_high = (high[i] - entry_price) / entry_price * 100
            exit_idx = i
            
            if pnl_low <= -current_sl:
                trade_pnl_pct = (hc / 2) if half_closed else -sl
                break
            
            if not half_closed and pnl_high >= hc:
                half_closed = True
                current_sl = 0.0
            
            if pnl_high >= tp:
                trade_pnl_pct = (hc / 2 + tp / 2) if half_closed else tp
                break
        else:
            end_idx = min(entry_idx + 199, n - 1)
            exit_idx = end_idx
            pnl = (close[end_idx] - entry_price) / entry_price * 100
            trade_pnl_pct = (hc / 2 + pnl / 2) if half_closed else pnl
        
        position_value = capital * profile.position_size
        notional_value = position_value * profile.leverage
        
        entry_fee = notional_value * entry_fee_rate
        exit_fee = notional_value * exit_fee_rate
        trade_fees = entry_fee + exit_fee
        
        funding_periods = calculate_funding_periods(entry_idx, exit_idx, timeframe)
        funding_cost = notional_value * fee_config.funding_rate_8h * funding_periods
        
        total_holding_bars += (exit_idx - entry_idx)
        
        gross_pnl = position_value * (trade_pnl_pct * profile.leverage / 100)
        net_pnl = gross_pnl - trade_fees - funding_cost
        
        capital += net_pnl
        total_fees += trade_fees
        total_funding += funding_cost
        
        net_return_pct = (net_pnl / position_value) * 100 if position_value > 0 else 0
        trade_returns.append(net_return_pct)
        
        if capital > peak_capital:
            peak_capital = capital
        
        current_dd = (peak_capital - capital) / peak_capital * 100
        if current_dd > max_dd:
            max_dd = current_dd
        
        if capital <= initial_capital * 0.01:
            bankruptcy = True
            break
    
    if len(trade_returns) == 0:
        return BacktestResult(
            profile_name=profile.name,
            timeframe=timeframe,
            initial_capital=initial_capital,
            final_capital=capital,
            total_return_pct=0,
            cagr_pct=0,
            max_drawdown_pct=0,
            sharpe_ratio=0,
            calmar_ratio=0,
            total_trades=0,
            win_rate=0,
            total_fees_paid=0,
            total_funding_paid=0,
            avg_holding_hours=0,
            bankruptcy=False,
        )
    
    total_return = (capital - initial_capital) / initial_capital * 100
    
    if timeframe == '1h':
        years = len(close) / (24 * 365)
    elif timeframe == '15m':
        years = len(close) / (4 * 24 * 365)
    else:
        years = len(close) / (12 * 24 * 365)
    
    cagr = ((capital / initial_capital) ** (1 / years) - 1) * 100 if capital > 0 and years > 0 else -100
    
    returns_array = np.array(trade_returns)
    sharpe = (np.mean(returns_array) / np.std(returns_array) * np.sqrt(len(returns_array) / years)) if np.std(returns_array) > 0 else 0
    calmar = cagr / max_dd if max_dd > 0 else 0
    
    wins = sum(1 for r in trade_returns if r > 0)
    win_rate = wins / len(trade_returns) * 100
    
    if timeframe == '1h':
        avg_holding_hours = total_holding_bars / len(trade_returns) if trade_returns else 0
    elif timeframe == '15m':
        avg_holding_hours = total_holding_bars * 0.25 / len(trade_returns) if trade_returns else 0
    else:
        avg_holding_hours = total_holding_bars * (5/60) / len(trade_returns) if trade_returns else 0
    
    return BacktestResult(
        profile_name=profile.name,
        timeframe=timeframe,
        initial_capital=initial_capital,
        final_capital=capital,
        total_return_pct=total_return,
        cagr_pct=cagr,
        max_drawdown_pct=max_dd,
        sharpe_ratio=sharpe,
        calmar_ratio=calmar,
        total_trades=len(trade_returns),
        win_rate=win_rate,
        total_fees_paid=total_fees,
        total_funding_paid=total_funding,
        avg_holding_hours=avg_holding_hours,
        bankruptcy=bankruptcy,
    )


def main():
    print("="*100)
    print("REALISTIC BACKTEST WITH FEES AND FUNDING")
    print("="*100)
    
    fee_config = FeeConfig(
        maker_fee=0.0002,  # 0.02%
        taker_fee=0.0005,  # 0.05%
        funding_rate_8h=0.0001,  # 0.01% per 8h
        use_limit_orders=False,
    )
    
    print(f"\nFee Configuration:")
    print(f"  Maker Fee: {fee_config.maker_fee*100:.3f}%")
    print(f"  Taker Fee: {fee_config.taker_fee*100:.3f}%")
    print(f"  Funding Rate (8h): {fee_config.funding_rate_8h*100:.4f}%")
    print(f"  Order Type: {'Limit (Maker)' if fee_config.use_limit_orders else 'Market (Taker)'}")
    
    timeframes = ['1h', '15m', '5m']
    all_results = []
    
    for tf in timeframes:
        print(f"\n{'='*100}")
        print(f"TIMEFRAME: {tf.upper()}")
        print(f"{'='*100}")
        
        print(f"\nLoading {tf} data...")
        df = load_data(tf)
        print(f"Loaded {len(df):,} bars")
        
        print("Detecting signals...")
        signal_indices = detect_signals(df, tf)
        print(f"Found {len(signal_indices)} signals")
        
        if len(signal_indices) < 5:
            print(f"Not enough signals for {tf}, skipping...")
            continue
        
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        timestamps = df["open_time"].to_list()
        
        for profile_name, profile in PROFILES.items():
            result = run_realistic_backtest(
                high, low, close, timestamps,
                signal_indices,
                profile,
                fee_config,
                tf,
            )
            all_results.append(result)
            
            print(f"\n{profile.name} ({tf}):")
            print(f"  Final Capital: ${result.final_capital:,.0f}")
            print(f"  Return: {result.total_return_pct:.1f}%")
            print(f"  CAGR: {result.cagr_pct:.1f}%")
            print(f"  Max DD: {result.max_drawdown_pct:.1f}%")
            print(f"  Calmar: {result.calmar_ratio:.2f}")
            print(f"  Win Rate: {result.win_rate:.1f}%")
            print(f"  Trades: {result.total_trades}")
            print(f"  Fees Paid: ${result.total_fees_paid:,.0f}")
            print(f"  Funding Paid: ${result.total_funding_paid:,.0f}")
            print(f"  Avg Hold: {result.avg_holding_hours:.1f}h")
    
    print(f"\n{'='*100}")
    print("SUMMARY COMPARISON")
    print(f"{'='*100}\n")
    
    results_df = pl.DataFrame([r.__dict__ for r in all_results])
    
    print("All Results (sorted by Calmar Ratio):")
    sorted_df = results_df.sort('calmar_ratio', descending=True)
    print(sorted_df.select([
        'profile_name', 'timeframe', 'final_capital', 'total_return_pct',
        'cagr_pct', 'max_drawdown_pct', 'calmar_ratio', 'total_trades',
        'total_fees_paid', 'total_funding_paid'
    ]))
    
    print(f"\n{'='*100}")
    print("FEE IMPACT ANALYSIS")
    print(f"{'='*100}\n")
    
    for tf in timeframes:
        tf_results = [r for r in all_results if r.timeframe == tf]
        if tf_results:
            total_fees = sum(r.total_fees_paid for r in tf_results) / len(tf_results)
            total_funding = sum(r.total_funding_paid for r in tf_results) / len(tf_results)
            avg_trades = sum(r.total_trades for r in tf_results) / len(tf_results)
            print(f"{tf.upper()}:")
            print(f"  Avg Fees: ${total_fees:,.0f}")
            print(f"  Avg Funding: ${total_funding:,.0f}")
            print(f"  Avg Trades: {avg_trades:.0f}")
            print(f"  Cost per Trade: ${(total_fees + total_funding) / avg_trades:.2f}" if avg_trades > 0 else "")
    
    output_path = Path('outputs/realistic_backtest_results.parquet')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.write_parquet(output_path)
    print(f"\nSaved to {output_path}")
    
    return results_df


if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')
    main()
