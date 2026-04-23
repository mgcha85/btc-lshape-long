# BTC L-Shape Long Strategy Backtester

비트코인 1시간봉 기반 ㄴ자 패턴 롱 전략 백테스팅 및 ML/DL 분석 시스템.

## 전략 개요

### ㄴ자 (L-Shape) 패턴이란?

```
     ┌──────┐
     │ HIGH │ ← 이전 고점 (하락 전)
     └──┬───┘
        │
        ▼ 하락 (drop_threshold_pct 이상)
        │
   ┌────┴────────────────────┐
   │  횡보 구간 (consolidation) │ ← ㄴ자의 바닥
   │  range_pct 이내 등락      │
   └─────────────────┬───────┘
                     │
                     ▲ MA 돌파 → LONG 진입
                     │
```

### 진입 조건 (3가지 모두 충족)

1. **선행 하락**: 최근 20봉 내 `drop_threshold_pct`% 이상 하락 발생
2. **횡보 확인**: 최근 N봉이 `consolidation_range_pct`% 범위 내 등락
3. **MA 돌파**: 이전 봉 종가 < MA, 현재 봉 종가 > MA + 양봉

### 청산 조건

- **Take Profit**: 진입가 대비 +N% 도달
- **Stop Loss**: 진입가 대비 -N% 도달
- **Half Close (선택)**: 중간 목표가 도달 시 50% 익절 + 본절 SL 이동

## 설치

```bash
pip install -e .
```

## 사용법

### 백테스트 실행

```python
from pathlib import Path
from crypto_backtest.data_loader import BacktestConfig, load_hourly_data
from crypto_backtest.long_strategy import LongStrategyConfig, LongBacktestEngine

config = LongStrategyConfig(
    data_path=Path('path/to/data'),
    symbol="BTCUSDT",
    breakout_ma=100,
    consolidation_bars=3,
    consolidation_range_pct=5.0,
    drop_threshold_pct=3.0,
    take_profit_pct=10.0,
    stop_loss_pct=5.0,
    half_close_enabled=True,
    half_close_pct=3.0,
)

data = load_hourly_data(BacktestConfig(data_path=config.data_path, ma_periods=[25, 50, 100, 200, 400]))
engine = LongBacktestEngine(config)
engine.run(data)
trades_df = engine.get_trades_df()
```

### 파라메트릭 스터디

```python
from crypto_backtest.long_parametric import run_long_parametric_study, analyze_long_results

results = run_long_parametric_study(
    data_path=Path('path/to/data'),
    ma_periods=[25, 50, 100],
    take_profit_pcts=[5.0, 7.0, 10.0],
    stop_loss_pcts=[2.0, 3.0, 5.0],
)
df = analyze_long_results(results)
```

## 최적 파라미터

### 반익절 없음 (최대 수익)

| Parameter | Value |
|-----------|-------|
| MA Period | 50 |
| Take Profit | 10% |
| Stop Loss | 3% |
| **Total Profit** | **188.6%** |
| Max Drawdown | 62% |
| Win Rate | 28.8% |

### 반익절 있음 (리스크 관리)

| Parameter | Value |
|-----------|-------|
| MA Period | 100 |
| Take Profit | 10% |
| Stop Loss | 5% |
| Half Close | 3% |
| **Total Profit** | **112.5%** |
| **Max Drawdown** | **26%** |
| Win Rate | 69.7% |

## 프로젝트 구조

```
src/crypto_backtest/
├── data_loader.py      # 데이터 로딩 및 1m→1h 리샘플링
├── long_strategy.py    # ㄴ자 롱 전략 엔진
├── long_parametric.py  # 롱 전략 파라메트릭 스터디
├── features.py         # ML 피처 엔지니어링 (50+ 지표)
├── models_tree.py      # 트리 기반 모델 (XGBoost, LightGBM)
├── models_deep.py      # 딥러닝 모델 (CNN, LSTM)
├── storage.py          # SQLite 저장
├── report.py           # 리포트 생성
└── cli.py              # CLI 인터페이스
```

## 문서

- [ㄴ자 전략 구현 상세](docs/STRATEGY_IMPLEMENTATION.md)
- [파라메트릭 스터디 결과](docs/PARAMETRIC_STUDY.md)
- [ML/DL 분석 결과](docs/ML_ANALYSIS.md)

## 라이선스

MIT
