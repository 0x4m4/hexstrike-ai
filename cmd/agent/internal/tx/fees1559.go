package tx

import (
	"context"
	"math/big"

	"github.com/ethereum/go-ethereum/ethclient"
)

// FeeSuggestion holds EIP-1559 fee envelope.
type FeeSuggestion struct {
	GasFeeCap *big.Int
	GasTipCap *big.Int
}

// FeeCalculator suggests dynamic fees from an RPC client.
type FeeCalculator struct {
	client     *ethclient.Client
	tipPercent int // e.g. 120 = +20%
}

// NewFeeCalculator wraps an ethclient. tipPercent defaults to 120 (+20%).
func NewFeeCalculator(client *ethclient.Client, tipPercent int) *FeeCalculator {
	if tipPercent <= 0 {
		tipPercent = 120
	}
	return &FeeCalculator{client: client, tipPercent: tipPercent}
}

// SuggestAggressiveFees returns EIP-1559 caps with aggressive tip offset.
func (fc *FeeCalculator) SuggestAggressiveFees(ctx context.Context) (*FeeSuggestion, error) {
	tip, err := fc.client.SuggestGasTipCap(ctx)
	if err != nil {
		return nil, err
	}
	header, err := fc.client.HeaderByNumber(ctx, nil)
	if err != nil {
		return nil, err
	}
	baseFee := header.BaseFee
	if baseFee == nil {
		baseFee = big.NewInt(0)
	}
	return CalculateAggressiveFees(baseFee, tip, fc.tipPercent), nil
}

// CalculateAggressiveFees is pure math for tests and offline estimation.
// feeCap = baseFee*2 + aggressiveTip; aggressiveTip = tip * tipPercent / 100.
func CalculateAggressiveFees(baseFee, tip *big.Int, tipPercent int) *FeeSuggestion {
	if tipPercent <= 0 {
		tipPercent = 120
	}
	if baseFee == nil {
		baseFee = big.NewInt(0)
	}
	if tip == nil {
		tip = big.NewInt(0)
	}
	aggressiveTip := new(big.Int).Mul(tip, big.NewInt(int64(tipPercent)))
	aggressiveTip.Div(aggressiveTip, big.NewInt(100))
	feeCap := new(big.Int).Mul(baseFee, big.NewInt(2))
	feeCap.Add(feeCap, aggressiveTip)
	return &FeeSuggestion{GasFeeCap: feeCap, GasTipCap: aggressiveTip}
}

// MinReplacementBumpPct is the minimum fee increase BSC nodes expect for tx replacement.
const MinReplacementBumpPct = 10

// BumpFeeSuggestionStrict scales prev fees by (100+bumpPct)/100, rounding up so caps strictly increase.
// bumpPct below MinReplacementBumpPct is clamped (BSC replacement rule).
func BumpFeeSuggestionStrict(prev *FeeSuggestion, bumpPct int) *FeeSuggestion {
	if prev == nil {
		return &FeeSuggestion{GasFeeCap: big.NewInt(1), GasTipCap: big.NewInt(1)}
	}
	if bumpPct < MinReplacementBumpPct {
		bumpPct = MinReplacementBumpPct
	}
	mul := big.NewInt(int64(100 + bumpPct))
	scale := func(v *big.Int) *big.Int {
		if v == nil || v.Sign() <= 0 {
			return big.NewInt(1)
		}
		out := new(big.Int).Mul(v, mul)
		out.Div(out, big.NewInt(100))
		min := new(big.Int).Add(v, big.NewInt(1))
		if out.Cmp(min) <= 0 {
			return min
		}
		return out
	}
	return &FeeSuggestion{GasFeeCap: scale(prev.GasFeeCap), GasTipCap: scale(prev.GasTipCap)}
}

// EnsureReplacementFees returns candidate fees that are strictly greater than prev on both caps.
func EnsureReplacementFees(prev, candidate *FeeSuggestion) *FeeSuggestion {
	if prev == nil || candidate == nil {
		return candidate
	}
	bumpOne := func(v *big.Int) *big.Int {
		if v == nil {
			return big.NewInt(1)
		}
		return new(big.Int).Add(v, big.NewInt(1))
	}
	out := &FeeSuggestion{
		GasFeeCap: new(big.Int).Set(candidate.GasFeeCap),
		GasTipCap: new(big.Int).Set(candidate.GasTipCap),
	}
	if out.GasFeeCap.Cmp(prev.GasFeeCap) <= 0 {
		out.GasFeeCap = bumpOne(prev.GasFeeCap)
	}
	if out.GasTipCap.Cmp(prev.GasTipCap) <= 0 {
		out.GasTipCap = bumpOne(prev.GasTipCap)
	}
	return out
}

// BumpFeeSuggestion scales both caps by (100+bumpPct)/100 for relay gas escalation.
// Deprecated: use BumpFeeSuggestionStrict for mempool replacements.
func BumpFeeSuggestion(base *FeeSuggestion, bumpPct int) *FeeSuggestion {
	return BumpFeeSuggestionStrict(base, bumpPct)
}
