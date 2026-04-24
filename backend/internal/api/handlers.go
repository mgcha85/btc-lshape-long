package api

import (
	"strconv"

	"github.com/gofiber/fiber/v2"

	"lshape-trader/internal/database"
	"lshape-trader/internal/strategy"
)

type Handler struct {
	positions map[string]*database.Position
	trading   bool
}

func NewHandler() *Handler {
	return &Handler{
		positions: make(map[string]*database.Position),
	}
}

func (h *Handler) SetPositions(positions map[string]*database.Position) {
	h.positions = positions
}

func (h *Handler) SetTradingEnabled(enabled bool) {
	h.trading = enabled
}

func (h *Handler) GetDashboard(c *fiber.Ctx) error {
	stats := getTradeStats()

	var openTrades int64
	database.DB.Model(&database.Trade{}).Where("close_time IS NULL").Count(&openTrades)

	positions := make([]database.Position, 0, len(h.positions))
	for _, p := range h.positions {
		positions = append(positions, *p)
	}

	return c.JSON(fiber.Map{
		"stats":           stats,
		"open_trades":     openTrades,
		"positions":       positions,
		"trading_enabled": h.trading,
	})
}

func getTradeStats() map[string]interface{} {
	var totalTrades int64
	var winningTrades int64
	var totalProfit float64

	database.DB.Model(&database.Trade{}).Where("close_time IS NOT NULL").Count(&totalTrades)
	database.DB.Model(&database.Trade{}).Where("close_time IS NOT NULL AND profit_pct > 0").Count(&winningTrades)
	database.DB.Model(&database.Trade{}).Where("close_time IS NOT NULL").Select("COALESCE(SUM(profit_pct), 0)").Row().Scan(&totalProfit)

	winRate := 0.0
	if totalTrades > 0 {
		winRate = float64(winningTrades) / float64(totalTrades) * 100
	}

	var winSum, loseSum float64
	database.DB.Model(&database.Trade{}).Where("profit_pct > 0 AND close_time IS NOT NULL").Select("COALESCE(SUM(profit_pct), 0)").Row().Scan(&winSum)
	database.DB.Model(&database.Trade{}).Where("profit_pct < 0 AND close_time IS NOT NULL").Select("COALESCE(SUM(ABS(profit_pct)), 0)").Row().Scan(&loseSum)

	profitFactor := 0.0
	if loseSum > 0 {
		profitFactor = winSum / loseSum
	}

	maxDD := calculateMaxDrawdown()

	return map[string]interface{}{
		"total_trades":    totalTrades,
		"winning_trades":  winningTrades,
		"win_rate":        winRate,
		"total_profit":    totalProfit,
		"profit_factor":   profitFactor,
		"max_drawdown":    maxDD,
	}
}

func calculateMaxDrawdown() float64 {
	var trades []database.Trade
	database.DB.Where("close_time IS NOT NULL").Order("close_time").Find(&trades)

	var cumulative, peak, maxDD float64
	for _, t := range trades {
		if t.ProfitPct != nil {
			cumulative += *t.ProfitPct
		}
		if cumulative > peak {
			peak = cumulative
		}
		dd := peak - cumulative
		if dd > maxDD {
			maxDD = dd
		}
	}
	return maxDD
}

func (h *Handler) GetTrades(c *fiber.Ctx) error {
	limit := c.QueryInt("limit", 50)
	offset := c.QueryInt("offset", 0)

	var trades []database.Trade
	database.DB.Order("open_time DESC").Limit(limit).Offset(offset).Find(&trades)

	return c.JSON(trades)
}

func (h *Handler) GetSettings(c *fiber.Ctx) error {
	return c.JSON(database.GetAllConfigs())
}

func (h *Handler) UpdateSettings(c *fiber.Ctx) error {
	var body map[string]string
	if err := c.BodyParser(&body); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
	}

	for k, v := range body {
		database.SetConfig(k, v)
	}

	return c.JSON(fiber.Map{"status": "updated"})
}

func (h *Handler) GetStrategyConfig(c *fiber.Ctx) error {
	cfg := loadStrategyConfig()
	return c.JSON(cfg)
}

func loadStrategyConfig() strategy.StrategyConfig {
	cfg := strategy.DefaultConfig()

	if v := database.GetConfig("BREAKOUT_MA"); v != "" {
		cfg.BreakoutMA, _ = strconv.Atoi(v)
	}
	if v := database.GetConfig("CONSOLIDATION_BARS"); v != "" {
		cfg.ConsolidationBars, _ = strconv.Atoi(v)
	}
	if v := database.GetConfig("CONSOLIDATION_RANGE"); v != "" {
		cfg.ConsolidationRangePct, _ = strconv.ParseFloat(v, 64)
	}
	if v := database.GetConfig("DROP_THRESHOLD"); v != "" {
		cfg.DropThresholdPct, _ = strconv.ParseFloat(v, 64)
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

func (h *Handler) UpdateStrategyConfig(c *fiber.Ctx) error {
	var cfg strategy.StrategyConfig
	if err := c.BodyParser(&cfg); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
	}

	database.SetConfig("BREAKOUT_MA", strconv.Itoa(cfg.BreakoutMA))
	database.SetConfig("CONSOLIDATION_BARS", strconv.Itoa(cfg.ConsolidationBars))
	database.SetConfig("CONSOLIDATION_RANGE", strconv.FormatFloat(cfg.ConsolidationRangePct, 'f', 2, 64))
	database.SetConfig("DROP_THRESHOLD", strconv.FormatFloat(cfg.DropThresholdPct, 'f', 2, 64))
	database.SetConfig("TAKE_PROFIT_PCT", strconv.FormatFloat(cfg.TakeProfitPct, 'f', 2, 64))
	database.SetConfig("STOP_LOSS_PCT", strconv.FormatFloat(cfg.StopLossPct, 'f', 2, 64))
	database.SetConfig("HALF_CLOSE_ENABLED", strconv.FormatBool(cfg.HalfCloseEnabled))
	database.SetConfig("HALF_CLOSE_PCT", strconv.FormatFloat(cfg.HalfClosePct, 'f', 2, 64))

	return c.JSON(fiber.Map{"status": "ok"})
}

func (h *Handler) ToggleTrading(c *fiber.Ctx) error {
	var body struct {
		Enabled bool `json:"enabled"`
	}
	if err := c.BodyParser(&body); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
	}

	h.trading = body.Enabled
	database.SetConfig("TRADING_ENABLED", strconv.FormatBool(body.Enabled))

	return c.JSON(fiber.Map{"trading_enabled": h.trading})
}

func (h *Handler) GetPositions(c *fiber.Ctx) error {
	positions := make([]database.Position, 0, len(h.positions))
	for _, p := range h.positions {
		positions = append(positions, *p)
	}
	return c.JSON(positions)
}

func (h *Handler) GetStats(c *fiber.Ctx) error {
	return c.JSON(getTradeStats())
}

func (h *Handler) HealthCheck(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"status":  "ok",
		"trading": h.trading,
	})
}
