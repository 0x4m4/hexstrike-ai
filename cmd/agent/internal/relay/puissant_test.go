package relay

import (
	"context"
	"testing"
)

func TestPuissantPublicFallback(t *testing.T) {
	t.Skip("covered by TestPublicFallbackAfterBundleMiss with HTTP mocks")
}

func TestPuissantNoFallbackFails(t *testing.T) {
	r := DefaultPuissantRelay()
	r.AllowPublicFallback = false
	_, err := r.Submit(context.Background(), SubmitRequest{RawTx: []byte{0x02}})
	if err == nil {
		t.Fatal("expected error without fallback")
	}
}
