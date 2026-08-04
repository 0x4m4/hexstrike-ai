package relay

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

type mockBundle struct {
	confirmed bool
}

func TestSendBundleLiveHTTP(t *testing.T) {
	var called bool
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		var req jsonRPCRequest
		_ = json.NewDecoder(r.Body).Decode(&req)
		if req.Method != "eth_sendBundle" {
			t.Fatalf("method=%s", req.Method)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"jsonrpc": "2.0",
			"id":      "hexstrike",
			"result":  "0xbundlehash",
		})
	}))
	defer srv.Close()

	c := &BundleClient{Endpoint: srv.URL, HTTPClient: srv.Client()}
	hash, err := c.SendBundle(context.Background(), BundleParams{Txs: []string{"0xdead"}})
	if err != nil {
		t.Fatal(err)
	}
	if !called || hash == "" {
		t.Fatalf("called=%v hash=%q", called, hash)
	}
}

func TestPublicFallbackAfterBundleMiss(t *testing.T) {
	bundleSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{
			"result": "0xbundle",
		})
	}))
	defer bundleSrv.Close()

	rpcSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{
			"result": "0xtxhash",
		})
	}))
	defer rpcSrv.Close()

	r := DefaultPuissantRelay()
	r.Bundle = &BundleClient{Endpoint: bundleSrv.URL, HTTPClient: bundleSrv.Client()}
	r.Public = &PublicRPC{URL: rpcSrv.URL, HTTPClient: rpcSrv.Client()}
	r.PollInterval = 10 * time.Millisecond
	r.MaxWaitBlocks = 1
	r.GasBumpSteps = []int{0}
	r.StatusQuery = func(context.Context, string) (*BundleStatus, error) {
		return &BundleStatus{Submitted: true, Confirmed: false}, nil
	}

	res, err := r.Submit(context.Background(), SubmitRequest{RawTx: []byte{0x02, 0xf8}})
	if err != nil {
		t.Fatal(err)
	}
	if res.Strategy != StrategyPublic {
		t.Fatalf("strategy=%s", res.Strategy)
	}
}
