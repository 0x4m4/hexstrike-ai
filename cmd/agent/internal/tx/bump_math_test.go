package tx

import (
	"math/big"
	"testing"
)

func TestBumpMath_NoOverflow(t *testing.T) {
	prev := &FeeSuggestion{GasTipCap: big.NewInt(1), GasFeeCap: big.NewInt(1)}
	for _, bump := range []int{0, 15, 25} {
		if bump == 0 {
			continue
		}
		next := BumpFeeSuggestionStrict(prev, bump)
		if next.GasTipCap.Cmp(prev.GasTipCap) <= 0 {
			t.Fatalf("bump=%d tip %s not > %s", bump, next.GasTipCap, prev.GasTipCap)
		}
		if next.GasFeeCap.Cmp(prev.GasFeeCap) <= 0 {
			t.Fatalf("bump=%d feeCap %s not > %s", bump, next.GasFeeCap, prev.GasFeeCap)
		}
		prev = next
	}
}

func TestBumpMath_StrictlyGreater(t *testing.T) {
	prev := &FeeSuggestion{
		GasTipCap: big.NewInt(2_000_000_000),
		GasFeeCap: big.NewInt(62_000_000_000),
	}
	next := BumpFeeSuggestionStrict(prev, 15)
	minTip := new(big.Int).Mul(prev.GasTipCap, big.NewInt(115))
	minTip.Div(minTip, big.NewInt(100))
	if next.GasTipCap.Cmp(minTip) < 0 {
		t.Fatalf("tip %s < min %s", next.GasTipCap, minTip)
	}
	if next.GasTipCap.Cmp(prev.GasTipCap) <= 0 {
		t.Fatalf("tip must strictly increase")
	}
}

func TestBumpMath_IncrementalSteps(t *testing.T) {
	base := &FeeSuggestion{
		GasTipCap: big.NewInt(100),
		GasFeeCap: big.NewInt(1000),
	}
	step1 := BumpFeeSuggestionStrict(base, 15)   // +15%
	step2 := BumpFeeSuggestionStrict(step1, 25)  // +25% over step1, not base
	if step2.GasTipCap.Cmp(BumpFeeSuggestionStrict(base, 25).GasTipCap) <= 0 {
		t.Fatalf("incremental step2 tip=%s should exceed single +25%% from base", step2.GasTipCap)
	}
}

func TestEnsureReplacementFees(t *testing.T) {
	prev := &FeeSuggestion{GasTipCap: big.NewInt(100), GasFeeCap: big.NewInt(1000)}
	candidate := &FeeSuggestion{GasTipCap: big.NewInt(100), GasFeeCap: big.NewInt(1100)}
	out := EnsureReplacementFees(prev, candidate)
	if out.GasTipCap.Cmp(prev.GasTipCap) <= 0 {
		t.Fatalf("tip not bumped: %s", out.GasTipCap)
	}
}
