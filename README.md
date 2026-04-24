# L-Shape Trader

ㄴ자 패턴 롱 전략 자동매매 시스템 (BTC/ETH Futures)

## Strategy

1. **Prior Drop**: 이전 구간에서 일정% 이상 하락
2. **Consolidation**: 좁은 범위에서 횡보
3. **MA Breakout**: MA50 돌파 시 진입

## Tech Stack

- **Backend**: Go (Fiber + GORM + SQLite)
- **Frontend**: Svelte 5 + Tailwind 4
- **Exchange**: Binance Futures

## Run

```bash
# Development
cd backend && APP_ENV=dev go run ./cmd/server

# Production (Docker)
docker compose up -d
```

## API Endpoints

- `GET /api/dashboard` - 통계, 포지션, 트레이딩 상태
- `GET /api/trades` - 거래 내역
- `GET /api/settings` - 설정 조회
- `POST /api/settings` - 설정 저장
- `GET /api/strategy` - 전략 파라미터
- `POST /api/strategy` - 전략 파라미터 저장
- `POST /api/trading/toggle` - 트레이딩 on/off

## Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| MA Period | 50 | Breakout MA |
| Consolidation Bars | 5 | 횡보 확인 봉 수 |
| Consolidation Range | 5% | 횡보 범위 |
| Prior Drop | 5% | 이전 하락 기준 |
| Take Profit | 10% | 익절 |
| Stop Loss | 3% | 손절 |
| Half Close | 5% | 반익절 (SL → 본전) |
