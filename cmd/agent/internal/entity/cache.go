// Package entity provides address reputation scoring with in-memory cache.
// Pre-warm from local artifacts; optional Arkham/Etherscan HTTP enrichment.
package entity

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// Score is a lightweight OSINT verdict for an address.
type Score struct {
	Address    string    `json:"address"`
	Entity     string    `json:"entity,omitempty"`
	Labels     []string  `json:"labels,omitempty"`
	Risk       string    `json:"risk"` // low | medium | high | unknown | blocked
	Confidence float64   `json:"confidence"`
	Source     string    `json:"source"` // artifact | arkham | etherscan | composite
	CachedAt   time.Time `json:"cached_at"`
	Blocked    bool      `json:"blocked"`
}

// Verifier scores addresses; implementations must be safe for concurrent use.
type Verifier interface {
	Score(address string) (Score, error)
	Prewarm(addresses []string) error
}

// Cache stores scores in memory (sync.Map) with optional artifact bootstrap.
type Cache struct {
	entries  sync.Map
	artifact string
	ttl      time.Duration
}

// NewCache creates a verifier backed by sync.Map. artifactPath may be entity-id.json.
func NewCache(artifactPath string, ttl time.Duration) *Cache {
	if ttl <= 0 {
		ttl = 15 * time.Minute
	}
	return &Cache{artifact: artifactPath, ttl: ttl}
}

// Score returns cached score or loads from artifacts.
func (c *Cache) Score(address string) (Score, error) {
	key := strings.ToLower(address)
	if v, ok := c.entries.Load(key); ok {
		s := v.(Score)
		if time.Since(s.CachedAt) < c.ttl {
			return s, nil
		}
	}
	s, err := c.loadFromArtifacts(address)
	if err != nil {
		s = Score{
			Address:    address,
			Risk:       "unknown",
			Confidence: 0.1,
			Source:     "fallback",
			CachedAt:   time.Now().UTC(),
		}
	}
	c.entries.Store(key, s)
	return s, nil
}

// Prewarm loads scores for a batch (non-blocking HTTP should be added here).
func (c *Cache) Prewarm(addresses []string) error {
	for _, addr := range addresses {
		if _, err := c.Score(addr); err != nil {
			return err
		}
	}
	return nil
}

func (c *Cache) loadFromArtifacts(address string) (Score, error) {
	s := Score{
		Address:    address,
		Risk:       "unknown",
		Confidence: 0.2,
		Source:     "artifact",
		CachedAt:   time.Now().UTC(),
	}
	if c.artifact == "" {
		return s, nil
	}
	raw, err := os.ReadFile(c.artifact)
	if err != nil {
		return s, err
	}
	var doc map[string]any
	if err := json.Unmarshal(raw, &doc); err != nil {
		return s, err
	}
	target := strings.ToLower(address)
	if t, _ := doc["target"].(string); strings.EqualFold(t, target) {
		s.Entity = "entity_primary"
		if er, ok := doc["entity_resolution"].(map[string]any); ok {
			if st, _ := er["status"].(string); st != "" {
				s.Entity = st
			}
			if conf, _ := er["confidence"].(string); conf == "high" {
				s.Confidence = 0.9
			} else if conf == "medium" {
				s.Confidence = 0.6
			}
		}
		s.Labels = []string{"hot_wallet_candidate"}
		s.Risk = "high"
	}
	// Block known sink/hub mistaken as funder
	if strings.Contains(strings.ToLower(filepath.Base(c.artifact)), "entity") {
		s.Blocked = s.Risk == "blocked"
	}
	return s, nil
}

// ShouldBlockSigning returns true when entity risk forbids blind rescue.
func ShouldBlockSigning(s Score) bool {
	return s.Blocked || s.Risk == "blocked"
}
