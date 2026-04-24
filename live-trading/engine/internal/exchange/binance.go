package exchange

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"

	"github.com/mgcha85/lshape-engine/internal/config"
	"github.com/mgcha85/lshape-engine/internal/types"
)

type Binance struct {
	apiKey    string
	secretKey string
	baseURL   string
	client    *http.Client
}

func NewBinance(cfg *config.Config) (*Binance, error) {
	baseURL := "https://fapi.binance.com"
	if cfg.Exchange.Testnet {
		baseURL = "https://testnet.binancefuture.com"
	}

	return &Binance{
		apiKey:    cfg.Exchange.APIKey,
		secretKey: cfg.Exchange.SecretKey,
		baseURL:   baseURL,
		client:    &http.Client{Timeout: 10 * time.Second},
	}, nil
}

func (b *Binance) GetKlines(ctx context.Context, symbol, interval string, limit int) ([]types.Candle, error) {
	params := url.Values{}
	params.Set("symbol", symbol)
	params.Set("interval", interval)
	params.Set("limit", strconv.Itoa(limit))

	resp, err := b.publicRequest(ctx, "GET", "/fapi/v1/klines", params)
	if err != nil {
		return nil, err
	}

	var raw [][]interface{}
	if err := json.Unmarshal(resp, &raw); err != nil {
		return nil, err
	}

	candles := make([]types.Candle, len(raw))
	for i, k := range raw {
		candles[i] = types.Candle{
			OpenTime:  time.UnixMilli(int64(k[0].(float64))),
			Open:      parseFloat(k[1]),
			High:      parseFloat(k[2]),
			Low:       parseFloat(k[3]),
			Close:     parseFloat(k[4]),
			Volume:    parseFloat(k[5]),
			CloseTime: time.UnixMilli(int64(k[6].(float64))),
		}
	}

	return candles, nil
}

func (b *Binance) GetBalance(ctx context.Context) (float64, error) {
	params := url.Values{}
	params.Set("timestamp", strconv.FormatInt(time.Now().UnixMilli(), 10))

	resp, err := b.signedRequest(ctx, "GET", "/fapi/v2/balance", params)
	if err != nil {
		return 0, err
	}

	var balances []struct {
		Asset            string `json:"asset"`
		AvailableBalance string `json:"availableBalance"`
	}
	if err := json.Unmarshal(resp, &balances); err != nil {
		return 0, err
	}

	for _, b := range balances {
		if b.Asset == "USDT" {
			return strconv.ParseFloat(b.AvailableBalance, 64)
		}
	}

	return 0, fmt.Errorf("USDT balance not found")
}

func (b *Binance) PlaceOrder(ctx context.Context, req OrderRequest) (*OrderResponse, error) {
	params := url.Values{}
	params.Set("symbol", req.Symbol)
	params.Set("side", req.Side)
	params.Set("type", req.Type)
	params.Set("quantity", strconv.FormatFloat(req.Quantity, 'f', 4, 64))
	params.Set("timestamp", strconv.FormatInt(time.Now().UnixMilli(), 10))

	resp, err := b.signedRequest(ctx, "POST", "/fapi/v1/order", params)
	if err != nil {
		return nil, err
	}

	var order struct {
		OrderID      int64  `json:"orderId"`
		Symbol       string `json:"symbol"`
		Side         string `json:"side"`
		AvgPrice     string `json:"avgPrice"`
		ExecutedQty  string `json:"executedQty"`
		Status       string `json:"status"`
	}
	if err := json.Unmarshal(resp, &order); err != nil {
		return nil, err
	}

	avgPrice, _ := strconv.ParseFloat(order.AvgPrice, 64)
	filledQty, _ := strconv.ParseFloat(order.ExecutedQty, 64)

	return &OrderResponse{
		OrderID:   strconv.FormatInt(order.OrderID, 10),
		Symbol:    order.Symbol,
		Side:      order.Side,
		AvgPrice:  avgPrice,
		FilledQty: filledQty,
		Status:    order.Status,
	}, nil
}

func (b *Binance) GetPosition(ctx context.Context, symbol string) (*types.Position, error) {
	params := url.Values{}
	params.Set("symbol", symbol)
	params.Set("timestamp", strconv.FormatInt(time.Now().UnixMilli(), 10))

	resp, err := b.signedRequest(ctx, "GET", "/fapi/v2/positionRisk", params)
	if err != nil {
		return nil, err
	}

	var positions []struct {
		Symbol       string `json:"symbol"`
		PositionAmt  string `json:"positionAmt"`
		EntryPrice   string `json:"entryPrice"`
		PositionSide string `json:"positionSide"`
	}
	if err := json.Unmarshal(resp, &positions); err != nil {
		return nil, err
	}

	for _, p := range positions {
		amt, _ := strconv.ParseFloat(p.PositionAmt, 64)
		if amt != 0 {
			entryPrice, _ := strconv.ParseFloat(p.EntryPrice, 64)
			return &types.Position{
				Symbol:     p.Symbol,
				Side:       "LONG",
				EntryPrice: entryPrice,
				Quantity:   amt,
			}, nil
		}
	}

	return nil, nil
}

func (b *Binance) publicRequest(ctx context.Context, method, path string, params url.Values) ([]byte, error) {
	reqURL := b.baseURL + path
	if len(params) > 0 {
		reqURL += "?" + params.Encode()
	}

	req, err := http.NewRequestWithContext(ctx, method, reqURL, nil)
	if err != nil {
		return nil, err
	}

	return b.doRequest(req)
}

func (b *Binance) signedRequest(ctx context.Context, method, path string, params url.Values) ([]byte, error) {
	signature := b.sign(params.Encode())
	params.Set("signature", signature)

	reqURL := b.baseURL + path + "?" + params.Encode()

	req, err := http.NewRequestWithContext(ctx, method, reqURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-MBX-APIKEY", b.apiKey)

	return b.doRequest(req)
}

func (b *Binance) sign(data string) string {
	h := hmac.New(sha256.New, []byte(b.secretKey))
	h.Write([]byte(data))
	return hex.EncodeToString(h.Sum(nil))
}

func (b *Binance) doRequest(req *http.Request) ([]byte, error) {
	resp, err := b.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("API error %d: %s", resp.StatusCode, string(body))
	}

	return body, nil
}

func parseFloat(v interface{}) float64 {
	switch val := v.(type) {
	case string:
		f, _ := strconv.ParseFloat(val, 64)
		return f
	case float64:
		return val
	default:
		return 0
	}
}
