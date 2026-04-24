package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/mgcha85/lshape-engine/internal/config"
	"github.com/mgcha85/lshape-engine/internal/engine"
	"github.com/mgcha85/lshape-engine/internal/server"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	eng, err := engine.New(cfg)
	if err != nil {
		log.Fatalf("Failed to create engine: %v", err)
	}

	srv := server.New(cfg, eng)

	go func() {
		if err := srv.Start(); err != nil {
			log.Fatalf("Server error: %v", err)
		}
	}()

	go func() {
		if err := eng.Run(ctx); err != nil {
			log.Printf("Engine stopped: %v", err)
		}
	}()

	fmt.Printf("L-Shape Trading Engine started\n")
	fmt.Printf("Strategy: %s\n", cfg.Strategy.Profile)
	fmt.Printf("Symbol: %s\n", cfg.Exchange.Symbol)
	fmt.Printf("API Server: http://localhost:%d\n", cfg.Server.Port)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	fmt.Println("\nShutting down...")
	cancel()
	srv.Stop()
}
