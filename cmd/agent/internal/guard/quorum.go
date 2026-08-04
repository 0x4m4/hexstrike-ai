package guard

import (
	"context"
	"fmt"
	"math/big"
	"sync"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/ethclient"
)

// QuorumSource is the fail-closed truth interface for balance/nonce reads.
type QuorumSource interface {
	BalanceQuorum(ctx context.Context, addr common.Address) (*big.Int, error)
	NonceQuorum(ctx context.Context, addr common.Address) (uint64, error)
}

// QuorumReader fetches balance/nonce from multiple RPC endpoints.
type QuorumReader struct {
	URLs     []string
	MinAgree int
}

// BalanceQuorum returns balance when >= MinAgree endpoints agree.
func (q *QuorumReader) BalanceQuorum(ctx context.Context, addr common.Address) (*big.Int, error) {
	if len(q.URLs) == 0 {
		return nil, fmt.Errorf("quorum: no RPC URLs")
	}
	need := q.MinAgree
	if need < 1 {
		need = 2
	}
	if need > len(q.URLs) {
		need = len(q.URLs)
	}

	type result struct {
		val *big.Int
		err error
	}
	ch := make(chan result, len(q.URLs))
	var wg sync.WaitGroup
	for _, url := range q.URLs {
		wg.Add(1)
		go func(u string) {
			defer wg.Done()
			client, err := ethclient.DialContext(ctx, u)
			if err != nil {
				ch <- result{err: err}
				return
			}
			defer client.Close()
			bal, err := client.BalanceAt(ctx, addr, nil)
			ch <- result{val: bal, err: err}
		}(url)
	}
	wg.Wait()
	close(ch)

	counts := make(map[string]int)
	values := make(map[string]*big.Int)
	for r := range ch {
		if r.err != nil || r.val == nil {
			continue
		}
		key := r.val.String()
		counts[key]++
		values[key] = r.val
	}
	for key, cnt := range counts {
		if cnt >= need {
			return new(big.Int).Set(values[key]), nil
		}
	}
	return nil, fmt.Errorf("quorum: balance agreement not reached (%d/%d)", 0, need)
}

// NonceQuorum returns pending nonce when >= MinAgree endpoints agree.
func (q *QuorumReader) NonceQuorum(ctx context.Context, addr common.Address) (uint64, error) {
	if len(q.URLs) == 0 {
		return 0, fmt.Errorf("quorum: no RPC URLs")
	}
	need := q.MinAgree
	if need < 1 {
		need = 2
	}
	if need > len(q.URLs) {
		need = len(q.URLs)
	}

	type result struct {
		val uint64
		err error
	}
	ch := make(chan result, len(q.URLs))
	var wg sync.WaitGroup
	for _, url := range q.URLs {
		wg.Add(1)
		go func(u string) {
			defer wg.Done()
			client, err := ethclient.DialContext(ctx, u)
			if err != nil {
				ch <- result{err: err}
				return
			}
			defer client.Close()
			n, err := client.PendingNonceAt(ctx, addr)
			ch <- result{val: n, err: err}
		}(url)
	}
	wg.Wait()
	close(ch)

	counts := make(map[uint64]int)
	for r := range ch {
		if r.err != nil {
			continue
		}
		counts[r.val]++
	}
	for val, cnt := range counts {
		if cnt >= need {
			return val, nil
		}
	}
	return 0, fmt.Errorf("quorum: nonce agreement not reached")
}
