package providers

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"
)

const getBlockFraudThreshold = 0.5

// GetBlockWalletResponse describes the GetBlock wallet risk API envelope.
type GetBlockWalletResponse struct {
	Data GetBlockWalletData `json:"data"`
}

// GetBlockWalletData holds wallet risk fields from GetBlock Address Audit.
type GetBlockWalletData struct {
	Status           string            `json:"status"`
	ProbabilityFraud string            `json:"probabilityFraud"`
	WalletAddress    string            `json:"walletAddress"`
	Chain            string            `json:"chain"`
	ForensicDetails  map[string]string `json:"forensic_details"`
	SanctionData     json.RawMessage   `json:"sanctionData"`
}

// GetBlockProvider performs AML wallet screening via GetBlock Address Audit.
type GetBlockProvider struct {
	apiKey     string
	httpClient *http.Client
	baseURL    string
}

// NewGetBlockProvider creates a GetBlockProvider with the given API key.
func NewGetBlockProvider(apiKey string) *GetBlockProvider {
	return &GetBlockProvider{
		apiKey: apiKey,
		httpClient: &http.Client{
			Timeout: 4 * time.Second,
		},
		baseURL: "https://services.getblock.io/v1",
	}
}

type getBlockRequest struct {
	Network string `json:"network"`
	Address string `json:"address"`
}

// AnalyzeAddress checks wallet risk using GetBlock wallet-audit/check endpoint.
func (gp *GetBlockProvider) AnalyzeAddress(ctx context.Context, address string) (bool, string, error) {
	normalized := strings.ToLower(strings.TrimSpace(address))

	if gp.apiKey == "" {
		return true, "SIMULATED_CLEAN (No GetBlock Key)", nil
	}

	body, err := json.Marshal(getBlockRequest{
		Network: "ETH",
		Address: normalized,
	})
	if err != nil {
		return false, "", fmt.Errorf("failed to marshal request: %w", err)
	}

	url := gp.baseURL + "/wallet-audit/check"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, strings.NewReader(string(body)))
	if err != nil {
		return false, "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+gp.apiKey)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := gp.httpClient.Do(req)
	if err != nil {
		return false, "", fmt.Errorf("getblock transport error: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusPaymentRequired {
		return false, "", fmt.Errorf("getblock api auth/billing error: %d", resp.StatusCode)
	}

	if resp.StatusCode != http.StatusOK {
		return false, "", fmt.Errorf("getblock api returned bad status: %d", resp.StatusCode)
	}

	var walletData GetBlockWalletResponse
	if err := json.NewDecoder(resp.Body).Decode(&walletData); err != nil {
		return false, "", fmt.Errorf("failed to decode getblock response: %w", err)
	}

	return evaluateGetBlockRisk(walletData.Data)
}

func evaluateGetBlockRisk(data GetBlockWalletData) (bool, string, error) {
	if strings.EqualFold(data.Status, "Fraud") {
		return false, fmt.Sprintf("GETBLOCK_FRAUD_STATUS (probability=%s)", data.ProbabilityFraud), nil
	}

	if isSanctioned(data.SanctionData) {
		return false, "GETBLOCK_SANCTIONED_ENTITY", nil
	}

	for flag, value := range data.ForensicDetails {
		if flag == "data_source" {
			continue
		}
		if value == "1" {
			return false, fmt.Sprintf("GETBLOCK_AML_FLAG: %s", flag), nil
		}
	}

	probability, err := strconv.ParseFloat(data.ProbabilityFraud, 64)
	if err != nil {
		return false, "", fmt.Errorf("invalid probabilityFraud value: %q", data.ProbabilityFraud)
	}

	if probability >= getBlockFraudThreshold {
		return false, fmt.Sprintf("GETBLOCK_HIGH_FRAUD_PROBABILITY: %.2f (status=%s)", probability, data.Status), nil
	}

	return true, fmt.Sprintf("GETBLOCK_CLEAN (status=%s, probability=%.2f)", data.Status, probability), nil
}

func isSanctioned(raw json.RawMessage) bool {
	if len(raw) == 0 {
		return false
	}

	var objectForm struct {
		IsSanctioned bool `json:"isSanctioned"`
	}
	if err := json.Unmarshal(raw, &objectForm); err == nil && objectForm.IsSanctioned {
		return true
	}

	var arrayForm []struct {
		IsSanctioned bool `json:"isSanctioned"`
	}
	if err := json.Unmarshal(raw, &arrayForm); err == nil {
		for _, entry := range arrayForm {
			if entry.IsSanctioned {
				return true
			}
		}
	}

	return false
}
