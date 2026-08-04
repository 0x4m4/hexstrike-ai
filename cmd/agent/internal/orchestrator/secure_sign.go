package orchestrator

import (
	"context"
	"fmt"
	"math/big"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/ethclient"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/signer"
	txpkg "github.com/hexstrike-ai/hexstrike/cmd/agent/internal/tx"
)

// SignedRescue is a post-TOCTOU-approved raw tx ready for broadcast.
type SignedRescue struct {
	Raw        []byte
	Hash       string
	Nonce      uint64
	IntentHash string
	Fees       *txpkg.FeeSuggestion
	ChainID    int64
}

// SecureSignRescue performs the mandatory TOCTOU path:
// single-flight → quorum nonce/balance → intent claim → sign via TxSigner → post-sign recheck.
// On any failure the signed payload must not be broadcast (caller must drop).
func (e *Engine) SecureSignRescue(
	ctx context.Context,
	_ *ethclient.Client,
	s signer.TxSigner,
	chainID *big.Int,
	to common.Address,
	value *big.Int,
	fees *txpkg.FeeSuggestion,
) (*SignedRescue, error) {
	if e == nil {
		return nil, fmt.Errorf("ENGINE: nil engine")
	}
	if s == nil {
		return nil, fmt.Errorf("ENGINE: signer required")
	}
	if engaged, reason := e.killSwitch.Engaged(); engaged {
		return nil, fmt.Errorf("ENGINE: kill switch engaged — %s", reason)
	}
	if e.phase == signer.PhaseShadow {
		return nil, fmt.Errorf("ENGINE: shadow phase — no sign/broadcast")
	}
	if e.requireRemoteSigner && s.Backend() == signer.BackendLocal {
		return nil, fmt.Errorf("ENGINE: local_key forbidden — require kms/remote signer")
	}
	if fees == nil {
		return nil, fmt.Errorf("ENGINE: fees required before secure sign")
	}
	if chainID == nil {
		return nil, fmt.Errorf("ENGINE: chainID required")
	}

	from := s.Address()
	rescueSignMu.Lock()
	defer rescueSignMu.Unlock()

	balanceBefore, err := e.quorumBalanceOrFail(ctx, from)
	if err != nil {
		e.OnCritical("pre_sign_quorum_balance", err.Error())
		return nil, err
	}
	nonce, err := e.quorumNonceOrFail(ctx, from)
	if err != nil {
		e.OnCritical("pre_sign_quorum_nonce", err.Error())
		return nil, err
	}

	intentHash, err := e.ClaimSignIntent(to.Hex(), value, chainID.Int64(), nonce)
	if err != nil {
		return nil, err
	}

	unsigned := types.NewTx(&types.DynamicFeeTx{
		ChainID:   chainID,
		Nonce:     nonce,
		To:        &to,
		Value:     value,
		Gas:       21_000,
		GasTipCap: fees.GasTipCap,
		GasFeeCap: fees.GasFeeCap,
	})
	signed, err := s.SignTx(ctx, unsigned, chainID)
	if err != nil {
		e.ReleaseIntent(intentHash, nonce, chainID.Int64())
		return nil, fmt.Errorf("ENGINE: sign failed: %w", err)
	}
	raw, err := signed.MarshalBinary()
	if err != nil {
		e.ReleaseIntent(intentHash, nonce, chainID.Int64())
		return nil, err
	}

	if err := e.VerifyPostSign(ctx, from.Hex(), nonce, balanceBefore, intentHash, chainID.Int64()); err != nil {
		e.OnCritical("post_sign_drift", err.Error())
		return nil, fmt.Errorf("ENGINE: drop signed tx — %w", err)
	}

	return &SignedRescue{
		Raw:        raw,
		Hash:       signed.Hash().Hex(),
		Nonce:      nonce,
		IntentHash: intentHash,
		Fees:       fees,
		ChainID:    chainID.Int64(),
	}, nil
}

// SecureResignRescue re-signs with same nonce after fee bump, with post-sign recheck.
func (e *Engine) SecureResignRescue(
	ctx context.Context,
	s signer.TxSigner,
	chainID *big.Int,
	to common.Address,
	value *big.Int,
	nonce uint64,
	intentHash string,
	prevFees *txpkg.FeeSuggestion,
	bumpPct int,
	fees *txpkg.FeeSuggestion,
) (raw []byte, outFees *txpkg.FeeSuggestion, err error) {
	if engaged, reason := e.killSwitch.Engaged(); engaged {
		return nil, nil, fmt.Errorf("ENGINE: kill switch engaged — %s", reason)
	}
	rescueSignMu.Lock()
	defer rescueSignMu.Unlock()

	useFees := fees
	if useFees == nil {
		useFees = txpkg.BumpFeeSuggestionStrict(prevFees, bumpPct)
	} else {
		useFees = txpkg.EnsureReplacementFees(prevFees, useFees)
	}

	from := s.Address()
	balanceBefore, err := e.quorumBalanceOrFail(ctx, from)
	if err != nil {
		e.OnCritical("resign_quorum_balance", err.Error())
		return nil, nil, err
	}

	unsigned := types.NewTx(&types.DynamicFeeTx{
		ChainID:   chainID,
		Nonce:     nonce,
		To:        &to,
		Value:     value,
		Gas:       21_000,
		GasTipCap: useFees.GasTipCap,
		GasFeeCap: useFees.GasFeeCap,
	})
	signed, err := s.SignTx(ctx, unsigned, chainID)
	if err != nil {
		return nil, nil, err
	}
	raw, err = signed.MarshalBinary()
	if err != nil {
		return nil, nil, err
	}
	if err := e.VerifyPostSign(ctx, from.Hex(), nonce, balanceBefore, intentHash, chainID.Int64()); err != nil {
		e.OnCritical("resign_post_sign_drift", err.Error())
		return nil, nil, fmt.Errorf("ENGINE: drop resigned tx — %w", err)
	}
	return raw, useFees, nil
}

func (e *Engine) quorumBalanceOrFail(ctx context.Context, addr common.Address) (*big.Int, error) {
	if e.quorum == nil {
		return nil, fmt.Errorf("ENGINE: quorum required for secure sign (fail-closed)")
	}
	return e.quorum.BalanceQuorum(ctx, addr)
}

func (e *Engine) quorumNonceOrFail(ctx context.Context, addr common.Address) (uint64, error) {
	if e.quorum == nil {
		return 0, fmt.Errorf("ENGINE: quorum required for secure sign (fail-closed)")
	}
	return e.quorum.NonceQuorum(ctx, addr)
}
