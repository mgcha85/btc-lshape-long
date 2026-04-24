package detector

import (
	"math"

	"github.com/mgcha85/lshape-engine/internal/types"
)

type DetectorConfig struct {
	DropATRMultiplier   float64
	ConsolATRMultiplier float64
	FlatnessThreshold   float64
	MinConfidence       float64
	ATRPeriod           int
	DropLookback        int
	ConsolBars          int
}

type Signal struct {
	Detected   bool
	Confidence float64
	DropPct    float64
	RangePct   float64
	Flatness   float64
}

type EnhancedDetector struct {
	config DetectorConfig
}

func NewEnhanced(timeframe string) *EnhancedDetector {
	cfg := DetectorConfig{
		ATRPeriod:    14,
		DropLookback: 20,
		ConsolBars:   5,
	}

	switch timeframe {
	case "5m":
		cfg.DropATRMultiplier = 1.5
		cfg.ConsolATRMultiplier = 1.0
		cfg.FlatnessThreshold = 0.5
		cfg.MinConfidence = 0.5
	case "15m":
		cfg.DropATRMultiplier = 2.0
		cfg.ConsolATRMultiplier = 1.2
		cfg.FlatnessThreshold = 0.45
		cfg.MinConfidence = 0.5
	default: // 1h
		cfg.DropATRMultiplier = 2.5
		cfg.ConsolATRMultiplier = 1.5
		cfg.FlatnessThreshold = 0.4
		cfg.MinConfidence = 0.6
	}

	return &EnhancedDetector{config: cfg}
}

func (d *EnhancedDetector) Detect(candles []types.Candle) Signal {
	if len(candles) < d.config.DropLookback+d.config.ATRPeriod {
		return Signal{}
	}

	idx := len(candles) - 1
	atr := d.calculateATR(candles, idx)
	if atr <= 0 {
		return Signal{}
	}

	currentPrice := candles[idx].Close
	atrPct := (atr / currentPrice) * 100

	dropOk, dropPct := d.checkDrop(candles, idx, atrPct)
	consolOk, rangePct, flatness := d.checkConsolidation(candles, idx, atrPct)
	breakoutOk := d.checkBreakout(candles, idx)

	detected := dropOk && consolOk && breakoutOk

	confidence := d.calculateConfidence(dropPct, rangePct, flatness, atrPct)

	if detected && confidence < d.config.MinConfidence {
		detected = false
	}

	return Signal{
		Detected:   detected,
		Confidence: confidence,
		DropPct:    dropPct,
		RangePct:   rangePct,
		Flatness:   flatness,
	}
}

func (d *EnhancedDetector) calculateATR(candles []types.Candle, idx int) float64 {
	period := d.config.ATRPeriod
	if idx < period {
		return 0
	}

	sum := 0.0
	for i := idx - period + 1; i <= idx; i++ {
		tr := candles[i].High - candles[i].Low
		if i > 0 {
			tr = math.Max(tr, math.Abs(candles[i].High-candles[i-1].Close))
			tr = math.Max(tr, math.Abs(candles[i].Low-candles[i-1].Close))
		}
		sum += tr
	}

	return sum / float64(period)
}

func (d *EnhancedDetector) checkDrop(candles []types.Candle, idx int, atrPct float64) (bool, float64) {
	lookback := d.config.DropLookback
	if idx < lookback {
		return false, 0
	}

	half := lookback / 2
	maxHigh := 0.0
	minLow := math.MaxFloat64

	for i := idx - lookback; i < idx-half; i++ {
		if candles[i].High > maxHigh {
			maxHigh = candles[i].High
		}
	}

	for i := idx - half; i < idx; i++ {
		if candles[i].Low < minLow {
			minLow = candles[i].Low
		}
	}

	if maxHigh <= 0 {
		return false, 0
	}

	dropPct := (maxHigh - minLow) / maxHigh * 100
	threshold := atrPct * d.config.DropATRMultiplier

	return dropPct >= threshold, dropPct
}

func (d *EnhancedDetector) checkConsolidation(candles []types.Candle, idx int, atrPct float64) (bool, float64, float64) {
	bars := d.config.ConsolBars
	if idx < bars {
		return false, 0, 1
	}

	maxHigh := 0.0
	minLow := math.MaxFloat64
	closes := make([]float64, bars)

	for i := 0; i < bars; i++ {
		c := candles[idx-bars+i]
		if c.High > maxHigh {
			maxHigh = c.High
		}
		if c.Low < minLow {
			minLow = c.Low
		}
		closes[i] = c.Close
	}

	if minLow <= 0 {
		return false, 0, 1
	}

	rangePct := (maxHigh - minLow) / minLow * 100
	threshold := atrPct * d.config.ConsolATRMultiplier

	priceRange := maxHigh - minLow
	flatness := 1.0
	if priceRange > 0 {
		flatness = stdDev(closes) / priceRange
	}

	consolOk := rangePct <= threshold
	flatOk := flatness <= d.config.FlatnessThreshold

	return consolOk && flatOk, rangePct, flatness
}

func (d *EnhancedDetector) checkBreakout(candles []types.Candle, idx int) bool {
	if idx < 51 {
		return false
	}

	current := candles[idx]
	prev := candles[idx-1]

	ma := 0.0
	for i := idx - 50; i < idx; i++ {
		ma += candles[i].Close
	}
	ma /= 50

	prevMA := 0.0
	for i := idx - 51; i < idx-1; i++ {
		prevMA += candles[i].Close
	}
	prevMA /= 50

	wasBelow := prev.Close < prevMA
	brokeAbove := current.Close > ma
	bullish := current.Close > current.Open

	return wasBelow && brokeAbove && bullish
}

func (d *EnhancedDetector) calculateConfidence(dropPct, rangePct, flatness, atrPct float64) float64 {
	dropScore := math.Min(1.0, dropPct/(atrPct*3)) * 0.25
	rangeScore := math.Max(0.0, 1.0-rangePct/(atrPct*2)) * 0.25
	flatScore := math.Max(0.0, 1.0-flatness/0.5) * 0.25
	baseScore := 0.25

	return dropScore + rangeScore + flatScore + baseScore
}

func stdDev(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	mean := 0.0
	for _, v := range values {
		mean += v
	}
	mean /= float64(len(values))

	variance := 0.0
	for _, v := range values {
		variance += (v - mean) * (v - mean)
	}
	variance /= float64(len(values))

	return math.Sqrt(variance)
}
