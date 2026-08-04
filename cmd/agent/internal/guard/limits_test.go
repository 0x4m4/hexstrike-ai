package guard

import (
	"math/big"
	"testing"
)

func eth(whole string) *big.Int {
	v, ok := new(big.Int).SetString(whole, 10)
	if !ok {
		panic("bad test literal")
	}
	return v
}

func TestEvaluateBalance(t *testing.T) {
	rg := NewRouteGuard()
	cases := []struct {
		name string
		wei  *big.Int
		want ExecutionStrategy
	}{
		{"micro_no_gas", eth("1000000000000000"), StrategyBlockNoGas},           // 0.001 ETH
		{"min_gas_edge", eth("10000000000000000"), StrategyAutoSign},            // 0.01 ETH
		{"small_trigger", eth("300000000000000000"), StrategyAutoSign},          // 0.3 ETH
		{"boundary_below", eth("499000000000000000"), StrategyAutoSign},        // 0.499 ETH
		{"boundary_at", eth("500000000000000000"), StrategyNoTrigger},          // 0.5 ETH
		{"boundary_above", eth("501000000000000000"), StrategyNoTrigger},        // 0.501 ETH
		{"large_idle", eth("10000000000000000000"), StrategyNoTrigger},         // 10 ETH
		{"large_max", eth("100000000000000000000"), StrategyNoTrigger},         // 100 ETH
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := rg.EvaluateBalance(tc.wei); got != tc.want {
				t.Fatalf("EvaluateBalance(%s) = %s, want %s", tc.name, got, tc.want)
			}
		})
	}
}

func TestEvaluateRescueValue(t *testing.T) {
	rg := NewRouteGuard()
	if got := rg.EvaluateRescueValue(eth("400000000000000000")); got != StrategyAutoSign {
		t.Fatalf("0.4 ETH rescue: got %s", got)
	}
	if got := rg.EvaluateRescueValue(eth("1000000000000000000")); got != StrategyEscalate {
		t.Fatalf("1 ETH rescue: got %s, want ESCALATE", got)
	}
}

func TestEvaluateCombined(t *testing.T) {
	rg := NewRouteGuard()
	// Low balance + small rescue → auto
	if got := rg.EvaluateCombined(eth("300000000000000000"), eth("1000000000000000")); got != StrategyAutoSign {
		t.Fatalf("combined small: %s", got)
	}
	// Low balance + high rescue → escalate
	if got := rg.EvaluateCombined(eth("300000000000000000"), eth("600000000000000000")); got != StrategyEscalate {
		t.Fatalf("combined escalate: %s", got)
	}
	// Healthy balance → no trigger even if rescue value high
	if got := rg.EvaluateCombined(eth("10000000000000000000"), eth("600000000000000000")); got != StrategyNoTrigger {
		t.Fatalf("healthy balance: %s", got)
	}
}
