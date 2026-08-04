package entity

import (
	"context"
	"path/filepath"
	"testing"
)

func TestEntityGatePrewarmBootstrap(t *testing.T) {
	path := filepath.Join("testdata", "entity-gate-bootstrap.json")
	eg := NewEntityGate("", path)
	if err := eg.Prewarm(); err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	ok, err := eg.VerifyAddress(ctx, "0x730ea0231808f42a20f8921ba7fbc788226768f5")
	if err != nil || !ok {
		t.Fatalf("authority should be allowed: ok=%v err=%v", ok, err)
	}
	ok, err = eg.VerifyAddress(ctx, "0x000000000000000000000000000000000000dEaD")
	if err == nil || ok {
		t.Fatalf("dead sink should be blocked")
	}
}

func TestEntityGateNoAPIKeyPermissive(t *testing.T) {
	eg := NewEntityGate("", "")
	ctx := context.Background()
	ok, err := eg.VerifyAddress(ctx, "0x1234567890123456789012345678901234567890")
	if err != nil || !ok {
		t.Fatalf("unknown without API key should pass in lab mode: %v %v", ok, err)
	}
}

func TestEntityGateBlockAllow(t *testing.T) {
	eg := NewEntityGate("", "")
	attacker := "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
	eg.BlockAddress(attacker, "COMPROMISED", "COMPROMISED")
	ctx := context.Background()
	if ok, _ := eg.VerifyAddress(ctx, attacker); ok {
		t.Fatal("expected block")
	}
	eg.AllowAddress(attacker, "recovered_funder", "ALLOWLIST")
	ok, err := eg.VerifyAddress(ctx, attacker)
	if !ok || err != nil {
		t.Fatalf("allow should override: %v %v", ok, err)
	}
}
