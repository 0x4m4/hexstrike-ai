package signer

import (
	"crypto/ecdsa"
	"crypto/x509"
	"encoding/asn1"
	"fmt"
	"math/big"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
)

type ecdsaSignature struct {
	R, S *big.Int
}

// parseDERSignature decodes ASN.1 DER ECDSA signature from KMS.
func parseDERSignature(der []byte) (r, s *big.Int, err error) {
	var sig ecdsaSignature
	if _, err = asn1.Unmarshal(der, &sig); err != nil {
		return nil, nil, fmt.Errorf("signer: der decode: %w", err)
	}
	if sig.R == nil || sig.S == nil {
		return nil, nil, fmt.Errorf("signer: incomplete der signature")
	}
	return sig.R, sig.S, nil
}

var secp256k1N = crypto.S256().Params().N
var secp256k1HalfN = new(big.Int).Rsh(secp256k1N, 1)

func normalizeLowS(s *big.Int) *big.Int {
	if s.Cmp(secp256k1HalfN) > 0 {
		return new(big.Int).Sub(secp256k1N, s)
	}
	return s
}

// ethSignatureFromKMS builds [R||S||V] matching expect address for digest.
func ethSignatureFromKMS(digest []byte, der []byte, expect common.Address) ([]byte, error) {
	if len(digest) != 32 {
		return nil, fmt.Errorf("signer: digest must be 32 bytes")
	}
	r, s, err := parseDERSignature(der)
	if err != nil {
		return nil, err
	}
	s = normalizeLowS(s)
	rb := common.LeftPadBytes(r.Bytes(), 32)
	sb := common.LeftPadBytes(s.Bytes(), 32)
	for v := byte(0); v < 2; v++ {
		sig := make([]byte, 65)
		copy(sig[0:32], rb)
		copy(sig[32:64], sb)
		sig[64] = v
		pub, err := crypto.SigToPub(digest, sig)
		if err != nil {
			continue
		}
		if crypto.PubkeyToAddress(*pub) == expect {
			return sig, nil
		}
	}
	return nil, fmt.Errorf("signer: cannot recover address %s from KMS signature", expect.Hex())
}

type pkixPublicKey struct {
	Algo struct {
		Algorithm  asn1.ObjectIdentifier
		Parameters asn1.RawValue `asn1:"optional"`
	}
	SubjectPublicKey asn1.BitString
}

// pubkeyFromSPKI parses AWS/GCP SubjectPublicKeyInfo or raw uncompressed secp256k1 pubkey.
func pubkeyFromSPKI(der []byte) (*ecdsa.PublicKey, error) {
	if pub, err := crypto.UnmarshalPubkey(der); err == nil {
		return pub, nil
	}
	if len(der) == 64 {
		buf := append([]byte{0x04}, der...)
		if pub, err := crypto.UnmarshalPubkey(buf); err == nil {
			return pub, nil
		}
	}
	if pubAny, err := x509.ParsePKIXPublicKey(der); err == nil {
		if pub, ok := pubAny.(*ecdsa.PublicKey); ok {
			return pub, nil
		}
	}
	var spki pkixPublicKey
	if _, err := asn1.Unmarshal(der, &spki); err != nil {
		return nil, fmt.Errorf("signer: parse SPKI: %w", err)
	}
	pub, err := crypto.UnmarshalPubkey(spki.SubjectPublicKey.Bytes)
	if err != nil {
		return nil, fmt.Errorf("signer: SPKI bitstring: %w", err)
	}
	return pub, nil
}

func withSignature(tx *types.Transaction, chainID *big.Int, sig []byte) (*types.Transaction, error) {
	return tx.WithSignature(types.NewLondonSigner(chainID), sig)
}

func hashForSign(tx *types.Transaction, chainID *big.Int) common.Hash {
	return types.NewLondonSigner(chainID).Hash(tx)
}

// marshalSecp256k1SPKI builds a SubjectPublicKeyInfo DER for an uncompressed secp256k1 pubkey.
func marshalSecp256k1SPKI(uncompressed []byte) ([]byte, error) {
	oidEcPublicKey := asn1.ObjectIdentifier{1, 2, 840, 10045, 2, 1}
	oidSecp256k1 := asn1.ObjectIdentifier{1, 3, 132, 0, 10}
	paramDER, err := asn1.Marshal(oidSecp256k1)
	if err != nil {
		return nil, err
	}
	spki := pkixPublicKey{
		Algo: struct {
			Algorithm  asn1.ObjectIdentifier
			Parameters asn1.RawValue `asn1:"optional"`
		}{
			Algorithm:  oidEcPublicKey,
			Parameters: asn1.RawValue{FullBytes: paramDER},
		},
		SubjectPublicKey: asn1.BitString{Bytes: uncompressed, BitLength: len(uncompressed) * 8},
	}
	return asn1.Marshal(spki)
}
