package orchestrator

import (
	"context"
	"math/big"
	"testing"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/guard"
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/signer"
	txpkg "github.com/hexstrike-ai/hexstrike/cmd/agent/internal/tx"
)

type stubQuorum struct {
	bal   *big.Int
	nonce uint64
}

func (s stubQuorum) BalanceQuorum(context.Context, common.Address) (*big.Int, error) {
	return new(big.Int).Set(s.bal), nil
}
func (s stubQuorum) NonceQuorum(context.Context, common.Address) (uint64, error) {
	return s.nonce, nil
}

func TestSecureSignRescue_TOCTOUHappyPath(t *testing.T) {
	key, _ := crypto.GenerateKey()
	local, err := signer.NewLocalKeySigner(common.Bytes2Hex(crypto.FromECDSA(key)))
	if err != nil {
		t.Fatal(err)
	}
	ks := guard.NewKillSwitch()
	eng, err := NewEngine(Config{
		AllowedFunders: []string{"0x730ea0231808f42a20f8921ba7fbc788226768f5"},
		KillSwitch:     ks,
		Phase:          signer.PhaseLab,
	})
	if err != nil {
		t.Fatal(err)
	}
	eng.quorum = stubQuorum{bal: big.NewInt(300_000_000_000_000_000), nonce: 7}
	eng.requireRemoteSigner = false
	eng.requireQuorum = true

	to := common.HexToAddress("0x730ea0231808f42a20f8921ba7fbc788226768f5")
	fees := &txpkg.FeeSuggestion{GasTipCap: big.NewInt(1), GasFeeCap: big.NewInt(2)}
	out, err := eng.SecureSignRescue(context.Background(), nil, local, big.NewInt(31337), to, big.NewInt(1), fees)
	if err != nil {
		t.Fatal(err)
	}
	if out.Nonce != 7 || out.IntentHash == "" || len(out.Raw) == 0 {
		t.Fatalf("unexpected out: %+v", out)
	}
	// duplicate intent must fail
	_, err = eng.SecureSignRescue(context.Background(), nil, local, big.NewInt(31337), to, big.NewInt(1), fees)
	if err == nil {
		t.Fatal("duplicate intent must be blocked")
	}
}

func TestSecureSignRescue_PostSignDriftDropsTx(t *testing.T) {
	key, _ := crypto.GenerateKey()
	local, _ := signer.NewLocalKeySigner(common.Bytes2Hex(crypto.FromECDSA(key)))
	eng, err := NewEngine(Config{
		AllowedFunders: []string{"0x730ea0231808f42a20f8921ba7fbc788226768f5"},
		Phase:          signer.PhaseLab,
	})
	if err != nil {
		t.Fatal(err)
	}
	// nonce drifts between pre-sign read and post-sign recheck
	q := &driftQuorum{bal: big.NewInt(1e18), nonce: 3}
	eng.quorum = q
	eng.requireQuorum = true

	to := common.HexToAddress("0x730ea0231808f42a20f8921ba7fbc788226768f5")
	fees := &txpkg.FeeSuggestion{GasTipCap: big.NewInt(1), GasFeeCap: big.NewInt(2)}
	_, err = eng.SecureSignRescue(context.Background(), nil, local, big.NewInt(31337), to, big.NewInt(1), fees)
	if err == nil {
		t.Fatal("expected post-sign drift drop")
	}
	if on, _ := eng.killSwitch.Engaged(); !on {
		t.Fatal("critical alert must engage kill switch")
	}
}

type driftQuorum struct {
	bal   *big.Int
	nonce uint64
	calls int
}

func (d *driftQuorum) BalanceQuorum(context.Context, common.Address) (*big.Int, error) {
	return new(big.Int).Set(d.bal), nil
}
func (d *driftQuorum) NonceQuorum(context.Context, common.Address) (uint64, error) {
	d.calls++
	if d.calls >= 2 {
		return d.nonce + 1, nil // drift on post-sign
	}
	return d.nonce, nil
}

