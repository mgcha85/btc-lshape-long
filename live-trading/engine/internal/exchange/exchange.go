package exchange

import (
	"context"

	"github.com/mgcha85/lshape-engine/internal/types"
)

type Exchange interface {
	GetKlines(ctx context.Context, symbol, interval string, limit int) ([]types.Candle, error)
	GetBalance(ctx context.Context) (float64, error)
	PlaceOrder(ctx context.Context, req OrderRequest) (*OrderResponse, error)
	GetPosition(ctx context.Context, symbol string) (*types.Position, error)
}

type OrderRequest struct {
	Symbol   string
	Side     string
	Type     string
	Quantity float64
	Price    float64
}

type OrderResponse struct {
	OrderID   string
	Symbol    string
	Side      string
	AvgPrice  float64
	FilledQty float64
	Status    string
}
