from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterator

import polars as pl

from .data_loader import BacktestConfig


class TradeType(str, Enum):
    SHORT = "short"


class TradeResult(str, Enum):
    STOP_LOSS = "SL"
    HALF_CLOSE = "HALF"
    BREAKEVEN = "BE"
    TAKE_PROFIT = "TP"


@dataclass
class Trade:
    symbol: str
    open_time: datetime
    open_price: float
    close_time: datetime | None = None
    close_price: float | None = None
    profit: float | None = None
    profit_pct: float | None = None
    trade_type: TradeType = TradeType.SHORT
    result: TradeResult | None = None
    half_closed: bool = False
    half_close_time: datetime | None = None
    half_close_price: float | None = None
    half_close_profit_pct: float | None = None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "open_time": self.open_time,
            "open_price": self.open_price,
            "close_time": self.close_time,
            "close_price": self.close_price,
            "profit": self.profit,
            "profit_pct": self.profit_pct,
            "type": self.trade_type.value,
            "result": self.result.value if self.result else None,
            "is_sl": self.result == TradeResult.STOP_LOSS,
            "half_closed": self.half_closed,
            "half_close_time": self.half_close_time,
            "half_close_price": self.half_close_price,
            "half_close_profit_pct": self.half_close_profit_pct,
        }


def detect_ma_resistance(
    row: dict,
    prev_row: dict | None,
    prev_prev_row: dict | None,
    ma_column: str,
    touch_tolerance: float = 0.002,
) -> bool:
    """
    아래에서 올라와서 MA에 저항 맞고 다시 떨어지는 패턴 감지.
    
    조건:
    1. 2봉 전: 종가가 MA 아래
    2. 1봉 전: 상승하면서 고가가 MA 근처 터치 (tolerance 내)
    3. 현재봉: MA 아래에서 음봉 마감 (저항 확인)
    """
    if prev_row is None or prev_prev_row is None:
        return False
    
    ma_value = row.get(ma_column)
    prev_ma = prev_row.get(ma_column)
    prev_prev_ma = prev_prev_row.get(ma_column)
    
    if ma_value is None or prev_ma is None or prev_prev_ma is None:
        return False
    
    prev_prev_close = prev_prev_row.get("close", 0)
    prev_open = prev_row.get("open", 0)
    prev_close = prev_row.get("close", 0)
    prev_high = prev_row.get("high", 0)
    current_open = row.get("open", 0)
    current_close = row.get("close", 0)
    current_high = row.get("high", 0)
    
    was_below_ma = prev_prev_close < prev_prev_ma * (1 - touch_tolerance)
    
    rose_toward_ma = prev_close > prev_prev_close
    
    touched_ma = (
        (prev_high >= prev_ma * (1 - touch_tolerance) and prev_high <= prev_ma * (1 + touch_tolerance)) or
        (current_high >= ma_value * (1 - touch_tolerance) and current_high <= ma_value * (1 + touch_tolerance))
    )
    
    rejected = (
        current_close < current_open and
        current_close < ma_value and
        current_close < prev_close
    )
    
    return was_below_ma and rose_toward_ma and touched_ma and rejected


def calculate_short_pnl(entry_price: float, current_price: float) -> float:
    return ((entry_price - current_price) / entry_price) * 100


class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.trades: list[Trade] = []
        self.current_trade: Trade | None = None
        
    def run(self, data: pl.DataFrame) -> list[Trade]:
        self.trades = []
        self.current_trade = None
        
        rows = data.to_dicts()
        ma_column = f"ma_{self.config.resistance_ma}"
        
        for i, row in enumerate(rows):
            prev_row = rows[i - 1] if i > 0 else None
            prev_prev_row = rows[i - 2] if i > 1 else None
            self._process_candle(row, prev_row, prev_prev_row, ma_column)
        
        if self.current_trade:
            last_row = rows[-1]
            self._close_trade(
                last_row["datetime"],
                last_row["close"],
                TradeResult.TAKE_PROFIT,
            )
        
        return self.trades
    
    def _process_candle(self, row: dict, prev_row: dict | None, prev_prev_row: dict | None, ma_column: str) -> None:
        if self.current_trade:
            self._manage_position(row)
        else:
            self._check_entry(row, prev_row, prev_prev_row, ma_column)
    
    def _check_entry(self, row: dict, prev_row: dict | None, prev_prev_row: dict | None, ma_column: str) -> None:
        if detect_ma_resistance(row, prev_row, prev_prev_row, ma_column):
            self.current_trade = Trade(
                symbol=self.config.symbol,
                open_time=row["datetime"],
                open_price=row["close"],
                trade_type=TradeType.SHORT,
            )
    
    def _manage_position(self, row: dict) -> None:
        if not self.current_trade:
            return
        
        entry_price = self.current_trade.open_price
        high = row["high"]
        low = row["low"]
        close = row["close"]
        current_time = row["datetime"]
        
        pnl_at_high = calculate_short_pnl(entry_price, high)
        pnl_at_low = calculate_short_pnl(entry_price, low)
        
        if pnl_at_high <= -self.config.stop_loss_pct:
            sl_price = entry_price * (1 + self.config.stop_loss_pct / 100)
            self._close_trade(current_time, sl_price, TradeResult.STOP_LOSS)
            return
        
        if self.current_trade.half_closed:
            if pnl_at_high <= 0:
                self._close_trade(current_time, entry_price, TradeResult.BREAKEVEN)
                return
            
            if pnl_at_low >= self.config.take_profit_pct:
                tp_price = entry_price * (1 - self.config.take_profit_pct / 100)
                self._close_trade(current_time, tp_price, TradeResult.TAKE_PROFIT)
                return
        else:
            if pnl_at_low >= self.config.half_close_pct:
                half_price = entry_price * (1 - self.config.half_close_pct / 100)
                self.current_trade.half_closed = True
                self.current_trade.half_close_time = current_time
                self.current_trade.half_close_price = half_price
                self.current_trade.half_close_profit_pct = self.config.half_close_pct
            
            if pnl_at_low >= self.config.take_profit_pct:
                tp_price = entry_price * (1 - self.config.take_profit_pct / 100)
                self._close_trade(current_time, tp_price, TradeResult.TAKE_PROFIT)
                return
    
    def _close_trade(
        self,
        close_time: datetime,
        close_price: float,
        result: TradeResult,
    ) -> None:
        if not self.current_trade:
            return
        
        self.current_trade.close_time = close_time
        self.current_trade.close_price = close_price
        self.current_trade.result = result
        self.current_trade.profit_pct = calculate_short_pnl(
            self.current_trade.open_price,
            close_price,
        )
        self.current_trade.profit = (
            self.current_trade.open_price - close_price
        )
        
        self.trades.append(self.current_trade)
        self.current_trade = None
    
    def get_trades_df(self) -> pl.DataFrame:
        if not self.trades:
            return pl.DataFrame()
        
        return pl.DataFrame([t.to_dict() for t in self.trades])


def run_backtest(config: BacktestConfig, data: pl.DataFrame) -> pl.DataFrame:
    engine = BacktestEngine(config)
    engine.run(data)
    return engine.get_trades_df()
