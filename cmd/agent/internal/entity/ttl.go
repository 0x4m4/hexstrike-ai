package entity

import (
	"os"
	"strconv"
	"time"
)

// DefaultCacheTTL is how long safe-address scores remain valid before API refresh.
const DefaultCacheTTL = 15 * time.Minute

// BlockedCacheTTL — blocked entries are re-verified sooner (still fail-closed until API clears).
const BlockedCacheTTL = 10 * time.Minute

// ResolveCacheTTL reads ENTITY_CACHE_TTL_MINUTES (default 15).
func ResolveCacheTTL() time.Duration {
	raw := os.Getenv("ENTITY_CACHE_TTL_MINUTES")
	if raw == "" {
		return DefaultCacheTTL
	}
	m, err := strconv.Atoi(raw)
	if err != nil || m <= 0 {
		return DefaultCacheTTL
	}
	return time.Duration(m) * time.Minute
}

func stampMeta(meta EntityMetadata, ttl time.Duration) EntityMetadata {
	now := time.Now().UTC()
	meta.LastChecked = now
	if !meta.IsSafe {
		meta.ValidUntil = now.Add(BlockedCacheTTL)
		return meta
	}
	if ttl <= 0 {
		ttl = DefaultCacheTTL
	}
	meta.ValidUntil = now.Add(ttl)
	return meta
}

func metaExpired(meta EntityMetadata) bool {
	if meta.ValidUntil.IsZero() {
		return true
	}
	return time.Now().UTC().After(meta.ValidUntil)
}
