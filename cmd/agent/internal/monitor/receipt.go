package monitor

import (
	"context"
	"fmt"
	"math/big"
)

// ReceiptStatus values from eth_getTransactionReceipt.status.
const (
	ReceiptSuccess = uint64(1)
	ReceiptFailed  = uint64(0)
)

// ReceiptResult is a normalized transaction receipt.
type ReceiptResult struct {
	TxHash      string
	BlockNumber *big.Int
	Status      uint64
	Success     bool
}

// ReceiptFetcher loads receipts from chain RPC.
type ReceiptFetcher interface {
	GetReceipt(ctx context.Context, txHash string) (*ReceiptResult, error)
}

// DedupReleaser clears rescue dedup keys on on-chain failure.
type DedupReleaser interface {
	ReleaseDedup(dedupKey string)
}

// HandleReceipt clears dedup when tx reverted or failed (status=0).
// Successful inclusion keeps dedup to prevent replay (#04).
func HandleReceipt(releaser DedupReleaser, dedupKey string, receipt *ReceiptResult) error {
	if releaser == nil {
		return fmt.Errorf("monitor: nil dedup releaser")
	}
	if receipt == nil {
		releaser.ReleaseDedup(dedupKey)
		return fmt.Errorf("monitor: nil receipt for %s", dedupKey)
	}
	if !receipt.Success || receipt.Status == ReceiptFailed {
		releaser.ReleaseDedup(dedupKey)
		return fmt.Errorf("monitor: tx %s reverted (status=%d) — dedup released", receipt.TxHash, receipt.Status)
	}
	return nil
}
