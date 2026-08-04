// Package orchestrator wires guard, entity gate, fee calc, and dedup before signing.
package orchestrator

import (
	"context"
	"fmt"
	"math/big"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/alerting"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/entity"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/guard"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/signer"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/tx"
)

// RescueRequest is the pre-sign payload evaluated by the engine.
type RescueRequest struct {
	BotAddress         string
	FunderAddress      string
	DestinationAddress string // tx `to`; defaults to FunderAddress when empty
	BalanceWei         *big.Int
	RescueValue        *big.Int
	ChainID            int64
	DryRun             bool
}

// RescuePlan is returned when the engine approves signing.
type RescuePlan struct {
	Strategy  guard.ExecutionStrategy
	Fees      *tx.FeeSuggestion
	DedupKey  string
	AllowedAt time.Time
}

// Engine coordinates P0–P2 checks immediately before signing.
type Engine struct {
	limits              *guard.RouteGuard
	gate                *entity.EntityGate
	fees                *tx.FeeCalculator
	allow               map[string]struct{}
	destAllow           map[string]struct{}
	dedup               sync.Map
	intentDedup         *guard.IntentDedup
	killSwitch          *guard.KillSwitch
	quorum              guard.QuorumSource
	failGate            bool
	requireAllowlist    bool
	requireQuorum       bool
	requireRemoteSigner bool
	phase               signer.Phase
	maxRescueValueWei   *big.Int
	maxRescuesPerWindow int
	rescueWindowSec     float64
	cooldownAfterBlock  float64
	attempts            []time.Time
	blockedUntil        time.Time
	mu                  sync.Mutex
}

// Config for battle / production engine.
type Config struct {
	BootstrapPath       string
	APIKey              string
	FailClosed          bool
	RequireAllowlist    bool
	RequireQuorum       bool // if true, missing/failed quorum = fail-closed (no skip)
	RequireRemoteSigner bool // if true, local_key signer rejected on SecureSign
	Phase               signer.Phase
	AllowedFunders      []string
	AllowedDestinations []string
	QuorumRPCURLs       []string
	QuorumMinAgree      int
	MaxRescueValueWei   *big.Int
	MaxRescuesPerWindow int
	RescueWindowSec     float64
	CooldownAfterBlock  float64
	FeeCalculator       *tx.FeeCalculator
	KillSwitch          *guard.KillSwitch
}

