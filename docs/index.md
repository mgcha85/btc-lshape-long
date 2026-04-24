---
layout: default
title: Home
nav_order: 1
description: "비트코인 ㄴ자 패턴 롱 전략 백테스팅 및 ML/DL 분석"
permalink: /
---

<div class="hero-section" markdown="0">
  <span class="hero-badge">BTC / USDT · 4H / 1H / 15M / 5M</span>
  <h1>L-Shape Long Strategy</h1>
  <p class="hero-subtitle">급락 → 횡보 → MA 돌파 패턴을 포착하는 비트코인 롱 전략</p>
</div>

<div class="stat-grid" markdown="0">
  <div class="stat-card green">
    <div class="stat-value">1,480%</div>
    <div class="stat-label">Enhanced 복리 수익</div>
  </div>
  <div class="stat-card gold">
    <div class="stat-value">55%</div>
    <div class="stat-label">CAGR</div>
  </div>
  <div class="stat-card red">
    <div class="stat-value">48%</div>
    <div class="stat-label">Max DD</div>
  </div>
  <div class="stat-card blue">
    <div class="stat-value">1.14</div>
    <div class="stat-label">Calmar Ratio</div>
  </div>
</div>

---

## 전략 개요

ㄴ자(L-Shape) 패턴은 **급락 후 바닥을 다지며 횡보**하다가 **이동평균선(MA)을 돌파**할 때 매수하는 전략입니다.

```
     ┌──────┐
     │ HIGH │ ← 이전 고점
     └──┬───┘
        │
        ▼ 하락 (3%+ 이상)
        │
   ┌────┴────────────────────┐
   │  횡보 구간 (consolidation) │ ← ㄴ자의 바닥
   └─────────────────┬───────┘
                     │
                     ▲ MA100 돌파 → LONG 진입
```

| 구분 | 조건 | 기본값 |
|:-----|:-----|:-------|
| 선행 하락 | 최근 20봉 내 하락률 | ≥ 3% |
| 횡보 확인 | 최근 N봉 변동폭 | ≤ 5% |
| MA 돌파 | 이전 봉 < MA, 현재 봉 > MA + 양봉 | MA100 |
| Take Profit | 목표 수익 | +10% |
| Stop Loss | 손절 | -5% |
| Half Close | 반익절 후 본절 SL 이동 | +3% |

---

## 타임프레임별 비교

| 항목 | 4시간봉 | 1시간봉 | 15분봉 | 5분봉 |
|:-----|-------:|-------:|------:|------:|
| 총 수익률 | 104%* | **112.5%** | 160%* | 50%* |
| 최대 낙폭 | 48%* | **26%** | 35%* | 24.5%* |
| 승률 | 81%* | **69.7%** | 37%* | 45.2% |
| 수익/MDD | 2.17* | **4.33** | 4.56* | 2.04 |
| ML AUC | 0.56 | **0.62** | 0.53 | 0.55 |
| 거래 수 | 189* | 165 | 968* | 620 |

<small>* 반익절 적용 기준 (4H: HC2%, 15M: HC3%)</small>

{: .highlight }
> **1시간봉이 리스크 대비 수익률에서 가장 안정적**입니다.
> 15분봉은 반익절 적용 시 유사한 수익/MDD 비율을 달성합니다.

---

## 전략 비교

{: .highlight }
> **반익절(Half Close)** 적용 시 수익은 40% 줄지만, 최대 낙폭이 **58% 감소**합니다.

| 전략 | 총 수익 | 최대 낙폭 | 승률 | 수익/MDD |
|:-----|-------:|--------:|-----:|--------:|
| 공격적 (MA50, HC 없음) | 188.6% | 62% | 28.8% | 3.04 |
| **균형 (MA100, HC 3%)** | **112.5%** | **26%** | **69.7%** | **4.33** |
| 보수적 (MA100, HC 1%) | 75.5% | 16.5% | 88.4% | 4.58 |

---

## 문서 탐색

### 1시간봉 분석 (권장)

<div class="nav-cards" markdown="0">
  <a class="nav-card" href="{{ '/results-1h' | relative_url }}">
    <div class="nav-card-icon">📊</div>
    <div class="nav-card-title">1H 백테스트 결과</div>
    <div class="nav-card-desc">최적 설정 성과, 연도별 분석, 거래 시나리오</div>
  </a>
  <a class="nav-card" href="{{ '/parametric-1h' | relative_url }}">
    <div class="nav-card-icon">🔬</div>
    <div class="nav-card-title">1H 파라메트릭 스터디</div>
    <div class="nav-card-desc">960개 파라미터 조합 탐색 및 최적화</div>
  </a>
  <a class="nav-card" href="{{ '/ml-analysis-1h' | relative_url }}">
    <div class="nav-card-icon">🤖</div>
    <div class="nav-card-title">1H ML/DL 분석</div>
    <div class="nav-card-desc">AUC 0.62 - 의미있는 SL/TP 예측</div>
  </a>
</div>

### 5분봉 분석 (참고)

<div class="nav-cards" markdown="0">
  <a class="nav-card" href="{{ '/results-5m' | relative_url }}">
    <div class="nav-card-icon">📊</div>
    <div class="nav-card-title">5M 백테스트 결과</div>
    <div class="nav-card-desc">50% 수익, 24.5% MDD, 45% 승률</div>
  </a>
  <a class="nav-card" href="{{ '/parametric-5m' | relative_url }}">
    <div class="nav-card-icon">🔬</div>
    <div class="nav-card-title">5M 파라메트릭 스터디</div>
    <div class="nav-card-desc">729개 파라미터 조합 탐색</div>
  </a>
  <a class="nav-card" href="{{ '/ml-analysis-5m' | relative_url }}">
    <div class="nav-card-icon">🤖</div>
    <div class="nav-card-title">5M ML/DL 분석</div>
    <div class="nav-card-desc">AUC 0.55 - 예측력 부족</div>
  </a>
