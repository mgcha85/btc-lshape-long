---
layout: default
title: Detection Quality Analysis
nav_order: 11
description: "L-Shape 패턴 감지 품질 및 TP/SL 분석"
permalink: /detection-quality
---

# Detection Quality Analysis

ㄴ자 패턴 감지의 품질과 Take Profit / Stop Loss 적중률 분석입니다.

---

## Summary

| Metric | BTCUSDT | ETHUSDT |
|:-------|--------:|--------:|
| **Total Trades** | 244 | 321 |
| **Win Rate** | 43.0% | 41.7% |
| **TP Hit Rate** | ~28% | ~27% |
| **HC + TP Rate** | ~15% | ~15% |
| **SL Hit Rate** | ~57% | ~58% |
| **Profit Factor** | 1.36 | 1.36 |

{: .note }
> **손익비 3:1 (TP 10% : SL 3%)** 로 낮은 승률에도 수익 창출

---

## Exit Type Distribution

### Trade Outcomes

반익절 (Half Close) 적용 시 발생 가능한 청산 유형:

| Exit Type | Description | Profit Range |
|:----------|:------------|:-------------|
| **Full TP** | TP 10% 도달 후 전량 청산 | +7.5% |
| **HC + TP** | 5%에서 50% 익절 → 잔여 10%에서 청산 | +7.5% |
| **HC + BE** | 5%에서 50% 익절 → 본절 SL 청산 | +2.5% |
| **Full SL** | SL -3% 도달 후 전량 청산 | -3.0% |

### Estimated Distribution (from profit patterns)

**BTCUSDT (244 trades):**

| Exit Type | Count | Percentage | Avg Profit |
|:----------|------:|----------:|----------:|
| Full TP | ~68 | 28% | +7.5% |
| HC + TP | ~37 | 15% | +7.5% |
| HC + BE | ~0 | 0% | +2.5% |
| Full SL | ~139 | 57% | -3.0% |

**ETHUSDT (321 trades):**

| Exit Type | Count | Percentage | Avg Profit |
|:----------|------:|----------:|----------:|
| Full TP | ~87 | 27% | +7.5% |
| HC + TP | ~47 | 15% | +7.5% |
| HC + BE | ~0 | 0% | +2.5% |
| Full SL | ~187 | 58% | -3.0% |

{: .highlight }
> **HC + BE (본절 청산) 케이스 거의 발생 안함** - Half Close 도달 후 대부분 Full TP까지 진행

---

## Monthly Performance Analysis

### High-Quality Detection Months

**Win Rate ≥ 60% 월 (BTCUSDT):**

| Month | Profit | Trades | Win Rate | Pattern |
|:------|-------:|-------:|---------:|:--------|
| 2020-01 | +10.0% | 2 | 100% | COVID 회복 초기 |
| 2020-08 | +7.5% | 3 | 100% | 여름 상승장 |
| 2020-10 | +5.0% | 2 | 100% | 10월 랠리 전 |
| 2021-02 | +24.5% | 6 | 83% | 불마켓 최고점 전 |
| 2023-01 | +10.0% | 2 | 100% | 베어 종료 후 |
| 2024-02 | +7.5% | 1 | 100% | BTC ETF 후 |
| 2024-11 | +15.0% | 2 | 100% | 연말 랠리 |

**Win Rate ≥ 60% 월 (ETHUSDT):**

| Month | Profit | Trades | Win Rate | Pattern |
|:------|-------:|-------:|---------:|:--------|
| 2020-02 | +17.5% | 3 | 100% | DeFi Summer 전 |
| 2020-07 | +7.5% | 1 | 100% | ETH 2.0 기대 |
| 2020-11 | +22.0% | 5 | 80% | 불마켓 시작 |
| 2021-05 | +7.5% | 1 | 100% | ATH 전 |
| 2024-12 | +22.0% | 5 | 80% | 연말 랠리 |
| 2025-06 | +10.0% | 2 | 100% | - |
| 2025-08 | +19.5% | 4 | 75% | - |

### Low-Quality Detection Months

**Win Rate ≤ 25% 월 (BTCUSDT):**

| Month | Profit | Trades | Win Rate | Pattern |
|:------|-------:|-------:|---------:|:--------|
| 2020-06 | -9.0% | 3 | 0% | 횡보장 |
| 2021-01 | -4.5% | 5 | 20% | ATH 후 조정 |
| 2022-06 | -9.5% | 5 | 20% | Terra 붕괴 후 |
| 2022-08 | -9.5% | 5 | 20% | 베어마켓 심화 |
| 2022-10 | -6.0% | 2 | 0% | FTX 전 |
| 2025-02 | -9.0% | 3 | 0% | 조정 |

**Win Rate ≤ 25% 월 (ETHUSDT):**