// NewEngine builds an engine from repo-relative defaults.
func NewEngine(cfg Config) (*Engine, error) {
	bootstrap := cfg.BootstrapPath
	if bootstrap == "" {
		bootstrap = defaultBootstrapPath()
	}
	apiKey := cfg.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("ARKHAM_API_KEY")
	}
	eg := entity.NewEntityGate(apiKey, bootstrap, entity.WithFailClosed(cfg.FailClosed))
	if err := eg.Prewarm(); err != nil {
		return nil, fmt.Errorf("entity prewarm: %w", err)
	}
	allow := make(map[string]struct{})
	for _, a := range cfg.AllowedFunders {
		key := strings.ToLower(strings.TrimSpace(a))
		if key != "" {
			allow[key] = struct{}{}
			if eg.IsDenied(a) {
				continue
			}
			eg.AllowAddress(a, "configured_funder", "ALLOWLIST")
		}
	}
	destAllow := make(map[string]struct{})
	destList := cfg.AllowedDestinations
	if len(destList) == 0 {
		destList = cfg.AllowedFunders
	}
	for _, a := range destList {
		key := strings.ToLower(strings.TrimSpace(a))
		if key != "" {
			destAllow[key] = struct{}{}
		}
	}
	ks := cfg.KillSwitch
	if ks == nil {
		ks = guard.NewKillSwitch()
	}
	phase := cfg.Phase
	if phase == "" {
		phase = signer.PhaseLab
	}
	requireQuorum := cfg.RequireQuorum || cfg.FailClosed || phase == signer.PhaseCanary || phase == signer.PhaseLimited
	requireRemote := cfg.RequireRemoteSigner || phase == signer.PhaseCanary || phase == signer.PhaseLimited
	requireAllow := cfg.RequireAllowlist || cfg.FailClosed || phase != signer.PhaseLab

	var quorum guard.QuorumSource
	if len(cfg.QuorumRPCURLs) > 0 {
		minAgree := cfg.QuorumMinAgree
		if minAgree < 1 {
			minAgree = 2
		}
		if requireQuorum && minAgree > len(cfg.QuorumRPCURLs) {
			return nil, fmt.Errorf("ENGINE: quorum need ≥%d URLs for minAgree=%d (got %d)", minAgree, minAgree, len(cfg.QuorumRPCURLs))
		}
		// Never silently degrade below 2 when quorum is required.
		if requireQuorum && minAgree < 2 {
			minAgree = 2
		}
		quorum = &guard.QuorumReader{URLs: cfg.QuorumRPCURLs, MinAgree: minAgree}
	} else if requireQuorum {
		return nil, fmt.Errorf("ENGINE: RequireQuorum set but QuorumRPCURLs empty")
	}

	maxWindow := cfg.MaxRescuesPerWindow
	if maxWindow <= 0 {
		maxWindow = 3
	}
	windowSec := cfg.RescueWindowSec
	if windowSec <= 0 {
		windowSec = 3600
	}
	cooldown := cfg.CooldownAfterBlock
	if cooldown <= 0 {
		cooldown = 300
	}

	return &Engine{
		limits:              guard.NewRouteGuard(),
		gate:                eg,
		fees:                cfg.FeeCalculator,
		allow:               allow,
		destAllow:           destAllow,
		intentDedup:         guard.NewIntentDedup(),
		killSwitch:          ks,
		quorum:              quorum,
		failGate:            cfg.FailClosed,
		requireAllowlist:    requireAllow,
		requireQuorum:       requireQuorum,
		requireRemoteSigner: requireRemote,
		phase:               phase,
		maxRescueValueWei:   cfg.MaxRescueValueWei,
		maxRescuesPerWindow: maxWindow,
		rescueWindowSec:     windowSec,
		cooldownAfterBlock:  cooldown,
	}, nil
}

func defaultBootstrapPath() string {
	for _, p := range []string{
		"cmd/agent/internal/entity/testdata/entity-gate-bootstrap.json",
		"artifacts/entity-id.json",
	} {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return "cmd/agent/internal/entity/testdata/entity-gate-bootstrap.json"
}

// OnCritical engages kill switch (auto-stop broadcast/sign) on critical alerts.
func (e *Engine) OnCritical(kind, detail string) {
	e.killSwitch.Engage(fmt.Sprintf("%s: %s", kind, detail))
	e.mu.Lock()
	e.blockedUntil = time.Now().Add(time.Duration(e.cooldownAfterBlock * float64(time.Second)))
	e.mu.Unlock()
	// Best-effort paging (Slack/PagerDuty webhook); never blocks kill-switch path.
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = alerting.PageCritical(ctx, kind, detail)
	}()
}

