# L-Shape Live Trading System

ETHUSDT L-Shape 패턴 실매매 시스템 (Go 엔진 + Svelte 프론트엔드)

## 구조

```
live-trading/
├── engine/          # Go 트레이딩 엔진
│   ├── cmd/         # 진입점
│   └── internal/    # 내부 패키지
│       ├── config/      # 전략 프로필 설정
│       ├── detector/    # L-Shape 패턴 감지
│       ├── engine/      # 트레이딩 로직
│       ├── exchange/    # Binance API 클라이언트
│       ├── server/      # HTTP API 서버
│       └── types/       # 데이터 타입
└── frontend/        # Svelte 프론트엔드
    └── src/
        ├── lib/         # API 클라이언트, 설정
        └── routes/      # 페이지 (Dashboard, History, Settings)
```

## 전략 프로필

| Profile | Position | Leverage | CAGR | MDD | Calmar | Trades |
|---------|----------|----------|------|-----|--------|--------|
| 5m-balanced | 20% | 10x | 33.4% | 32.0% | 1.05 | 334 |
| 5m-aggressive | 30% | 10x | 46.8% | 46.3% | 1.01 | 334 |
| 15m-aggressive | 30% | 10x | 60.7% | 69.9% | 0.87 | 255 |

**추천**: `5m-balanced` (최고 Calmar ratio)

## 실행

### 1. 환경 변수 설정

```bash
export BINANCE_API_KEY="your-api-key"
export BINANCE_SECRET_KEY="your-secret-key"
export SYMBOL="ETHUSDT"
export STRATEGY_PROFILE="5m-balanced"
export TRADING_ENABLED="false"
export TESTNET="true"
export SERVER_PORT="8080"
export STATIC_DIR="../frontend/build"
```

### 2. 프론트엔드 빌드

```bash
cd live-trading/frontend
npm install
npm run build
```

### 3. Go 엔진 실행 (프론트엔드 포함)

```bash
cd live-trading/engine
go run cmd/main.go
```

브라우저에서 `http://localhost:8080` 접속

### 개발 모드 (프론트엔드 별도 실행)

```bash
# Terminal 1: Go 엔진
cd live-trading/engine
go run cmd/main.go

# Terminal 2: Svelte dev server
cd live-trading/frontend
npm run dev
```

## API 엔드포인트

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | 현재 상태 (트레이딩 on/off, 포지션, 거래 수) |
| `/api/config` | GET | 설정 정보 (프로필, 레버리지, TP/SL) |
| `/api/position` | GET | 현재 포지션 상세 |
| `/api/trades` | GET | 거래 내역 |
| `/api/toggle` | POST | 트레이딩 on/off 토글 |
| `/api/profiles` | GET | 사용 가능한 프로필 목록 |

## 프론트엔드 탭

- **Dashboard**: 현재 상태, 포지션, 선택된 프로필 요약
- **History**: 거래 내역 테이블 (시간, 진입/청산가, 결과, PnL%)
- **Settings**: API 키, 프로필 선택, 트레이딩 on/off

## 백테스트 결과

상세 결과: [Realistic Backtest](https://mgcha85.github.io/btc-lshape-long/realistic-backtest)

## 주의사항

⚠️ **실매매 전 확인**:
1. Testnet에서 충분히 테스트
2. API 키 권한 확인 (Futures 거래 권한 필요)
3. 초기에는 작은 포지션 사이즈로 시작
4. Stop Loss 설정 확인

## 라이선스

MIT
