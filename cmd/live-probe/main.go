package main

import (
	"context"
	"fmt"
	"os"
	"time"

	"hexstrike-osint-agent/internal/providers"
)

const testWallet = "0x730ea0231808f42a20f8921ba7fbc788226768f5"

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	fmt.Println("=== OSINT Live Probe ===")

	if key := os.Getenv("ARKHAM_API_KEY"); key != "" {
		runArkham(ctx, key)
	} else {
		fmt.Println("\n[ARKHAM] SKIP — ARKHAM_API_KEY not set")
	}

	if key := os.Getenv("GETBLOCK_API_KEY"); key != "" {
		runGetBlock(ctx, key)
	} else {
		fmt.Println("\n[GETBLOCK] SKIP — GETBLOCK_API_KEY not set")
	}

	if key := os.Getenv("SHODAN_API_KEY"); key != "" {
		runShodan(ctx, key)
	} else {
		fmt.Println("\n[SHODAN] SKIP — SHODAN_API_KEY not set")
	}
}

func runArkham(ctx context.Context, key string) {
	provider := providers.NewArkhamProvider(key)
	safe, reason, err := provider.AnalyzeAddress(ctx, testWallet)
	fmt.Printf("\n[ARKHAM] wallet=%s\n", testWallet)
	if err != nil {
		fmt.Printf("  error: %v\n", err)
		return
	}
	fmt.Printf("  safe=%t reason=%s\n", safe, reason)
}

func runGetBlock(ctx context.Context, key string) {
	provider := providers.NewGetBlockProvider(key)
	safe, reason, err := provider.AnalyzeAddress(ctx, testWallet)
	fmt.Printf("\n[GETBLOCK] wallet=%s\n", testWallet)
	if err != nil {
		fmt.Printf("  error: %v\n", err)
		return
	}
	fmt.Printf("  safe=%t reason=%s\n", safe, reason)
}

func runShodan(ctx context.Context, key string) {
	const testIP = "51.250.97.223"
	provider := providers.NewNetworkProvider(key)
	safe, reason, err := provider.AnalyzeIP(ctx, testIP)
	fmt.Printf("\n[SHODAN] ip=%s\n", testIP)
	if err != nil {
		fmt.Printf("  error: %v\n", err)
		return
	}
	fmt.Printf("  safe=%t reason=%s\n", safe, reason)
}