func TestSecureSignRescue_LocalKeyForbiddenInCanary(t *testing.T) {
	key, _ := crypto.GenerateKey()
	local, _ := signer.NewLocalKeySigner(common.Bytes2Hex(crypto.FromECDSA(key)))
	_, err := NewEngine(Config{
		Phase:         signer.PhaseCanary,
		AllowedFunders: []string{"0x730ea0231808f42a20f8921ba7fbc788226768f5"},
		QuorumRPCURLs: []string{"http://a", "http://b", "http://c"},
		QuorumMinAgree: 2,
		MaxRescueValueWei: big.NewInt(1e15),
	})
	if err != nil {
		t.Fatal(err)
	}
	eng, _ := NewEngine(Config{
		Phase:          signer.PhaseLab,
		AllowedFunders: []string{"0x730ea0231808f42a20f8921ba7fbc788226768f5"},
	})
	eng.requireRemoteSigner = true
	eng.quorum = stubQuorum{bal: big.NewInt(1e18), nonce: 1}
	fees := &txpkg.FeeSuggestion{GasTipCap: big.NewInt(1), GasFeeCap: big.NewInt(2)}
	_, err = eng.SecureSignRescue(context.Background(), nil, local, big.NewInt(1), common.HexToAddress("0x730ea0231808f42a20f8921ba7fbc788226768f5"), big.NewInt(1), fees)
	if err == nil {
		t.Fatal("local key must be rejected when requireRemoteSigner")
	}
}

func TestSecureSignRescue_KMSPath(t *testing.T) {
	key, _ := crypto.GenerateKey()
	addr := crypto.PubkeyToAddress(key.PublicKey)
	remote, err := signer.NewRemoteSigner(addr, signer.BackendKMS, func(ctx context.Context, tx *types.Transaction, chainID *big.Int) (*types.Transaction, error) {
		return types.SignTx(tx, types.NewLondonSigner(chainID), key)
	})
	if err != nil {
		t.Fatal(err)
	}
	eng, err := NewEngine(Config{
		Phase:               signer.PhaseCanary,
		RequireRemoteSigner: true,
		RequireQuorum:       true,
		AllowedFunders:      []string{"0x730ea0231808f42a20f8921ba7fbc788226768f5"},
		QuorumRPCURLs:       []string{"http://a", "http://b", "http://c"},
		QuorumMinAgree:      2,
		MaxRescueValueWei:   big.NewInt(1e15),
	})
	if err != nil {
		t.Fatal(err)
	}
	// Override dialing quorum with stub for unit test
	eng.quorum = stubQuorum{bal: big.NewInt(1e18), nonce: 2}
	eng.requireRemoteSigner = true
	fees := &txpkg.FeeSuggestion{GasTipCap: big.NewInt(1), GasFeeCap: big.NewInt(2)}
	out, err := eng.SecureSignRescue(context.Background(), nil, remote, big.NewInt(56), common.HexToAddress("0x730ea0231808f42a20f8921ba7fbc788226768f5"), big.NewInt(1), fees)
	if err != nil {
		t.Fatal(err)
	}
	if remote.Backend() != signer.BackendKMS || out.Hash == "" {
		t.Fatal("kms path failed")
	}
}

func TestPrepareRescue_ValueCapAutoKill(t *testing.T) {
	eng, err := NewEngine(Config{
		Phase:             signer.PhaseLab,
		AllowedFunders:    []string{"0x730ea0231808f42a20f8921ba7fbc788226768f5"},
		MaxRescueValueWei: big.NewInt(1000),
	})
	if err != nil {
		t.Fatal(err)
	}
	_, err = eng.PrepareRescue(context.Background(), RescueRequest{
		BotAddress:    "0x4943",
		FunderAddress: "0x730ea0231808f42a20f8921ba7fbc788226768f5",
		BalanceWei:    big.NewInt(300_000_000_000_000_000),
		RescueValue:   big.NewInt(5000),
		DryRun:        true,
	})
	if err == nil {
		t.Fatal("value cap must block")
	}
	if on, _ := eng.killSwitch.Engaged(); !on {
		t.Fatal("value cap must auto-engage kill switch")
	}
}

func TestVerifyPostSign_FailClosedNoQuorum(t *testing.T) {
	eng, err := NewEngine(Config{Phase: signer.PhaseLab})
	if err != nil {
		t.Fatal(err)
	}
	err = eng.VerifyPostSign(context.Background(), "0xabc", 1, big.NewInt(1), "ih", 56)
	if err == nil {
		t.Fatal("must fail closed without quorum")
	}
}

var _ guard.QuorumSource = stubQuorum{}
