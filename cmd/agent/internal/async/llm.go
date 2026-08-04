// Package async ensures LLM/Ollama never blocks the rescue hot path.
package async

import (
	"os"
	"sync"
)

// HotPathPolicy documents that PrepareRescue and signing must never await LLM.
const HotPathPolicy = "LLM calls are fire-and-forget; hot path uses sync.Map + RPC only"

// LLMWorkQueue runs Ollama/bytecode/OSINT enrichment off the signing goroutine.
type LLMWorkQueue struct {
	mu     sync.Mutex
	queued int
}

// Enqueue schedules fn in a detached goroutine. Returns immediately (0 ms hot-path impact).
func (q *LLMWorkQueue) Enqueue(fn func()) {
	if fn == nil {
		return
	}
	q.mu.Lock()
	q.queued++
	q.mu.Unlock()
	go func() {
		defer func() {
			q.mu.Lock()
			q.queued--
			q.mu.Unlock()
		}()
		fn()
	}()
}

// Pending returns in-flight async LLM jobs (diagnostics only).
func (q *LLMWorkQueue) Pending() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return q.queued
}

// RescuePathBlocksLLM is true when battle hot path must never call LLM synchronously.
func RescuePathBlocksLLM() bool {
	v := os.Getenv("LLM_ASYNC_ONLY")
	if v == "" {
		return true // safe default for mainnet deployment
	}
	return v == "1" || v == "true" || v == "yes"
}