// PrepareRescue runs limits → kill switch → phase → allowlist → rate → fees.
func (e *Engine) PrepareRescue(ctx context.Context, req RescueRequest) (*RescuePlan, error) {
	if req.BalanceWei == nil {
		req.BalanceWei = big.NewInt(0)
	}
	if req.RescueValue == nil {
		req.RescueValue = big.NewInt(0)
	}

	if engaged, reason := e.killSwitch.Engaged(); engaged {
		return nil, fmt.Errorf("ENGINE: kill switch engaged — %s", reason)
	}
	if e.phase == signer.PhaseShadow {
		return nil, fmt.Errorf("ENGINE: shadow phase — no sign/broadcast (guard decisions only)")
	}

	e.mu.Lock()
	if time.Now().Before(e.blockedUntil) {
		e.mu.Unlock()
		return nil, fmt.Errorf("ENGINE: cooldown active after risk event")
	}
	cutoff := time.Now().Add(-time.Duration(e.rescueWindowSec * float64(time.Second)))
	kept := e.attempts[:0]
	for _, t := range e.attempts {
		if t.After(cutoff) {
			kept = append(kept, t)
		}
	}
	e.attempts = kept
	if len(e.attempts) >= e.maxRescuesPerWindow {
		e.mu.Unlock()
		return nil, fmt.Errorf("ENGINE: rate limit exceeded (%d/%d window)", len(e.attempts), e.maxRescuesPerWindow)
	}
	e.mu.Unlock()

	if e.maxRescueValueWei != nil && req.RescueValue.Cmp(e.maxRescueValueWei) > 0 {
		e.OnCritical("value_cap", fmt.Sprintf("rescue %s > max %s", req.RescueValue, e.maxRescueValueWei))
		return nil, fmt.Errorf("ENGINE: rescue value exceeds phase cap")
	}

	strategy := e.limits.EvaluateCombined(req.BalanceWei, req.RescueValue)
	switch strategy {
	case guard.StrategyBlockNoGas:
		return nil, fmt.Errorf("ENGINE: balance below MIN_GAS")
	case guard.StrategyNoTrigger:
		return nil, fmt.Errorf("ENGINE: THRESHOLD_OK — rescue not required")
	case guard.StrategyEscalate:
		return nil, fmt.Errorf("ENGINE: %s — emit %s for KMS review", strategy, guard.TopicHighValuePending)
	}

	funder := strings.ToLower(strings.TrimSpace(req.FunderAddress))
	if funder == "" {
		return nil, fmt.Errorf("ENGINE: empty funder address")
	}
	destRaw := strings.TrimSpace(req.DestinationAddress)
	if destRaw == "" {
		destRaw = req.FunderAddress
	}
	destination := strings.ToLower(destRaw)
	if destination == "" {
		return nil, fmt.Errorf("ENGINE: empty destination address")
	}

	if e.requireAllowlist && len(e.allow) == 0 && len(e.destAllow) == 0 {
		return nil, fmt.Errorf("ENGINE: allowlist required (attack #06) — empty ALLOWED_FUNDERS/DESTINATIONS")
	}
	if len(e.allow) > 0 {
		if _, ok := e.allow[funder]; !ok {
			e.OnCritical("BLOCK_COMPROMISED_FUNDER", req.FunderAddress)
			return nil, fmt.Errorf("ENGINE: funder %s not in allowlist (attack #06) BLOCK_COMPROMISED_FUNDER", req.FunderAddress)
		}
	}
	if len(e.destAllow) > 0 {
		if _, ok := e.destAllow[destination]; !ok {
			e.OnCritical("BLOCK_COMPROMISED_FUNDER", destRaw)
			return nil, fmt.Errorf("ENGINE: destination %s not in allowlist (attack #06) BLOCK_COMPROMISED_FUNDER", destRaw)
		}
	}

	ok, err := e.gate.VerifyAddress(ctx, req.FunderAddress)
	if err != nil || !ok {
		if err != nil {
			return nil, err
		}
		return nil, fmt.Errorf("ENGINE: entity gate denied funder %s", req.FunderAddress)
	}
	if destination != funder {
		okDest, errDest := e.gate.VerifyAddress(ctx, destRaw)
		if errDest != nil || !okDest {
			if errDest != nil {
				return nil, errDest
			}
			return nil, fmt.Errorf("ENGINE: entity gate denied destination %s", destRaw)
		}
	}

	dedupKey := fmt.Sprintf("%s:%s:%s:%s", req.BotAddress, req.FunderAddress, destRaw, req.RescueValue.String())
	if _, loaded := e.dedup.LoadOrStore(dedupKey, time.Now().UTC()); loaded {
		return nil, fmt.Errorf("ENGINE: duplicate rescue suppressed (attack #02/#04)")
	}

	var fees *tx.FeeSuggestion
	if e.fees != nil && !req.DryRun {
		fees, err = e.fees.SuggestAggressiveFees(ctx)
		if err != nil {
			return nil, fmt.Errorf("ENGINE: fee suggestion failed: %w", err)
		}
	}

	e.mu.Lock()
	e.attempts = append(e.attempts, time.Now())
	e.mu.Unlock()

	return &RescuePlan{
		Strategy:  guard.StrategyAutoSign,
		Fees:      fees,
		DedupKey:  dedupKey,
		AllowedAt: time.Now().UTC(),
	}, nil
}

