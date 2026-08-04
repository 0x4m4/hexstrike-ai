package entity

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

// EntityMetadata is the in-memory reputation record for an address.
type EntityMetadata struct {
	Name        string    `json:"name"`
	IsSafe      bool      `json:"is_safe"`
	Tags        []string  `json:"tags"`
	LastChecked time.Time `json:"last_checked,omitempty"`
	ValidUntil  time.Time `json:"valid_until,omitempty"`
}

// EntityGate combines 0ms sync.Map cache with optional Arkham/OSINT HTTP scoring.
type EntityGate struct {
	cache         sync.Map
	client        *http.Client
	apiKey        string
	bootstrapPath string
	failClosed    bool
	cacheTTL      time.Duration
}

// GateOption configures EntityGate behavior.
type GateOption func(*EntityGate)

// WithFailClosed blocks signing when external API is unavailable (battle mode).
func WithFailClosed(on bool) GateOption {
	return func(eg *EntityGate) { eg.failClosed = on }
}

// WithCacheTTL sets safe-address TTL (default 15m, env ENTITY_CACHE_TTL_MINUTES).
func WithCacheTTL(d time.Duration) GateOption {
	return func(eg *EntityGate) { eg.cacheTTL = d }
}

// NewEntityGate creates a gate. bootstrapPath may be entity-gate-bootstrap.json or entity-id.json.
func NewEntityGate(apiKey, bootstrapPath string, opts ...GateOption) *EntityGate {
	eg := &EntityGate{
		client:        &http.Client{Timeout: 2 * time.Second},
		apiKey:        apiKey,
		bootstrapPath: bootstrapPath,
		cacheTTL:      ResolveCacheTTL(),
	}
	for _, o := range opts {
		o(eg)
	}
	return eg
}

// Prewarm loads known addresses from local JSON (0 ms hot-path after boot).
func (eg *EntityGate) Prewarm() error {
	if eg.bootstrapPath == "" {
		return nil
	}
	raw, err := os.ReadFile(eg.bootstrapPath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return err
	}
	var generic map[string]json.RawMessage
	if err := json.Unmarshal(raw, &generic); err == nil && len(generic) > 0 {
		allAddr := true
		for k := range generic {
			if !strings.HasPrefix(k, "0x") || len(k) != 42 {
				allAddr = false
				break
			}
		}
		if allAddr {
			for addr, blob := range generic {
				var meta EntityMetadata
				if err := json.Unmarshal(blob, &meta); err != nil {
					continue
				}
				meta.LastChecked = time.Now().UTC()
				meta = stampMeta(meta, eg.cacheTTL)
				eg.cache.Store(normalizeAddr(addr), meta)
			}
			return nil
		}
	}
	return eg.ingestEntityID(raw)
}

func (eg *EntityGate) ingestEntityID(raw []byte) error {
	var doc map[string]any
	if err := json.Unmarshal(raw, &doc); err != nil {
		return err
	}
	if target, _ := doc["target"].(string); target != "" {
		meta := EntityMetadata{
			Name:        "hot_wallet_target",
			IsSafe:      true,
			Tags:        []string{"monitored", "high_activity"},
		}
		eg.cache.Store(normalizeAddr(target), stampMeta(meta, eg.cacheTTL))
	}
	if er, ok := doc["entity_resolution"].(map[string]any); ok {
		if tags, _ := er["blocklist_tags"].([]any); len(tags) > 0 {
			for _, t := range tags {
				if s, ok := t.(string); ok && strings.EqualFold(s, "COMPROMISED") {
					if target, _ := doc["target"].(string); target != "" {
						eg.cache.Store(normalizeAddr(target), stampMeta(EntityMetadata{
							Name: "COMPROMISED", IsSafe: false, Tags: []string{"COMPROMISED"},
						}, eg.cacheTTL))
					}
				}
			}
		}
	}
	return nil
}

