package binance

import (
	"context"
	"strconv"
	"time"

	"github.com/adshao/go-binance/v2"
	"github.com/adshao/go-binance/v2/futures"

	"lshape-trader/internal/models"
)

type Client struct {
	spot    *binance.Client
	futures *futures.Client
	useFutures bool
}

func NewClient(apiKey, secretKey string, useFutures bool) *Client {
	c := &Client{useFutures: useFutures}
	if useFutures {
		c.futures = futures.NewClient(apiKey, secretKey)
	} else {
		c.spot = binance.NewClient(apiKey, secretKey)
	}
	return c
}

func (c *Client) GetKlines(symbol, interval string, limit int) ([]models.Candle, error) {
	ctx := context.Background()
	var candles []models.Candle

	if c.useFutures {
		klines, err := c.futures.NewKlinesService().
			Symbol(symbol).
			Interval(interval).
			Limit(limit).
			Do(ctx)
		if err != nil {
			return nil, err
		}
		for _, k := range klines {
			candles = append(candles, models.Candle{
				Symbol:   symbol,
				OpenTime: time.Unix(k.OpenTime/1000, 0),
				Open:     parseFloat(k.Open),
				High:     parseFloat(k.High),
				Low:      parseFloat(k.Low),
				Close:    parseFloat(k.Close),
				Volume:   parseFloat(k.Volume),
			})
		}
	} else {
		klines, err := c.spot.NewKlinesService().
			Symbol(symbol).
			Interval(interval).
			Limit(limit).
			Do(ctx)
		if err != nil {
			return nil, err
		}
		for _, k := range klines {
			candles = append(candles, models.Candle{
				Symbol:   symbol,
				OpenTime: time.Unix(k.OpenTime/1000, 0),
				Open:     parseFloat(k.Open),
				High:     parseFloat(k.High),
				Low:      parseFloat(k.Low),
				Close:    parseFloat(k.Close),
				Volume:   parseFloat(k.Volume),
			})
		}
	}

	return candles, nil
}

func (c *Client) GetPrice(symbol string) (float64, error) {
	ctx := context.Background()
	if c.useFutures {
		prices, err := c.futures.NewListPricesService().Symbol(symbol).Do(ctx)
		if err != nil {
			return 0, err
		}
		if len(prices) > 0 {
			return parseFloat(prices[0].Price), nil
		}
	} else {
		prices, err := c.spot.NewListPricesService().Symbol(symbol).Do(ctx)
		if err != nil {
			return 0, err
		}
		for _, p := range prices {
			if p.Symbol == symbol {
				return parseFloat(p.Price), nil
			}
		}
	}
	return 0, nil
}

func (c *Client) PlaceMarketOrder(symbol string, side string, quantity float64) (string, error) {
	ctx := context.Background()
	qtyStr := strconv.FormatFloat(quantity, 'f', 8, 64)

	if c.useFutures {
		orderSide := futures.SideTypeBuy
		if side == "SELL" {
			orderSide = futures.SideTypeSell
		}
		order, err := c.futures.NewCreateOrderService().
			Symbol(symbol).
			Side(orderSide).
			Type(futures.OrderTypeMarket).
			Quantity(qtyStr).
			Do(ctx)
		if err != nil {
			return "", err
		}
		return strconv.FormatInt(order.OrderID, 10), nil
	} else {
		orderSide := binance.SideTypeBuy
		if side == "SELL" {
			orderSide = binance.SideTypeSell
		}
		order, err := c.spot.NewCreateOrderService().
			Symbol(symbol).
			Side(orderSide).
			Type(binance.OrderTypeMarket).
			Quantity(qtyStr).
			Do(ctx)
		if err != nil {
			return "", err
		}
		return strconv.FormatInt(order.OrderID, 10), nil
	}
}

func (c *Client) GetBalance(asset string) (float64, error) {
	ctx := context.Background()
	if c.useFutures {
		account, err := c.futures.NewGetAccountService().Do(ctx)
		if err != nil {
			return 0, err
		}
		for _, a := range account.Assets {
			if a.Asset == asset {
				return parseFloat(a.WalletBalance), nil
			}
		}
	} else {
		account, err := c.spot.NewGetAccountService().Do(ctx)
		if err != nil {
			return 0, err
		}
		for _, b := range account.Balances {
			if b.Asset == asset {
				return parseFloat(b.Free), nil
			}
		}
	}
	return 0, nil
}

func parseFloat(s string) float64 {
	f, _ := strconv.ParseFloat(s, 64)
	return f
}
