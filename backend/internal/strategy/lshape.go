package strategy

type Candle struct {
	Open   float64
	High   float64
	Low    float64
	Close  float64
	Volume float64
}

type StrategyConfig struct {
	BreakoutMA            int
	ConsolidationBars     int
	ConsolidationRangePct float64
	DropThresholdPct      float64
	TakeProfitPct         float64
	StopLossPct           float64
	HalfCloseEnabled      bool
	HalfClosePct          float64
}

func DefaultConfig() StrategyConfig {
	return StrategyConfig{
		BreakoutMA:            50,
		ConsolidationBars:     5,
		ConsolidationRangePct: 5.0,
		DropThresholdPct:      5.0,
		TakeProfitPct:         10.0,
		StopLossPct:           3.0,
		HalfCloseEnabled:      true,
		HalfClosePct:          5.0,
	}
}

type LShapeStrategy struct {
	Config StrategyConfig
}

func New(cfg StrategyConfig) *LShapeStrategy {
	return &LShapeStrategy{Config: cfg}
}

func (s *LShapeStrategy) CalculateMA(candles []Candle, period int) float64 {
	if len(candles) < period {
		return 0
	}
	var sum float64
	for i := len(candles) - period; i < len(candles); i++ {
		sum += candles[i].Close
	}
	return sum / float64(period)
}

func (s *LShapeStrategy) DetectConsolidation(candles []Candle) bool {
	n := s.Config.ConsolidationBars
	if len(candles) < n {
		return false
	}

	window := candles[len(candles)-n:]
	high, low := window[0].High, window[0].Low

	for _, c := range window {
		if c.High > high {
			high = c.High
		}
		if c.Low < low {
			low = c.Low
		}
	}

	if low <= 0 {
		return false
	}

	rangePct := (high - low) / low * 100
	return rangePct <= s.Config.ConsolidationRangePct
}

func (s *LShapeStrategy) DetectPriorDrop(candles []Candle, lookback int) bool {
	if len(candles) < lookback {
		return false
	}

	window := candles[len(candles)-lookback:]
	half := len(window) / 2

	var maxHigh float64
	for _, c := range window[:half] {
		if c.High > maxHigh {
			maxHigh = c.High
		}
	}

	minLow := window[half].Low
	for _, c := range window[half:] {
		if c.Low < minLow {
			minLow = c.Low
		}
	}

	if maxHigh <= 0 {
		return false
	}

	dropPct := (maxHigh - minLow) / maxHigh * 100
	return dropPct >= s.Config.DropThresholdPct
}

func (s *LShapeStrategy) DetectMABreakout(candles []Candle) bool {
	if len(candles) < s.Config.BreakoutMA+1 {
		return false
	}

	current := candles[len(candles)-1]
	prev := candles[len(candles)-2]

	currentMA := s.CalculateMA(candles, s.Config.BreakoutMA)
	prevCandles := candles[:len(candles)-1]
	prevMA := s.CalculateMA(prevCandles, s.Config.BreakoutMA)

	if currentMA == 0 || prevMA == 0 {
		return false
	}

	wasBelow := prev.Close < prevMA
	brokeAbove := current.Close > currentMA
	bullishCandle := current.Close > current.Open

	return wasBelow && brokeAbove && bullishCandle
}

func (s *LShapeStrategy) CheckEntry(candles []Candle) bool {
	if len(candles) < s.Config.BreakoutMA+20 {
		return false
	}

	hasConsolidation := s.DetectConsolidation(candles)
	hasPriorDrop := s.DetectPriorDrop(candles, 20)
	hasBreakout := s.DetectMABreakout(candles)

	return hasConsolidation && hasPriorDrop && hasBreakout
}

func (s *LShapeStrategy) CalculatePnL(entryPrice, currentPrice float64) float64 {
	return (currentPrice - entryPrice) / entryPrice * 100
}

type ExitSignal int

const (
	NoExit ExitSignal = iota
	HalfClose
	TakeProfit
	StopLoss
)

func (s *LShapeStrategy) CheckExit(entryPrice, currentPrice float64, halfClosed bool) ExitSignal {
	pnl := s.CalculatePnL(entryPrice, currentPrice)

	if pnl >= s.Config.TakeProfitPct {
		return TakeProfit
	}

	stopLoss := s.Config.StopLossPct
	if halfClosed {
		stopLoss = 0
	}

	if pnl <= -stopLoss {
		return StopLoss
	}

	if s.Config.HalfCloseEnabled && !halfClosed && pnl >= s.Config.HalfClosePct {
		return HalfClose
	}

	return NoExit
}