// ClaimSignIntent binds intent_hash+nonce+chainId before sign (TOCTOU + dedup).
func (e *Engine) ClaimSignIntent(to string, value *big.Int, chainID int64, nonce uint64) (string, error) {
	ih := guard.IntentHash(to, value, "0x", chainID, nonce)
	if e.intentDedup == nil {
		return ih, nil
	}
	if !e.intentDedup.Claim(ih, nonce, chainID) {
		return ih, fmt.Errorf("ENGINE: duplicate intent suppressed (intent_hash+nonce+chainId)")
	}
	return ih, nil
}

// VerifyPostSign rechecks balance+nonce via quorum before broadcast (TOCTOU).
// Never skips — missing quorum is always an error (fail-closed).
func (e *Engine) VerifyPostSign(
	ctx context.Context,
	botAddress string,
	expectedNonce uint64,
	balanceBefore *big.Int,
	intentHash string,
	chainID int64,
) error {
	if e.quorum == nil {
		e.OnCritical("quorum_missing", "post-sign recheck")
		return fmt.Errorf("ENGINE: quorum required for post-sign recheck (fail-closed)")
	}
	addr := common.HexToAddress(botAddress)
	bal, err := e.quorum.BalanceQuorum(ctx, addr)
	if err != nil {
		if e.intentDedup != nil {
			e.intentDedup.Release(intentHash, expectedNonce, chainID)
		}
		e.OnCritical("post_sign_quorum_balance", err.Error())
		return fmt.Errorf("ENGINE: post-sign quorum balance failed: %w", err)
	}
	nonce, err := e.quorum.NonceQuorum(ctx, addr)
	if err != nil {
		if e.intentDedup != nil {
			e.intentDedup.Release(intentHash, expectedNonce, chainID)
		}
		e.OnCritical("post_sign_quorum_nonce", err.Error())
		return fmt.Errorf("ENGINE: post-sign quorum nonce failed: %w", err)
	}
	drift, reasons := guard.PostSignDrift(expectedNonce, balanceBefore, guard.PostSignSnapshot{
		BalanceWei: bal,
		Nonce:      nonce,
	})
	if drift {
		if e.intentDedup != nil {
			e.intentDedup.Release(intentHash, expectedNonce, chainID)
		}
		e.OnCritical("post_sign_drift", fmt.Sprintf("%v", reasons))
		return fmt.Errorf("ENGINE: post-sign drift %v — drop tx (TOCTOU)", reasons)
	}
	return nil
}

// ReleaseIntent releases intent dedup after drop/revert (requires chainId).
func (e *Engine) ReleaseIntent(intentHash string, nonce uint64, chainID int64) {
	if e.intentDedup != nil {
		e.intentDedup.Release(intentHash, nonce, chainID)
	}
}

// ReleaseDedup clears a dedup key after on-chain revert (monitor.HandleReceipt).
func (e *Engine) ReleaseDedup(dedupKey string) {
	e.dedup.Delete(dedupKey)
}

// HandleReceipt processes tx receipt; releases dedup on failure/revert.
func (e *Engine) HandleReceipt(dedupKey string, success bool, txHash string) error {
	if success {
		return nil
	}
	e.ReleaseDedup(dedupKey)
	return fmt.Errorf("ENGINE: tx %s failed — dedup released for retry", txHash)
}

// BlockFunder marks an address compromised (runtime policy update).
func (e *Engine) BlockFunder(address, reason string) {
	e.gate.BlockAddress(address, reason, "COMPROMISED")
	e.OnCritical("BLOCK_COMPROMISED_FUNDER", reason)
}
