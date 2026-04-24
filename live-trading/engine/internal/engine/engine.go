package engine

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/mgcha85/lshape-engine/internal/config"
	"github.com/mgcha85/lshape-engine/internal/detector"
	"github.com/mgcha85/lshape-engine/internal/exchange"
	"github.com/mgcha85/lshape-engine/internal/types"
)

type Engine struct {
	cfg      *config.Config
	exchange exchange.Exchange
	detector *detector.EnhancedDetector
	position *types.Position
	trades   []types.Trade
	mu       sync.RWMutex
	enabled  bool
}

func New(cfg *config.Config) (*Engine, error) {
	ex, err := exchange.NewBinance(cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to create exchange client: %w", err)
	}

	det := detector.NewEnhanced(cfg.Strategy.Timeframe)

	return &Engine{
		cfg:      cfg,
		exchange: ex,
		detector: det,
		trades:   make([]types.Trade, 0),
		enabled:  cfg.Strategy.Enabled,
	}, nil
}

func (e *Engine) Run(ctx context.Context) error {
	ticker := time.NewTicker(e.cfg.GetTimeframeDuration())
	defer ticker.Stop()

	log.Printf("Engine running with %s timeframe", e.cfg.Strategy.Timeframe)

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			if err := e.tick(ctx); err != nil {
				log.Printf("Tick error: %v", err)
			}
		}
	}
}

func (e *Engine) tick(ctx context.Context) error {
	e.mu.Lock()
	defer e.mu.Unlock()

	if !e.enabled {
		return nil
	}

	candles, err := e.exchange.GetKlines(ctx, e.cfg.Exchange.Symbol, e.cfg.Strategy.Timeframe, 200)
	if err != nil {
		return fmt.Errorf("failed to get candles: %w", err)
	}

	if e.position != nil {
		return e.managePosition(ctx, candles)
	}

	signal := e.detector.Detect(candles)
	if signal.Detected && signal.Confidence >= 0.6 {
		return e.openPosition(ctx, candles[len(candles)-1])
	}

	return nil
}

func (e *Engine) openPosition(ctx context.Context, candle types.Candle) error {
	balance, err := e.exchange.GetBalance(ctx)
	if err != nil {
		return err
	}

	positionValue := balance * e.cfg.Strategy.PositionSize
	quantity := (positionValue * float64(e.cfg.Strategy.Leverage)) / candle.Close

	order, err := e.exchange.PlaceOrder(ctx, exchange.OrderRequest{
		Symbol:   e.cfg.Exchange.Symbol,
		Side:     "BUY",
		Type:     "MARKET",
		Quantity: quantity,
	})
	if err != nil {
		return err
	}

	e.position = &types.Position{
		Symbol:      e.cfg.Exchange.Symbol,
		Side:        "LONG",
		EntryPrice:  order.AvgPrice,
		Quantity:    order.FilledQty,
		EntryTime:   time.Now(),
		HalfClosed:  false,
		CurrentSL:   e.cfg.Strategy.StopLoss,
	}

	log.Printf("Opened LONG position at %.2f, qty: %.4f", order.AvgPrice, order.FilledQty)
	return nil
}

func (e *Engine) managePosition(ctx context.Context, candles []types.Candle) error {
	current := candles[len(candles)-1]
	pnlPct := (current.Close - e.position.EntryPrice) / e.position.EntryPrice * 100

	if pnlPct <= -e.position.CurrentSL {
		return e.closePosition(ctx, "STOP_LOSS")
	}

	if !e.position.HalfClosed && pnlPct >= e.cfg.Strategy.HalfClose {
		if err := e.halfClose(ctx); err != nil {
			return err
		}
	}

	if pnlPct >= e.cfg.Strategy.TakeProfit {
		return e.closePosition(ctx, "TAKE_PROFIT")
	}

	return nil
}

func (e *Engine) halfClose(ctx context.Context) error {
	halfQty := e.position.Quantity / 2

	order, err := e.exchange.PlaceOrder(ctx, exchange.OrderRequest{
		Symbol:   e.cfg.Exchange.Symbol,
		Side:     "SELL",
		Type:     "MARKET",
		Quantity: halfQty,
	})
	if err != nil {
		return err
	}

	e.position.Quantity = e.position.Quantity - order.FilledQty
	e.position.HalfClosed = true
	e.position.HalfClosePrice = order.AvgPrice
	e.position.CurrentSL = 0

	log.Printf("Half closed at %.2f, remaining qty: %.4f", order.AvgPrice, e.position.Quantity)
	return nil
}

func (e *Engine) closePosition(ctx context.Context, reason string) error {
	order, err := e.exchange.PlaceOrder(ctx, exchange.OrderRequest{
		Symbol:   e.cfg.Exchange.Symbol,
		Side:     "SELL",
		Type:     "MARKET",
		Quantity: e.position.Quantity,
	})
	if err != nil {
		return err
	}

	trade := types.Trade{
		Symbol:     e.position.Symbol,
		Side:       e.position.Side,
		EntryPrice: e.position.EntryPrice,
		ExitPrice:  order.AvgPrice,
		Quantity:   e.position.Quantity,
		EntryTime:  e.position.EntryTime,
		ExitTime:   time.Now(),
		Result:     reason,
		PnLPct:     (order.AvgPrice - e.position.EntryPrice) / e.position.EntryPrice * 100,
	}
	e.trades = append(e.trades, trade)
	e.position = nil

	log.Printf("Closed position: %s at %.2f, PnL: %.2f%%", reason, order.AvgPrice, trade.PnLPct)
	return nil
}

func (e *Engine) SetEnabled(enabled bool) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.enabled = enabled
}

func (e *Engine) IsEnabled() bool {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.enabled
}

func (e *Engine) GetPosition() *types.Position {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.position
}

func (e *Engine) GetTrades() []types.Trade {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.trades
}

func (e *Engine) GetConfig() *config.Config {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.cfg
}

func (e *Engine) SetPositionSize(size float64) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.cfg.Strategy.PositionSize = size
}
