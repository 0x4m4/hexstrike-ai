package relay

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

// PublicRPC sends eth_sendRawTransaction to a standard JSON-RPC endpoint.
type PublicRPC struct {
	URL        string
	HTTPClient *http.Client
}

func NewPublicRPC() *PublicRPC {
	url := os.Getenv("RELAY_PUBLIC_RPC")
	if url == "" {
		url = os.Getenv("RPC_URL")
	}
	if url == "" {
		url = "http://127.0.0.1:8545"
	}
	return &PublicRPC{URL: url, HTTPClient: &http.Client{Timeout: 10 * time.Second}}
}

func (p *PublicRPC) SendRawTransaction(ctx context.Context, rawTxHex string) (string, error) {
	if !has0x(rawTxHex) {
		rawTxHex = "0x" + rawTxHex
	}
	payload := map[string]any{
		"jsonrpc": "2.0",
		"id":      1,
		"method":  "eth_sendRawTransaction",
		"params":  []string{rawTxHex},
	}
	body, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, p.URL, bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := p.HTTPClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	var out struct {
		Result string `json:"result"`
		Error  *struct{ Message string `json:"message"` } `json:"error"`
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return "", err
	}
	if out.Error != nil {
		return "", fmt.Errorf("public rpc: %s", out.Error.Message)
	}
	return out.Result, nil
}

func has0x(s string) bool {
	return len(s) >= 2 && (s[0:2] == "0x" || s[0:2] == "0X")
}
