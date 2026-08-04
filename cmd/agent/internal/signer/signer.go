// Package signer provides fail-closed transaction signing backends.
// Production paths must use KMS or remote signer — raw keys are lab-only.
package signer

import (
	"context"
	"crypto/ecdsa"
	"fmt"
	"math/big"
	"os"
	"strings"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
)

// Backend identifies how signatures are produced.
type Backend string

const (
	BackendLocal  Backend = "local_key" // lab / Anvil only
	BackendKMS    Backend = "kms"
	BackendRemote Backend = "remote" // HSM / remote signer HTTP
)

// Phase gates whether local keys are permitted.
type Phase string

const (
	PhaseLab     Phase = "lab"
	PhaseShadow  Phase = "shadow"
	PhaseCanary  Phase = "canary"
	PhaseLimited Phase = "limited"
)

// TxSigner signs EIP-1559 txs without exposing raw key material to callers
// (except LocalKeySigner, which is rejected outside lab).
type TxSigner interface {
	Backend() Backend
	Address() common.Address
	SignTx(ctx context.Context, tx *types.Transaction, chainID *big.Int) (*types.Transaction, error)
}

// LocalKeySigner holds an in-process private key — LAB ONLY.
type LocalKeySigner struct {
	key  *ecdsa.PrivateKey
	addr common.Address
}

// NewLocalKeySigner builds a lab-only signer from a hex private key.
func NewLocalKeySigner(hexKey string) (*LocalKeySigner, error) {
	hexKey = strings.TrimPrefix(strings.TrimSpace(hexKey), "0x")
	if hexKey == "" {
		return nil, fmt.Errorf("signer: empty local key")
	}
	key, err := crypto.HexToECDSA(hexKey)
	if err != nil {
		return nil, fmt.Errorf("signer: invalid local key: %w", err)
	}
	return &LocalKeySigner{key: key, addr: crypto.PubkeyToAddress(key.PublicKey)}, nil
}

func (s *LocalKeySigner) Backend() Backend           { return BackendLocal }
func (s *LocalKeySigner) Address() common.Address    { return s.addr }
func (s *LocalKeySigner) SignTx(_ context.Context, tx *types.Transaction, chainID *big.Int) (*types.Transaction, error) {
	return types.SignTx(tx, types.NewLondonSigner(chainID), s.key)
}

// RemoteSigner signs via an external HTTP endpoint that never returns the key.
// POST JSON: {chainId, nonce, to, value, data, gas, maxFeePerGas, maxPriorityFeePerGas}
// Response: {rawTx: "0x..."} signed payload.
type RemoteSigner struct {
	backend Backend
	addr    common.Address
	signFn  func(ctx context.Context, unsigned *types.Transaction, chainID *big.Int) (*types.Transaction, error)
}

// NewRemoteSigner constructs a remote/HSM signer with an injected sign function (testable).
func NewRemoteSigner(addr common.Address, backend Backend, signFn func(ctx context.Context, unsigned *types.Transaction, chainID *big.Int) (*types.Transaction, error)) (*RemoteSigner, error) {
	if signFn == nil {
		return nil, fmt.Errorf("signer: remote signFn required")
	}
	if backend != BackendKMS && backend != BackendRemote {
		return nil, fmt.Errorf("signer: invalid remote backend %q", backend)
	}
	return &RemoteSigner{backend: backend, addr: addr, signFn: signFn}, nil
}

func (s *RemoteSigner) Backend() Backend           { return s.backend }
func (s *RemoteSigner) Address() common.Address    { return s.addr }
func (s *RemoteSigner) SignTx(ctx context.Context, tx *types.Transaction, chainID *big.Int) (*types.Transaction, error) {
	return s.signFn(ctx, tx, chainID)
}

// NewFromEnv selects signer backend. Raw keys forbidden outside PhaseLab.
// For BackendKMS with remote==nil, wires a real cloud KMS SDK client:
//   KMS_PROVIDER=aws (default) → AWS KMS (AWS_KMS_KEY_ID, AWS_REGION)
//   KMS_PROVIDER=gcp → GCP Cloud KMS (GCP_KMS_KEY_NAME)
func NewFromEnv(phase Phase, backend Backend, localKeyHex string, remote TxSigner) (TxSigner, error) {
	switch backend {
	case BackendLocal, "":
		if phase != PhaseLab {
			return nil, fmt.Errorf("signer: local_key forbidden in phase %s — use kms/remote", phase)
		}
		if strings.TrimSpace(localKeyHex) == "" {
			return nil, fmt.Errorf("signer: BOT_PRIVATE_KEY required for lab local_key")
		}
		return NewLocalKeySigner(localKeyHex)
	case BackendKMS:
		if remote != nil {
			if remote.Backend() != BackendKMS && remote.Backend() != BackendRemote {
				return nil, fmt.Errorf("signer: remote backend mismatch for kms")
			}
			return remote, nil
		}
		return newCloudKMSFromEnv(context.Background())
	case BackendRemote:
		if remote == nil {
			return nil, fmt.Errorf("signer: remote backend requires wired remote signer")
		}
		return remote, nil
	default:
		return nil, fmt.Errorf("signer: unknown backend %q", backend)
	}
}

func newCloudKMSFromEnv(ctx context.Context) (TxSigner, error) {
	provider := strings.ToLower(strings.TrimSpace(os.Getenv("KMS_PROVIDER")))
	switch provider {
	case "", "aws":
		return NewAWSKMSSignerFromEnv(ctx)
	case "gcp", "google":
		return NewGCPKMSSignerFromEnv(ctx)
	default:
		return nil, fmt.Errorf("signer: unknown KMS_PROVIDER %q (want aws|gcp)", provider)
	}
}

// ParsePhase maps GO_LIVE_PHASE env values.
func ParsePhase(raw string) Phase {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "shadow":
		return PhaseShadow
	case "canary":
		return PhaseCanary
	case "limited":
		return PhaseLimited
	default:
		return PhaseLab
	}
}

// ParseBackend maps SIGNER_BACKEND env values.
func ParseBackend(raw string) Backend {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "kms":
		return BackendKMS
	case "remote", "hsm":
		return BackendRemote
	default:
		return BackendLocal
	}
}
