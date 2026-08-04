package alerting

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestPageCritical_DisabledNoop(t *testing.T) {
	t.Setenv("ALERT_PAGING_ENABLED", "")
	t.Setenv("ALERT_WEBHOOK_URL", "http://127.0.0.1:1/nope")
	if err := PageCritical(context.Background(), "rpc_mismatch", "test"); err != nil {
		t.Fatalf("disabled should noop: %v", err)
	}
}

func TestPageCritical_PostsWebhook(t *testing.T) {
	var got map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(body, &got)
		w.WriteHeader(204)
	}))
	defer srv.Close()

	t.Setenv("ALERT_PAGING_ENABLED", "true")
	t.Setenv("ALERT_WEBHOOK_URL", srv.URL)
	t.Setenv("ALERT_PAGING_TIMEOUT_SEC", "3")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := PageCritical(ctx, "rpc_mismatch", "proxy skew"); err != nil {
		t.Fatal(err)
	}
	if got["kind"] != "rpc_mismatch" {
		t.Fatalf("payload=%v", got)
	}
}
