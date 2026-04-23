# ㄴ자 (L-Shape) 롱 전략 구현 상세

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

## 코드 구현

### 1. 선행 하락 감지 (`detect_prior_drop`)

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

**로직 설명:**
- 20봉 윈도우를 절반으로 나눔
- 전반 10봉에서 최고가, 후반 10봉에서 최저가 탐색
- 하락률이 임계값 이상이면 True

### 2. 횡보 감지 (`detect_consolidation`)

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

**로직 설명:**
- 최근 N봉의 고가/저가 범위 계산
- 범위가 임계값 이내면 횡보로 판단

### 3. MA 돌파 감지 (`detect_ma_breakout_long`)

```python
def detect_ma_breakout_long(row: dict, prev_row: dict, ma_column: str) -> bool:
    was_below = prev_row["close"] < prev_row[ma_column]
    broke_above = row["close"] > row[ma_column]
    bullish_candle = row["close"] > row["open"]
    
    return was_below and broke_above and bullish_candle
```

**로직 설명:**
- 이전 봉: MA 아래
- 현재 봉: MA 위 + 양봉
- 세 조건 모두 충족 시 돌파로 판단

### 4. 진입 조건 통합

```python
def _check_entry(self, row, prev_row, rows, idx, ma_column):
    is_consolidating = detect_consolidation(rows, idx, ...)
    had_drop = detect_prior_drop(rows, idx, ...)
    ma_breakout = detect_ma_breakout_long(row, prev_row, ma_column)
    
    if is_consolidating and had_drop and ma_breakout:
        # LONG 진입
        self.current_trade = Trade(...)
```

## 반익절 (Half Close) 로직

### 동작 방식

1. **진입 시**: SL = -stop_loss_pct%
2. **half_close_pct% 도달 시**:
   - 포지션의 50% 청산 (익절)
   - SL을 본절(진입가)로 이동
3. **이후**:
   - TP 도달 → 나머지 50% 청산
   - 본절 터치 → 나머지 50% 청산 (손실 0)

### 수익 계산

```python
if self.current_trade.half_closed:
    # 반익절한 경우
    half_profit = half_close_pct / 2  # 50% 포지션의 수익
    remaining_profit = final_pnl / 2  # 나머지 50%의 수익
    total_profit = half_profit + remaining_profit
else:
    total_profit = final_pnl
```

**예시 (half_close=3%, TP=10%, SL=5%):**

| 시나리오 | 50% 포지션 | 50% 포지션 | 총 수익 |
|---------|----------|----------|--------|
| 3% 도달 후 TP | +3% * 0.5 = 1.5% | +10% * 0.5 = 5% | **+6.5%** |
| 3% 도달 후 본절 | +3% * 0.5 = 1.5% | 0% * 0.5 = 0% | **+1.5%** |
| 바로 SL | -5% | - | **-5%** |
| 바로 TP | +10% | - | **+10%** |

## 설정 파라미터

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `breakout_ma` | int | 50 | 돌파 기준 MA 기간 |
| `consolidation_bars` | int | 5 | 횡보 판단 봉 수 |
| `consolidation_range_pct` | float | 3.0 | 횡보 범위 % |
| `drop_threshold_pct` | float | 5.0 | 선행 하락 임계값 % |
| `take_profit_pct` | float | 5.0 | 익절 % |
| `stop_loss_pct` | float | 3.0 | 손절 % |
| `half_close_enabled` | bool | False | 반익절 활성화 |
| `half_close_pct` | float | 2.0 | 반익절 트리거 % |

## 차트 예시

![Long Strategy Sample](long_strategy_sample.png)

위 차트에서:
- 파란선: MA50
- 녹색 화살표: LONG 진입점
- 빨간 X: Stop Loss
- 녹색 체크: Take Profit
