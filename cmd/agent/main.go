package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	verbose := flag.Bool("v", false, "verbose output")
	repoDir := flag.String("d", "", "hexstrike-ai repository root (default: auto-detect)")
	showVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()

	if *showVersion {
		fmt.Printf("hexstrike-agent %s\n", version)
		os.Exit(0)
	}

	args := flag.Args()
	if len(args) == 0 {
		printUsage()
		os.Exit(1)
	}

	switch args[0] {
	case "battle":
		BootstrapMainnet()
		agent, err := NewAgent(*repoDir, *verbose)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: %v\n", err)
			os.Exit(1)
		}
		code, err := agent.RunBattle()
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: %v\n", err)
			os.Exit(1)
		}
		os.Exit(code)
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n", args[0])
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println(`HexStrike Battle Agent — autonomous sandbox red-team orchestrator

Usage:
  hexstrike-agent battle [-v] [-d /path/to/hexstrike-ai]
  hexstrike-agent version

Commands:
  battle    Run the 7-attack sandbox battle suite
  version   Print agent version`)
}
