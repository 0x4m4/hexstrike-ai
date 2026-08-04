package relay

import (
	"context"
	"crypto/ecdsa"
	"math/big"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/tx"
)

func TestTxHashFromRawNotBundleHex(t *testing.T) {
	key, err := crypto.GenerateKey()
	if err != nil {
		t.Fatal(err)
	}
	chainID := big.NewInt(56)
	to := common.HexToAddress("0x060447dC91dfb22A5233731aF67E9E8dafdF24d1")
	txn := types.NewTx(&types.DynamicFeeTx{
		ChainID:   chainID,
		Nonce:     7,
		To:        &to,
		Value:     big.NewInt(1000),
		Gas:       21_000,
		GasTipCap: big.NewInt(1_000_000_000),
		GasFeeCap: big.NewInt(3_000_000_000),
	})
	signed, err := types.SignTx(txn, types.NewLondonSigner(chainID), key)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := signed.MarshalBinary()
	if err != nil {
		t.Fatal(err)
	}
	got, err := TxHashFromRaw(raw)
	if err != nil {
		t.Fatal(err)
	}
	if got != signed.Hash().Hex() {
		t.Fatalf("hash=%s want=%s", got, signed.Hash().Hex())
	}
	if len(got) != 66 {
		t.Fatalf("expected 32-byte hash hex, got len=%d %q", len(got), got)
	}
}

func TestPrivateBundleReturnsTxHashNotRawHex(t *testing.T) {
	key, _ := crypto.GenerateKey()
	chainID := big.NewInt(56)
	to := common.HexToAddress("0x730ea0231808f42a20f8921ba7fbc788226768f5")
	build := func(bump int, _ *tx.FeeSuggestion) ([]byte, error) {
		tip := big.NewInt(int64(1_000_000_000 + bump*1_000_000))
		fee := big.NewInt(int64(3_000_000_000 + bump*1_000_000))
		txn := types.NewTx(&types.DynamicFeeTx{
			ChainID: chainID, Nonce: 1, To: &to, Value: big.NewInt(1),
			Gas: 21_000, GasTipCap: tip, GasFeeCap: fee,
		})
		signed, err := types.SignTx(txn, types.NewLondonSigner(chainID), key)
		if err != nil {
			return nil, err
		}
		return signed.MarshalBinary()
	}
	raw0, _ := build(0, nil)
	wantHash, _ := TxHashFromRaw(raw0)

	r := DefaultPuissantRelay()
	r.GasBumpSteps = []int{0}
	r.PollInterval = 0
	r.MaxWaitBlocks = 1
	r.Bundle = &confirmBundleClient{}
	r.Public = nil
	r.AllowPublicFallback = false
	r.StatusQuery = func(context.Context, string) (*BundleStatus, error) {
		return &BundleStatus{Confirmed: true, Block: 1}, nil
	}

	res, err := r.Submit(context.Background(), SubmitRequest{
		RawTx:  raw0,
		Resign: func(_ context.Context, bump int, fees *tx.FeeSuggestion) ([]byte, error) {
			return build(bump, fees)
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if res.TxHash != wantHash {
		t.Fatalf("TxHash=%q want=%q (must not be raw hex)", res.TxHash, wantHash)
	}
	if res.Strategy != StrategyPrivate {
		t.Fatalf("strategy=%s", res.Strategy)
	}
}

func TestGasBumpWithoutResignFails(t *testing.T) {
	r := DefaultPuissantRelay()
	r.GasBumpSteps = []int{0, 15}
	r.Bundle = &confirmBundleClient{}
	r.StatusQuery = func(context.Context, string) (*BundleStatus, error) {
		return &BundleStatus{Confirmed: false}, nil
	}
	_, err := r.Submit(context.Background(), SubmitRequest{RawTx: []byte{0x02, 0x00}})
	if err == nil {
		t.Fatal("expected error when bump>0 without Resign")
	}
}

type confirmBundleClient struct{}

func (confirmBundleClient) SendBundle(context.Context, BundleParams) (string, error) {
	return "0xbundle", nil
}

// silence unused import if key type needed
var _ *ecdsa.PrivateKey
