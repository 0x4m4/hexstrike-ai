# Vanilla Drainer Forensics — Full Operational Protocol

## Role
Drainer-as-a-Service OSINT — fee wallet tracing and affiliate TTP mapping.

## Priority Target
Fee wallet: `0x9d38606C16E6C4F7B1ed4224eA5724FF5C6E710d`
Commission: 15-20% | Active since 2024-10

## Workflow
1. Load OSINT from `VANILLA_INTEL_DIR` and `artifacts/recon/vanilla-drainer-intel/`
2. Map rotating domain + fresh contract per site TTP
3. **Full on-chain analyze** on fee wallet via `run_analyze()`
4. Correlate predecessor customers (Inferno, Angel Drainer)
5. Attack chain: affiliate onboarding → site spinup → lure → drain → fee split

## Output
`artifacts/forensics/vanilla-drainer-report.json`
Bus: `skill.vanilla_drainer.complete` ← `vanilla_drainer_analyzer`
