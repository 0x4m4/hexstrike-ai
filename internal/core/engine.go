package core

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	"hexstrike-osint-agent/internal/cache"
	"hexstrike-osint-agent/internal/providers"
)

const cacheTTL = 10 * time.Minute

// OsintEngine orchestrates OSINT collection across providers with TTL caching.
type OsintEngine struct {
	Cache    *cache.MemoryCache
	Arkham   *providers.ArkhamProvider
	GetBlock *providers.GetBlockProvider
	Network  *providers.NetworkProvider
}

// NewOsintEngine wires cache and providers into a ready-to-run engine.
func NewOsintEngine(
	memCache *cache.MemoryCache,
	arkham *providers.ArkhamProvider,
	getblock *providers.GetBlockProvider,
	network *providers.NetworkProvider,
) *OsintEngine {
	return &OsintEngine{
		Cache:    memCache,
		Arkham:   arkham,
		GetBlock: getblock,
		Network:  network,
	}
}

// MonitorTarget runs a background refresh loop for a single target until ctx is cancelled.
func (e *OsintEngine) MonitorTarget(ctx context.Context, target string, targetType string, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	e.refreshTarget(ctx, target, targetType)

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			e.refreshTarget(ctx, target, targetType)
		}
	}
}

func (e *OsintEngine) refreshTarget(ctx context.Context, target string, targetType string) {
	if ctx.Err() != nil {
		return
	}

	cacheKey := fmt.Sprintf("%s:%s", strings.ToLower(targetType), target)

	if _, ok := e.Cache.Get(cacheKey); ok {
		return
	}

	switch strings.ToLower(targetType) {
	case "wallet":
		e.refreshWallet(ctx, target, targetType, cacheKey)
	case "ip":
		e.refreshIP(ctx, target, targetType, cacheKey)
	default:
		log.Printf("[OSINT-ENGINE] [%s] Unknown target type for %s", strings.ToUpper(targetType), target)
	}
}

func (e *OsintEngine) refreshWallet(ctx context.Context, target, targetType, cacheKey string) {
	arkhamSafe, arkhamReason, err := e.Arkham.AnalyzeAddress(ctx, target)
	if err != nil {
		log.Printf("[OSINT-ENGINE] [%s] Arkham refresh failed: %s error: %v", strings.ToUpper(targetType), target, err)
		return
	}

	getblockSafe, getblockReason, err := e.GetBlock.AnalyzeAddress(ctx, target)
	if err != nil {
		log.Printf("[OSINT-ENGINE] [%s] GetBlock refresh failed: %s error: %v", strings.ToUpper(targetType), target, err)
		return
	}

	isSafe := arkhamSafe && getblockSafe
	status := fmt.Sprintf(
		"safe=%t arkham=%s getblock=%s",
		isSafe,
		formatProviderVerdict(arkhamSafe, arkhamReason),
		formatProviderVerdict(getblockSafe, getblockReason),
	)

	e.Cache.Set(cacheKey, status, cacheTTL)
	log.Printf("[OSINT-ENGINE] [%s] Target refreshed: %s status: %s", strings.ToUpper(targetType), target, status)
}

func formatProviderVerdict(isSafe bool, reason string) string {
	if isSafe {
		return "clean(" + reason + ")"
	}
	return "unsafe(" + reason + ")"
}

func (e *OsintEngine) refreshIP(ctx context.Context, target, targetType, cacheKey string) {
	isSafe, reason, err := e.Network.AnalyzeIP(ctx, target)
	if err != nil {
		log.Printf("[OSINT-ENGINE] [%s] Target refresh failed: %s error: %v", strings.ToUpper(targetType), target, err)
		return
	}

	status := fmt.Sprintf("safe=%t reason=%s", isSafe, reason)
	e.Cache.Set(cacheKey, status, cacheTTL)
	log.Printf("[OSINT-ENGINE] [%s] Target refreshed: %s status: %s", strings.ToUpper(targetType), target, status)
}
