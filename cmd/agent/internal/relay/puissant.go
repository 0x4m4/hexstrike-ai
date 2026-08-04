package relay

import (
	"context"
	"encoding/hex"
	"fmt"
	"time"

	"github.com/ethereum/go-ethereum/core/types"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/tx"
)

// ResignFunc rebuilds a signed raw tx after a gas bump (required when bumpPct > 0).
type ResignFunc func(ctx context.Context, bumpPct int, fees *tx.FeeSuggestion) ([]byte, error)

// Strategy for bundle delivery.
type Strategy string

const (
	StrategyPrivate Strategy = "private_bundle"
	StrategyPublic  Strategy = "public_mempool"
)

// SubmitRequest is a signed raw tx payload.
type SubmitRequest struct {
	RawTx       []byte
	ChainID     int64
	MaxWait     time.Duration
	BlockTarget int // max blocks before fallback
	Resign      ResignFunc
}

// SubmitResult reports how the tx was sent.
type SubmitResult struct {
	Strategy     Strategy
	BundleID     string
	TxHash       string
	BlocksWaited int
	GasBumpPct   int
}

// Client abstracts bundle + public submission (for tests).
type Client interface {
	SendBundle(ctx context.Context, params BundleParams) (string, error)
}

// PuissantRelay sends BSC bundles via 48Club Puissant with gas bump + public fallback.
type PuissantRelay struct {
	Endpoint            string
	MaxWaitBlocks       int
	GasBumpSteps        []int
	AllowPublicFallback bool
	FeeCalc             func(ctx context.Context, bumpPct int) (*tx.FeeSuggestion, error)
	Bundle              Client
	Public              *PublicRPC
	PollInterval        time.Duration
	// StatusQuery overrides bundle status polling (tests); nil → QueryBundleStatus.
	StatusQuery func(ctx context.Context, bundleHash string) (*BundleStatus, error)
}

// DefaultPuissantRelay returns BSC-oriented defaults (3-block wait, +15/+25% gas steps).
func DefaultPuissantRelay() *PuissantRelay {
	return &PuissantRelay{
		Endpoint:            "https://puissant-builder.48.club/",
		MaxWaitBlocks:       3,
		GasBumpSteps:        []int{0, 15, 25}, // each non-zero step: +N% over previous attempt fees
		AllowPublicFallback: true,
		Bundle:              NewBundleClient(),
		Public:              NewPublicRPC(),
		PollInterval:        2 * time.Second,
	}
}

// TxHashFromRaw decodes a signed EIP-2718 tx and returns its canonical hash.
func TxHashFromRaw(raw []byte) (string, error) {
	if len(raw) == 0 {
		return "", fmt.Errorf("relay: empty raw tx")
	}
	var txn types.Transaction
	if err := txn.UnmarshalBinary(raw); err != nil {
		return "", fmt.Errorf("relay: decode raw tx: %w", err)
	}
	return txn.Hash().Hex(), nil
}

// Submit tries private bundle with escalating gas; polls status; falls back to public mempool.
func (p *PuissantRelay) Submit(ctx context.Context, req SubmitRequest) (*SubmitResult, error) {
	if len(req.RawTx) == 0 {
		return nil, fmt.Errorf("relay: empty raw tx")
	}
	maxBlocks := req.BlockTarget
	if maxBlocks <= 0 {
		maxBlocks = p.MaxWaitBlocks
	}
	if maxBlocks <= 0 {
		maxBlocks = 3
	}
	if p.Bundle == nil {
		p.Bundle = NewBundleClient()
	}
	if p.Public == nil {
		p.Public = NewPublicRPC()
	}

	currentRaw := req.RawTx
	for _, bump := range p.GasBumpSteps {
		if bump > 0 {
			if req.Resign == nil {
				return nil, fmt.Errorf("relay: gas bump %d%% requires Resign callback", bump)
			}
			var fees *tx.FeeSuggestion
			var err error
			if p.FeeCalc != nil {
				fees, err = p.FeeCalc(ctx, bump)
				if err != nil {
					return nil, fmt.Errorf("relay: fee bump %d%%: %w", bump, err)
				}
			}
			currentRaw, err = req.Resign(ctx, bump, fees)
			if err != nil {
				return nil, fmt.Errorf("relay: resign bump %d%%: %w", bump, err)
			}
		} else if p.FeeCalc != nil {
			if _, err := p.FeeCalc(ctx, bump); err != nil {
				return nil, fmt.Errorf("relay: fee calc: %w", err)
			}
		}

		rawHex := "0x" + hex.EncodeToString(currentRaw)
		bundleHash, err := p.Bundle.SendBundle(ctx, BundleParams{
			Txs:            []string{rawHex},
			MaxBlockNumber: 0,
		})
		if err != nil {
			continue
		}
		deadline := time.Now().Add(time.Duration(maxBlocks) * 3 * time.Second)
		statusFn := p.StatusQuery
		if statusFn == nil {
			statusFn = QueryBundleStatus
		}
		for time.Now().Before(deadline) {
			st, qerr := statusFn(ctx, bundleHash)
			if qerr == nil && st != nil && st.Confirmed {
				txHash, herr := TxHashFromRaw(currentRaw)
				if herr != nil {
					return nil, herr
				}
				return &SubmitResult{
					Strategy:     StrategyPrivate,
					BundleID:     bundleHash,
					TxHash:       txHash,
					BlocksWaited: maxBlocks,
					GasBumpPct:   bump,
				}, nil
			}
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(p.PollInterval):
			}
		}
	}

	if !p.AllowPublicFallback {
		return nil, fmt.Errorf("relay: private bundle not included after %d blocks", maxBlocks)
	}
	rawHex := "0x" + hex.EncodeToString(currentRaw)
	txHash, err := p.Public.SendRawTransaction(ctx, rawHex)
	if err != nil {
		return nil, fmt.Errorf("relay: public fallback failed: %w", err)
	}
	return &SubmitResult{
		Strategy:     StrategyPublic,
		TxHash:       txHash,
		BlocksWaited: maxBlocks,
		GasBumpPct:   p.GasBumpSteps[len(p.GasBumpSteps)-1],
	}, nil
}
