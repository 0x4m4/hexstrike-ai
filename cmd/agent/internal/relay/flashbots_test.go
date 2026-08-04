package relay

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/ethereum/go-ethereum/crypto"
)

func TestFlashbotsSendBundleSigned(t *testing.T) {
	key, err := crypto.GenerateKey()
	if err != nil {
		t.Fatal(err)
	}
	keyHex := hex.EncodeToString(crypto.FromECDSA(key))

	var gotSig string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotSig = r.Header.Get("X-Flashbots-Signature")
		if r.Method != http.MethodPost {
			t.Errorf("method=%s", r.Method)
		}
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		if body["method"] != "eth_sendBundle" {
			t.Errorf("method field=%v", body["method"])
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"jsonrpc": "2.0",
			"id":      1,
			"result":  "0xflashbundle",
		})
	}))
	defer srv.Close()

	fc, err := NewFlashbotsClient(srv.URL, keyHex)
	if err != nil {
		t.Fatal(err)
	}
	hash, err := fc.SendBundle(context.Background(), []string{"0xdead"}, 19_000_000)
	if err != nil {
		t.Fatal(err)
	}
	if hash == "" {
		t.Fatal("empty bundle hash")
	}
	if gotSig == "" || !strings.Contains(gotSig, ":") {
		t.Fatalf("missing X-Flashbots-Signature: %q", gotSig)
	}
	addr := crypto.PubkeyToAddress(key.PublicKey).Hex()
	if !strings.HasPrefix(gotSig, addr) {
		t.Fatalf("sig prefix want %s got %s", addr, gotSig)
	}
}

func TestFlashbotsMissingKey(t *testing.T) {
	_, err := NewFlashbotsClient("http://localhost", "")
	if err == nil {
		t.Fatal("expected error without signing key")
	}
}
