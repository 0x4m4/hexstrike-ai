package signer

import (
	"context"
	"crypto/ecdsa"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"math/big"
	"os"
	"strings"

	kms "cloud.google.com/go/kms/apiv1"
	"cloud.google.com/go/kms/apiv1/kmspb"
	"github.com/ethereum/go-ethereum/common"
	gethtypes "github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
)

// GCPKMSAPI is the subset of GCP KMS used for Ethereum signing (mockable).
type GCPKMSAPI interface {
	GetPublicKey(ctx context.Context, req *kmspb.GetPublicKeyRequest) (*kmspb.PublicKey, error)
	AsymmetricSign(ctx context.Context, req *kmspb.AsymmetricSignRequest) (*kmspb.AsymmetricSignResponse, error)
	Close() error
}

type gcpSDKClient struct {
	inner *kms.KeyManagementClient
}

func (c *gcpSDKClient) GetPublicKey(ctx context.Context, req *kmspb.GetPublicKeyRequest) (*kmspb.PublicKey, error) {
	return c.inner.GetPublicKey(ctx, req)
}
func (c *gcpSDKClient) AsymmetricSign(ctx context.Context, req *kmspb.AsymmetricSignRequest) (*kmspb.AsymmetricSignResponse, error) {
	return c.inner.AsymmetricSign(ctx, req)
}
func (c *gcpSDKClient) Close() error { return c.inner.Close() }

// GCPKMSSigner signs txs with GCP Cloud KMS — private key never leaves KMS.
type GCPKMSSigner struct {
	client  GCPKMSAPI
	keyName string
	addr    common.Address
}

// NewGCPKMSSigner binds a crypto key version resource name to an eth address.
func NewGCPKMSSigner(ctx context.Context, client GCPKMSAPI, keyName string) (*GCPKMSSigner, error) {
	keyName = strings.TrimSpace(keyName)
	if keyName == "" {
		return nil, fmt.Errorf("signer: GCP_KMS_KEY_NAME required")
	}
	if client == nil {
		return nil, fmt.Errorf("signer: GCP KMS client required")
	}
	pub, err := client.GetPublicKey(ctx, &kmspb.GetPublicKeyRequest{Name: keyName})
	if err != nil {
		return nil, fmt.Errorf("signer: GCP GetPublicKey: %w", err)
	}
	block, _ := pem.Decode([]byte(pub.GetPem()))
	if block == nil {
		return nil, fmt.Errorf("signer: GCP public key PEM decode failed")
	}
	ecdsaPub, err := pubkeyFromSPKI(block.Bytes)
	if err != nil {
		// last resort stdlib PKIX (P-256 etc.)
		pubAny, err2 := x509.ParsePKIXPublicKey(block.Bytes)
		if err2 != nil {
			return nil, fmt.Errorf("signer: GCP parse public key: %w", err)
		}
		var ok bool
		ecdsaPub, ok = pubAny.(*ecdsa.PublicKey)
		if !ok {
			return nil, fmt.Errorf("signer: GCP key is not ECDSA public key")
		}
	}
	addr := crypto.PubkeyToAddress(*ecdsaPub)
	if expect := strings.TrimSpace(os.Getenv("SIGNER_ADDRESS")); expect != "" {
		if !strings.EqualFold(addr.Hex(), expect) {
			return nil, fmt.Errorf("signer: GCP pubkey address %s != SIGNER_ADDRESS %s", addr.Hex(), expect)
		}
	}
	return &GCPKMSSigner{client: client, keyName: keyName, addr: addr}, nil
}

// NewGCPKMSSignerFromEnv builds a real GCP KMS client (ADC credentials).
func NewGCPKMSSignerFromEnv(ctx context.Context) (*GCPKMSSigner, error) {
	keyName := strings.TrimSpace(os.Getenv("GCP_KMS_KEY_NAME"))
	if keyName == "" {
		return nil, fmt.Errorf("signer: GCP_KMS_KEY_NAME required for KMS_PROVIDER=gcp")
	}
	client, err := kms.NewKeyManagementClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("signer: GCP KMS client: %w", err)
	}
	return NewGCPKMSSigner(ctx, &gcpSDKClient{inner: client}, keyName)
}

func (s *GCPKMSSigner) Backend() Backend        { return BackendKMS }
func (s *GCPKMSSigner) Address() common.Address { return s.addr }

// SignTx uses AsymmetricSign with digest slot (keccak hash for secp256k1 eth path).
func (s *GCPKMSSigner) SignTx(ctx context.Context, tx *gethtypes.Transaction, chainID *big.Int) (*gethtypes.Transaction, error) {
	if s == nil || s.client == nil {
		return nil, fmt.Errorf("signer: GCP KMS not configured")
	}
	digest := hashForSign(tx, chainID).Bytes()
	out, err := s.client.AsymmetricSign(ctx, &kmspb.AsymmetricSignRequest{
		Name: s.keyName,
		Digest: &kmspb.Digest{
			Digest: &kmspb.Digest_Sha256{Sha256: digest},
		},
	})
	if err != nil {
		return nil, fmt.Errorf("signer: GCP AsymmetricSign: %w", err)
	}
	if len(out.Signature) == 0 {
		return nil, fmt.Errorf("signer: GCP returned empty signature")
	}
	sig, err := ethSignatureFromKMS(digest, out.Signature, s.addr)
	if err != nil {
		return nil, err
	}
	return withSignature(tx, chainID, sig)
}
