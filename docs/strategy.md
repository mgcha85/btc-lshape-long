---
layout: default
title: 전략 구현
nav_order: 5
---

# ㄴ자 (L-Shape) 전략 구현 상세
{: .no_toc }

## 목차
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## 전략 철학

ㄴ자 패턴은 급락 후 바닥을 다지며 횡보하다가 상승 전환하는 가격 패턴을 포착합니다.

```
가격
  │
  │    ┌─┐
  │    │ │ 
  │    │ │     ← 하락 전 고점
  │    │ └┐
  │    │  │
  │    │  └┐
  │    │   │   ← 급락 구간 (drop_threshold_pct)
  │    │   └┐
  │    │    │
  │    │    └──────────────┐
  │    │                   │  ← 횡보 구간 (consolidation)
  │    │    ┌──────────────┘
  │    │    │
  │────┼────┼──────────────────── MA Line
  │    │    │     ↑
  │    │    └─────┼────────────── MA 돌파 = 진입점
  │              
  └────────────────────────────── 시간
```

---

## 핵심 함수

### 1. 선행 하락 감지

```python
def detect_prior_drop(
    rows: list[dict],
    current_idx: int,
    lookback: int = 20,
    drop_threshold: float = 5.0,
) -> bool:
    window = rows[current_idx - lookback : current_idx]
    
    # 전반부에서 최고점, 후반부에서 최저점 찾기
    max_high = max(r["high"] for r in window[:len(window)//2])
    min_low = min(r["low"] for r in window[len(window)//2:])
    
    drop_pct = (max_high - min_low) / max_high * 100
    return drop_pct >= drop_threshold
```

**로직**:
- 20봉 윈도우를 절반으로 분할
- 전반 10봉: 최고가 탐색 (하락 전 고점)
- 후반 10봉: 최저가 탐색 (바닥)
- 하락률이 임계값 이상이면 True

### 2. 횡보 감지

```python
def detect_consolidation(
    rows: list[dict],
    current_idx: int,
    lookback: int = 5,
    range_pct: float = 3.0,
) -> bool:
    window = rows[current_idx - lookback : current_idx]
    
    range_high = max(r["high"] for r in window)
    range_low = min(r["low"] for r in window)
    
    range_pct_actual = (range_high - range_low) / range_low * 100
    return range_pct_actual <= range_pct
```

**로직**:
- 최근 N봉의 고가/저가 범위 계산
- 범위가 임계값 이내면 횡보로 판단

### 3. MA 돌파 감지

```python
def detect_ma_breakout_long(
    row: dict, 
    prev_row: dict, 
    ma_column: str
) -> bool:
    was_below = prev_row["close"] < prev_row[ma_column]
    broke_above = row["close"] > row[ma_column]
    bullish_candle = row["close"] > row["open"]
    
    return was_below and broke_above and bullish_candle
```

**조건**:
1. 이전 봉 종가 < MA (아래에 있었음)
2. 현재 봉 종가 > MA (위로 돌파)
3. 현재 봉이 양봉

---

## 반익절 로직

### 동작 흐름

```
진입 → [SL = -5%]
   │
   ├─→ 가격 하락 → SL 터치 → 전량 청산 (-5%)
   │
   └─→ 가격 상승 → +3% 도달
                      │
                      ├─→ 50% 익절 (+1.5% 확보)
                      │   SL → 본절 (0%)
                      │
                      └─→ 이후
                           │
                           ├─→ +10% 도달 → 나머지 50% 익절 (+5%)
                           │               총 수익: +6.5%
                           │
                           └─→ 본절 터치 → 나머지 50% 청산 (0%)
                                           총 수익: +1.5%
```

### 수익 계산

```python
if self.current_trade.half_closed:
    # 반익절 완료 상태
    half_profit = half_close_pct / 2   # 50% 포지션 수익
    remaining_profit = final_pnl / 2   # 나머지 50% 수익
    total_profit = half_profit + remaining_profit
else:
    # 반익절 없이 청산
    total_profit = final_pnl
```

### 시나리오별 수익

| 시나리오 | 첫 50% | 나머지 50% | 총 수익 |
|:---------|------:|----------:|-------:|
| HC → TP | +3% × 0.5 = 1.5% | +10% × 0.5 = 5% | **+6.5%** |
| HC → BE | +3% × 0.5 = 1.5% | 0% × 0.5 = 0% | **+1.5%** |
| 바로 SL | -5% | - | **-5%** |
| 바로 TP | +10% | - | **+10%** |

---

## 설정 파라미터

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `breakout_ma` | int | 50 | 돌파 기준 MA 기간 |
| `consolidation_bars` | int | 5 | 횡보 판단 봉 수 |
| `consolidation_range_pct` | float | 3.0 | 횡보 범위 % |
| `drop_threshold_pct` | float | 5.0 | 선행 하락 임계값 % |
| `take_profit_pct` | float | 5.0 | 익절 % |
| `stop_loss_pct` | float | 3.0 | 손절 % |
| `half_close_enabled` | bool | False | 반익절 활성화 |
| `half_close_pct` | float | 2.0 | 반익절 트리거 % |

---

## 사용 예시

### 기본 사용

```python
from pathlib import Path
from crypto_backtest.data_loader import BacktestConfig, load_hourly_data
from crypto_backtest.long_strategy import LongStrategyConfig, LongBacktestEngine

# 데이터 로드
base_config = BacktestConfig(
    data_path=Path('data'),
    ma_periods=[25, 50, 100, 200, 400],
)
data = load_hourly_data(base_config)

# 전략 설정
config = LongStrategyConfig(
    data_path=Path('data'),
    breakout_ma=100,
    consolidation_bars=3,
    consolidation_range_pct=5.0,
    drop_threshold_pct=3.0,
    take_profit_pct=10.0,
    stop_loss_pct=5.0,
    half_close_enabled=True,
    half_close_pct=3.0,
)

# 백테스트 실행
engine = LongBacktestEngine(config)
engine.run(data)

# 결과 확인
trades_df = engine.get_trades_df()
print(f"Total trades: {len(trades_df)}")
print(f"Win rate: {trades_df['is_sl'].value_counts()}")
```

### 결과 분석

```python
from crypto_backtest.storage import calculate_stats

stats = calculate_stats(trades_df)
print(f"Total Profit: {stats['total_profit_pct']:.2f}%")
print(f"Max Drawdown: {stats['max_drawdown_pct']:.2f}%")
print(f"Win Rate: {stats['win_rate']:.2f}%")
```