| Month | Profit | Trades | Win Rate | Pattern |
|:------|-------:|-------:|---------:|:--------|
| 2020-08 | -10.5% | 7 | 14% | 과열 후 조정 |
| 2021-01 | -3.0% | 1 | 0% | 신호 미스 |
| 2022-04 | -12.0% | 4 | 0% | Terra 하락 시작 |
| 2022-06 | -9.0% | 3 | 0% | 베어마켓 |
| 2023-02 | -9.0% | 3 | 0% | - |
| 2025-01 | -15.5% | 7 | 14% | - |

---

## Pattern Quality by Market Phase

### Bull Market Performance

**2020-2021 Bull Run:**

| Asset | Total Profit | Trades | Win Rate |
|:------|------------:|-------:|---------:|
| BTCUSDT | +67.5% | 109 | 45% |
| ETHUSDT | +107.0% | 125 | 43% |

### Bear Market Performance

**2022 Bear Market:**

| Asset | Total Profit | Trades | Win Rate |
|:------|------------:|-------:|---------:|
| BTCUSDT | **-39.0%** | 47 | 30% |
| ETHUSDT | **+1.5%** | 53 | 40% |

{: .warning }
> **ETH는 베어마켓에서도 수익** - 더 안정적인 패턴 인식

### Recovery Phase

**2023-2024 Recovery:**

| Asset | Total Profit | Trades | Win Rate |
|:------|------------:|-------:|---------:|
| BTCUSDT | +88.0% | 54 | 56% |
| ETHUSDT | +33.5% | 70 | 39% |

---

## Signal Quality Metrics

### Best Trade Distribution

**Top 10% Trades (profit ≥ 7.5%):**

| Asset | Count | % of Total | Avg Profit |
|:------|------:|----------:|----------:|
| BTCUSDT | ~105 | 43% | +7.5% |
| ETHUSDT | ~134 | 42% | +7.5% |

### Worst Trade Distribution

**Bottom 10% Trades (profit = -3%):**

| Asset | Count | % of Total | Avg Profit |
|:------|------:|----------:|----------:|
| BTCUSDT | ~139 | 57% | -3.0% |
| ETHUSDT | ~187 | 58% | -3.0% |

---

## Detection Improvement Opportunities

### 1. 베어마켓 필터

현재: 모든 시장 조건에서 동일한 감지 로직
개선: 200일 MA 아래에서 감지 억제 또는 파라미터 조정

**예상 효과 (BTC 2022):**
- Before: -39% (47 trades, 30% win)
- After: ~0% (신호 대부분 필터링)

### 2. 변동성 필터

현재: 고정 consolidation_range_pct (3%)
개선: ATR 기반 동적 범위 조정

**고변동성 시기:**
- ATR 높을 때 → range 완화 (4-5%)
- ATR 낮을 때 → range 강화 (2%)

### 3. 볼륨 확인

현재: 볼륨 무시
개선: MA 돌파 시 평균 볼륨 1.5배 이상 요구

**기대 효과:**
- False breakout 감소
- 승률 5-10% 개선 예상

### 4. 시간대 필터

**분석 결과 (승률 by 시간):**
- UTC 00:00-08:00: 평균 승률
- UTC 08:00-16:00: 높은 승률 (아시아+유럽)
- UTC 16:00-24:00: 낮은 승률 (미국장 초기)

---

## Quality Score Model

### Proposed Scoring (0-100)

| Factor | Weight | Criteria |
|:-------|-------:|:---------|
| Trend Alignment | 30% | Price > 200 MA |
| Volume Confirmation | 25% | Volume > 1.5x avg |
| Drop Quality | 20% | Clean drop, not choppy |
| Consolidation Quality | 15% | Tight range, low wick |
| Time of Day | 10% | Optimal trading hours |

### Expected Performance by Score

| Score Range | Estimated Win Rate | Recommendation |
|:------------|-------------------:|:---------------|
| 80-100 | 60-70% | Aggressive entry |
| 60-79 | 45-55% | Normal entry |
| 40-59 | 30-40% | Reduced size |
| 0-39 | <30% | Skip signal |

---

## Key Insights

### 1. 패턴 품질과 시장 상태

- **상승장**: 높은 품질 신호, 40-50% 승률
- **하락장**: 낮은 품질 신호, 25-35% 승률
- **횡보장**: 중간 품질, 35-45% 승률

### 2. ETH vs BTC

- ETH가 BTC보다 **베어마켓에서 안정적**
- 동일 파라미터에서 ETH의 Profit/MDD 2.5배 우수
- 추천: ETH 비중 확대 또는 단독 운용

### 3. 개선 우선순위

1. **즉시 적용 가능**: 200일 MA 트렌드 필터
2. **중기 개선**: 볼륨 확인 로직 추가
3. **장기 연구**: Quality Score 모델 개발

---

## Data Sources

- **기간**: 2020-01 ~ 2026-04
- **타임프레임**: 1시간봉
- **데이터**: Binance Futures OHLCV
- **분석 기준일**: {{ site.time | date: "%Y-%m-%d" }}
