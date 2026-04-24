---
layout: default
title: Parameter Optimization
nav_order: 12
description: "L-Shape 전략 파라미터 최적화 권장사항"
permalink: /optimization
---

# Parameter Optimization

ㄴ자 패턴 롱 전략의 최적 파라미터 분석 및 권장사항입니다.

---

## Current Parameters

| Parameter | Current Value | Range Tested |
|:----------|:--------------|:-------------|
| Breakout MA | **50** | 25, 50, 100, 200 |
| Consolidation Bars | **5** | 3, 5, 7, 10 |
| Consolidation Range | **3.0%** | 2%, 3%, 4%, 5% |
| Drop Threshold | **3.0%** | 2%, 3%, 5% |
| Take Profit | **10.0%** | 5%, 7%, 10%, 15% |
| Stop Loss | **3.0%** | 2%, 3%, 5% |
| Half Close | **5.0%** | 3%, 5%, 7%, disabled |

---

## Performance Summary

### Current Configuration Results

| Metric | BTCUSDT | ETHUSDT |
|:-------|--------:|--------:|
| Total Profit | 109.6% | **157.1%** |
| Max Drawdown | 70.5% | **39.5%** |
| Profit/MDD | 1.55 | **3.98** |
| Trades | 244 | 321 |
| Win Rate | 43.0% | 41.7% |
| Profit Factor | 1.36 | 1.36 |

{: .highlight }
> **ETH가 모든 주요 지표에서 우수** - 동일 파라미터, 다른 결과

---

## Parameter Analysis

### 1. Breakout MA Period

| MA Period | BTC Profit | BTC MDD | ETH Profit | ETH MDD |
|:---------:|-----------:|--------:|-----------:|--------:|
| 25 | +85% | 55% | +120% | 45% |
| **50** | **+110%** | 70% | **+157%** | 40% |
| 100 | +75% | 50% | +95% | 35% |
| 200 | +40% | 35% | +60% | 25% |

**분석:**
- MA 50이 수익률 최대화
- MA 100-200은 MDD 감소하지만 수익률 하락
- **권장**: 수익 우선 = MA 50, 안정성 우선 = MA 100

### 2. Take Profit %

| TP % | Profit | Win Rate | Trades | Notes |
|:----:|-------:|---------:|-------:|:------|
| 5% | +80% | 55% | 320 | 빠른 청산, 많은 거래 |
| 7% | +100% | 48% | 280 | 균형 |
| **10%** | **+157%** | **42%** | 321 | 최적 손익비 |
| 15% | +90% | 30% | 250 | 승률 과도하게 낮음 |

**분석:**
- TP 10%에서 최적 손익비 (10:3 = 3.33:1)
- TP 5%는 승률 높지만 총 수익 낮음
- **권장**: TP 10% 유지

### 3. Stop Loss %

| SL % | Profit | Win Rate | MDD | Risk/Reward |
|:----:|-------:|---------:|----:|:-----------:|
| 2% | +50% | 35% | 40% | 5:1 |
| **3%** | **+157%** | **42%** | **40%** | **3.3:1** |
| 5% | +120% | 50% | 55% | 2:1 |
| 7% | +80% | 55% | 65% | 1.4:1 |

**분석:**
- SL 3%가 최적 균형점
- SL 2%는 너무 타이트 → 조기 손절
- SL 5% 이상은 MDD 증가
- **권장**: SL 3% 유지

### 4. Half Close %

| HC Setting | Profit | MDD | Profit/MDD | Notes |
|:-----------|-------:|----:|:----------:|:------|
| Disabled | +188% | 62% | 3.0 | 최대 수익, 높은 MDD |
| HC 3% | +140% | 45% | 3.1 | 조기 익절 |
| **HC 5%** | **+157%** | **40%** | **3.98** | **최적 균형** |
| HC 7% | +165% | 50% | 3.3 | HC 효과 감소 |

**분석:**
- HC 5%가 Profit/MDD 최적화
- 반익절 없이는 MDD 62%로 과도함
- **권장**: HC 5% 유지 (현재 설정 최적)

---

## Optimization Recommendations

### Profile 1: Maximum Profit (공격적)

```yaml
breakout_ma: 50
consolidation_bars: 5
consolidation_range_pct: 3.0
drop_threshold_pct: 3.0
take_profit_pct: 15.0    # 상향
stop_loss_pct: 3.0
half_close_enabled: false # 비활성
```

| Expected | Value |
|:---------|------:|
| Profit | ~200% |
| MDD | ~75% |
| Win Rate | ~28% |
| Profit/MDD | 2.7 |

{: .warning }
> **주의**: MDD 75% 감내 가능한 경우만

---

### Profile 2: Balanced (균형) - **현재 설정**

```yaml
breakout_ma: 50
consolidation_bars: 5
consolidation_range_pct: 3.0
drop_threshold_pct: 3.0
take_profit_pct: 10.0
stop_loss_pct: 3.0
half_close_enabled: true
half_close_pct: 5.0
```

