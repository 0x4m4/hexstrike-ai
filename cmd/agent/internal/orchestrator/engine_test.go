package orchestrator

import (
	"context"
	"math/big"
	"path/filepath"
	"testing"
)

func bootstrapFixture(t *testing.T) string {
	t.Helper()
	return filepath.Join("..", "entity", "testdata", "entity-gate-bootstrap.json")
}

func TestPrepareRescueCompromisedFunderBlocked(t *testing.T) {
	eng, err := NewEngine(Config{
		AllowedFunders: []string{
			"0x730ea0231808f42a20f8921ba7fbc788226768f5",
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	attacker := "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
	_, err = eng.PrepareRescue(ctx, RescueRequest{
		BotAddress:    "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA",
		FunderAddress: attacker,
		BalanceWei:    big.NewInt(300_000_000_000_000_000),
		RescueValue:   big.NewInt(1_000_000_000_000_000),
		DryRun:        true,
	})
	if err == nil {
		t.Fatal("compromised funder must be blocked by allowlist")
	}
}

func TestPrepareRescueEmptyAllowlistFailClosed(t *testing.T) {
	eng, err := NewEngine(Config{RequireAllowlist: true})
	if err != nil {
		t.Fatal(err)
	}
	_, err = eng.PrepareRescue(context.Background(), RescueRequest{
		BotAddress:    "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA",
		FunderAddress: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
		BalanceWei:    big.NewInt(300_000_000_000_000_000),
		RescueValue:   big.NewInt(1_000_000_000_000_000),
		DryRun:        true,
	})
	if err == nil {
		t.Fatal("empty allowlist must fail closed when RequireAllowlist")
	}
}

func TestPrepareRescueCaseNormalizedAllowlist(t *testing.T) {
	safe := "0x730ea0231808f42a20f8921ba7fbc788226768f5"
	eng, err := NewEngine(Config{AllowedFunders: []string{safe}})
	if err != nil {
		t.Fatal(err)
	}
	// Uppercase variant of attacker — still not on allowlist
	attacker := "0x70997970C51812DC3A010C7D01B50E0D17DC79C8"
	_, err = eng.PrepareRescue(context.Background(), RescueRequest{
		BotAddress:    "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA",
		FunderAddress: attacker,
		BalanceWei:    big.NewInt(300_000_000_000_000_000),
		RescueValue:   big.NewInt(1_000_000_000_000_000),
		DryRun:        true,
	})
	if err == nil {
		t.Fatal("case-normalized attacker must still be blocked")
	}
}

func TestPrepareRescueDestinationMismatchBlocked(t *testing.T) {
	safe := "0x730ea0231808f42a20f8921ba7fbc788226768f5"
	attacker := "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
	eng, err := NewEngine(Config{
		AllowedFunders:      []string{safe},
		AllowedDestinations: []string{safe},
	})
	if err != nil {
		t.Fatal(err)
	}
	// Funder allowlisted, destination is attacker — must deny destination check
	_, err = eng.PrepareRescue(context.Background(), RescueRequest{
		BotAddress:         "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA",
		FunderAddress:      safe,
		DestinationAddress: attacker,
		BalanceWei:         big.NewInt(300_000_000_000_000_000),
		RescueValue:        big.NewInt(1_000_000_000_000_000),
		DryRun:             true,
	})
	if err == nil {
		t.Fatal("non-allowlisted destination must be blocked even when funder is allowlisted")
	}
}

func TestPrepareRescueDedup(t *testing.T) {
	eng, err := NewEngine(Config{
		AllowedFunders: []string{"0x730ea0231808f42a20f8921ba7fbc788226768f5"},
	})
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	req := RescueRequest{
		BotAddress:    "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA",
		FunderAddress: "0x730ea0231808f42a20f8921ba7fbc788226768f5",
		BalanceWei:    big.NewInt(300_000_000_000_000_000),
		RescueValue:   big.NewInt(1_000_000_000_000_000),
		DryRun:        true,
	}
	if _, err := eng.PrepareRescue(ctx, req); err != nil {
		t.Fatalf("first: %v", err)
	}
	if _, err := eng.PrepareRescue(ctx, req); err == nil {
		t.Fatal("duplicate must be blocked")
	}
}

func TestPrepareRescueThresholdOK(t *testing.T) {
	eng, err := NewEngine(Config{})
	if err != nil {
		t.Fatal(err)
	}
	_, err = eng.PrepareRescue(context.Background(), RescueRequest{
		BotAddress:    "0x4943",
		FunderAddress: "0x730ea0231808f42a20f8921ba7fbc788226768f5",
		BalanceWei:    big.NewInt(600_000_000_000_000_000),
		RescueValue:   big.NewInt(1_000_000_000_000_000),
		DryRun:        true,
	})
	if err == nil {
		t.Fatal("healthy balance should not trigger")
	}
}

func TestPrepareRescueHighValueEscalation(t *testing.T) {
	eng, err := NewEngine(Config{
		AllowedFunders: []string{"0x730ea0231808f42a20f8921ba7fbc788226768f5"},
	})
	if err != nil {
		t.Fatal(err)
	}
	_, err = eng.PrepareRescue(context.Background(), RescueRequest{
		BotAddress:    "0x4943",
		FunderAddress: "0x730ea0231808f42a20f8921ba7fbc788226768f5",
		BalanceWei:    big.NewInt(300_000_000_000_000_000),
		RescueValue:   big.NewInt(600_000_000_000_000_000),
		DryRun:        true,
	})
	if err == nil {
		t.Fatal("high rescue value must escalate")
	}
}

func TestHandleReceiptRevertReleasesDedup(t *testing.T) {
	eng, err := NewEngine(Config{
		AllowedFunders: []string{"0x730ea0231808f42a20f8921ba7fbc788226768f5"},
	})
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	req := RescueRequest{
		BotAddress:    "0x4943",
		FunderAddress: "0x730ea0231808f42a20f8921ba7fbc788226768f5",
		BalanceWei:    big.NewInt(300_000_000_000_000_000),
		RescueValue:   big.NewInt(1_000_000_000_000_000),
		DryRun:        true,
	}
	plan, err := eng.PrepareRescue(ctx, req)
	if err != nil {
		t.Fatal(err)
	}
	if err := eng.HandleReceipt(plan.DedupKey, false, "0xfail"); err == nil {
		t.Fatal("expected error")
	}
	// second attempt must succeed after dedup release
	if _, err := eng.PrepareRescue(ctx, req); err != nil {
		t.Fatalf("retry after revert: %v", err)
	}
}

func TestPrepareRescueBlockedEntity(t *testing.T) {
	eng, err := NewEngine(Config{
		BootstrapPath: bootstrapFixture(t),
	})
	if err != nil {
		t.Fatal(err)
	}
	_, err = eng.PrepareRescue(context.Background(), RescueRequest{
		BotAddress:    "0x4943",
		FunderAddress: "0x000000000000000000000000000000000000dEaD",
		BalanceWei:    big.NewInt(300_000_000_000_000_000),
		RescueValue:   big.NewInt(1_000_000_000_000_000),
		DryRun:        true,
	})
	if err == nil {
		t.Fatal("compromised entity in bootstrap must block")
	}
}
