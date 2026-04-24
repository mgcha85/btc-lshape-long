package main

import (
	"context"
	"log"
	"math"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/adshao/go-binance/v2/futures"
	"github.com/gofiber/fiber/v2"
	"github.com/joho/godotenv"

	"lshape-trader/internal/api"
	"lshape-trader/internal/database"
	"lshape-trader/internal/strategy"
)

type Trader struct {
	client     *futures.Client
	strategy   *strategy.LShapeStrategy
	positions  map[string]*database.Position
	mu         sync.RWMutex
	trading    bool
	candlesBuf map[string][]strategy.Candle
	symbols    []string
	stopCh     chan struct{}
}

func NewTrader() *Trader {
	apiKey := database.GetConfig("BINANCE_API_KEY")
	apiSecret := database.GetConfig("BINANCE_SECRET_KEY")
	useTestnet := database.GetConfig("USE_TESTNET") == "true"

	futures.UseTestnet = useTestnet
	var client *futures.Client
	if apiKey != "" && apiSecret != "" {
		client = futures.NewClient(apiKey, apiSecret)
	}

	symbolsStr := database.GetConfig("TARGET_SYMBOLS")
	if symbolsStr == "" {
		symbolsStr = "BTCUSDT,ETHUSDT"
	}
	symbols := strings.Split(symbolsStr, ",")

	trading := database.GetConfig("TRADING_ENABLED") == "true"

	return &Trader{
		client:     client,
		strategy:   strategy.New(loadStrategyConfigFromDB()),
		positions:  make(map[string]*database.Position),
		trading:    trading,
		candlesBuf: make(map[string][]strategy.Candle),
		symbols:    symbols,
		stopCh:     make(chan struct{}),
	}
}

func loadStrategyConfigFromDB() strategy.StrategyConfig {
	cfg := strategy.DefaultConfig()

	if v := database.GetConfig("BREAKOUT_MA"); v != "" {
		cfg.BreakoutMA, _ = strconv.Atoi(v)
	}
	if v := database.GetConfig("TAKE_PROFIT_PCT"); v != "" {
		cfg.TakeProfitPct, _ = strconv.ParseFloat(v, 64)
	}
	if v := database.GetConfig("STOP_LOSS_PCT"); v != "" {
		cfg.StopLossPct, _ = strconv.ParseFloat(v, 64)
	}
	if v := database.GetConfig("HALF_CLOSE_ENABLED"); v != "" {
		cfg.HalfCloseEnabled = v == "true"
	}
	if v := database.GetConfig("HALF_CLOSE_PCT"); v != "" {
		cfg.HalfClosePct, _ = strconv.ParseFloat(v, 64)
	}

	return cfg
}

func (t *Trader) Start() error {
	log.Println("[TRADER] Starting...")

	for _, symbol := range t.symbols {
		candles, err := t.getKlines(symbol, "1h", 500)
		if err != nil {
			log.Printf("[TRADER] Failed to get candles for %s: %v", symbol, err)
			continue
		}
		t.candlesBuf[symbol] = candles
		log.Printf("[TRADER] Loaded %d candles for %s", len(candles), symbol)
	}

	go t.runCandlePoller()
	go t.runPriceMonitor()

	return nil
}

func (t *Trader) getKlines(symbol, interval string, limit int) ([]strategy.Candle, error) {
	if t.client == nil {
		return nil, nil
	}

	klines, err := t.client.NewKlinesService().
		Symbol(symbol).
		Interval(interval).
		Limit(limit).
		Do(context.Background())
	if err != nil {
		return nil, err
	}

	candles := make([]strategy.Candle, 0, len(klines))
	for _, k := range klines {
		candles = append(candles, strategy.Candle{
			Open:   parseFloat(k.Open),
			High:   parseFloat(k.High),
			Low:    parseFloat(k.Low),
			Close:  parseFloat(k.Close),
			Volume: parseFloat(k.Volume),
		})
	}
	return candles, nil
}

func (t *Trader) runCandlePoller() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-t.stopCh:
			return
		case <-ticker.C:
			for _, symbol := range t.symbols {
				candles, err := t.getKlines(symbol, "1h", 500)
				if err != nil {
					log.Printf("[POLLER] Error fetching %s: %v", symbol, err)
					continue
				}

				t.mu.Lock()
				t.candlesBuf[symbol] = candles
				t.mu.Unlock()

				if len(candles) > 0 {
					t.checkEntry(symbol, candles)
				}
			}
		}
	}
}

