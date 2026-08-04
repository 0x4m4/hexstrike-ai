package providers

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const (
	compromisedSinkAddress = "0x730ea0231808f42a20f8921ba7fbc788226768f5"
	defaultArkhamChain     = "bsc"
)

var toxicArkhamEntityIDs = []string{
	"lazarus-group",
}

var toxicArkhamPatterns = []string{
	"hacker",
	"exploit",
	"scam",
	"sanction",
	"mixer",
	"stolen",
	"phishing",
	"ransom",
	"malware",
	"darknet",
	"drainer",
}

// ArkhamEntity describes an attributed on-chain entity.
type ArkhamEntity struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Type string `json:"type"`
}

// ArkhamLabel describes a human-readable wallet label.
type ArkhamLabel struct {
	Name string `json:"name"`
}

// ArkhamTag describes a classification tag on an address.
type ArkhamTag struct {
	Name string `json:"name"`
	Slug string `json:"slug"`
	Type string `json:"type"`
}

// ArkhamAddressIntel describes the enriched address intelligence payload.
type ArkhamAddressIntel struct {
	Address      string        `json:"address"`
	Chain        string        `json:"chain"`
	ArkhamEntity *ArkhamEntity `json:"arkhamEntity"`
	ArkhamLabel  *ArkhamLabel  `json:"arkhamLabel"`
	Contract     bool          `json:"contract"`
	Tags         []ArkhamTag   `json:"tags"`
}

// ArkhamProvider collects wallet intelligence via the Arkham API.
type ArkhamProvider struct {
	apiKey     string
	httpClient *http.Client
	baseURL    string
	chain      string
}

// NewArkhamProvider creates an ArkhamProvider with the given API key.
func NewArkhamProvider(apiKey string) *ArkhamProvider {
	return &ArkhamProvider{
		apiKey: apiKey,
		httpClient: &http.Client{
			Timeout: 3 * time.Second,
		},
		baseURL: "https://api.arkm.com",
		chain:   defaultArkhamChain,
	}
}

// AnalyzeAddress queries Arkham intelligence to assess address risk.
func (ap *ArkhamProvider) AnalyzeAddress(ctx context.Context, address string) (bool, string, error) {
	normalized := strings.ToLower(strings.TrimSpace(address))

	if normalized == compromisedSinkAddress {
		return false, "COMPROMISED_SINK_LOCAL_RULE", nil
	}

	if ap.apiKey == "" {
		return true, "SIMULATED_CLEAN (No API Key)", nil
	}

	endpoint := fmt.Sprintf("%s/intelligence/address_enriched/%s", ap.baseURL, normalized)
	query := url.Values{}
	query.Set("chain", ap.chain)
	query.Set("includeTags", "true")
	query.Set("includeEntityPredictions", "false")
	query.Set("includeClusters", "false")

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint+"?"+query.Encode(), nil)
	if err != nil {
		return false, "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("API-Key", ap.apiKey)
	req.Header.Set("Accept", "application/json")

	resp, err := ap.httpClient.Do(req)
	if err != nil {
		return false, "", fmt.Errorf("arkham transport error: %w", err)
	}
	defer resp.Body.Close()

	switch resp.StatusCode {
	case http.StatusNotFound:
		return true, "UNKNOWN_UNLABELED", nil
	case http.StatusUnauthorized:
		return false, "", fmt.Errorf("arkham api unauthorized: invalid API key")
	case http.StatusTooManyRequests:
		return false, "", fmt.Errorf("arkham api rate limited")
	case http.StatusOK:
		// continue
	default:
		return false, "", fmt.Errorf("arkham api returned bad status: %d", resp.StatusCode)
	}

	var intel ArkhamAddressIntel
	if err := json.NewDecoder(resp.Body).Decode(&intel); err != nil {
		return false, "", fmt.Errorf("failed to decode arkham response: %w", err)
	}

	return evaluateArkhamIntel(intel)
}

func evaluateArkhamIntel(intel ArkhamAddressIntel) (bool, string, error) {
	if intel.ArkhamEntity != nil {
		entityID := strings.ToLower(strings.TrimSpace(intel.ArkhamEntity.ID))
		for _, deniedID := range toxicArkhamEntityIDs {
			if entityID == deniedID {
				return false, fmt.Sprintf("DENIED_ENTITY: %s (%s)", intel.ArkhamEntity.Name, intel.ArkhamEntity.ID), nil
			}
		}

		if match, pattern := containsToxicPattern(intel.ArkhamEntity.Name); match {
			return false, fmt.Sprintf("TOXIC_ENTITY_NAME: %s (pattern=%s)", intel.ArkhamEntity.Name, pattern), nil
		}
	}

	if intel.ArkhamLabel != nil {
		if match, pattern := containsToxicPattern(intel.ArkhamLabel.Name); match {
			return false, fmt.Sprintf("TOXIC_LABEL: %s (pattern=%s)", intel.ArkhamLabel.Name, pattern), nil
		}
	}

	for _, tag := range intel.Tags {
		for _, candidate := range []string{tag.Name, tag.Slug, tag.Type} {
			if match, pattern := containsToxicPattern(candidate); match {
				return false, fmt.Sprintf("TOXIC_TAG: %s (pattern=%s)", candidate, pattern), nil
			}
		}
	}

	entityName := "unknown"
	entityType := "unknown"
	if intel.ArkhamEntity != nil {
		entityName = intel.ArkhamEntity.Name
		entityType = intel.ArkhamEntity.Type
	}

	labelName := "none"
	if intel.ArkhamLabel != nil && intel.ArkhamLabel.Name != "" {
		labelName = intel.ArkhamLabel.Name
	}

	return true, fmt.Sprintf("Entity: %s, Type: %s, Label: %s, Tags: %d", entityName, entityType, labelName, len(intel.Tags)), nil
}

func containsToxicPattern(value string) (bool, string) {
	normalized := strings.ToLower(strings.TrimSpace(value))
	if normalized == "" {
		return false, ""
	}

	for _, pattern := range toxicArkhamPatterns {
		if strings.Contains(normalized, pattern) {
			return true, pattern
		}
	}

	return false, ""
}
