package monitor

import (
	"context"
	"fmt"
	"math/big"
	"strings"
	"time"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/ethclient"
)

// EthReceiptFetcher uses eth_getTransactionReceipt.
type EthReceiptFetcher struct {
	client *ethclient.Client
}

func NewEthReceiptFetcher(rpcURL string) (*EthReceiptFetcher, error) {
	c, err := ethclient.Dial(rpcURL)
	if err != nil {
		return nil, err
	}
	return &EthReceiptFetcher{client: c}, nil
}

func (f *EthReceiptFetcher) GetReceipt(ctx context.Context, txHash string) (*ReceiptResult, error) {
	hash := common.HexToHash(txHash)
	rcpt, err := f.client.TransactionReceipt(ctx, hash)
	if err != nil {
		return nil, err
	}
	if rcpt == nil {
		return nil, fmt.Errorf("monitor: nil receipt for %s", txHash)
	}
	status := rcpt.Status
	return &ReceiptResult{
		TxHash:      txHash,
		BlockNumber: rcpt.BlockNumber,
		Status:      status,
		Success:     status == ReceiptSuccess,
	}, nil
}

// Watcher polls receipts and releases dedup on revert/failure.
type Watcher struct {
	Fetcher      ReceiptFetcher
	Releaser     DedupReleaser
	PollInterval time.Duration
	Timeout      time.Duration
}

// Watch blocks until receipt is found or timeout; calls HandleReceipt on releaser.
func (w *Watcher) Watch(ctx context.Context, txHash, dedupKey string) (*ReceiptResult, error) {
	if w.Fetcher == nil {
		return nil, fmt.Errorf("monitor: nil fetcher")
	}
	if w.Releaser == nil {
		return nil, fmt.Errorf("monitor: nil releaser")
	}
	interval := w.PollInterval
	if interval <= 0 {
		interval = 500 * time.Millisecond
	}
	timeout := w.Timeout
	if timeout <= 0 {
		timeout = 30 * time.Second
	}
	deadline := time.Now().Add(timeout)
	txHash = strings.TrimSpace(txHash)

	for time.Now().Before(deadline) {
		rcpt, err := w.Fetcher.GetReceipt(ctx, txHash)
		if err == nil && rcpt != nil {
			_ = HandleReceipt(w.Releaser, dedupKey, rcpt)
			return rcpt, nil
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(interval):
		}
	}
	w.Releaser.ReleaseDedup(dedupKey)
	return nil, fmt.Errorf("monitor: receipt timeout for %s", txHash)
}

// ReceiptFromTypes converts geth receipt for tests.
func ReceiptFromTypes(rcpt *types.Receipt) *ReceiptResult {
	if rcpt == nil {
		return nil
	}
	return &ReceiptResult{
		TxHash:      rcpt.TxHash.Hex(),
		BlockNumber: new(big.Int).SetUint64(rcpt.BlockNumber.Uint64()),
		Status:      rcpt.Status,
		Success:     rcpt.Status == ReceiptSuccess,
	}
}