</div>

### 15분봉 분석

<div class="nav-cards" markdown="0">
  <a class="nav-card" href="{{ '/15m' | relative_url }}">
    <div class="nav-card-icon">📊</div>
    <div class="nav-card-title">15M 백테스트 결과</div>
    <div class="nav-card-desc">160% 수익, 35% MDD, 37% 승률 (HC3%)</div>
  </a>
  <a class="nav-card" href="{{ '/parametric-15m' | relative_url }}">
    <div class="nav-card-icon">🔬</div>
    <div class="nav-card-title">15M 파라메트릭 스터디</div>
    <div class="nav-card-desc">729개 파라미터 조합 탐색</div>
  </a>
  <a class="nav-card" href="{{ '/ml-analysis-15m' | relative_url }}">
    <div class="nav-card-icon">🤖</div>
    <div class="nav-card-title">15M ML/DL 분석</div>
    <div class="nav-card-desc">AUC 0.53 - 예측력 부족</div>
  </a>
</div>

### 4시간봉 분석

<div class="nav-cards" markdown="0">
  <a class="nav-card" href="{{ '/4h' | relative_url }}">
    <div class="nav-card-icon">📊</div>
    <div class="nav-card-title">4H 백테스트 결과</div>
    <div class="nav-card-desc">104% 수익, 48% MDD, 81% 승률 (HC2%)</div>
  </a>
  <a class="nav-card" href="{{ '/parametric-4h' | relative_url }}">
    <div class="nav-card-icon">🔬</div>
    <div class="nav-card-title">4H 파라메트릭 스터디</div>
    <div class="nav-card-desc">729개 파라미터 조합 탐색</div>
  </a>
  <a class="nav-card" href="{{ '/ml-analysis-4h' | relative_url }}">
    <div class="nav-card-icon">🤖</div>
    <div class="nav-card-title">4H ML/DL 분석</div>
    <div class="nav-card-desc">AUC 0.56 - 샘플 부족</div>
  </a>
</div>

### Multi-Asset 분석

<div class="nav-cards" markdown="0">
  <a class="nav-card" href="{{ '/multi-asset-1h' | relative_url }}">
    <div class="nav-card-icon">🌐</div>
    <div class="nav-card-title">Multi-Asset 1H 분석</div>
    <div class="nav-card-desc">ETH, SOL, XRP 등 7개 코인 비교 분석</div>
  </a>
  <a class="nav-card" href="{{ '/train-test-split' | relative_url }}">
    <div class="nav-card-icon">🧪</div>
    <div class="nav-card-title">Train/Test Split 검증</div>
    <div class="nav-card-desc">2020-2025 학습, 2026 테스트 - BTC vs ETH</div>
  </a>
</div>

### Enhanced Strategy (신규)

<div class="nav-cards" markdown="0">
  <a class="nav-card" href="{{ '/enhanced-strategy' | relative_url }}">
    <div class="nav-card-icon">🚀</div>
    <div class="nav-card-title">Enhanced Strategy Results</div>
    <div class="nav-card-desc">ATR 기반 감지 + Kelly Criterion 포지션 사이징 - CAGR 55%</div>
  </a>
  <a class="nav-card" href="{{ '/realistic-backtest' | relative_url }}">
    <div class="nav-card-icon">💰</div>
    <div class="nav-card-title">Realistic Backtest (수수료 포함)</div>
    <div class="nav-card-desc">5M/15M/1H 비교 - 5M Balanced 최적 (Calmar 1.05)</div>
  </a>
</div>

### 성과 분석

<div class="nav-cards" markdown="0">
  <a class="nav-card" href="{{ '/monthly-returns' | relative_url }}">
    <div class="nav-card-icon">📅</div>
    <div class="nav-card-title">월별 수익률 분석</div>
    <div class="nav-card-desc">BTC +110%, ETH +157% - 연도별/월별 성과</div>
  </a>
  <a class="nav-card" href="{{ '/detection-quality' | relative_url }}">
    <div class="nav-card-icon">🎯</div>
    <div class="nav-card-title">감지 품질 분석</div>
    <div class="nav-card-desc">TP/SL 적중률, 시장 상태별 성과</div>
  </a>
  <a class="nav-card" href="{{ '/optimization' | relative_url }}">
    <div class="nav-card-icon">⚡</div>
    <div class="nav-card-title">파라미터 최적화</div>
    <div class="nav-card-desc">공격적/균형/보수적 프로필 권장사항</div>
  </a>
</div>

### 공통

<div class="nav-cards" markdown="0">
  <a class="nav-card" href="{{ '/strategy' | relative_url }}">
    <div class="nav-card-icon">⚙️</div>
    <div class="nav-card-title">전략 구현 상세</div>
    <div class="nav-card-desc">핵심 함수, 반익절 로직, 파라미터 설명</div>
  </a>
</div>

---

## 빠른 시작

<div class="quickstart-box" markdown="1">

### 설치 및 실행

```bash
pip install -e .
```

```python
from crypto_backtest.long_strategy import LongStrategyConfig, LongBacktestEngine
from crypto_backtest.data_loader import BacktestConfig, load_hourly_data

config = LongStrategyConfig(
    data_path=Path('data'),
    breakout_ma=100,
    take_profit_pct=10.0,
    stop_loss_pct=5.0,
    half_close_enabled=True,
    half_close_pct=3.0,
)

data = load_hourly_data(BacktestConfig(data_path=config.data_path))
engine = LongBacktestEngine(config)
engine.run(data)
trades = engine.get_trades_df()
```

</div>
