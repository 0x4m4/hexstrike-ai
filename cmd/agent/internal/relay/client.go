package relay

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

// BundleClient submits eth_sendBundle to Puissant Builder.
type BundleClient struct {
	Endpoint   string
	HTTPClient *http.Client
}

// BundleParams mirrors Puissant eth_sendBundle params[0].
type BundleParams struct {
	Txs            []string `json:"txs"`
	MaxBlockNumber uint64   `json:"maxBlockNumber,omitempty"`
}

type jsonRPCRequest struct {
	JSONRPC string        `json:"jsonrpc"`
	ID      string        `json:"id"`
	Method  string        `json:"method"`
	Params  []BundleParams `json:"params"`
}

type jsonRPCResponse struct {
	Result json.RawMessage `json:"result"`
	Error  *struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
	} `json:"error"`
}

// NewBundleClient returns Puissant HTTP client (env PUISSANT_BUILDER_URL).
func NewBundleClient() *BundleClient {
	ep := os.Getenv("PUISSANT_BUILDER_URL")
	if ep == "" {
		ep = "https://puissant-builder.48.club/"
	}
	return &BundleClient{
		Endpoint: ep,
		HTTPClient: &http.Client{Timeout: 8 * time.Second},
	}
}

// SendBundle posts signed raw txs (0x-prefixed hex) to eth_sendBundle.
func (c *BundleClient) SendBundle(ctx context.Context, params BundleParams) (string, error) {
	if len(params.Txs) == 0 {
		return "", fmt.Errorf("puissant: empty txs")
	}
	body, err := json.Marshal(jsonRPCRequest{
		JSONRPC: "2.0",
		ID:      "hexstrike",
		Method:  "eth_sendBundle",
		Params:  []BundleParams{params},
	})
	if err != nil {
		return "", err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.Endpoint, bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))

	var out jsonRPCResponse
	if err := json.Unmarshal(raw, &out); err != nil {
		return "", fmt.Errorf("puissant: decode: %w body=%s", err, truncate(string(raw), 200))
	}
	if out.Error != nil {
		return "", fmt.Errorf("puissant RPC %d: %s", out.Error.Code, out.Error.Message)
	}
	var bundleHash string
	if err := json.Unmarshal(out.Result, &bundleHash); err == nil && bundleHash != "" {
		return bundleHash, nil
	}
	return strings.Trim(string(out.Result), `"`), nil
}

// BundleStatus from explore.48.club status API.
type BundleStatus struct {
	Submitted bool   `json:"submitted"`
	Confirmed bool   `json:"confirmed"`
	Block     uint64 `json:"block"`
}

// QueryBundleStatus GET https://explore.48.club/v2/bundle?hash=...
func QueryBundleStatus(ctx context.Context, bundleHash string) (*BundleStatus, error) {
	base := os.Getenv("PUISSANT_EXPLORE_URL")
	if base == "" {
		base = "https://explore.48.club/v2/bundle"
	}
	url := fmt.Sprintf("%s?hash=%s", strings.TrimRight(base, "/"), bundleHash)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	client := &http.Client{Timeout: 6 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	var st BundleStatus
	if err := json.Unmarshal(raw, &st); err != nil {
		return nil, err
	}
	return &st, nil
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}
