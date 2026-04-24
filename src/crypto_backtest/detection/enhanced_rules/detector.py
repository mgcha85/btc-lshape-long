"""
Enhanced Rule-Based L-Shape Detector

Improvements over original:
1. ATR-based dynamic thresholds (vs fixed percentages)
2. Volume decline confirmation during consolidation
3. Flatness quality check (std/range ratio)
4. scipy peak detection for precise pivots
"""

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
import polars as pl
from scipy.signal import find_peaks


class DetectionResult(NamedTuple):
    """Detection result with confidence score."""
    detected: bool
    confidence: float  # 0.0 - 1.0
    drop_pct: float
    consolidation_range_pct: float
    flatness_score: float
    volume_declining: bool
    pivot_quality: float
    details: dict


@dataclass
class EnhancedDetectorConfig:
    """Configuration for enhanced L-shape detection."""
    # ATR multipliers (replace fixed percentages)
    drop_atr_multiplier: float = 2.5  # drop_threshold = ATR * this
    consolidation_atr_multiplier: float = 1.0  # consolidation_range = ATR * this
    
    # Lookback periods
    drop_lookback: int = 20
    consolidation_bars: int = 5
    atr_period: int = 14
    
    # Quality thresholds
    flatness_threshold: float = 0.35  # std/range ratio, lower = flatter
    volume_decline_required: bool = True
    min_confidence: float = 0.6
    
    # Peak detection
    peak_prominence_multiplier: float = 1.5  # prominence = ATR * this


