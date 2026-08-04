package main

import (
	"github.com/hexstrike-ai/hexstrike/cmd/agent/internal/async"
)

// BootstrapMainnet runs async prewarm hooks before battle/rescue loops.
func BootstrapMainnet() {
	async.PrewarmAll()
}
