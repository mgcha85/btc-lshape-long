package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/mgcha85/lshape-engine/internal/config"
	"github.com/mgcha85/lshape-engine/internal/engine"
)

type Server struct {
	cfg    *config.Config
	engine *engine.Engine
	server *http.Server
}

func New(cfg *config.Config, eng *engine.Engine) *Server {
	s := &Server{
		cfg:    cfg,
		engine: eng,
	}

	mux := http.NewServeMux()
	
	mux.HandleFunc("/api/status", s.corsMiddleware(s.handleStatus))
	mux.HandleFunc("/api/config", s.corsMiddleware(s.handleConfig))
	mux.HandleFunc("/api/position", s.corsMiddleware(s.handlePosition))
	mux.HandleFunc("/api/trades", s.corsMiddleware(s.handleTrades))
	mux.HandleFunc("/api/toggle", s.corsMiddleware(s.handleToggle))
	mux.HandleFunc("/api/profiles", s.corsMiddleware(s.handleProfiles))
	
	staticDir := cfg.Server.StaticDir
	if _, err := os.Stat(staticDir); err == nil {
		mux.Handle("/", s.spaHandler(staticDir))
	}

	s.server = &http.Server{
		Addr:    fmt.Sprintf(":%d", cfg.Server.Port),
		Handler: mux,
	}

	return s
}

func (s *Server) Start() error {
	return s.server.ListenAndServe()
}

func (s *Server) Stop() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return s.server.Shutdown(ctx)
}

func (s *Server) corsMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next(w, r)
	}
}

func (s *Server) handleStatus(w http.ResponseWriter, r *http.Request) {
	status := map[string]interface{}{
		"trading_enabled": s.engine.IsEnabled(),
		"profile":         s.cfg.Strategy.Profile,
		"symbol":          s.cfg.Exchange.Symbol,
		"timeframe":       s.cfg.Strategy.Timeframe,
		"position":        s.engine.GetPosition(),
		"trade_count":     len(s.engine.GetTrades()),
	}

	s.jsonResponse(w, status)
}

func (s *Server) handleConfig(w http.ResponseWriter, r *http.Request) {
	cfg := s.engine.GetConfig()
	
	response := map[string]interface{}{
		"profile":       cfg.Strategy.Profile,
		"position_size": cfg.Strategy.PositionSize,
		"leverage":      cfg.Strategy.Leverage,
		"take_profit":   cfg.Strategy.TakeProfit,
		"stop_loss":     cfg.Strategy.StopLoss,
		"half_close":    cfg.Strategy.HalfClose,
		"timeframe":     cfg.Strategy.Timeframe,
		"symbol":        cfg.Exchange.Symbol,
		"testnet":       cfg.Exchange.Testnet,
	}

	s.jsonResponse(w, response)
}

func (s *Server) handlePosition(w http.ResponseWriter, r *http.Request) {
	s.jsonResponse(w, s.engine.GetPosition())
}

func (s *Server) handleTrades(w http.ResponseWriter, r *http.Request) {
	s.jsonResponse(w, s.engine.GetTrades())
}

func (s *Server) handleToggle(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Enabled bool `json:"enabled"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	s.engine.SetEnabled(req.Enabled)

	s.jsonResponse(w, map[string]bool{"enabled": s.engine.IsEnabled()})
}

func (s *Server) handleProfiles(w http.ResponseWriter, r *http.Request) {
	profiles := make([]map[string]interface{}, 0)

	for name, profile := range config.Profiles {
		backtest := config.BacktestResults[name]
		profiles = append(profiles, map[string]interface{}{
			"name":          name,
			"position_size": profile.PositionSize,
			"leverage":      profile.Leverage,
			"take_profit":   profile.TakeProfit,
			"stop_loss":     profile.StopLoss,
			"half_close":    profile.HalfClose,
			"timeframe":     profile.Timeframe,
			"backtest":      backtest,
		})
	}

	s.jsonResponse(w, profiles)
}

func (s *Server) jsonResponse(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

func (s *Server) spaHandler(staticDir string) http.Handler {
	fileServer := http.FileServer(http.Dir(staticDir))
	
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/api/") {
			http.NotFound(w, r)
			return
		}
		
		path := filepath.Join(staticDir, r.URL.Path)
		
		if _, err := os.Stat(path); os.IsNotExist(err) {
			http.ServeFile(w, r, filepath.Join(staticDir, "index.html"))
			return
		}
		
		fileServer.ServeHTTP(w, r)
	})
}