class EnhancedLShapeDetector:
    """
    Enhanced L-shape pattern detector with dynamic thresholds.
    
    Example:
        detector = EnhancedLShapeDetector(config)
        result = detector.detect(df, current_idx)
        if result.detected and result.confidence > 0.7:
            # High confidence L-shape signal
    """
    
    def __init__(self, config: EnhancedDetectorConfig | None = None):
        self.config = config or EnhancedDetectorConfig()
    
    def calculate_atr(self, df: pl.DataFrame, idx: int) -> float:
        """Calculate ATR at given index."""
        period = self.config.atr_period
        if idx < period:
            return 0.0
        
        window = df.slice(idx - period, period)
        
        high = window["high"].to_numpy()
        low = window["low"].to_numpy()
        close = window["close"].to_numpy()
        
        # True Range calculation
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        tr[0] = tr1[0]  # First TR is just high-low
        
        return float(np.mean(tr))
    
    def detect_pivots(
        self, 
        prices: np.ndarray, 
        atr: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """Detect peaks and troughs using scipy with ATR-based prominence."""
        prominence = atr * self.config.peak_prominence_multiplier
        
        peaks, peak_props = find_peaks(prices, prominence=prominence, distance=3)
        troughs, trough_props = find_peaks(-prices, prominence=prominence, distance=3)
        
        return peaks, troughs
    
    def check_prior_drop(
        self,
        df: pl.DataFrame,
        idx: int,
        atr: float,
    ) -> tuple[bool, float, float]:
        """
        Check for prior drop with ATR-based threshold.
        
        Returns: (drop_detected, drop_pct, pivot_quality)
        """
        lookback = self.config.drop_lookback
        if idx < lookback:
            return False, 0.0, 0.0
        
        window = df.slice(idx - lookback, lookback)
        highs = window["high"].to_numpy()
        lows = window["low"].to_numpy()
        closes = window["close"].to_numpy()
        
        # Find pivots
        peaks, troughs = self.detect_pivots(closes, atr)
        
        # Calculate pivot quality (more clear pivots = higher quality)
        pivot_quality = min(1.0, (len(peaks) + len(troughs)) / 6)
        
        # Traditional drop detection with ATR threshold
        half = lookback // 2
        max_high = np.max(highs[:half])
        min_low = np.min(lows[half:])
        
        if max_high <= 0:
            return False, 0.0, pivot_quality
        
        drop_pct = (max_high - min_low) / max_high * 100
        threshold = (atr / closes[-1] * 100) * self.config.drop_atr_multiplier
        
        return drop_pct >= threshold, drop_pct, pivot_quality
    
    def check_consolidation(
        self,
        df: pl.DataFrame,
        idx: int,
        atr: float,
    ) -> tuple[bool, float, float]:
        """
        Check for consolidation with ATR-based range and flatness quality.
        
        Returns: (consolidation_detected, range_pct, flatness_score)
        """
        bars = self.config.consolidation_bars
        if idx < bars:
            return False, 0.0, 1.0
        
        window = df.slice(idx - bars, bars)
        highs = window["high"].to_numpy()
        lows = window["low"].to_numpy()
        closes = window["close"].to_numpy()
        
        range_high = np.max(highs)
        range_low = np.min(lows)
        
        if range_low <= 0:
            return False, 0.0, 1.0
        
        # Range percentage
        range_pct = (range_high - range_low) / range_low * 100
        
        # ATR-based threshold
        threshold = (atr / closes[-1] * 100) * self.config.consolidation_atr_multiplier
        
        # Flatness score: std / range (lower = flatter = better)
        price_range = range_high - range_low
        if price_range > 0:
            flatness_score = np.std(closes) / price_range
        else:
            flatness_score = 0.0
        
        consolidation_ok = range_pct <= threshold
        flatness_ok = flatness_score <= self.config.flatness_threshold
        
        return consolidation_ok and flatness_ok, range_pct, flatness_score
    
    def check_volume_decline(
        self,
        df: pl.DataFrame,
        idx: int,
    ) -> bool:
        """Check if volume is declining during consolidation (accumulation sign)."""
        bars = self.config.consolidation_bars
        if idx < bars:
            return True  # Default to True if not enough data
        
        window = df.slice(idx - bars, bars)
        
        if "volume" not in window.columns:
            return True  # Skip if no volume data
        
        volumes = window["volume"].to_numpy()
        
        # Linear regression slope
        x = np.arange(len(volumes))
        slope = np.polyfit(x, volumes, 1)[0]
        
        return slope < 0  # Declining volume
    
    def check_ma_breakout(
        self,
        df: pl.DataFrame,
        idx: int,
        ma_column: str = "ma_50",
    ) -> bool:
        """Check for MA breakout with bullish candle."""
        if idx < 1:
            return False
        
        current = df.row(idx, named=True)
        prev = df.row(idx - 1, named=True)
        
        ma_value = current.get(ma_column)
        prev_ma = prev.get(ma_column)
        
        if ma_value is None or prev_ma is None:
            return False
        
        prev_close = prev.get("close", 0)
        current_close = current.get("close", 0)
        current_open = current.get("open", 0)
        
        was_below = prev_close < prev_ma
        broke_above = current_close > ma_value
        bullish_candle = current_close > current_open
        
        return was_below and broke_above and bullish_candle
    
    def calculate_confidence(
        self,
        drop_pct: float,
        range_pct: float,
        flatness_score: float,
        volume_declining: bool,
        pivot_quality: float,
        atr_pct: float,
    ) -> float:
        """Calculate overall confidence score (0.0 - 1.0)."""
        scores = []
        
        # Drop quality (larger drop relative to ATR = better)
        drop_score = min(1.0, drop_pct / (atr_pct * 3))
        scores.append(drop_score * 0.25)
        
        # Consolidation tightness (smaller range = better)
        range_score = max(0.0, 1.0 - range_pct / (atr_pct * 2))
        scores.append(range_score * 0.25)
        
        # Flatness (lower std/range = better)
        flatness_quality = max(0.0, 1.0 - flatness_score / 0.5)
        scores.append(flatness_quality * 0.20)
        
        # Volume confirmation
        volume_score = 1.0 if volume_declining else 0.5
        scores.append(volume_score * 0.15)
        
        # Pivot clarity
        scores.append(pivot_quality * 0.15)
        
        return sum(scores)
    
    def detect(
        self,
        df: pl.DataFrame,
        idx: int,
        ma_column: str = "ma_50",
    ) -> DetectionResult:
        """
        Detect L-shape pattern at given index.
        
        Args:
            df: OHLCV DataFrame with MA columns
            idx: Current bar index
            ma_column: MA column name for breakout detection
            
        Returns:
            DetectionResult with detection status and confidence
        """
        # Calculate ATR
        atr = self.calculate_atr(df, idx)
        if atr <= 0:
            return DetectionResult(
                detected=False,
                confidence=0.0,
                drop_pct=0.0,
                consolidation_range_pct=0.0,
                flatness_score=1.0,
                volume_declining=False,
                pivot_quality=0.0,
                details={"error": "ATR calculation failed"},
            )
        
        current_price = df.row(idx, named=True).get("close", 0)
        atr_pct = (atr / current_price * 100) if current_price > 0 else 0
        
        # Check all conditions
        drop_ok, drop_pct, pivot_quality = self.check_prior_drop(df, idx, atr)
        consol_ok, range_pct, flatness_score = self.check_consolidation(df, idx, atr)
        volume_declining = self.check_volume_decline(df, idx)
        breakout_ok = self.check_ma_breakout(df, idx, ma_column)
        
        # Volume requirement
        if self.config.volume_decline_required and not volume_declining:
            volume_ok = False
        else:
            volume_ok = True
        
        # All conditions must pass
        detected = drop_ok and consol_ok and breakout_ok and volume_ok
        
        # Calculate confidence
        confidence = self.calculate_confidence(
            drop_pct=drop_pct,
            range_pct=range_pct,
            flatness_score=flatness_score,
            volume_declining=volume_declining,
            pivot_quality=pivot_quality,
            atr_pct=atr_pct,
        )
        
        # Apply minimum confidence threshold
        if detected and confidence < self.config.min_confidence:
            detected = False
        
        return DetectionResult(
            detected=detected,
            confidence=confidence,
            drop_pct=drop_pct,
            consolidation_range_pct=range_pct,
            flatness_score=flatness_score,
            volume_declining=volume_declining,
            pivot_quality=pivot_quality,
            details={
                "atr": atr,
                "atr_pct": atr_pct,
                "drop_ok": drop_ok,
                "consol_ok": consol_ok,
                "breakout_ok": breakout_ok,
                "volume_ok": volume_ok,
            },
        )
    
    def detect_batch(
        self,
        df: pl.DataFrame,
        ma_column: str = "ma_50",
        min_idx: int = 50,
    ) -> list[tuple[int, DetectionResult]]:
        """
        Detect L-shape patterns across entire DataFrame.
        
        Returns: List of (index, DetectionResult) for detected patterns
        """
        results = []
        
        for idx in range(min_idx, len(df)):
            result = self.detect(df, idx, ma_column)
            if result.detected:
                results.append((idx, result))
        
        return results
