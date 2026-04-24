package notifier

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/mgcha85/lshape-engine/internal/types"
)

type TelegramNotifier struct {
	botToken string
	chatID   string
	enabled  bool
	client   *http.Client
}

func NewTelegram(botToken, chatID string, enabled bool) *TelegramNotifier {
	return &TelegramNotifier{
		botToken: botToken,
		chatID:   chatID,
		enabled:  enabled,
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (t *TelegramNotifier) IsEnabled() bool {
	return t.enabled
}

func (t *TelegramNotifier) SetEnabled(enabled bool) {
	t.enabled = enabled
}

func (t *TelegramNotifier) SendTradeNotification(trade types.Trade) error {
	if !t.enabled || t.botToken == "" || t.chatID == "" {
		return nil
	}

	emoji := "🟢"
	if trade.PnLPct < 0 {
		emoji = "🔴"
	}

	msg := fmt.Sprintf(
		"%s *Trade Closed*\n\n"+
			"Symbol: `%s`\n"+
			"Side: `%s`\n"+
			"Entry: `%.2f`\n"+
			"Exit: `%.2f`\n"+
			"Result: `%s`\n"+
			"PnL: `%.2f%%`\n"+
			"Duration: `%s`",
		emoji,
		trade.Symbol,
		trade.Side,
		trade.EntryPrice,
		trade.ExitPrice,
		trade.Result,
		trade.PnLPct,
		trade.ExitTime.Sub(trade.EntryTime).Round(time.Minute).String(),
	)

	return t.sendMessage(msg)
}

func (t *TelegramNotifier) SendMessage(text string) error {
	if !t.enabled || t.botToken == "" || t.chatID == "" {
		return nil
	}
	return t.sendMessage(text)
}

func (t *TelegramNotifier) sendMessage(text string) error {
	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", t.botToken)

	payload := map[string]interface{}{
		"chat_id":    t.chatID,
		"text":       text,
		"parse_mode": "Markdown",
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal payload: %w", err)
	}

	resp, err := t.client.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("failed to send telegram message: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("telegram API returned status %d", resp.StatusCode)
	}

	return nil
}
