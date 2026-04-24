# L-Shape Long Strategy Note

## Strategy Overview

**Name**: Enhanced L-Shape Long Strategy  
**Asset**: ETHUSDT Perpetual Futures  
**Exchange**: Binance Futures  
**Version**: 1.0  
**Date**: 2026-04-25

## Pattern Definition

L-Shape 패턴은 급락 후 횡보 구간을 거쳐 MA 돌파 시 롱 진입하는 패턴이다.

```
     ┌──────┐
     │ HIGH │ ← 이전 고점
     └──┬───┘
        │
        ▼ ATR 기반 하락 (drop_atr_mult × ATR)
        │
   ┌────┴────────────────────┐
   │  횡보 구간 (consolidation) │ ← ATR 기반 범위
   │  range < consol_atr_mult × ATR │
   └─────────────────┬───────┘
                     │
                     ▲ MA 돌파 → LONG 진입
```

## Entry Conditions (Enhanced Rules)

1. **선행 하락**: 최근 20봉 내 `drop_atr_mult × ATR(14)` 이상 하락
2. **횡보 확인**: 최근 N봉 범위가 `consol_atr_mult × ATR(14)` 이내
3. **MA 돌파**: 이전 봉 종가 < MA, 현재 봉 종가 > MA + 양봉

### Optimal ATR Multipliers

| Parameter | Value | Description |
|-----------|-------|-------------|
| `drop_atr_mult` | 2.5 | 하락 감지 임계값 |
| `consol_atr_mult` | 1.5 | 횡보 범위 임계값 |

## Exit Conditions

- **Take Profit**: 진입가 +15%
- **Stop Loss**: 진입가 -2%
- **Half Close**: 진입가 +5% 도달 시 50% 익절 + SL을 본절로 이동

## Strategy Profiles

### 5M Balanced (Recommended)

| Parameter | Value |
|-----------|-------|
| Timeframe | 5m |
| Position Size | 20% |
| Leverage | 10x |
| Take Profit | 15% |
| Stop Loss | 2% |
| Half Close | 5% |

**Backtest Results (2021-2025, with fees)**:
- Return: 510.9%
- CAGR: 33.4%
- Max DD: 32.0%
- Calmar: 1.05
- Win Rate: 45.5%
- Trades: 334
- Avg Holding: 12.7h

### 5M Aggressive

| Parameter | Value |
|-----------|-------|
| Position Size | 30% |
| Leverage | 10x |

**Backtest Results**:
- Return: 1,012.0%
- CAGR: 46.8%
- Max DD: 46.3%
- Calmar: 1.01

### 15M Aggressive

| Parameter | Value |
|-----------|-------|
| Timeframe | 15m |
| Position Size | 30% |
| Leverage | 10x |

**Backtest Results**:
- Return: 1,862.4%
- CAGR: 60.7%
- Max DD: 69.9%
- Calmar: 0.87

## Fee Structure

| Fee Type | Rate |
|----------|------|
| Maker | 0.02% |
| Taker | 0.05% |
| Funding (avg) | 0.01% / 8h |

5M 전략이 최적인 이유: 평균 보유 시간 12.7시간으로 펀딩 비용 최소화

## Risk Management

1. **Position Sizing**: Kelly Criterion 기반
   - Full Kelly: 15.9%
   - Half Kelly (권장): 8.0%
   - 실제 적용: 20% (보수적 버퍼)

2. **Stop Loss**: 2% (타이트)
3. **Half Close**: 5% 도달 시 50% 익절 → 본절 SL

## Implementation Status

### Backtest ✅
- [x] Basic backtest engine
- [x] Parametric study (MA, TP, SL, HC)
- [x] Enhanced rules (ATR-based detection)
- [x] Realistic fees simulation
- [x] Multi-timeframe comparison

### Live Trading ✅
- [x] Go engine with Binance API
- [x] Enhanced L-shape detector (ATR-based)
- [x] 3 strategy profiles
- [x] Svelte frontend (Dashboard/History/Settings)
- [ ] F/E → B/E static serving integration
- [ ] Testnet validation

## Validation Checklist

- [x] Backtest CAGR > 30%
- [x] Max DD < 50% (5M Balanced: 32%)
- [x] Calmar > 1.0 (5M Balanced: 1.05)
- [x] Win Rate > 40%
- [x] Sufficient trades (>300)
- [ ] Testnet paper trading (1 week)
- [ ] Production deployment

## Files

- Backtest engine: `src/crypto_backtest/long_strategy.py`
- Parametric study: `scripts/run_realistic_backtest.py`
- Go engine: `live-trading/engine/`
- Svelte frontend: `live-trading/frontend/`
- Results page: `docs/realistic-backtest.md`

## References

- [Enhanced Strategy](enhanced-strategy.md)
- [Realistic Backtest Results](realistic-backtest.md)
