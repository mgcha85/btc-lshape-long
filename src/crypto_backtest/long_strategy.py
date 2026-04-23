from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import polars as pl

from .data_loader import BacktestConfig


class TradeType(str, Enum):
    LONG = "long"
    SHORT = "short"


class TradeResult(str, Enum):
    STOP_LOSS = "SL"
    TAKE_PROFIT = "TP"
    TIMEOUT = "TIMEOUT"


@dataclass
class Trade:
    symbol: str
    open_time: datetime
    open_price: float
    close_time: datetime | None = None
    close_price: float | None = None
    profit: float | None = None
    profit_pct: float | None = None
    trade_type: TradeType = TradeType.LONG
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


@dataclass 
class LongStrategyConfig:
    data_path: any
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    
    ma_periods: list[int] | None = None
    breakout_ma: int = 50
    consolidation_bars: int = 5
    consolidation_range_pct: float = 3.0
    drop_threshold_pct: float = 5.0
    
    take_profit_pct: float = 5.0
    stop_loss_pct: float = 3.0
    
    half_close_enabled: bool = False
    half_close_pct: float = 2.0
    
    start_date: str | None = None
    end_date: str | None = None


def detect_consolidation(
    rows: list[dict],
    current_idx: int,
    lookback: int = 5,
    range_pct: float = 3.0,
) -> bool:
    """최근 N봉이 횡보(range_pct 이내) 상태인지 확인"""
    if current_idx < lookback:
        return False
    
    window = rows[current_idx - lookback : current_idx]
    highs = [r["high"] for r in window]
    lows = [r["low"] for r in window]
    
    range_high = max(highs)
    range_low = min(lows)
    
    if range_low <= 0:
        return False
    
    range_pct_actual = (range_high - range_low) / range_low * 100
    return range_pct_actual <= range_pct


def detect_prior_drop(
    rows: list[dict],
    current_idx: int,
    lookback: int = 20,
    drop_threshold: float = 5.0,
) -> bool:
    """횡보 전에 하락이 있었는지 확인"""
    if current_idx < lookback:
        return False
    
    window = rows[current_idx - lookback : current_idx]
    
    max_high = max(r["high"] for r in window[:len(window)//2])
    min_low = min(r["low"] for r in window[len(window)//2:])
    
    if max_high <= 0:
        return False
    
    drop_pct = (max_high - min_low) / max_high * 100
    return drop_pct >= drop_threshold


def detect_ma_breakout_long(
    row: dict,
    prev_row: dict | None,
    ma_column: str,
) -> bool:
    """MA 아래에서 위로 돌파하는 패턴 감지"""
    if prev_row is None:
        return False
    
    ma_value = row.get(ma_column)
    prev_ma = prev_row.get(ma_column)
    
    if ma_value is None or prev_ma is None:
        return False
    
    prev_close = prev_row.get("close", 0)
    current_close = row.get("close", 0)
    current_open = row.get("open", 0)
    
    was_below = prev_close < prev_ma
    broke_above = current_close > ma_value
    bullish_candle = current_close > current_open
    
    return was_below and broke_above and bullish_candle


def calculate_long_pnl(entry_price: float, current_price: float) -> float:
    return ((current_price - entry_price) / entry_price) * 100


class LongBacktestEngine:
    def __init__(self, config: LongStrategyConfig):
        self.config = config
        self.trades: list[Trade] = []
        self.current_trade: Trade | None = None
        self.current_sl_pct: float = config.stop_loss_pct
        
    def run(self, data: pl.DataFrame) -> list[Trade]:
        self.trades = []
        self.current_trade = None
        
        rows = data.to_dicts()
        ma_column = f"ma_{self.config.breakout_ma}"
        
        for i, row in enumerate(rows):
            prev_row = rows[i - 1] if i > 0 else None
            self._process_candle(row, prev_row, rows, i, ma_column)
        
        if self.current_trade:
            last_row = rows[-1]
            self._close_trade(
                last_row["datetime"],
                last_row["close"],
                TradeResult.TIMEOUT,
            )
        
        return self.trades
    
    def _process_candle(
        self,
        row: dict,
        prev_row: dict | None,
        rows: list[dict],
        idx: int,
        ma_column: str,
    ) -> None:
        if self.current_trade:
            self._manage_position(row)
        else:
            self._check_entry(row, prev_row, rows, idx, ma_column)
    
    def _check_entry(
        self,
        row: dict,
        prev_row: dict | None,
        rows: list[dict],
        idx: int,
        ma_column: str,
    ) -> None:
        is_consolidating = detect_consolidation(
            rows, idx,
            self.config.consolidation_bars,
            self.config.consolidation_range_pct,
        )
        
        had_drop = detect_prior_drop(
            rows, idx,
            lookback=20,
            drop_threshold=self.config.drop_threshold_pct,
        )
        
        ma_breakout = detect_ma_breakout_long(row, prev_row, ma_column)
        
        if is_consolidating and had_drop and ma_breakout:
            self.current_trade = Trade(
                symbol=self.config.symbol,
                open_time=row["datetime"],
                open_price=row["close"],
                trade_type=TradeType.LONG,
            )
            self.current_sl_pct = self.config.stop_loss_pct
    
    def _manage_position(self, row: dict) -> None:
        if not self.current_trade:
            return
        
        entry_price = self.current_trade.open_price
        high = row["high"]
        low = row["low"]
        current_time = row["datetime"]
        
        pnl_at_low = calculate_long_pnl(entry_price, low)
        pnl_at_high = calculate_long_pnl(entry_price, high)
        
        if pnl_at_low <= -self.current_sl_pct:
            if self.current_trade.half_closed:
                sl_price = entry_price
                self._close_trade(current_time, sl_price, TradeResult.STOP_LOSS)
            else:
                sl_price = entry_price * (1 - self.current_sl_pct / 100)
                self._close_trade(current_time, sl_price, TradeResult.STOP_LOSS)
            return
        
        if (self.config.half_close_enabled and 
            not self.current_trade.half_closed and
            pnl_at_high >= self.config.half_close_pct):
            
            half_close_price = entry_price * (1 + self.config.half_close_pct / 100)
            self.current_trade.half_closed = True
            self.current_trade.half_close_time = current_time
            self.current_trade.half_close_price = half_close_price
            self.current_trade.half_close_profit_pct = self.config.half_close_pct
            
            self.current_sl_pct = 0.0
        
        if pnl_at_high >= self.config.take_profit_pct:
            tp_price = entry_price * (1 + self.config.take_profit_pct / 100)
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
        
        if self.current_trade.half_closed:
            half_profit = self.current_trade.half_close_profit_pct / 2
            remaining_profit = calculate_long_pnl(self.current_trade.open_price, close_price) / 2
            self.current_trade.profit_pct = half_profit + remaining_profit
        else:
            self.current_trade.profit_pct = calculate_long_pnl(
                self.current_trade.open_price,
                close_price,
            )
        
        self.current_trade.profit = self.current_trade.open_price * (self.current_trade.profit_pct / 100)
        
        self.trades.append(self.current_trade)
        self.current_trade = None
    
    def get_trades_df(self) -> pl.DataFrame:
        if not self.trades:
            return pl.DataFrame()
        
        return pl.DataFrame([t.to_dict() for t in self.trades])


def run_long_backtest(config: LongStrategyConfig, data: pl.DataFrame) -> pl.DataFrame:
    engine = LongBacktestEngine(config)
    engine.run(data)
    return engine.get_trades_df()
