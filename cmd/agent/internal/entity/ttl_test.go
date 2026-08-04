package entity

import (
	"context"
	"testing"
	"time"
)

func TestCacheTTLExpiryTriggersRefreshPath(t *testing.T) {
	eg := NewEntityGate("test-key", "", WithCacheTTL(50*time.Millisecond), WithFailClosed(true))
	eg.cache.Store("0xabc", stampMeta(EntityMetadata{Name: "old", IsSafe: true}, 50*time.Millisecond))
	time.Sleep(60 * time.Millisecond)
	// expired cache + api key → fetch path (will fail closed without real API)
	_, err := eg.VerifyAddress(context.Background(), "0xAbc")
	if err == nil {
		t.Fatal("expected refresh error with fake API key")
	}
}

func TestBlockedEntryTTLShorterThanSafe(t *testing.T) {
	safe := stampMeta(EntityMetadata{IsSafe: true}, 15*time.Minute)
	blocked := stampMeta(EntityMetadata{IsSafe: false}, 15*time.Minute)
	if !blocked.ValidUntil.Before(safe.ValidUntil) {
		t.Fatalf("blocked TTL should refresh sooner")
	}
}
