---
layout: default
title: Realistic Backtest Results
nav_order: 16
description: "Backtest with Trading Fees and Funding Costs"
permalink: /realistic-backtest
---

# Realistic Backtest Results

수수료 + 펀딩비 포함 실전 백테스트 결과 (ETHUSDT, 2020-2026)

---

## 수수료 구조

### Binance USDT-M Perpetual Futures (VIP 0)

| 항목 | 비율 | 설명 |
|:-----|:-----|:-----|
| **Maker Fee** | 0.02% | 지정가 주문 |
| **Taker Fee** | 0.05% | 시장가 주문 |
| **Funding Rate** | ~0.01%/8h | 포지션 유지 비용 |

**라운드 트립 비용 (시장가 기준):** 0.10% + 펀딩비

---

## 전략 프로필

| 프로필 | Position Size | Leverage | TP | SL | HC |
|:-------|:------------:|:--------:|:--:|:--:|:--:|
| 🟢 Conservative | 10% | 5x | 15% | 2% | 5% |
| 🟡 Balanced | 20% | 10x | 15% | 2% | 5% |
| 🔴 Aggressive | 30% | 10x | 15% | 2% | 5% |

---

## 타임프레임별 결과 비교

### 📊 핵심 지표 요약

<div class="stat-grid" markdown="0">
  <div class="stat-card green">
    <div class="stat-value">5M</div>
    <div class="stat-label">Best Calmar</div>
  </div>
  <div class="stat-card gold">
    <div class="stat-value">1.05</div>
    <div class="stat-label">Balanced 5M</div>
  </div>
  <div class="stat-card blue">
    <div class="stat-value">45.5%</div>
    <div class="stat-label">5M Win Rate</div>
  </div>
  <div class="stat-card red">
    <div class="stat-value">32%</div>
    <div class="stat-label">5M MDD</div>
  </div>
</div>

---

## 5분봉 (5M) - 🏆 Best Risk-Adjusted

| 프로필 | Final Capital | Return | CAGR | MDD | Calmar | Win Rate | Trades |
|:-------|-------------:|-------:|-----:|----:|-------:|--------:|-------:|
| 🟢 Conservative | $17,037 | 70% | 8.9% | 8.6% | **1.03** | 45.5% | 334 |
| 🟡 **Balanced** | $61,094 | **511%** | **33.4%** | 32.0% | **1.05** | 45.5% | 334 |
| 🔴 Aggressive | $111,200 | 1,012% | 46.8% | 46.3% | 1.01 | 45.5% | 334 |

**특징:**
- ✅ 최고 승률 (45.5%)
- ✅ 최고 Calmar Ratio (1.05)
- ✅ 가장 낮은 평균 보유시간 (12.7h) → 펀딩비 최소화
- ✅ 가장 낮은 MDD (Conservative 8.6%)

**비용 분석:**
- 평균 수수료: $30,870
- 평균 펀딩비: $4,267
- 거래당 비용: $105.20

---

## 15분봉 (15M)

| 프로필 | Final Capital | Return | CAGR | MDD | Calmar | Win Rate | Trades |
|:-------|-------------:|-------:|-----:|----:|-------:|--------:|-------:|
| 🟢 Conservative | $19,535 | 95% | 11.3% | 15.5% | 0.73 | 42.4% | 255 |
| 🟡 Balanced | $94,927 | 849% | 43.1% | 52.8% | 0.82 | 42.4% | 255 |
| 🔴 Aggressive | $196,237 | **1,862%** | **60.7%** | 69.9% | 0.87 | 42.4% | 255 |

**특징:**
- 📈 최고 절대 수익률 (Aggressive 1,862%)
- ⚖️ 중간 수준의 승률과 MDD
- ⏱️ 평균 보유시간 28.2h

**비용 분석:**
- 평균 수수료: $32,015
- 평균 펀딩비: $9,421
- 거래당 비용: $162.50

---

## 1시간봉 (1H)

| 프로필 | Final Capital | Return | CAGR | MDD | Calmar | Win Rate | Trades |
|:-------|-------------:|-------:|-----:|----:|-------:|--------:|-------:|
| 🟢 Conservative | $19,519 | 95% | 11.2% | 17.3% | 0.65 | 35.9% | 167 |
| 🟡 Balanced | $91,005 | 810% | 42.2% | 55.6% | 0.76 | 35.9% | 167 |
| 🔴 Aggressive | $179,985 | 1,700% | 58.5% | 72.9% | 0.80 | 35.9% | 167 |

