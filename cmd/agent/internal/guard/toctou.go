// Package guard provides production safety controls for the rescue money circuit.
package guard

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/big"
	"strings"
	"sync"
)

// PolicyVersionDefault binds intent hashes to the active go-live policy.
const PolicyVersionDefault = "v1"

// IntentFields canonical tx intent for hashing.
// Hash = H(chainId,to,value,data,nonce,policyVersion).
type IntentFields struct {
	ChainID       int64  `json:"chainId"`
	To            string `json:"to"`
	Value         string `json:"value"`
	Data          string `json:"data"`
	Nonce         uint64 `json:"nonce"`
	PolicyVersion string `json:"policyVersion"`
}

// IntentHash returns SHA-256 of canonical JSON intent (TOCTOU binding).
func IntentHash(to string, value *big.Int, data string, chainID int64, nonce uint64) string {
	return IntentHashWithPolicy(to, value, data, chainID, nonce, PolicyVersionDefault)
}

// IntentHashWithPolicy includes an explicit policy version in the binding.
func IntentHashWithPolicy(to string, value *big.Int, data string, chainID int64, nonce uint64, policyVersion string) string {
	if value == nil {
		value = big.NewInt(0)
	}
	if data == "" {
		data = "0x"
	}
	if policyVersion == "" {
		policyVersion = PolicyVersionDefault
	}
	payload := IntentFields{
		ChainID:       chainID,
		To:            strings.ToLower(strings.TrimSpace(to)),
		Value:         value.String(),
		Data:          data,
		Nonce:         nonce,
		PolicyVersion: policyVersion,
	}
	raw, _ := json.Marshal(payload)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

// IntentDedup suppresses duplicate intent_hash+nonce pairs (attacks #02/#04).
type IntentDedup struct {
	mu   sync.Mutex
	seen map[string]struct{}
}

// NewIntentDedup returns an empty dedup registry.
func NewIntentDedup() *IntentDedup {
	return &IntentDedup{seen: make(map[string]struct{})}
}

// Claim returns false if (intent_hash, nonce, chainId) already in flight.
func (d *IntentDedup) Claim(intentHash string, nonce uint64, chainID int64) bool {
	key := fmt.Sprintf("%s:%d:%d", intentHash, nonce, chainID)
	d.mu.Lock()
	defer d.mu.Unlock()
	if _, ok := d.seen[key]; ok {
		return false
	}
	d.seen[key] = struct{}{}
	return true
}

// Release clears a dedup slot after revert or dropped broadcast.
func (d *IntentDedup) Release(intentHash string, nonce uint64, chainID int64) {
	key := fmt.Sprintf("%s:%d:%d", intentHash, nonce, chainID)
	d.mu.Lock()
	defer d.mu.Unlock()
	delete(d.seen, key)
}

// PostSignSnapshot is quorum-verified chain state after sign.
type PostSignSnapshot struct {
	BalanceWei *big.Int
	Nonce      uint64
}

// PostSignDrift reports mismatch between signed intent and live quorum state.
func PostSignDrift(
	expectedNonce uint64,
	balanceBefore *big.Int,
	snap PostSignSnapshot,
) (drift bool, reasons []string) {
	if snap.Nonce != expectedNonce {
		drift = true
		reasons = append(reasons, "nonce_drift")
	}
	if balanceBefore != nil && snap.BalanceWei != nil && snap.BalanceWei.Cmp(balanceBefore) < 0 {
		drift = true
		reasons = append(reasons, "balance_drift")
	}
	return drift, reasons
}

// KillSwitch is a process-local emergency stop (env/file hook in agent main).
type KillSwitch struct {
	mu      sync.RWMutex
	engaged bool
	reason  string
}

// NewKillSwitch returns a disengaged kill switch.
func NewKillSwitch() *KillSwitch {
	return &KillSwitch{}
}

// Engage stops all signing until cleared.
func (k *KillSwitch) Engage(reason string) {
	k.mu.Lock()
	defer k.mu.Unlock()
	k.engaged = true
	k.reason = reason
}

// Clear releases the kill switch.
func (k *KillSwitch) Clear() {
	k.mu.Lock()
	defer k.mu.Unlock()
	k.engaged = false
	k.reason = ""
}

// Engaged reports whether signing must halt.
func (k *KillSwitch) Engaged() (bool, string) {
	k.mu.RLock()
	defer k.mu.RUnlock()
	return k.engaged, k.reason
}
