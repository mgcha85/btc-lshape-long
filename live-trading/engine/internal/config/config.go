package config

import (
	"fmt"
	"os"
	"strconv"
	"time"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Exchange ExchangeConfig `yaml:"exchange"`
	Strategy StrategyConfig `yaml:"strategy"`
	Server   ServerConfig   `yaml:"server"`
}

type ExchangeConfig struct {
	APIKey    string `yaml:"api_key"`
	SecretKey string `yaml:"secret_key"`
	Symbol    string `yaml:"symbol"`
	Testnet   bool   `yaml:"testnet"`
}

type StrategyConfig struct {
	Profile      string  `yaml:"profile"`
	Enabled      bool    `yaml:"enabled"`
	PositionSize float64 `yaml:"position_size"`
	Leverage     int     `yaml:"leverage"`
	TakeProfit   float64 `yaml:"take_profit"`
	StopLoss     float64 `yaml:"stop_loss"`
	HalfClose    float64 `yaml:"half_close"`
	Timeframe    string  `yaml:"timeframe"`
}

type ServerConfig struct {
	Port int `yaml:"port"`
}

var Profiles = map[string]StrategyConfig{
	"5m-aggressive": {
		Profile:      "5m-aggressive",
		PositionSize: 0.30,
		Leverage:     10,
		TakeProfit:   15.0,
		StopLoss:     2.0,
		HalfClose:    5.0,
		Timeframe:    "5m",
	},
	"15m-aggressive": {
		Profile:      "15m-aggressive",
		PositionSize: 0.30,
		Leverage:     10,
		TakeProfit:   15.0,
		StopLoss:     2.0,
		HalfClose:    5.0,
		Timeframe:    "15m",
	},
	"5m-balanced": {
		Profile:      "5m-balanced",
		PositionSize: 0.20,
		Leverage:     10,
		TakeProfit:   15.0,
		StopLoss:     2.0,
		HalfClose:    5.0,
		Timeframe:    "5m",
	},
}

var BacktestResults = map[string]map[string]interface{}{
	"5m-aggressive": {
		"return":   1012.0,
		"cagr":     46.8,
		"mdd":      46.3,
		"calmar":   1.01,
		"win_rate": 45.5,
		"trades":   334,
	},
	"15m-aggressive": {
		"return":   1862.4,
		"cagr":     60.7,
		"mdd":      69.9,
		"calmar":   0.87,
		"win_rate": 42.4,
		"trades":   255,
	},
	"5m-balanced": {
		"return":   510.9,
		"cagr":     33.4,
		"mdd":      32.0,
		"calmar":   1.05,
		"win_rate": 45.5,
		"trades":   334,
	},
}

func Load() (*Config, error) {
	cfg := &Config{
		Exchange: ExchangeConfig{
			APIKey:    os.Getenv("BINANCE_API_KEY"),
			SecretKey: os.Getenv("BINANCE_SECRET_KEY"),
			Symbol:    getEnvOrDefault("SYMBOL", "ETHUSDT"),
			Testnet:   getEnvOrDefault("TESTNET", "true") == "true",
		},
		Strategy: StrategyConfig{
			Profile: getEnvOrDefault("STRATEGY_PROFILE", "5m-balanced"),
			Enabled: getEnvOrDefault("TRADING_ENABLED", "false") == "true",
		},
		Server: ServerConfig{
			Port: getEnvOrDefaultInt("SERVER_PORT", 8080),
		},
	}

	if profile, ok := Profiles[cfg.Strategy.Profile]; ok {
		cfg.Strategy.PositionSize = profile.PositionSize
		cfg.Strategy.Leverage = profile.Leverage
		cfg.Strategy.TakeProfit = profile.TakeProfit
		cfg.Strategy.StopLoss = profile.StopLoss
		cfg.Strategy.HalfClose = profile.HalfClose
		cfg.Strategy.Timeframe = profile.Timeframe
	} else {
		return nil, fmt.Errorf("unknown strategy profile: %s", cfg.Strategy.Profile)
	}

	if configPath := os.Getenv("CONFIG_PATH"); configPath != "" {
		if err := loadFromFile(configPath, cfg); err != nil {
			return nil, err
		}
	}

	return cfg, nil
}

func loadFromFile(path string, cfg *Config) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return yaml.Unmarshal(data, cfg)
}

func getEnvOrDefault(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

func getEnvOrDefaultInt(key string, defaultVal int) int {
	if val := os.Getenv(key); val != "" {
		if i, err := strconv.Atoi(val); err == nil {
			return i
		}
	}
	return defaultVal
}

func (c *Config) GetTimeframeDuration() time.Duration {
	switch c.Strategy.Timeframe {
	case "5m":
		return 5 * time.Minute
	case "15m":
		return 15 * time.Minute
	case "1h":
		return time.Hour
	default:
		return 5 * time.Minute
	}
}