func (t *Trader) runPriceMonitor() {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-t.stopCh:
			return
		case <-ticker.C:
			t.mu.RLock()
			positionsCopy := make(map[string]*database.Position)
			for k, v := range t.positions {
				positionsCopy[k] = v
			}
			t.mu.RUnlock()

			for symbol, pos := range positionsCopy {
				price, err := t.getPrice(symbol)
				if err != nil {
					continue
				}
				t.checkExit(symbol, pos, price)
			}
		}
	}
}

func (t *Trader) getPrice(symbol string) (float64, error) {
	if t.client == nil {
		return 0, nil
	}

	prices, err := t.client.NewListPricesService().Symbol(symbol).Do(context.Background())
	if err != nil {
		return 0, err
	}
	if len(prices) > 0 {
		return parseFloat(prices[0].Price), nil
	}
	return 0, nil
}

func (t *Trader) checkEntry(symbol string, candles []strategy.Candle) {
	t.mu.Lock()
	defer t.mu.Unlock()

	if _, hasPosition := t.positions[symbol]; hasPosition {
		return
	}

	if !t.trading {
		return
	}

	if t.strategy.CheckEntry(candles) {
		log.Printf("[SIGNAL] Entry signal for %s!", symbol)
		t.openPosition(symbol, candles[len(candles)-1].Close)
	}
}

func (t *Trader) checkExit(symbol string, pos *database.Position, currentPrice float64) {
	t.mu.Lock()
	defer t.mu.Unlock()

	exitSignal := t.strategy.CheckExit(pos.EntryPrice, currentPrice, pos.HalfClosed)

	switch exitSignal {
	case strategy.TakeProfit:
		log.Printf("[EXIT] Take profit for %s at %.2f", symbol, currentPrice)
		t.closePosition(symbol, currentPrice, "TP")
	case strategy.StopLoss:
		log.Printf("[EXIT] Stop loss for %s at %.2f", symbol, currentPrice)
		t.closePosition(symbol, currentPrice, "SL")
	case strategy.HalfClose:
		log.Printf("[EXIT] Half close for %s at %.2f", symbol, currentPrice)
		t.halfClosePosition(symbol, currentPrice)
	}
}

func (t *Trader) openPosition(symbol string, price float64) {
	quantity := 0.01
	if t.client != nil {
		balance, _ := t.getBalance("USDT")
		if balance > 0 {
			positionSize := balance * 0.1
			quantity = positionSize / price
		}
	}

	if t.client != nil && t.trading {
		_, err := t.client.NewCreateOrderService().
			Symbol(symbol).
			Side(futures.SideTypeBuy).
			PositionSide(futures.PositionSideTypeLong).
			Type(futures.OrderTypeMarket).
			Quantity(formatQuantity(quantity)).
			Do(context.Background())
		if err != nil {
			log.Printf("[ORDER] Failed to open %s: %v", symbol, err)
			return
		}
	}

	now := time.Now()
	pos := &database.Position{
		Symbol:       symbol,
		Side:         "LONG",
		EntryPrice:   price,
		EntryTime:    now,
		Quantity:     quantity,
		RemainingQty: quantity,
		StopLoss:     price * (1 - t.strategy.Config.StopLossPct/100),
		TakeProfit:   price * (1 + t.strategy.Config.TakeProfitPct/100),
		UpdatedAt:    now,
	}

	t.positions[symbol] = pos
	database.DB.Save(pos)

	database.DB.Create(&database.Trade{
		Symbol:       symbol,
		Side:         "LONG",
		OpenTime:     now,
		OpenPrice:    price,
		Quantity:     quantity,
		RemainingQty: quantity,
	})

	log.Printf("[POSITION] Opened %s LONG @ %.2f, qty=%.6f", symbol, price, quantity)
}

