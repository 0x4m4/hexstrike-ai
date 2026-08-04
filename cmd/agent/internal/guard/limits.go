package guard

import "math/big"

// ExecutionStrategy classifies how the battle agent should handle a rescue event.
type ExecutionStrategy string

const (
	// StrategyAutoSign — balance/value within safe auto-sign envelope.
	StrategyAutoSign ExecutionStrategy = "AUTO_SIGN_CLEAR"
	// StrategyEscalate — high-value rescue; emit security.high_value_pending, no blind sign.
	StrategyEscalate ExecutionStrategy = "HIGH_VALUE_ESCALATION"
	// StrategyBlockNoGas — wallet cannot cover MIN_GAS; block signing.
	StrategyBlockNoGas ExecutionStrategy = "BLOCKED_LOW_BALANCE"
	// StrategyNoTrigger — wallet balance at/above THRESHOLD; no rescue needed (not a blind idle).
	StrategyNoTrigger ExecutionStrategy = "THRESHOLD_OK"
)

// RouteGuard encodes economic thresholds for rescue routing.
// Defaults align with scripts/sandbox/anvil.env (THRESHOLD=0.5 ETH, MIN_GAS=0.01 ETH).
type RouteGuard struct {
	AutoSignThreshold *big.Int // wallet balance below this triggers rescue watch
	MinGasWei         *big.Int // minimum native balance required to sign
	HighValueWei      *big.Int // rescue tx value above this requires escalation
}

// NewRouteGuard returns production-aligned defaults.
func NewRouteGuard() *RouteGuard {
	return &RouteGuard{
		MinGasWei:         big.NewInt(10_000_000_000_000_000),    // 0.01 ETH
		AutoSignThreshold: big.NewInt(500_000_000_000_000_000),   // 0.5 ETH
		HighValueWei:      big.NewInt(500_000_000_000_000_000),   // 0.5 ETH rescue → escalate
	}
}

// EvaluateBalance decides rescue trigger from monitored wallet balance (not tx value).
// balance >= AutoSignThreshold → THRESHOLD_OK (healthy, no rescue).
// balance < AutoSignThreshold && balance >= MinGas → AUTO_SIGN_CLEAR.
// balance < MinGas → BLOCKED_LOW_BALANCE.
func (rg *RouteGuard) EvaluateBalance(balance *big.Int) ExecutionStrategy {
	if balance == nil {
		return StrategyBlockNoGas
	}
	if balance.Cmp(rg.MinGasWei) < 0 {
		return StrategyBlockNoGas
	}
	if balance.Cmp(rg.AutoSignThreshold) >= 0 {
		return StrategyNoTrigger
	}
	return StrategyAutoSign
}

// EvaluateRescueValue applies high-value policy to the outbound rescue native transfer.
// Values above HighValueWei must escalate (multi-sig/KMS/whitelist), not auto-sign.
func (rg *RouteGuard) EvaluateRescueValue(rescueValue *big.Int) ExecutionStrategy {
	if rescueValue == nil || rescueValue.Sign() <= 0 {
		return StrategyAutoSign
	}
	if rescueValue.Cmp(rg.HighValueWei) > 0 {
		return StrategyEscalate
	}
	return StrategyAutoSign
}

// EvaluateCombined merges balance trigger with rescue value policy.
// Escalation wins over auto-sign; block-no-gas wins over everything.
func (rg *RouteGuard) EvaluateCombined(balance, rescueValue *big.Int) ExecutionStrategy {
	bal := rg.EvaluateBalance(balance)
	if bal == StrategyBlockNoGas || bal == StrategyNoTrigger {
		return bal
	}
	if rg.EvaluateRescueValue(rescueValue) == StrategyEscalate {
		return StrategyEscalate
	}
	return StrategyAutoSign
}

// TopicHighValuePending is the event bus topic for KMS/multi-sig handoff.
const TopicHighValuePending = "security.high_value_pending"
