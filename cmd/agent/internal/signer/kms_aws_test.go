package signer

import (
	"context"
	"crypto/ecdsa"
	"crypto/rand"
	"math/big"
	"testing"

	"github.com/aws/aws-sdk-go-v2/service/kms"
	kmstypes "github.com/aws/aws-sdk-go-v2/service/kms/types"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
)

type mockKMS struct {
	key    *ecdsa.PrivateKey
	pubDER []byte
}

func (m *mockKMS) GetPublicKey(ctx context.Context, params *kms.GetPublicKeyInput, optFns ...func(*kms.Options)) (*kms.GetPublicKeyOutput, error) {
	return &kms.GetPublicKeyOutput{PublicKey: m.pubDER}, nil
}

func (m *mockKMS) Sign(ctx context.Context, params *kms.SignInput, optFns ...func(*kms.Options)) (*kms.SignOutput, error) {
	der, err := ecdsa.SignASN1(rand.Reader, m.key, params.Message)
	if err != nil {
		return nil, err
	}
	return &kms.SignOutput{Signature: der, SigningAlgorithm: kmstypes.SigningAlgorithmSpecEcdsaSha256}, nil
}

func TestAWSKMSSigner_SignTxNoRawKeyInCaller(t *testing.T) {
	key, err := crypto.GenerateKey()
	if err != nil {
		t.Fatal(err)
	}
	pubDER, err := marshalSecp256k1SPKI(crypto.FromECDSAPub(&key.PublicKey))
	if err != nil {
		t.Fatal(err)
	}
	mock := &mockKMS{key: key, pubDER: pubDER}
	s, err := NewAWSKMSSigner(context.Background(), mock, "arn:aws:kms:test:key")
	if err != nil {
		t.Fatal(err)
	}
	if s.Backend() != BackendKMS {
		t.Fatalf("backend=%s", s.Backend())
	}
	if s.Address() != crypto.PubkeyToAddress(key.PublicKey) {
		t.Fatalf("address mismatch")
	}
	to := common.HexToAddress("0x730ea0231808f42a20f8921ba7fbc788226768f5")
	unsigned := types.NewTx(&types.DynamicFeeTx{
		ChainID: big.NewInt(56), Nonce: 1, To: &to, Value: big.NewInt(1),
		Gas: 21000, GasTipCap: big.NewInt(1), GasFeeCap: big.NewInt(2),
	})
	signed, err := s.SignTx(context.Background(), unsigned, big.NewInt(56))
	if err != nil {
		t.Fatal(err)
	}
	from, err := types.Sender(types.NewLondonSigner(big.NewInt(56)), signed)
	if err != nil {
		t.Fatal(err)
	}
	if from != s.Address() {
		t.Fatalf("recovered %s want %s", from.Hex(), s.Address().Hex())
	}
}

func TestEthSignatureFromKMS_RoundTrip(t *testing.T) {
	key, _ := crypto.GenerateKey()
	digest := crypto.Keccak256([]byte("hello-hexstrike-kms"))
	der, err := ecdsa.SignASN1(rand.Reader, key, digest)
	if err != nil {
		t.Fatal(err)
	}
	addr := crypto.PubkeyToAddress(key.PublicKey)
	sig, err := ethSignatureFromKMS(digest, der, addr)
	if err != nil {
		t.Fatal(err)
	}
	pub, err := crypto.SigToPub(digest, sig)
	if err != nil {
		t.Fatal(err)
	}
	if crypto.PubkeyToAddress(*pub) != addr {
		t.Fatal("recover mismatch")
	}
}

func TestNewFromEnv_KMSFailClosedWithoutCloudConfig(t *testing.T) {
	t.Setenv("AWS_KMS_KEY_ID", "")
	t.Setenv("GCP_KMS_KEY_NAME", "")
	t.Setenv("KMS_PROVIDER", "aws")
	_, err := NewFromEnv(PhaseCanary, BackendKMS, "0xdeadbeef", nil)
	if err == nil {
		t.Fatal("expected fail-closed without AWS_KMS_KEY_ID")
	}
}

func TestNewFromEnv_KMSAcceptsInjectedAWSSigner(t *testing.T) {
	key, _ := crypto.GenerateKey()
	mock := &mockKMS{key: key, pubDER: crypto.FromECDSAPub(&key.PublicKey)}
	awsSigner, err := NewAWSKMSSigner(context.Background(), mock, "test")
	if err != nil {
		t.Fatal(err)
	}
	s, err := NewFromEnv(PhaseLimited, BackendKMS, "", awsSigner)
	if err != nil {
		t.Fatal(err)
	}
	if s.Backend() != BackendKMS {
		t.Fatal(s.Backend())
	}
}

var _ KMSAPI = (*mockKMS)(nil)