**특징:**
- ⏱️ 가장 긴 평균 보유시간 (59.7h) → 펀딩비 증가
- 📉 가장 낮은 승률 (35.9%)
- 🔢 가장 적은 거래 수 (167)

**비용 분석:**
- 평균 수수료: $13,996
- 평균 펀딩비: $9,546
- 거래당 비용: $140.97

---

## 종합 비교

### Calmar Ratio 순위 (Risk-Adjusted Performance)

| 순위 | 전략 | Calmar | Return | MDD |
|:----:|:-----|-------:|-------:|----:|
| 🥇 | **5M Balanced** | **1.05** | 511% | 32% |
| 🥈 | 5M Conservative | 1.03 | 70% | 8.6% |
| 🥉 | 5M Aggressive | 1.01 | 1,012% | 46% |
| 4 | 15M Aggressive | 0.87 | 1,862% | 70% |
| 5 | 15M Balanced | 0.82 | 849% | 53% |
| 6 | 1H Aggressive | 0.80 | 1,700% | 73% |

### 절대 수익 순위

| 순위 | 전략 | Return | CAGR | MDD |
|:----:|:-----|-------:|-----:|----:|
| 🥇 | 15M Aggressive | **1,862%** | 60.7% | 70% |
| 🥈 | 1H Aggressive | 1,700% | 58.5% | 73% |
| 🥉 | 5M Aggressive | 1,012% | 46.8% | 46% |

---

## 수수료 영향 분석

### 수수료 없는 결과 vs 수수료 포함 결과 (Balanced 기준)

| 타임프레임 | 수수료 전 | 수수료 후 | 감소율 |
|:-----------|----------:|----------:|-------:|
| 1H | 1,480% | 810% | **-45%** |
| 15M | ~1,200% | 849% | ~-29% |
| 5M | ~700% | 511% | ~-27% |

{: .warning }
> **수수료 영향**: 1H는 수수료 + 높은 펀딩비로 **수익 45% 감소**. 5M은 짧은 보유 시간으로 펀딩비 최소화.

---

## 권장 전략

### 🏆 Best Overall: 5M Balanced

```
Position Size: 20%
Leverage: 10x
Take Profit: 15%
Stop Loss: 2%
Half Close: 5%

Expected Results:
- CAGR: 33.4%
- Max DD: 32.0%
- Calmar: 1.05
- Win Rate: 45.5%
- Avg Holding: 12.7 hours
```

**장점:**
1. 최고 리스크 조정 수익률 (Calmar 1.05)
2. 짧은 보유시간 → 펀딩비 최소화
3. 높은 승률 (45.5%)
4. 관리 가능한 MDD (32%)

### 🛡️ Safest: 5M Conservative

```
Position Size: 10%
Leverage: 5x

Expected Results:
- CAGR: 8.9%
- Max DD: 8.6%
- Calmar: 1.03
```

**적합 대상:** 낮은 변동성, 꾸준한 성장 추구

### 🚀 Highest Return: 15M Aggressive

```
Position Size: 30%
Leverage: 10x

Expected Results:
- CAGR: 60.7%
- Max DD: 69.9%
- Return: 1,862%
```

**적합 대상:** 높은 리스크 감수 가능, 최대 수익 추구

---

## 주의사항

{: .warning }
> **펀딩비 변동**: 실제 펀딩비는 시장 상황에 따라 크게 변동. 강세장에서는 롱 포지션에 불리 (최대 0.1%/8h).

{: .note }
> **슬리피지 미포함**: 실제 거래 시 슬리피지 0.01-0.05% 추가 고려 필요.

{: .important }
> **5분봉 권장 이유**: 동일 전략에서 5분봉이 1시간봉 대비 높은 승률 + 낮은 펀딩비 → 최적의 리스크/리턴.

---

## 관련 문서

- [Enhanced Strategy (수수료 미포함)](/enhanced-strategy)
- [파라미터 최적화](/optimization)
- [Multi-Asset 분석](/multi-asset-1h)
