---
layout: default
title: Home
nav_order: 1
description: "비트코인 ㄴ자 패턴 롱 전략 백테스팅 및 ML/DL 분석"
permalink: /
---

<div class="hero-section" markdown="0">
  <span class="hero-badge">BTC / USDT · 1H</span>
  <h1>L-Shape Long Strategy</h1>
  <p class="hero-subtitle">급락 → 횡보 → MA 돌파 패턴을 포착하는 비트코인 롱 전략</p>
</div>

<div class="stat-grid" markdown="0">
  <div class="stat-card green">
    <div class="stat-value">112.5%</div>
    <div class="stat-label">총 수익 (4년)</div>
  </div>
  <div class="stat-card gold">
    <div class="stat-value">69.7%</div>
    <div class="stat-label">승률</div>
  </div>
  <div class="stat-card red">
    <div class="stat-value">26%</div>
    <div class="stat-label">최대 낙폭</div>
  </div>
  <div class="stat-card blue">
    <div class="stat-value">1.45</div>
    <div class="stat-label">Profit Factor</div>
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

<div class="nav-cards" markdown="0">
  <a class="nav-card" href="{{ '/results' | relative_url }}">
    <div class="nav-card-icon">📊</div>
    <div class="nav-card-title">백테스트 결과</div>
    <div class="nav-card-desc">최적 설정 성과, 연도별 분석, 거래 시나리오 상세</div>
  </a>
  <a class="nav-card" href="{{ '/parametric' | relative_url }}">
    <div class="nav-card-icon">🔬</div>
    <div class="nav-card-title">파라메트릭 스터디</div>
    <div class="nav-card-desc">960개 파라미터 조합 탐색 결과 및 최적화 분석</div>
  </a>
  <a class="nav-card" href="{{ '/ml-analysis' | relative_url }}">
    <div class="nav-card-icon">🤖</div>
    <div class="nav-card-title">ML/DL 분석</div>
    <div class="nav-card-desc">XGBoost · LightGBM · CNN · LSTM 기반 SL/TP 예측</div>
  </a>
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
