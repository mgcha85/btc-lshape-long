---
layout: default
title: Enhanced Strategy Results
nav_order: 15
description: "Enhanced L-Shape Detection with Kelly Criterion Position Sizing"
permalink: /enhanced-strategy
---

# Enhanced L-Shape Strategy Results

Enhanced Rule-Based Detection + Kelly Criterion Position Sizing 최적화 결과

---

## 전략 개선 사항

### 1. Enhanced Detection (ATR 기반)

기존 고정 퍼센트 대신 **ATR(Average True Range) 기반 동적 임계값** 적용:

| 파라미터 | 기존 | Enhanced |
|:---------|:-----|:---------|
| 하락 감지 | 고정 3% | ATR × 2.5 |
| 횡보 범위 | 고정 5% | ATR × 1.5 |
| 평탄도 체크 | 없음 | std/range ≤ 0.4 |
| 볼륨 확인 | 없음 | 선택적 |
| 신뢰도 필터 | 없음 | ≥ 0.6 |

### 2. Kelly Criterion Position Sizing

<div class="stat-grid" markdown="0">
  <div class="stat-card blue">
    <div class="stat-value">35.9%</div>
    <div class="stat-label">Win Rate</div>
  </div>
  <div class="stat-card green">
    <div class="stat-value">+6.4%</div>
    <div class="stat-label">Avg Win</div>
  </div>
  <div class="stat-card red">
    <div class="stat-value">-2.0%</div>
    <div class="stat-label">Avg Loss</div>
  </div>
  <div class="stat-card gold">
    <div class="stat-value">15.9%</div>
    <div class="stat-label">Full Kelly</div>
  </div>
</div>

**Kelly Criterion 공식:**

```
f* = (p × b - q) / b

p = 승률 = 35.9%
q = 패율 = 64.1%
b = 평균이익/평균손실 = 6.4/2.0 = 3.2

Full Kelly = 15.9% of capital per trade
Half Kelly (권장) = 8.0%
Quarter Kelly (보수적) = 4.0%
```

---

## 복리 백테스트 결과 (6.3년)

### 💰 최적 전략 (Risk-Adjusted)

**Calmar Ratio 기준 TOP 5** (MDD < 50% 필터)

| Strategy | Final Capital | Return | CAGR | MDD | Calmar |
|:---------|-------------:|-------:|-----:|----:|-------:|
| **PS=20% Lev=10x** | $158,028 | 1,480% | 55.0% | 48.3% | **1.14** |
| PS=100% Lev=2x | $158,028 | 1,480% | 55.0% | 48.3% | 1.14 |
| PS=16% Lev=10x | $99,572 | 896% | 44.0% | 40.5% | 1.09 |
| PS=30% Lev=5x | $88,855 | 789% | 41.4% | 38.6% | 1.07 |
| PS=50% Lev=3x | $88,855 | 789% | 41.4% | 38.6% | 1.07 |

### 🚀 최대 수익 전략

**Total Return 기준 TOP 5** (파산 없음, MDD < 80%)

| Strategy | Final Capital | Return | CAGR | MDD | Calmar |
|:---------|-------------:|-------:|-----:|----:|-------:|
| **PS=100% Lev=3x** | $408,667 | **3,987%** | 80.2% | 64.3% | 1.25 |
| PS=30% Lev=10x | $408,667 | 3,987% | 80.2% | 64.3% | 1.25 |
| PS=50% Lev=5x | $262,468 | 2,525% | 68.0% | 56.8% | 1.20 |
| PS=20% Lev=10x | $158,028 | 1,480% | 55.0% | 48.3% | 1.14 |
| PS=100% Lev=2x | $158,028 | 1,480% | 55.0% | 48.3% | 1.14 |

### 🛡️ 안전 전략

**MDD < 30% 필터**

