package types

import "time"

type Candle struct {
	OpenTime  time.Time
	Open      float64
	High      float64
	Low       float64
	Close     float64
	Volume    float64
	CloseTime time.Time
}

type Position struct {
	Symbol         string
	Side           string
	EntryPrice     float64
	Quantity       float64
	EntryTime      time.Time
	HalfClosed     bool
	HalfClosePrice float64
	CurrentSL      float64
}

type Trade struct {
	Symbol     string
	Side       string
	EntryPrice float64
	ExitPrice  float64
	Quantity   float64
	EntryTime  time.Time
	ExitTime   time.Time
	Result     string
	PnLPct     float64
}

type AccountInfo struct {
	TotalBalance     float64
	AvailableBalance float64
	UnrealizedPnL    float64
}
