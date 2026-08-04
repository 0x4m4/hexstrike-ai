package signer

import (
	"context"
	"fmt"
	"math/big"
	"os"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/kms"
	"github.com/aws/aws-sdk-go-v2/service/kms/types"
	"github.com/ethereum/go-ethereum/common"
	gethtypes "github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
)

// KMSAPI is the subset of AWS KMS used for Ethereum signing (mockable).
type KMSAPI interface {
	Sign(ctx context.Context, params *kms.SignInput, optFns ...func(*kms.Options)) (*kms.SignOutput, error)
	GetPublicKey(ctx context.Context, params *kms.GetPublicKeyInput, optFns ...func(*kms.Options)) (*kms.GetPublicKeyOutput, error)
}

// AWSKMSSigner signs txs with AWS KMS ECC_SECG_P256K1 — private key never leaves KMS.
type AWSKMSSigner struct {
	client KMSAPI
	keyID  string
	addr   common.Address
}

// NewAWSKMSSigner loads public key from KMS and binds ethereum address.
// Env: AWS_KMS_KEY_ID (required), AWS_REGION (optional), SIGNER_ADDRESS (optional verify).
func NewAWSKMSSigner(ctx context.Context, client KMSAPI, keyID string) (*AWSKMSSigner, error) {
	keyID = strings.TrimSpace(keyID)
	if keyID == "" {
		return nil, fmt.Errorf("signer: AWS_KMS_KEY_ID required")
	}
	if client == nil {
		return nil, fmt.Errorf("signer: AWS KMS client required")
	}
	out, err := client.GetPublicKey(ctx, &kms.GetPublicKeyInput{KeyId: aws.String(keyID)})
	if err != nil {
		return nil, fmt.Errorf("signer: KMS GetPublicKey: %w", err)
	}
	if out.PublicKey == nil {
		return nil, fmt.Errorf("signer: KMS returned empty public key")
	}
	pub, err := pubkeyFromSPKI(out.PublicKey)
	if err != nil {
		return nil, err
	}
	addr := crypto.PubkeyToAddress(*pub)
	if expect := strings.TrimSpace(os.Getenv("SIGNER_ADDRESS")); expect != "" {
		if !strings.EqualFold(addr.Hex(), expect) {
			return nil, fmt.Errorf("signer: KMS pubkey address %s != SIGNER_ADDRESS %s", addr.Hex(), expect)
		}
	}
	return &AWSKMSSigner{client: client, keyID: keyID, addr: addr}, nil
}

// NewAWSKMSSignerFromEnv builds a real AWS SDK KMS client (default credential chain).
func NewAWSKMSSignerFromEnv(ctx context.Context) (*AWSKMSSigner, error) {
	keyID := strings.TrimSpace(os.Getenv("AWS_KMS_KEY_ID"))
	if keyID == "" {
		return nil, fmt.Errorf("signer: AWS_KMS_KEY_ID required for kms backend")
	}
	cfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		return nil, fmt.Errorf("signer: AWS config: %w", err)
	}
	if region := strings.TrimSpace(os.Getenv("AWS_REGION")); region != "" {
		cfg.Region = region
	}
	if cfg.Region == "" {
		return nil, fmt.Errorf("signer: AWS_REGION required for KMS")
	}
	return NewAWSKMSSigner(ctx, kms.NewFromConfig(cfg), keyID)
}

func (s *AWSKMSSigner) Backend() Backend        { return BackendKMS }
func (s *AWSKMSSigner) Address() common.Address { return s.addr }

// SignTx signs via KMS Sign (MessageType=DIGEST). Key material never enters process memory.
func (s *AWSKMSSigner) SignTx(ctx context.Context, tx *gethtypes.Transaction, chainID *big.Int) (*gethtypes.Transaction, error) {
	if s == nil || s.client == nil {
		return nil, fmt.Errorf("signer: AWS KMS not configured")
	}
	digest := hashForSign(tx, chainID).Bytes()
	out, err := s.client.Sign(ctx, &kms.SignInput{
		KeyId:            aws.String(s.keyID),
		Message:          digest,
		MessageType:      types.MessageTypeDigest,
		SigningAlgorithm: types.SigningAlgorithmSpecEcdsaSha256,
	})
	if err != nil {
		return nil, fmt.Errorf("signer: KMS Sign: %w", err)
	}
	if out.Signature == nil {
		return nil, fmt.Errorf("signer: KMS returned empty signature")
	}
	sig, err := ethSignatureFromKMS(digest, out.Signature, s.addr)
	if err != nil {
		return nil, err
	}
	return withSignature(tx, chainID, sig)
}