| Strategy | Final Capital | Return | CAGR | MDD | Calmar |
|:---------|-------------:|-------:|-----:|----:|-------:|
| **PS=10% Lev=10x** | $46,455 | 365% | 27.6% | 27.4% | **1.01** |
| PS=20% Lev=5x | $46,455 | 365% | 27.6% | 27.4% | 1.01 |
| PS=50% Lev=2x | $46,455 | 365% | 27.6% | 27.4% | 1.01 |
| PS=100% Lev=1x | $46,455 | 365% | 27.6% | 27.4% | 1.01 |

---

## 권장 전략 프로필

### 🟢 Conservative (보수적)

```
Position Size: 10%
Leverage: 5x (또는 1x with 50%)
예상 CAGR: 27.6%
예상 MDD: 27.4%
Sharpe: 1.16
```

**적합 대상:** 안정적 수익 추구, 낮은 변동성 선호

### 🟡 Balanced (균형)

```
Position Size: 20%
Leverage: 10x (또는 2x with 100%)
예상 CAGR: 55.0%
예상 MDD: 48.3%
Calmar: 1.14
```

**적합 대상:** 중간 리스크 감수, Half Kelly 수준

### 🔴 Aggressive (공격적)

```
Position Size: 30%
Leverage: 10x
예상 CAGR: 80.2%
예상 MDD: 64.3%
```

**적합 대상:** 고수익 추구, 높은 변동성 감수 가능

---

## 핵심 인사이트

### 1. Effective Leverage 동치

동일 수익/리스크를 달성하는 조합:

| 조합 A | 조합 B | 결과 |
|:-------|:-------|:-----|
| PS=10% × Lev=10x | PS=100% × Lev=1x | 동일 |
| PS=20% × Lev=5x | PS=50% × Lev=2x | 동일 |
| PS=30% × Lev=10x | PS=100% × Lev=3x | 동일 |

**핵심:** `Effective Exposure = Position Size × Leverage`

### 2. 파산 위험

- **테스트한 35개 조합 중 파산: 0건**
- 이유: Enhanced Detection의 높은 신호 품질 (TP=15%, SL=2%)
- Win/Loss Ratio = 3.2:1 → 연속 손실에도 회복력 확보

### 3. 최적 포지션 사이징

| 방법론 | 권장값 | 특징 |
|:-------|:-------|:-----|
| Full Kelly | 15.9% | 이론적 최대, 변동성 높음 |
| **Half Kelly** | **8.0%** | 실전 권장, 안정적 복리 |
| Quarter Kelly | 4.0% | 초보수적, 느린 성장 |

---

## 실전 적용 가이드

### ETHUSDT 1H 전략 설정

```python
# Enhanced Detection Config
config = EnhancedDetectorConfig(
    drop_atr_multiplier=2.5,
    consolidation_atr_multiplier=1.5,
    flatness_threshold=0.4,
    volume_decline_required=False,
    min_confidence=0.6,
)

# Exit Config
take_profit_pct = 15.0
stop_loss_pct = 2.0
half_close_pct = 5.0

# Position Sizing (Balanced)
position_size = 0.20  # 20% of capital
leverage = 10  # or 2x with 100%
```

### 시뮬레이션 가정

| 항목 | 값 |
|:-----|:---|
| 초기 자본 | $10,000 |
| 기간 | 2019.12 ~ 2026.04 (6.3년) |
| 거래 수 | 167회 |
| 연평균 거래 | ~26회 |
| 수수료 | 미포함 (별도 고려 필요) |

---

## 주의사항

{: .warning }
> **레버리지 리스크**: 10x 레버리지는 -10% 하락 시 청산 위험. 실제 거래 시 청산 마진 고려 필수.

{: .note }
> **수수료 미반영**: 실제 거래 시 maker/taker 수수료 + 펀딩비 고려 시 수익률 약 20-30% 감소 예상.

{: .important }
> **과거 성과 ≠ 미래 수익**: 백테스트 결과는 과거 데이터 기반. 시장 구조 변화 시 성과 달라질 수 있음.

---

## 관련 문서

- [Enhanced Detection 구현](/detection-quality)
- [파라미터 최적화](/optimization)
- [Multi-Asset 분석](/multi-asset-1h)
