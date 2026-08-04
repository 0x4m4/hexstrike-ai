package orchestrator

import (
	"context"
	"crypto/ecdsa"
	"math/big"
	"sync"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/ethclient"
	txpkg "github.com/hexstrike-ai/hexstrike/cmd/agent/internal/tx"
)

// rescueSignMu serializes nonce fetch + resign for a single bot signer (no parallel rescues).
var rescueSignMu sync.Mutex

// SignRescueTx builds and signs an EIP-1559 rescue transfer from bot → funder.
func SignRescueTx(
	ctx context.Context,
	client *ethclient.Client,
	key *ecdsa.PrivateKey,
	chainID *big.Int,
	from, to common.Address,
	value *big.Int,
	fees *txpkg.FeeSuggestion,
) (raw []byte, hash string, nonce uint64, err error) {
	rescueSignMu.Lock()
	defer rescueSignMu.Unlock()

	nonce, err = client.PendingNonceAt(ctx, from)
	if err != nil {
		return nil, "", 0, err
	}
	raw, hash, err = signRescueTxWithNonce(chainID, key, nonce, to, value, fees)
	return raw, hash, nonce, err
}

// ResignRescueTx re-signs with the same nonce and strictly higher fees (mempool replacement).
func ResignRescueTx(
	ctx context.Context,
	client *ethclient.Client,
	key *ecdsa.PrivateKey,
	chainID *big.Int,
	from, to common.Address,
	value *big.Int,
	nonce uint64,
	prevFees *txpkg.FeeSuggestion,
	bumpPct int,
	fees *txpkg.FeeSuggestion,
) (raw []byte, outFees *txpkg.FeeSuggestion, err error) {
	rescueSignMu.Lock()
	defer rescueSignMu.Unlock()

	useFees := fees
	if useFees == nil {
		useFees = txpkg.BumpFeeSuggestionStrict(prevFees, bumpPct)
	} else {
		useFees = txpkg.EnsureReplacementFees(prevFees, useFees)
	}
	raw, _, err = signRescueTxWithNonce(chainID, key, nonce, to, value, useFees)
	return raw, useFees, err
}

func signRescueTxWithNonce(
	chainID *big.Int,
	key *ecdsa.PrivateKey,
	nonce uint64,
	to common.Address,
	value *big.Int,
	fees *txpkg.FeeSuggestion,
) (raw []byte, hash string, err error) {
	txn := types.NewTx(&types.DynamicFeeTx{
		ChainID:   chainID,
		Nonce:     nonce,
		To:        &to,
		Value:     value,
		Gas:       21_000,
		GasTipCap: fees.GasTipCap,
		GasFeeCap: fees.GasFeeCap,
	})
	signed, err := types.SignTx(txn, types.NewLondonSigner(chainID), key)
	if err != nil {
		return nil, "", err
	}
	raw, err = signed.MarshalBinary()
	if err != nil {
		return nil, "", err
	}
	return raw, signed.Hash().Hex(), nil
}