// VerifyAddress checks cache first (with TTL), then optional Arkham/OSINT API.
func (eg *EntityGate) VerifyAddress(ctx context.Context, address string) (bool, error) {
	key := normalizeAddr(address)
	if val, ok := eg.cache.Load(key); ok {
		meta := val.(EntityMetadata)
		if !metaExpired(meta) {
			return eg.evaluateMeta(address, meta)
		}
		// TTL expired — refresh if API key present
		if eg.apiKey != "" {
			refreshed, err := eg.fetchFromAPI(ctx, address)
			if err != nil {
				if eg.failClosed {
					return false, fmt.Errorf("ENTITY_GATE: TTL refresh failed for %s: %w", address, err)
				}
				return eg.evaluateMeta(address, meta)
			}
			refreshed = stampMeta(refreshed, eg.cacheTTL)
			eg.cache.Store(key, refreshed)
			return eg.evaluateMeta(address, refreshed)
		}
		return eg.evaluateMeta(address, meta)
	}
	if eg.apiKey == "" {
		return true, nil
	}
	meta, err := eg.fetchFromAPI(ctx, address)
	if err != nil {
		if eg.failClosed {
			return false, fmt.Errorf("ENTITY_GATE: external scoring failed for %s: %w", address, err)
		}
		return true, nil
	}
	meta = stampMeta(meta, eg.cacheTTL)
	eg.cache.Store(key, meta)
	return eg.evaluateMeta(address, meta)
}

func (eg *EntityGate) evaluateMeta(address string, meta EntityMetadata) (bool, error) {
	if !meta.IsSafe {
		return false, fmt.Errorf("ENTITY_GATE: address %s blocked by local policy (%s)", address, meta.Name)
	}
	for _, tag := range meta.Tags {
		if strings.EqualFold(tag, "BLOCKED") || strings.EqualFold(tag, "COMPROMISED") {
			return false, fmt.Errorf("ENTITY_GATE: address %s tagged %s", address, tag)
		}
	}
	return true, nil
}

// IsDenied reports whether address is blocked in cache (bootstrap/runtime).
func (eg *EntityGate) IsDenied(address string) bool {
	val, ok := eg.cache.Load(normalizeAddr(address))
	if !ok {
		return false
	}
	meta := val.(EntityMetadata)
	return !meta.IsSafe
}

// BlockAddress adds or updates a deny entry (e.g. compromised funder).
func (eg *EntityGate) BlockAddress(address, reason string, tags ...string) {
	if reason == "" {
		reason = "blocked"
	}
	t := append([]string{"BLOCKED"}, tags...)
	eg.cache.Store(normalizeAddr(address), stampMeta(EntityMetadata{
		Name: reason, IsSafe: false, Tags: t,
	}, eg.cacheTTL))
}

// AllowAddress adds an explicit allow entry (funder allowlist).
func (eg *EntityGate) AllowAddress(address, name string, tags ...string) {
	t := append([]string{"ALLOWLIST"}, tags...)
	eg.cache.Store(normalizeAddr(address), stampMeta(EntityMetadata{
		Name: name, IsSafe: true, Tags: t,
	}, eg.cacheTTL))
}

func (eg *EntityGate) fetchFromAPI(ctx context.Context, address string) (EntityMetadata, error) {
	base := os.Getenv("ARKHAM_API_BASE")
	if base == "" {
		base = "https://api.arkhamintelligence.com"
	}
	url := fmt.Sprintf("%s/intelligence/address/%s", strings.TrimRight(base, "/"), normalizeAddr(address))
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return EntityMetadata{}, err
	}
	req.Header.Set("Authorization", "Bearer "+eg.apiKey)
	req.Header.Set("Accept", "application/json")

	resp, err := eg.client.Do(req)
	if err != nil {
		return EntityMetadata{}, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))

	if resp.StatusCode == http.StatusNotFound {
		return EntityMetadata{
			Name: "Unknown External", IsSafe: true, Tags: []string{"external"}, LastChecked: time.Now().UTC(),
		}, nil
	}
	if resp.StatusCode >= 400 {
		return EntityMetadata{}, fmt.Errorf("arkham HTTP %d: %s", resp.StatusCode, string(body))
	}

	var payload struct {
		Entity string   `json:"entity"`
		Labels []string `json:"labels"`
		Risk   string   `json:"risk"`
	}
	if err := json.Unmarshal(body, &payload); err != nil {
		// API shape unknown — permissive default until schema is wired
		return EntityMetadata{
			Name: "Unknown External", IsSafe: true, Tags: []string{"external"}, LastChecked: time.Now().UTC(),
		}, nil
	}
	isSafe := true
	for _, lbl := range payload.Labels {
		if strings.EqualFold(lbl, "COMPROMISED") || strings.EqualFold(lbl, "EXPLOIT") {
			isSafe = false
			break
		}
	}
	if strings.EqualFold(payload.Risk, "high") && payload.Entity == "" {
		isSafe = false
	}
	name := payload.Entity
	if name == "" {
		name = "Unknown External"
	}
	return EntityMetadata{
		Name: name, IsSafe: isSafe, Tags: payload.Labels, LastChecked: time.Now().UTC(),
	}, nil
}

func normalizeAddr(addr string) string {
	return strings.ToLower(strings.TrimSpace(addr))
}
