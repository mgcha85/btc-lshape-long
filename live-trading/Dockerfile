FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM golang:1.22-alpine AS backend-builder

WORKDIR /app/engine
COPY engine/go.mod engine/go.sum ./
RUN go mod download
COPY engine/ ./
RUN CGO_ENABLED=0 GOOS=linux go build -o /lshape-engine ./cmd/main.go

FROM alpine:3.19

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

COPY --from=backend-builder /lshape-engine /app/lshape-engine
COPY --from=frontend-builder /app/frontend/build /app/static

ENV STATIC_DIR=/app/static
ENV SERVER_PORT=8080
ENV TESTNET=true
ENV TRADING_ENABLED=false

EXPOSE 8080

CMD ["/app/lshape-engine"]
