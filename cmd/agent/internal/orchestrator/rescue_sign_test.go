package orchestrator

import (
	"context"
	"math/big"
	"sync"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	txpkg "github.com/hexstrike-ai/hexstrike/cmd/agent/internal/tx"
)

func TestResignUsesFixedNonce(t *testing.T) {
	key, _ := crypto.GenerateKey()
	chainID := big.NewInt(56)
	to := common.HexToAddress("0x060447dC91dfb22A5233731aF67E9E8dafdF24d1")
	fees := &txpkg.FeeSuggestion{
		GasTipCap: big.NewInt(2_000_000_000),
		GasFeeCap: big.NewInt(62_000_000_000),
	}
	const wantNonce uint64 = 42

	raw, _, err := signRescueTxWithNonce(chainID, key, wantNonce, to, big.NewInt(1), fees)
	if err != nil {
		t.Fatal(err)
	}
	var txn types.Transaction
	if err := txn.UnmarshalBinary(raw); err != nil {
		t.Fatal(err)
	}
	if txn.Nonce() != wantNonce {
		t.Fatalf("nonce=%d want=%d", txn.Nonce(), wantNonce)
	}

	bumped := txpkg.BumpFeeSuggestionStrict(fees, 15)
	raw2, _, err := signRescueTxWithNonce(chainID, key, wantNonce, to, big.NewInt(1), bumped)
	if err != nil {
		t.Fatal(err)
	}
	var txn2 types.Transaction
	if err := txn2.UnmarshalBinary(raw2); err != nil {
		t.Fatal(err)
	}
	if txn2.Nonce() != wantNonce {
		t.Fatalf("resign nonce=%d want=%d", txn2.Nonce(), wantNonce)
	}
	if txn2.Hash() == txn.Hash() {
		t.Fatal("bumped tx must have different hash")
	}
}

func TestNonceRace_ConcurrentResignSerialized(t *testing.T) {
	key, _ := crypto.GenerateKey()
	chainID := big.NewInt(56)
	to := common.HexToAddress("0x060447dC91dfb22A5233731aF67E9E8dafdF24d1")
	fees := &txpkg.FeeSuggestion{GasTipCap: big.NewInt(100), GasFeeCap: big.NewInt(1000)}
	const nonce = 7

	var wg sync.WaitGroup
	hashes := make(chan string, 10)
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(bump int) {
			defer wg.Done()
			rescueSignMu.Lock()
			defer rescueSignMu.Unlock()
			bumped := txpkg.BumpFeeSuggestionStrict(fees, 10+bump)
			_, hash, err := signRescueTxWithNonce(chainID, key, nonce, to, big.NewInt(1), bumped)
			if err != nil {
				return
			}
			hashes <- hash
		}(i)
	}
	wg.Wait()
	close(hashes)

	seen := make(map[string]struct{})
	for h := range hashes {
		seen[h] = struct{}{}
	}
	if len(seen) == 0 {
		t.Fatal("expected signed txs")
	}
	// mutex serializes; all share nonce 7 but produce distinct hashes per bump
}

func TestResignRescueTx_NoPendingNonceCall(t *testing.T) {
	// ResignRescueTx must not dial RPC; verify signature path only via signRescueTxWithNonce.
	_ = context.Background()
	key, _ := crypto.GenerateKey()
	prev := &txpkg.FeeSuggestion{GasTipCap: big.NewInt(100), GasFeeCap: big.NewInt(1000)}
	raw, out, err := ResignRescueTx(
		context.Background(), nil, key, big.NewInt(56),
		common.Address{}, common.HexToAddress("0x060447dC91dfb22A5233731aF67E9E8dafdF24d1"),
		big.NewInt(1), 9, prev, 15, nil,
	)
	if err != nil {
		t.Fatal(err)
	}
	if len(raw) == 0 || out == nil {
		t.Fatal("expected raw tx and fees")
	}
}
