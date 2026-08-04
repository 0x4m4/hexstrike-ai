package guard

import (
	"math/big"
	"testing"
)

func TestIntentHashCanonical(t *testing.T) {
	h1 := IntentHash("0xABC", big.NewInt(1000), "0x", 56, 3)
	h2 := IntentHash("0xabc", big.NewInt(1000), "0x", 56, 3)
	if h1 != h2 {
		t.Fatalf("case mismatch: %s vs %s", h1, h2)
	}
	h3 := IntentHash("0xabc", big.NewInt(1001), "0x", 56, 3)
	if h1 == h3 {
		t.Fatal("value change must alter hash")
	}
	h4 := IntentHashWithPolicy("0xabc", big.NewInt(1000), "0x", 56, 3, "v2")
	if h1 == h4 {
		t.Fatal("policyVersion change must alter hash")
	}
}

func TestIntentDedup(t *testing.T) {
	d := NewIntentDedup()
	ih := IntentHash("0xabc", big.NewInt(1), "0x", 31337, 1)
	if !d.Claim(ih, 1, 31337) {
		t.Fatal("first claim")
	}
	if d.Claim(ih, 1, 31337) {
		t.Fatal("duplicate must fail")
	}
	if !d.Claim(ih, 1, 56) {
		t.Fatal("different chainId must be independent")
	}
	d.Release(ih, 1, 31337)
	if !d.Claim(ih, 1, 31337) {
		t.Fatal("after release")
	}
}

func TestPostSignDrift(t *testing.T) {
	before := big.NewInt(300_000_000_000_000_000)
	snap := PostSignSnapshot{
		BalanceWei: big.NewInt(200_000_000_000_000_000),
		Nonce:      6,
	}
	drift, reasons := PostSignDrift(5, before, snap)
	if !drift {
		t.Fatal("expected drift")
	}
	if len(reasons) != 2 {
		t.Fatalf("reasons=%v", reasons)
	}
}

func TestKillSwitch(t *testing.T) {
	ks := NewKillSwitch()
	if on, _ := ks.Engaged(); on {
		t.Fatal("default off")
	}
	ks.Engage("critical alert")
	if on, reason := ks.Engaged(); !on || reason == "" {
		t.Fatalf("engaged=%v reason=%q", on, reason)
	}
	ks.Clear()
	if on, _ := ks.Engaged(); on {
		t.Fatal("cleared")
	}
}
