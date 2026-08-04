package signer

import (
	"context"
	"crypto/ecdsa"
	"crypto/rand"
	"encoding/pem"
	"math/big"
	"testing"

	"cloud.google.com/go/kms/apiv1/kmspb"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
)

type mockGCP struct {
	key *ecdsa.PrivateKey
	pem string
}

func (m *mockGCP) GetPublicKey(ctx context.Context, req *kmspb.GetPublicKeyRequest) (*kmspb.PublicKey, error) {
	return &kmspb.PublicKey{Pem: m.pem}, nil
}
func (m *mockGCP) AsymmetricSign(ctx context.Context, req *kmspb.AsymmetricSignRequest) (*kmspb.AsymmetricSignResponse, error) {
	digest := req.GetDigest().GetSha256()
	der, err := ecdsa.SignASN1(rand.Reader, m.key, digest)
	if err != nil {
		return nil, err
	}
	return &kmspb.AsymmetricSignResponse{Signature: der}, nil
}
func (m *mockGCP) Close() error { return nil }

func TestGCPKMSSigner_SignTx(t *testing.T) {
	key, err := crypto.GenerateKey()
	if err != nil {
		t.Fatal(err)
	}
	spki, err := marshalSecp256k1SPKI(crypto.FromECDSAPub(&key.PublicKey))
	if err != nil {
		t.Fatal(err)
	}
	pemBytes := pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: spki})
	mock := &mockGCP{key: key, pem: string(pemBytes)}
	s, err := NewGCPKMSSigner(context.Background(), mock, "projects/p/locations/l/keyRings/r/cryptoKeys/k/cryptoKeyVersions/1")
	if err != nil {
		t.Fatal(err)
	}
	to := common.HexToAddress("0x730ea0231808f42a20f8921ba7fbc788226768f5")
	unsigned := types.NewTx(&types.DynamicFeeTx{
		ChainID: big.NewInt(56), Nonce: 2, To: &to, Value: big.NewInt(1),
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

var _ GCPKMSAPI = (*mockGCP)(nil)
