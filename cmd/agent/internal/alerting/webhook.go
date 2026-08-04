// Package alerting delivers critical alerts to an optional operator webhook.
package alerting

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

// PageCritical POSTs to ALERT_WEBHOOK_URL when ALERT_PAGING_ENABLED is truthy.
// Best-effort: errors are returned but callers should not unblock kill-switch on failure.
func PageCritical(ctx context.Context, kind, detail string) error {
	if !enabled() {
		return nil
	}
	url := strings.TrimSpace(os.Getenv("ALERT_WEBHOOK_URL"))
	if url == "" {
		return fmt.Errorf("alerting: ALERT_WEBHOOK_URL empty")
	}
	timeout := 5 * time.Second
	if raw := strings.TrimSpace(os.Getenv("ALERT_PAGING_TIMEOUT_SEC")); raw != "" {
		if sec, err := strconv.Atoi(raw); err == nil && sec > 0 {
			timeout = time.Duration(sec) * time.Second
		}
	}
	payload := map[string]any{
		"text":     fmt.Sprintf("[HexStrike CRITICAL] %s: %s", kind, detail),
		"severity": "critical",
		"source":   "hexstrike-go",
		"kind":     kind,
		"detail":   detail,
		"ts":       time.Now().UTC().Format(time.RFC3339Nano),
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	reqCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	req, err := http.NewRequestWithContext(reqCtx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "hexstrike-go-paging/1")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("alerting: webhook status %d", resp.StatusCode)
	}
	return nil
}

func enabled() bool {
	v := strings.ToLower(strings.TrimSpace(os.Getenv("ALERT_PAGING_ENABLED")))
	return v == "1" || v == "true" || v == "yes" || v == "on"
}
