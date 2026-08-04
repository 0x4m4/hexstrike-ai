.PHONY: battle battle-fast build-agent setup watch logs help

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
AGENT := $(ROOT)/bin/hexstrike-agent
SANDBOX := $(dir $(lastword $(MAKEFILE_LIST)))

help:
	@echo "HexStrike sandbox targets:"
	@echo "  make setup        - start Anvil + create anvil.env"
	@echo "  make build-agent  - compile Go battle agent"
	@echo "  make battle       - full 7-attack suite via Go agent"
	@echo "  make battle-fast  - bash redteam/run-all.sh"
	@echo "  make watch        - tail bot events"
	@echo "  make logs         - summarize artifact logs"

setup:
	bash $(SANDBOX)start-anvil.sh
	bash $(SANDBOX)setup-anvil-env.sh

build-agent:
	bash $(ROOT)/cmd/agent/build.sh

battle: build-agent setup
	$(AGENT) battle -v

battle-fast: setup
	bash $(SANDBOX)redteam/run-all.sh

watch:
	tail -f $(ROOT)/artifacts/sandbox/dummy-bot-events.jsonl

logs:
	@echo "Artifact logs:"
	@wc -l $(ROOT)/artifacts/sandbox/*.jsonl 2>/dev/null || true
	@test -f $(ROOT)/artifacts/sandbox/battle-report.json && jq '.summary' $(ROOT)/artifacts/sandbox/battle-report.json || true
