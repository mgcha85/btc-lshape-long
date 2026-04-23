---
layout: default
title: Home
nav_order: 1
description: "비트코인 ㄴ자 패턴 롱 전략 백테스팅 및 ML/DL 분석"
permalink: /
---

# BTC L-Shape Long Strategy
{: .fs-9 }

비트코인 1시간봉 기반 ㄴ자 패턴 롱 전략 백테스팅 시스템
{: .fs-6 .fw-300 }

[백테스트 결과 보기]({% link results.md %}){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[ML 분석 보기]({% link ml-analysis.md %}){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## 전략 개요

### ㄴ자 (L-Shape) 패턴이란?

급락 후 바닥을 다지며 횡보하다가 이동평균선을 돌파할 때 매수하는 전략입니다.

```
     ┌──────┐
     │ HIGH │ ← 이전 고점
     └──┬───┘
        │
        ▼ 하락 (3%+ 이상)
        │
   ┌────┴────────────────────┐
   │  횡보 구간 (consolidation) │ ← ㄴ자의 바닥
   │  5% 범위 이내 등락        │
   └─────────────────┬───────┘
                     │
                     ▲ MA100 돌파 → LONG 진입
```

### 진입 조건

| 조건 | 설명 | 기본값 |
|:-----|:-----|:-------|
| 선행 하락 | 최근 20봉 내 하락률 | ≥ 3% |
| 횡보 확인 | 최근 N봉 변동폭 | ≤ 5% |
| MA 돌파 | 이전 봉 < MA, 현재 봉 > MA + 양봉 | MA100 |

### 청산 조건

- **Take Profit**: +10% 도달
- **Stop Loss**: -5% 도달  
- **Half Close**: +3% 도달 시 50% 익절 + 본절 SL 이동

---

## 핵심 결과

{: .highlight }
> **최적 설정 (반익절 적용)**: MA100, TP 10%, SL 5%, Half Close 3%
> - 총 수익: **112.5%** (4년간)
> - 최대 낙폭: **26%**
> - 승률: **69.7%**

### 전략 비교

| 전략 | 총 수익 | 최대 낙폭 | 승률 | Profit Factor |
|:-----|-------:|--------:|-----:|-------------:|
| 반익절 없음 (MA50) | 188.6% | 62% | 28.8% | 1.35 |
| **반익절 있음 (MA100)** | **112.5%** | **26%** | **69.7%** | **1.45** |
| 초저위험 (MA100, HC1%) | 75.5% | 16.5% | 88.4% | 1.60 |

{: .important }
반익절 적용 시 수익은 40% 감소하지만, 최대 낙폭이 58% 줄어듭니다.

---

## 프로젝트 구조

```
src/crypto_backtest/
├── long_strategy.py    # ㄴ자 롱 전략 엔진
├── long_parametric.py  # 파라메트릭 스터디
├── features.py         # ML 피처 (50+ 지표)
├── models_tree.py      # XGBoost, LightGBM
├── models_deep.py      # CNN, LSTM
└── storage.py          # SQLite 저장
```

---

## 빠른 시작

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
