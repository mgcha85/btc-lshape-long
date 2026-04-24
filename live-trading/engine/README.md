# L-Shape Trading Engine

ETHUSDT L-Shape 패턴 실매매 엔진 (Go)

## 전략 프로필

| Profile | Position | Leverage | CAGR | MDD | Calmar |
|---------|----------|----------|------|-----|--------|
| 5m-aggressive | 30% | 10x | 46.8% | 46.3% | 1.01 |
| 15m-aggressive | 30% | 10x | 60.7% | 69.9% | 0.87 |
| 5m-balanced | 20% | 10x | 33.4% | 32.0% | 1.05 |

## 설정

환경 변수:

```bash
export BINANCE_API_KEY="your-api-key"
export BINANCE_SECRET_KEY="your-secret-key"
export SYMBOL="ETHUSDT"
export STRATEGY_PROFILE="5m-balanced"
export TRADING_ENABLED="false"
export TESTNET="true"
export SERVER_PORT="8080"
```

## 실행

```bash
cd live-trading/engine
go run cmd/main.go
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | 현재 상태 |
| `/api/config` | GET | 설정 정보 |
| `/api/position` | GET | 현재 포지션 |
| `/api/trades` | GET | 거래 내역 |
| `/api/toggle` | POST | 트레이딩 on/off |
| `/api/profiles` | GET | 사용 가능한 프로필 목록 |

## 백테스트 결과

상세 결과: [Realistic Backtest](/docs/realistic-backtest.md)
