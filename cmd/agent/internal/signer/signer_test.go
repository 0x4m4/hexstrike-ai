package signer

import (
	"context"
	"math/big"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
)

func TestLocalKeyForbiddenOutsideLab(t *testing.T) {
	key, _ := crypto.GenerateKey()
	hex := common.Bytes2Hex(crypto.FromECDSA(key))
	_, err := NewFromEnv(PhaseCanary, BackendLocal, hex, nil)
	if err == nil {
		t.Fatal("local key must be forbidden in canary")
	}
}

func TestLocalKeyAllowedInLab(t *testing.T) {
	key, _ := crypto.GenerateKey()
	hex := common.Bytes2Hex(crypto.FromECDSA(key))
	s, err := NewFromEnv(PhaseLab, BackendLocal, hex, nil)
	if err != nil {
		t.Fatal(err)
	}
	if s.Backend() != BackendLocal {
		t.Fatalf("backend=%s", s.Backend())
	}
}

func TestKMSRequiresCloudConfigOrInjected(t *testing.T) {
	t.Setenv("AWS_KMS_KEY_ID", "")
	t.Setenv("KMS_PROVIDER", "aws")
	_, err := NewFromEnv(PhaseLimited, BackendKMS, "", nil)
	if err == nil {
		t.Fatal("kms without cloud config must fail closed")
	}
}

func TestRemoteKMSSignDoesNotNeedLocalKey(t *testing.T) {
	key, _ := crypto.GenerateKey()
	addr := crypto.PubkeyToAddress(key.PublicKey)
	remote, err := NewRemoteSigner(addr, BackendKMS, func(ctx context.Context, tx *types.Transaction, chainID *big.Int) (*types.Transaction, error) {
		return types.SignTx(tx, types.NewLondonSigner(chainID), key)
	})
	if err != nil {
		t.Fatal(err)
	}
	s, err := NewFromEnv(PhaseLimited, BackendKMS, "", remote)
	if err != nil {
		t.Fatal(err)
	}
	if s.Backend() != BackendKMS {
		t.Fatalf("backend=%s", s.Backend())
	}
	to := common.HexToAddress("0x730ea0231808f42a20f8921ba7fbc788226768f5")
	unsigned := types.NewTx(&types.DynamicFeeTx{
		ChainID: big.NewInt(31337), Nonce: 1, To: &to, Value: big.NewInt(1),
		Gas: 21000, GasTipCap: big.NewInt(1), GasFeeCap: big.NewInt(2),
	})
	signed, err := s.SignTx(context.Background(), unsigned, big.NewInt(31337))
	if err != nil || signed == nil {
		t.Fatalf("sign: %v", err)
	}
}