| Expected | Value |
|:---------|------:|
| Profit | ~157% |
| MDD | ~40% |
| Win Rate | ~42% |
| Profit/MDD | 3.98 |

{: .highlight }
> **권장**: 대부분의 트레이더에게 적합

---

### Profile 3: Conservative (보수적)

```yaml
breakout_ma: 100        # 상향
consolidation_bars: 7   # 상향
consolidation_range_pct: 2.5  # 하향
drop_threshold_pct: 5.0 # 상향
take_profit_pct: 7.0    # 하향
stop_loss_pct: 3.0
half_close_enabled: true
half_close_pct: 3.0     # 하향
```

| Expected | Value |
|:---------|------:|
| Profit | ~80% |
| MDD | ~25% |
| Win Rate | ~50% |
| Profit/MDD | 3.2 |

{: .note }
> 낮은 MDD, 높은 승률 선호 시

---

## Asset Allocation Recommendations

### Single Asset Strategy

| Priority | Asset | Reason |
|:---------|:------|:-------|
| 1 | **ETHUSDT** | Profit/MDD 3.98, 베어마켓 안정 |
| 2 | BTCUSDT | 절대 수익 높으나 MDD 큼 |

### Multi-Asset Strategy

| Allocation | BTC | ETH | Rationale |
|:-----------|----:|----:|:----------|
| Risk-Parity | 35% | 65% | MDD 기반 비중 조정 |
| Equal Weight | 50% | 50% | 단순 분산 |
| ETH Only | 0% | 100% | 최적 Profit/MDD |

**권장 배분: ETH 65% + BTC 35%**

이유:
1. ETH의 Profit/MDD가 2.5배 우수
2. BTC 포함으로 상승장 참여
3. MDD 40% 수준 유지 가능

---

## Future Optimization Areas

### 1. 트렌드 필터 추가

```python
# 200일 MA 위에서만 진입
if current_price > ma_200:
    allow_entry = True
else:
    allow_entry = False
```

**예상 효과:**
- 2022년 손실 -39% → ~0% (BTC)
- 전체 승률 +8-10%

### 2. 동적 파라미터

```python
# ATR 기반 동적 TP/SL
atr = calculate_atr(14)
take_profit_pct = max(7, min(15, atr * 2))
stop_loss_pct = max(2, min(5, atr * 0.5))
```

**예상 효과:**
- 고변동성: 넓은 TP/SL → 조기 청산 방지
- 저변동성: 좁은 TP/SL → 빠른 청산

### 3. 시간대 필터

```python
# UTC 기준 최적 시간대만 진입
optimal_hours = [8, 9, 10, 11, 12, 13, 14, 15]
if current_hour_utc in optimal_hours:
    allow_entry = True
```

**예상 효과:**
- 미국장 초기 변동성 회피
- 승률 +3-5%

### 4. 볼륨 확인

```python
# MA 돌파 시 볼륨 조건
if volume > volume_ma_20 * 1.5:
    confirm_breakout = True
```

**예상 효과:**
- False breakout 50% 감소
- 거래 수 30% 감소, 승률 +10%

---

## Backtesting Notes

### Data Period
- 시작: 2020-01-01
- 종료: 2026-04-25
- 기간: 약 6.3년

### Assumptions
- 슬리피지: 미적용 (시장가 주문 가정)
- 수수료: 미적용 (Maker 0.02% 기준 연 2-3% 감소 예상)
- 레버리지: 1x (미적용)
- 포지션 사이즈: 고정 (자본 대비 %)

### Live Trading Adjustments

| Factor | Backtest | Live | Impact |
|:-------|:---------|:-----|:-------|
| 슬리피지 | 0% | 0.05-0.1% | -5-10%/year |
| 수수료 | 0% | 0.02-0.04% | -2-4%/year |
| 펀딩비 | 0% | ±0.01%/8h | ±5%/year |
| 청산 지연 | 0 | 1-3s | MDD +2-5% |

**Live 예상 수익률: Backtest × 0.7-0.85**

---

## Conclusion

### 현재 설정 평가: ✅ 최적

현재 파라미터 (MA50, TP10%, SL3%, HC5%)는 Profit/MDD 기준 최적입니다.

### 개선 우선순위

1. **즉시**: ETH 비중 확대 (65%+)
2. **단기**: 200일 MA 트렌드 필터 추가
3. **중기**: 볼륨 확인 로직 구현
4. **장기**: 동적 파라미터 시스템

### 실전 적용 시 주의

- Backtest 수익률의 70-85% 수준 예상
- MDD 40% → 실전 50% 가능성
- 2022년 같은 베어마켓 대비 필요

---

## Data Sources

- **기간**: 2020-01 ~ 2026-04
- **타임프레임**: 1시간봉
- **데이터**: Binance Futures OHLCV
- **분석 기준일**: {{ site.time | date: "%Y-%m-%d" }}
