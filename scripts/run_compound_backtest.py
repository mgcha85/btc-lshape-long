#!/usr/bin/env python3
"""
Compound Interest Backtest with Kelly Criterion Position Sizing

Simulates realistic trading with:
1. Kelly Criterion for optimal leverage
2. Fractional Kelly (safer)
3. Compound returns
4. Multiple position sizing strategies
"""

import itertools
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from tqdm import tqdm


@dataclass
class CompoundResult:
    strategy_name: str
    position_size: float
    leverage: float
    initial_capital: float
    final_capital: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    calmar_ratio: float
    total_trades: int
    win_rate: float
    max_consecutive_losses: int
    bankruptcy_occurred: bool


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


def calculate_kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Kelly Criterion: f* = (p * b - q) / b
    where p = win probability, q = loss probability, b = win/loss ratio
    """
    if avg_loss == 0:
        return 0.0
    
    p = win_rate
    q = 1 - win_rate
    b = abs(avg_win / avg_loss)
    
    kelly = (p * b - q) / b
    return max(0.0, kelly)


def run_compound_backtest(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    signal_indices: list[int],
    tp: float,
    sl: float,
    hc: float,
    position_size: float,
    leverage: float,
    initial_capital: float = 10000.0,
) -> CompoundResult:
    """Run backtest with compound returns and position sizing."""
    
    n = len(close)
    capital = initial_capital
    peak_capital = initial_capital
    max_dd = 0.0
    
    trade_returns = []
    equity_curve = [initial_capital]
    consecutive_losses = 0
    max_consecutive_losses = 0
    bankruptcy = False
    
    for entry_idx in signal_indices:
        if entry_idx >= n - 1 or capital <= 0:
            if capital <= 0:
                bankruptcy = True
            break
        
        entry_price = close[entry_idx]
        half_closed = False
        current_sl = sl
        
        trade_pnl_pct = 0.0
        
        for i in range(entry_idx + 1, min(entry_idx + 200, n)):
            pnl_low = (low[i] - entry_price) / entry_price * 100
            pnl_high = (high[i] - entry_price) / entry_price * 100
            
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
            pnl = (close[end_idx] - entry_price) / entry_price * 100
            trade_pnl_pct = (hc / 2 + pnl / 2) if half_closed else pnl
        
        position_value = capital * position_size
        leveraged_return = trade_pnl_pct * leverage / 100
        trade_pnl = position_value * leveraged_return
        
        capital += trade_pnl
        trade_returns.append(trade_pnl_pct * leverage * position_size)
        equity_curve.append(capital)
        
        if capital > peak_capital:
            peak_capital = capital
        
        current_dd = (peak_capital - capital) / peak_capital * 100
        if current_dd > max_dd:
            max_dd = current_dd
        
        if trade_pnl < 0:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0
        
        if capital <= initial_capital * 0.01:
            bankruptcy = True
            break
    
    if len(trade_returns) == 0:
        return CompoundResult(
            strategy_name="",
            position_size=position_size,
            leverage=leverage,
            initial_capital=initial_capital,
            final_capital=capital,
            total_return_pct=0,
            cagr_pct=0,
            max_drawdown_pct=0,
            sharpe_ratio=0,
            calmar_ratio=0,
            total_trades=0,
            win_rate=0,
            max_consecutive_losses=0,
            bankruptcy_occurred=bankruptcy,
        )
    
    total_return = (capital - initial_capital) / initial_capital * 100
    years = 6.3
    cagr = ((capital / initial_capital) ** (1 / years) - 1) * 100 if capital > 0 else -100
    
    returns_array = np.array(trade_returns)
    sharpe = (np.mean(returns_array) / np.std(returns_array) * np.sqrt(len(returns_array) / years)) if np.std(returns_array) > 0 else 0
    calmar = cagr / max_dd if max_dd > 0 else 0
    
    wins = sum(1 for r in trade_returns if r > 0)
    win_rate = wins / len(trade_returns) * 100
    
    return CompoundResult(
        strategy_name="",
        position_size=position_size,
        leverage=leverage,
        initial_capital=initial_capital,
        final_capital=capital,
        total_return_pct=total_return,
        cagr_pct=cagr,
        max_drawdown_pct=max_dd,
        sharpe_ratio=sharpe,
        calmar_ratio=calmar,
        total_trades=len(trade_returns),
        win_rate=win_rate,
        max_consecutive_losses=max_consecutive_losses,
        bankruptcy_occurred=bankruptcy,
    )


def main():
    from crypto_backtest.detection.enhanced_rules.detector import (
        EnhancedLShapeDetector,
        EnhancedDetectorConfig,
    )
    
    print("Loading ETHUSDT hourly data...")
    df = load_eth_hourly()
    print(f"Loaded {len(df)} bars")
    
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    
    print("\nDetecting signals with optimal config...")
    config = EnhancedDetectorConfig(
        drop_atr_multiplier=2.5,
        consolidation_atr_multiplier=1.5,
        flatness_threshold=0.4,
        volume_decline_required=False,
        min_confidence=0.6,
    )
    
    detector = EnhancedLShapeDetector(config)
    detections = detector.detect_batch_vectorized(df, ma_column='ma_50', min_idx=200)
    signal_indices = [d[0] for d in detections]
    print(f"Found {len(signal_indices)} signals")
    
    tp, sl, hc = 15.0, 2.0, 5.0
    
    print("\nCalculating Kelly Criterion...")
    simple_returns = []
    for entry_idx in signal_indices:
        if entry_idx >= len(close) - 1:
            continue
        entry_price = close[entry_idx]
        half_closed = False
        current_sl = sl
        
        for i in range(entry_idx + 1, min(entry_idx + 200, len(close))):
            pnl_low = (low[i] - entry_price) / entry_price * 100
            pnl_high = (high[i] - entry_price) / entry_price * 100
            
            if pnl_low <= -current_sl:
                simple_returns.append((hc / 2) if half_closed else -sl)
                break
            if not half_closed and pnl_high >= hc:
                half_closed = True
                current_sl = 0.0
            if pnl_high >= tp:
                simple_returns.append((hc / 2 + tp / 2) if half_closed else tp)
                break
        else:
            end_idx = min(entry_idx + 199, len(close) - 1)
            pnl = (close[end_idx] - entry_price) / entry_price * 100
            simple_returns.append((hc / 2 + pnl / 2) if half_closed else pnl)
    
    wins = [r for r in simple_returns if r > 0]
    losses = [r for r in simple_returns if r < 0]
    
    win_rate = len(wins) / len(simple_returns)
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0
    
    kelly = calculate_kelly_criterion(win_rate, avg_win, avg_loss)
    
    print(f"\n{'='*80}")
    print("KELLY CRITERION ANALYSIS")
    print(f"{'='*80}")
    print(f"Win Rate: {win_rate*100:.1f}%")
    print(f"Avg Win: +{avg_win:.2f}%")
    print(f"Avg Loss: {avg_loss:.2f}%")
    print(f"Full Kelly: {kelly*100:.1f}% of capital per trade")
    print(f"Half Kelly (recommended): {kelly*50:.1f}% of capital per trade")
    print(f"Quarter Kelly (conservative): {kelly*25:.1f}% of capital per trade")
    
    print(f"\n{'='*80}")
    print("RUNNING POSITION SIZING SIMULATIONS")
    print(f"{'='*80}")
    
    position_sizes = [0.1, 0.2, 0.3, 0.5, kelly * 0.5, kelly, 1.0]
    leverages = [1.0, 2.0, 3.0, 5.0, 10.0]
    
    results = []
    
    for ps in tqdm(position_sizes, desc="Position sizes"):
        for lev in leverages:
            result = run_compound_backtest(
                high, low, close, signal_indices,
                tp, sl, hc,
                position_size=ps,
                leverage=lev,
                initial_capital=10000.0,
            )
            result = CompoundResult(
                strategy_name=f"PS={ps*100:.0f}%_Lev={lev}x",
                **{k: v for k, v in result.__dict__.items() if k != 'strategy_name'}
            )
            results.append(result)
    
    results_df = pl.DataFrame([r.__dict__ for r in results])
    
    print(f"\n{'='*80}")
    print("TOP 10 BY CALMAR RATIO (CAGR/MDD) - RISK-ADJUSTED")
    print(f"{'='*80}")
    top_calmar = results_df.filter(
        (pl.col('bankruptcy_occurred') == False) & (pl.col('max_drawdown_pct') < 50)
    ).sort('calmar_ratio', descending=True).head(10)
    print(top_calmar.select([
        'strategy_name', 'final_capital', 'total_return_pct', 'cagr_pct',
        'max_drawdown_pct', 'sharpe_ratio', 'calmar_ratio'
    ]))
    
    print(f"\n{'='*80}")
    print("TOP 10 BY TOTAL RETURN (Survived, MDD < 80%)")
    print(f"{'='*80}")
    top_return = results_df.filter(
        (pl.col('bankruptcy_occurred') == False) & (pl.col('max_drawdown_pct') < 80)
    ).sort('total_return_pct', descending=True).head(10)
    print(top_return.select([
        'strategy_name', 'final_capital', 'total_return_pct', 'cagr_pct',
        'max_drawdown_pct', 'calmar_ratio'
    ]))
    
    print(f"\n{'='*80}")
    print("BANKRUPTCY ANALYSIS")
    print(f"{'='*80}")
    bankruptcies = results_df.filter(pl.col('bankruptcy_occurred') == True)
    print(f"Bankruptcies: {len(bankruptcies)} / {len(results)}")
    if len(bankruptcies) > 0:
        print(bankruptcies.select(['strategy_name', 'leverage', 'position_size', 'max_consecutive_losses']))
    
    print(f"\n{'='*80}")
    print("OPTIMAL STRATEGY RECOMMENDATION")
    print(f"{'='*80}")
    
    safe_results = results_df.filter(
        (pl.col('bankruptcy_occurred') == False) & 
        (pl.col('max_drawdown_pct') < 30) &
        (pl.col('total_return_pct') > 0)
    ).sort('calmar_ratio', descending=True)
    
    if len(safe_results) > 0:
        best = safe_results.head(1).to_dicts()[0]
        print(f"\nBest Safe Strategy: {best['strategy_name']}")
        print(f"  Position Size: {best['position_size']*100:.1f}% per trade")
        print(f"  Leverage: {best['leverage']}x")
        print(f"  Initial Capital: ${best['initial_capital']:,.0f}")
        print(f"  Final Capital: ${best['final_capital']:,.0f}")
        print(f"  Total Return: {best['total_return_pct']:.1f}%")
        print(f"  CAGR: {best['cagr_pct']:.1f}%")
        print(f"  Max Drawdown: {best['max_drawdown_pct']:.1f}%")
        print(f"  Sharpe Ratio: {best['sharpe_ratio']:.2f}")
        print(f"  Calmar Ratio: {best['calmar_ratio']:.2f}")
        print(f"  Win Rate: {best['win_rate']:.1f}%")
        print(f"  Total Trades: {best['total_trades']}")
    
    moderate_results = results_df.filter(
        (pl.col('bankruptcy_occurred') == False) & 
        (pl.col('max_drawdown_pct') < 50) &
        (pl.col('total_return_pct') > 100)
    ).sort('calmar_ratio', descending=True)
    
    if len(moderate_results) > 0:
        best_mod = moderate_results.head(1).to_dicts()[0]
        print(f"\nBest Moderate Risk Strategy: {best_mod['strategy_name']}")
        print(f"  Final Capital: ${best_mod['final_capital']:,.0f}")
        print(f"  Total Return: {best_mod['total_return_pct']:.1f}%")
        print(f"  CAGR: {best_mod['cagr_pct']:.1f}%")
        print(f"  Max Drawdown: {best_mod['max_drawdown_pct']:.1f}%")
        print(f"  Calmar Ratio: {best_mod['calmar_ratio']:.2f}")
    
    output_path = Path('outputs/compound_backtest_results.parquet')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.write_parquet(output_path)
    print(f"\nSaved results to {output_path}")
    
    return results_df, kelly, win_rate, avg_win, avg_loss


if __name__ == '__main__':
    import warnings
    warnings.filterwarnings('ignore')
    main()
