package relay

import (
	"bytes"
	"context"
	"crypto/ecdsa"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/ethereum/go-ethereum/common/hexutil"
	"github.com/ethereum/go-ethereum/crypto"
)

// FlashbotsClient submits eth_sendBundle to Flashbots relay with X-Flashbots-Signature.
type FlashbotsClient struct {
	relayURL   string
	signingKey *ecdsa.PrivateKey
	httpClient *http.Client
}

// NewFlashbotsClient builds an Ethereum mainnet private relay client.
// signingKeyHex is the agent reputation key (not the rescue signer).
func NewFlashbotsClient(relayURL string, signingKeyHex string) (*FlashbotsClient, error) {
	keyHex := signingKeyHex
	if keyHex == "" {
		keyHex = os.Getenv("FLASHBOTS_SIGNING_KEY")
	}
	if keyHex == "" {
		return nil, fmt.Errorf("flashbots: missing signing key")
	}
	privKey, err := crypto.HexToECDSA(trim0x(keyHex))
	if err != nil {
		return nil, fmt.Errorf("invalid flashbots signing key: %w", err)
	}
	if relayURL == "" {
		relayURL = os.Getenv("FLASHBOTS_RELAY_URL")
	}
	if relayURL == "" {
		relayURL = "https://relay.flashbots.net"
	}
	return &FlashbotsClient{
		relayURL:   relayURL,
		signingKey: privKey,
		httpClient: &http.Client{Timeout: 4 * time.Second},
	}, nil
}

// SendBundle posts signed raw txs to Flashbots eth_sendBundle.
func (fc *FlashbotsClient) SendBundle(ctx context.Context, signedHexTxs []string, targetBlock uint64) (string, error) {
	if len(signedHexTxs) == 0 {
		return "", fmt.Errorf("flashbots: empty txs")
	}
	payload := map[string]interface{}{
		"jsonrpc": "2.0",
		"id":      1,
		"method":  "eth_sendBundle",
		"params": []interface{}{
			map[string]interface{}{
				"txs":          signedHexTxs,
				"blockNumber":  fmt.Sprintf("0x%x", targetBlock),
				"minTimestamp": 0,
				"maxTimestamp": time.Now().Add(1 * time.Minute).Unix(),
			},
		},
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, fc.relayURL, bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	hashedBody := crypto.Keccak256Hash(body)
	sig, err := crypto.Sign(hashedBody.Bytes(), fc.signingKey)
	if err != nil {
		return "", fmt.Errorf("failed to sign flashbots header: %w", err)
	}
	pubKey := fc.signingKey.Public().(*ecdsa.PublicKey)
	addr := crypto.PubkeyToAddress(*pubKey)
	signatureHeader := fmt.Sprintf("%s:%s", addr.Hex(), hexutil.Encode(sig))
	req.Header.Set("X-Flashbots-Signature", signatureHeader)

	resp, err := fc.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))

	var jsonResp struct {
		Result json.RawMessage `json:"result"`
		Error  *struct {
			Code    int    `json:"code"`
			Message string `json:"message"`
		} `json:"error"`
	}
	if err := json.NewDecoder(bytes.NewReader(raw)).Decode(&jsonResp); err != nil {
		return "", fmt.Errorf("flashbots: decode: %w", err)
	}
	if jsonResp.Error != nil {
		return "", fmt.Errorf("flashbots rejected bundle: %s", jsonResp.Error.Message)
	}
	var bundleHash string
	if err := json.Unmarshal(jsonResp.Result, &bundleHash); err == nil && bundleHash != "" {
		return bundleHash, nil
	}
	return string(jsonResp.Result), nil
}

func trim0x(s string) string {
	if len(s) >= 2 && (s[0:2] == "0x" || s[0:2] == "0X") {
		return s[2:]
	}
	return s
}
