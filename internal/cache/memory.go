package cache

import (
	"sync"
	"time"
)

// CacheItem holds a cached value with an expiration timestamp.
type CacheItem struct {
	Value      interface{}
	ValidUntil time.Time
}

// MemoryCache is a thread-safe in-memory cache with TTL support.
type MemoryCache struct {
	mu    sync.RWMutex
	items map[string]CacheItem
}

// NewMemoryCache creates an empty MemoryCache.
func NewMemoryCache() *MemoryCache {
	return &MemoryCache{
		items: make(map[string]CacheItem),
	}
}

// Set stores a value under key with the given TTL.
func (c *MemoryCache) Set(key string, value interface{}, ttl time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.items[key] = CacheItem{
		Value:      value,
		ValidUntil: time.Now().Add(ttl),
	}
}

// Get returns the cached value if it exists and has not expired.
func (c *MemoryCache) Get(key string) (interface{}, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	item, ok := c.items[key]
	if !ok {
		return nil, false
	}

	if time.Now().After(item.ValidUntil) {
		return nil, false
	}

	return item.Value, true
}

// Delete removes a cache entry by key.
func (c *MemoryCache) Delete(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	delete(c.items, key)
}

// Destroy clears all cached entries.
func (c *MemoryCache) Destroy() {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.items = make(map[string]CacheItem)
}
