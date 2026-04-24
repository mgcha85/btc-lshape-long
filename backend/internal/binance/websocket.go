package binance

import (
	"log"
	"strconv"
	"time"

	"github.com/adshao/go-binance/v2"
	"github.com/adshao/go-binance/v2/futures"

	"lshape-trader/internal/models"
)

type KlineHandler func(candle models.Candle)

type WebSocketManager struct {
	useFutures bool
	handlers   map[string]KlineHandler
	stopCh     chan struct{}
}

func NewWebSocketManager(useFutures bool) *WebSocketManager {
	return &WebSocketManager{
		useFutures: useFutures,
		handlers:   make(map[string]KlineHandler),
		stopCh:     make(chan struct{}),
	}
}

func (w *WebSocketManager) SubscribeKline(symbol, interval string, handler KlineHandler) error {
	key := symbol + "_" + interval
	w.handlers[key] = handler

	go func() {
		for {
			select {
			case <-w.stopCh:
				return
			default:
			}

			var doneC, stopC chan struct{}
			var err error

			if w.useFutures {
				doneC, stopC, err = futures.WsKlineServe(symbol, interval, func(event *futures.WsKlineEvent) {
					if event.Kline.IsFinal {
						candle := models.Candle{
							Symbol:   symbol,
							OpenTime: time.Unix(event.Kline.StartTime/1000, 0),
							Open:     parseFloat(event.Kline.Open),
							High:     parseFloat(event.Kline.High),
							Low:      parseFloat(event.Kline.Low),
							Close:    parseFloat(event.Kline.Close),
							Volume:   parseFloat(event.Kline.Volume),
						}
						handler(candle)
					}
				}, func(err error) {
					log.Printf("WebSocket error for %s: %v", symbol, err)
				})
			} else {
				doneC, stopC, err = binance.WsKlineServe(symbol, interval, func(event *binance.WsKlineEvent) {
					if event.Kline.IsFinal {
						candle := models.Candle{
							Symbol:   symbol,
							OpenTime: time.Unix(event.Kline.StartTime/1000, 0),
							Open:     parseFloat(event.Kline.Open),
							High:     parseFloat(event.Kline.High),
							Low:      parseFloat(event.Kline.Low),
							Close:     parseFloat(event.Kline.Close),
							Volume:   parseFloat(event.Kline.Volume),
						}
						handler(candle)
					}
				}, func(err error) {
					log.Printf("WebSocket error for %s: %v", symbol, err)
				})
			}

			if err != nil {
				log.Printf("Failed to connect WebSocket for %s: %v, retrying in 5s", symbol, err)
				time.Sleep(5 * time.Second)
				continue
			}

			select {
			case <-doneC:
				log.Printf("WebSocket closed for %s, reconnecting...", symbol)
			case <-w.stopCh:
				close(stopC)
				return
			}

			time.Sleep(time.Second)
		}
	}()

	return nil
}

func (w *WebSocketManager) Close() {
	close(w.stopCh)
}

type TickerHandler func(symbol string, price float64)

func (w *WebSocketManager) SubscribeTicker(symbols []string, handler TickerHandler) error {
	go func() {
		for {
			select {
			case <-w.stopCh:
				return
			default:
			}

			var doneC, stopC chan struct{}
			var err error

			if w.useFutures {
				for _, symbol := range symbols {
					sym := symbol
					doneC, stopC, err = futures.WsBookTickerServe(sym, func(event *futures.WsBookTickerEvent) {
						price := (parseFloat(event.BestBidPrice) + parseFloat(event.BestAskPrice)) / 2
						handler(event.Symbol, price)
					}, func(err error) {
						log.Printf("Ticker WebSocket error: %v", err)
					})
					if err != nil {
						log.Printf("Failed to connect ticker WebSocket for %s: %v", sym, err)
					}
				}
			} else {
				doneC, stopC, err = binance.WsCombinedBookTickerServe(symbols, func(event *binance.WsBookTickerEvent) {
					bidPrice, _ := strconv.ParseFloat(event.BestBidPrice, 64)
					askPrice, _ := strconv.ParseFloat(event.BestAskPrice, 64)
					price := (bidPrice + askPrice) / 2
					handler(event.Symbol, price)
				}, func(err error) {
					log.Printf("Ticker WebSocket error: %v", err)
				})
			}

			if err != nil {
				log.Printf("Failed to connect ticker WebSocket: %v, retrying in 5s", err)
				time.Sleep(5 * time.Second)
				continue
			}

			select {
			case <-doneC:
				log.Printf("Ticker WebSocket closed, reconnecting...")
			case <-w.stopCh:
				close(stopC)
				return
			}

			time.Sleep(time.Second)
		}
	}()

	return nil
}
