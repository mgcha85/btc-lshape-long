package database

import (
	"log"
	"os"
	"time"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var DB *gorm.DB

type SystemConfig struct {
	Key   string `gorm:"primaryKey"`
	Value string
}

type Trade struct {
	ID             uint      `gorm:"primaryKey" json:"id"`
	Symbol         string    `gorm:"index" json:"symbol"`
	Side           string    `json:"side"`
	OpenTime       time.Time `json:"open_time"`
	OpenPrice      float64   `json:"open_price"`
	CloseTime      *time.Time `json:"close_time,omitempty"`
	ClosePrice     *float64  `json:"close_price,omitempty"`
	ProfitPct      *float64  `json:"profit_pct,omitempty"`
	Result         string    `json:"result"`
	HalfClosed     bool      `json:"half_closed"`
	HalfCloseTime  *time.Time `json:"half_close_time,omitempty"`
	HalfClosePrice *float64  `json:"half_close_price,omitempty"`
	HalfClosePct   *float64  `json:"half_close_pct,omitempty"`
	Quantity       float64   `json:"quantity"`
	RemainingQty   float64   `json:"remaining_qty"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

type Position struct {
	Symbol       string    `gorm:"primaryKey" json:"symbol"`
	Side         string    `json:"side"`
	EntryPrice   float64   `json:"entry_price"`
	EntryTime    time.Time `json:"entry_time"`
	Quantity     float64   `json:"quantity"`
	RemainingQty float64   `json:"remaining_qty"`
	HalfClosed   bool      `json:"half_closed"`
	StopLoss     float64   `json:"stop_loss"`
	TakeProfit   float64   `json:"take_profit"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type Candle struct {
	ID        uint      `gorm:"primaryKey"`
	Symbol    string    `gorm:"index:idx_candle_lookup"`
	Timeframe string    `gorm:"index:idx_candle_lookup"`
	OpenTime  time.Time `gorm:"index:idx_candle_lookup"`
	Open      float64
	High      float64
	Low       float64
	Close     float64
	Volume    float64
}

func Init(dbPath string) {
	var err error
	newLogger := logger.New(
		log.New(os.Stdout, "\r\n", log.LstdFlags),
		logger.Config{
			SlowThreshold:             time.Second,
			LogLevel:                  logger.Warn,
			IgnoreRecordNotFoundError: true,
			Colorful:                  true,
		},
	)

	DB, err = gorm.Open(sqlite.Open(dbPath), &gorm.Config{
		Logger: newLogger,
	})
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}

	DB.Exec("PRAGMA journal_mode=WAL")

	err = DB.AutoMigrate(
		&SystemConfig{},
		&Trade{},
		&Position{},
		&Candle{},
	)
	if err != nil {
		log.Fatal("Failed to migrate database:", err)
	}

	seedConfig()
}

func seedConfig() {
	defaults := map[string]string{
		"BINANCE_API_KEY":     "",
		"BINANCE_SECRET_KEY":  "",
		"TARGET_SYMBOLS":      "BTCUSDT,ETHUSDT",
		"TRADING_ENABLED":     "false",
		"USE_FUTURES":         "true",
		"BREAKOUT_MA":         "50",
		"CONSOLIDATION_BARS":  "5",
		"CONSOLIDATION_RANGE": "5.0",
		"DROP_THRESHOLD":      "5.0",
		"TAKE_PROFIT_PCT":     "10.0",
		"STOP_LOSS_PCT":       "3.0",
		"HALF_CLOSE_ENABLED":  "true",
		"HALF_CLOSE_PCT":      "5.0",
	}

	for k, v := range defaults {
		var count int64
		DB.Model(&SystemConfig{}).Where("key = ?", k).Count(&count)
		if count == 0 {
			DB.Create(&SystemConfig{Key: k, Value: v})
		}
	}
}

func GetConfig(key string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}

	var cfg SystemConfig
	result := DB.First(&cfg, "key = ?", key)
	if result.Error == nil && cfg.Value != "" {
		return cfg.Value
	}

	return ""
}

func SetConfig(key, value string) error {
	return DB.Save(&SystemConfig{Key: key, Value: value}).Error
}

func GetAllConfigs() map[string]string {
	var configs []SystemConfig
	DB.Find(&configs)

	result := make(map[string]string)
	for _, c := range configs {
		result[c.Key] = c.Value
	}
	return result
}
