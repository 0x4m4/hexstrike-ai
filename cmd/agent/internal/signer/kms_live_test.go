//go:build live_kms

package signer

import (
	"context"
	"math/big"
	"os"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
)

// TestLiveKMS_SignTx exercises a real cloud KMS key (operator credentials required).
// Run: go test ./internal/signer/ -tags=live_kms -run TestLiveKMS_SignTx -count=1 -v
func TestLiveKMS_SignTx(t *testing.T) {
	ctx := context.Background()
	s, err := newCloudKMSFromEnv(ctx)
	if err != nil {
		t.Fatalf("newCloudKMSFromEnv: %v", err)
	}
	if s.Backend() != BackendKMS {
		t.Fatalf("backend=%s want kms", s.Backend())
	}
	t.Logf("kms_address=%s provider=%s", s.Address().Hex(), os.Getenv("KMS_PROVIDER"))

	to := common.HexToAddress("0x730ea0231808f42a20f8921ba7fbc788226768f5")
	chainID := big.NewInt(56)
	if raw := os.Getenv("CHAIN_ID"); raw != "" {
		if v, ok := new(big.Int).SetString(raw, 10); ok {
			chainID = v
		}
	}
	unsigned := types.NewTx(&types.DynamicFeeTx{
		ChainID:   chainID,
		Nonce:     0,
		To:        &to,
		Value:     big.NewInt(1),
		Gas:       21000,
		GasTipCap: big.NewInt(1),
		GasFeeCap: big.NewInt(2),
	})
	signed, err := s.SignTx(ctx, unsigned, chainID)
	if err != nil {
		t.Fatalf("SignTx: %v", err)
	}
	from, err := types.Sender(types.NewLondonSigner(chainID), signed)
	if err != nil {
		t.Fatalf("Sender: %v", err)
	}
	if from != s.Address() {
		t.Fatalf("recovered %s != kms %s", from.Hex(), s.Address().Hex())
	}
	t.Logf("PASS live sign recovered_from=%s tx_hash=%s", from.Hex(), signed.Hash().Hex())
}
