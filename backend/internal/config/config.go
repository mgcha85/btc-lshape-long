package config

import (
	"os"
	"strings"

	"github.com/joho/godotenv"
)

type Config struct {
	Env            string
	Port           string
	DBPath         string
	BinanceAPIKey  string
	BinanceSecret  string
	TargetSymbols  []string
	TradingEnabled bool
}

func Load() (*Config, error) {
	env := os.Getenv("APP_ENV")
	if env == "" {
		env = "dev"
	}

	envFile := ".env." + env
	_ = godotenv.Load(envFile)
	_ = godotenv.Load(".env")

	symbols := os.Getenv("TARGET_SYMBOLS")
	if symbols == "" {
		symbols = "BTCUSDT,ETHUSDT"
	}

	tradingEnabled := os.Getenv("TRADING_ENABLED") == "true"

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "./data/trader.db"
	}

	return &Config{
		Env:            env,
		Port:           port,
		DBPath:         dbPath,
		BinanceAPIKey:  os.Getenv("BINANCE_API_KEY"),
		BinanceSecret:  os.Getenv("BINANCE_SECRET_KEY"),
		TargetSymbols:  strings.Split(symbols, ","),
		TradingEnabled: tradingEnabled,
	}, nil
}
