package async

import (
	"net/http"
	"os"
	"time"
)

// PrewarmOllama fires a background /api/tags request so first real LLM call avoids 27s cold start.
func PrewarmOllama() {
	if !RescuePathBlocksLLM() {
		return
	}
	host := os.Getenv("OLLAMA_HOST")
	if host == "" {
		host = "http://127.0.0.1:11434"
	}
	url := host + "/api/tags"
	q := &LLMWorkQueue{}
	q.Enqueue(func() {
		client := &http.Client{Timeout: 120 * time.Second}
		req, err := http.NewRequest(http.MethodGet, url, nil)
		if err != nil {
			return
		}
		resp, err := client.Do(req)
		if err != nil {
			return
		}
		resp.Body.Close()
	})
}

// PrewarmAll starts non-blocking warmups (Ollama, etc.).
func PrewarmAll() {
	PrewarmOllama()
}