func (t *Trader) closePosition(symbol string, price float64, result string) {
	pos, ok := t.positions[symbol]
	if !ok {
		return
	}

	if t.client != nil && t.trading {
		_, err := t.client.NewCreateOrderService().
			Symbol(symbol).
			Side(futures.SideTypeSell).
			PositionSide(futures.PositionSideTypeLong).
			Type(futures.OrderTypeMarket).
			Quantity(formatQuantity(pos.RemainingQty)).
			Do(context.Background())
		if err != nil {
			log.Printf("[ORDER] Failed to close %s: %v", symbol, err)
			return
		}
	}

	pnl := t.strategy.CalculatePnL(pos.EntryPrice, price)
	now := time.Now()

	var trade database.Trade
	database.DB.Where("symbol = ? AND close_time IS NULL", symbol).First(&trade)
	if trade.ID > 0 {
		trade.CloseTime = &now
		trade.ClosePrice = &price
		trade.ProfitPct = &pnl
		trade.Result = result
		trade.RemainingQty = 0
		database.DB.Save(&trade)
	}

	database.DB.Delete(&database.Position{}, "symbol = ?", symbol)
	delete(t.positions, symbol)

	log.Printf("[POSITION] Closed %s @ %.2f, PnL=%.2f%%, result=%s", symbol, price, pnl, result)
}

func (t *Trader) halfClosePosition(symbol string, price float64) {
	pos, ok := t.positions[symbol]
	if !ok || pos.HalfClosed {
		return
	}

	halfQty := pos.RemainingQty / 2

	if t.client != nil && t.trading {
		_, err := t.client.NewCreateOrderService().
			Symbol(symbol).
			Side(futures.SideTypeSell).
			PositionSide(futures.PositionSideTypeLong).
			Type(futures.OrderTypeMarket).
			Quantity(formatQuantity(halfQty)).
			Do(context.Background())
		if err != nil {
			log.Printf("[ORDER] Failed to half close %s: %v", symbol, err)
			return
		}
	}

	pnl := t.strategy.CalculatePnL(pos.EntryPrice, price)
	now := time.Now()

	pos.HalfClosed = true
	pos.RemainingQty = halfQty
	pos.StopLoss = pos.EntryPrice
	pos.UpdatedAt = now

	database.DB.Save(pos)

	var trade database.Trade
	database.DB.Where("symbol = ? AND close_time IS NULL", symbol).First(&trade)
	if trade.ID > 0 {
		trade.HalfClosed = true
		trade.HalfCloseTime = &now
		trade.HalfClosePrice = &price
		trade.HalfClosePct = &pnl
		trade.RemainingQty = halfQty
		database.DB.Save(&trade)
	}

	log.Printf("[POSITION] Half closed %s @ %.2f, PnL=%.2f%%", symbol, price, pnl)
}

func (t *Trader) getBalance(asset string) (float64, error) {
	if t.client == nil {
		return 10000, nil
	}

	res, err := t.client.NewGetBalanceService().Do(context.Background())
	if err != nil {
		return 0, err
	}

	for _, b := range res {
		if b.Asset == asset {
			return parseFloat(b.Balance), nil
		}
	}
	return 0, nil
}

func (t *Trader) GetPositions() map[string]*database.Position {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.positions
}

func (t *Trader) IsTradingEnabled() bool {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.trading
}

func (t *Trader) Close() {
	close(t.stopCh)
}

func parseFloat(s string) float64 {
	f, _ := strconv.ParseFloat(s, 64)
	return f
}

func formatQuantity(qty float64) string {
	return strconv.FormatFloat(math.Floor(qty*1000)/1000, 'f', 3, 64)
}

func main() {
	env := os.Getenv("APP_ENV")
	if env == "" {
		env = "dev"
	}
	_ = godotenv.Load(".env." + env)
	_ = godotenv.Load(".env")

	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "./data/trader.db"
	}

	os.MkdirAll("./data", 0755)
	database.Init(dbPath)

	trader := NewTrader()
	if err := trader.Start(); err != nil {
		log.Fatalf("Failed to start trader: %v", err)
	}
	defer trader.Close()

	app := fiber.New(fiber.Config{
		DisableStartupMessage: true,
		ReadBufferSize:        16384,
		WriteBufferSize:       16384,
	})

	handler := api.NewHandler()

	go func() {
		for {
			time.Sleep(time.Second)
			handler.SetPositions(trader.GetPositions())
			handler.SetTradingEnabled(trader.IsTradingEnabled())
		}
	}()

	api.SetupRoutes(app, handler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	go func() {
		log.Printf("[SERVER] Starting on port %s (env: %s)", port, env)
		if err := app.Listen(":" + port); err != nil {
			log.Fatalf("Server error: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("[SERVER] Shutting down...")
	app.Shutdown()
}
