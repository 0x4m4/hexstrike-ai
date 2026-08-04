package providers

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"slices"
	"strings"
	"time"
)

const jenkinsVulnIP = "51.250.97.223"

var riskyPorts = []int{22, 3389, 8080}

// ShodanHostResponse describes the Shodan host lookup payload.
type ShodanHostResponse struct {
	IP        string   `json:"ip_str"`
	Ports     []int    `json:"ports"`
	Hostnames []string `json:"hostnames"`
	OS        string   `json:"os"`
	Vulns     []string `json:"vulns"`
}

// NetworkProvider scans network infrastructure via the Shodan API.
type NetworkProvider struct {
	apiKey     string
	httpClient *http.Client
	baseURL    string
}

// NewNetworkProvider creates a NetworkProvider with the given Shodan API key.
func NewNetworkProvider(apiKey string) *NetworkProvider {
	return &NetworkProvider{
		apiKey: apiKey,
		httpClient: &http.Client{
			Timeout: 4 * time.Second,
		},
		baseURL: "https://api.shodan.io",
	}
}

// AnalyzeIP assesses host risk using Shodan intelligence or local fixtures.
func (np *NetworkProvider) AnalyzeIP(ctx context.Context, ip string) (bool, string, error) {
	normalized := strings.TrimSpace(ip)

	if np.apiKey == "" {
		if normalized == jenkinsVulnIP {
			return false, "JENKINS_PORT_EXPOSED_LOCAL_RULE (port=8080)", nil
		}
		return true, "SIMULATED_INFRA_CLEAN (No Shodan Key)", nil
	}

	url := fmt.Sprintf("%s/shodan/host/%s?key=%s", np.baseURL, normalized, np.apiKey)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return false, "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Accept", "application/json")

	resp, err := np.httpClient.Do(req)
	if err != nil {
		return false, "", fmt.Errorf("shodan transport error: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return true, "HOST_NOT_INDEXED_CLEAN", nil
	}

	if resp.StatusCode != http.StatusOK {
		return false, "", fmt.Errorf("shodan api returned bad status: %d", resp.StatusCode)
	}

	var hostData ShodanHostResponse
	if err := json.NewDecoder(resp.Body).Decode(&hostData); err != nil {
		return false, "", fmt.Errorf("failed to decode shodan response: %w", err)
	}

	for _, port := range hostData.Ports {
		if slices.Contains(riskyPorts, port) {
			return false, fmt.Sprintf("RISKY_PORT_OPEN: %d (OS: %s)", port, hostData.OS), nil
		}
	}

	if len(hostData.Vulns) > 0 {
		limit := 3
		if len(hostData.Vulns) < limit {
			limit = len(hostData.Vulns)
		}

		return false, fmt.Sprintf("CVE_DETECTED: %s (total=%d)", strings.Join(hostData.Vulns[:limit], ", "), len(hostData.Vulns)), nil
	}

	hostname := "none"
	if len(hostData.Hostnames) > 0 {
		hostname = hostData.Hostnames[0]
	}

	return true, fmt.Sprintf("HOST_SECURE (ports=%d, hostname=%s)", len(hostData.Ports), hostname), nil
}
