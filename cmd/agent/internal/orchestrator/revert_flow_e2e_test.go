package orchestrator

import (
	"context"
	"math/big"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/monitor"
)

// TestRevertFlowAnvilE2E validates dedup release after on-chain revert + retry PrepareRescue.
// Chain setup + reverting tx are driven by scripts/sandbox/test-revert-flow.sh.
func TestRevertFlowAnvilE2E(t *testing.T) {
	if os.Getenv("RUN_REVERT_E2E") != "1" {
		t.Skip("set RUN_REVERT_E2E=1 — use scripts/sandbox/test-revert-flow.sh")
	}

	txHash := strings.TrimSpace(os.Getenv("REVERT_TX_HASH"))
	bot := strings.TrimSpace(os.Getenv("BOT_ADDRESS"))
	funder := strings.TrimSpace(os.Getenv("FUNDER_ADDRESS"))
	if txHash == "" || bot == "" || funder == "" {
		t.Fatal("REVERT_TX_HASH, BOT_ADDRESS, FUNDER_ADDRESS required")
	}

	rpc := os.Getenv("RPC_URL")
	if rpc == "" {
		rpc = "http://127.0.0.1:8545"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	allowed := []string{funder}
	if v := os.Getenv("ALLOWED_FUNDERS"); v != "" {
		allowed = strings.Split(v, ",")
	}
	eng, err := NewEngine(Config{AllowedFunders: allowed, FailClosed: false})
	if err != nil {
		t.Fatal(err)
	}

	rescueValue := big.NewInt(1_000_000_000_000_000)
	req := RescueRequest{
		BotAddress:    bot,
		FunderAddress: funder,
		BalanceWei:    big.NewInt(300_000_000_000_000_000),
		RescueValue:   rescueValue,
		DryRun:        true,
	}

	plan, err := eng.PrepareRescue(ctx, req)
	if err != nil {
		t.Fatalf("first PrepareRescue: %v", err)
	}
	if _, err := eng.PrepareRescue(ctx, req); err == nil {
		t.Fatal("duplicate PrepareRescue must fail while dedup held")
	}

	fetcher, err := monitor.NewEthReceiptFetcher(rpc)
	if err != nil {
		t.Fatal(err)
	}
	watcher := &monitor.Watcher{
		Fetcher:      fetcher,
		Releaser:     eng,
		PollInterval: 200 * time.Millisecond,
		Timeout:      20 * time.Second,
	}
	rcpt, err := watcher.Watch(ctx, txHash, plan.DedupKey)
	if err != nil {
		t.Fatalf("watcher: %v", err)
	}
	if rcpt == nil || rcpt.Success || rcpt.Status != monitor.ReceiptFailed {
		t.Fatalf("expected reverting receipt, got %+v", rcpt)
	}

	plan2, err := eng.PrepareRescue(ctx, req)
	if err != nil {
		t.Fatalf("retry PrepareRescue after revert: %v", err)
	}
	if plan2.DedupKey != plan.DedupKey {
		t.Fatalf("dedup key mismatch: %s vs %s", plan2.DedupKey, plan.DedupKey)
	}
	t.Logf("revert e2e OK tx=%s dedup=%s status=%d", txHash, plan.DedupKey, rcpt.Status)
}
