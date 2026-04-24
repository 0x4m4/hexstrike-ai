# HexStrike Baseline Tool Study Guide

## Purpose
This guide is a study-oriented reference for the currently installed baseline tools in this environment. It focuses on:

- what each tool is best at
- when to use it
- how tools chain together in practical workflows

Use this for legal, authorized testing only.

---

## 1) Quick Tool Overview

| Tool | Primary Purpose | Typical Use Case | Example Command (Lab/Authorized Target) |
|---|---|---|---|
| `nmap` | Port/service discovery and host profiling | Baseline network mapping | `nmap -sV -Pn 127.0.0.1` |
| `rustscan` | Fast port pre-scan feeding Nmap | Rapid triage of open ports | `rustscan -a 127.0.0.1 -- -sV` |
| `masscan` | Internet-scale/high-speed port scan | Very large host ranges with controlled rate | `masscan 127.0.0.1 -p1-1000 --rate 1000` |
| `amass` | Deep subdomain/asset enumeration | Passive + active external surface mapping | `amass enum -passive -d example.com` |
| `subfinder` | Fast passive subdomain enumeration | Early recon pass before heavier tools | `subfinder -d example.com -silent` |
| `gobuster` | Directory/vhost/DNS brute force | Content discovery on web targets | `gobuster dir -u http://127.0.0.1 -w /usr/share/wordlists/dirb/common.txt` |
| `ffuf` | Flexible HTTP fuzzing | Parameter, path, host header fuzzing | `ffuf -u http://127.0.0.1/FUZZ -w /usr/share/wordlists/dirb/common.txt` |
| `dirb` | Legacy directory/file brute force | Fast first-pass content enumeration | `dirb http://127.0.0.1 /usr/share/dirb/wordlists/common.txt` |
| `nikto` | Web server misconfiguration checks | Quick known-issue web server sweep | `nikto -h http://127.0.0.1` |
| `nuclei` | Template-based vulnerability scanning | CVE/misconfiguration checks at scale | `nuclei -u http://127.0.0.1 -severity medium,high` |
| `sqlmap` | SQL injection detection/exploitation support | Validating suspected SQLi parameters | `sqlmap -u "http://127.0.0.1/item.php?id=1" --batch` |
| `hydra` | Online credential brute force | Password policy/credential robustness testing | `hydra -L users.txt -P passwords.txt ssh://127.0.0.1` |
| `john` | Offline password hash cracking | Validating hash strength after audit extraction | `john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt` |
| `hashcat` | GPU/CPU offline cracking with modes | High-speed hash auditing | `hashcat -m 0 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt` |
| `trivy` | Vulnerability + secret + misconfig scanning | Container/image/filesystem/IaC security checks | `trivy fs .` |
| `prowler` | Cloud security posture assessment | AWS/Azure/GCP control/compliance checks | `prowler aws --check aws_well_architected_framework_security_pillar` |

---

## 2) Tool-by-Tool Study Notes

### `nmap`
- Strength: reliable host/service fingerprints and script-based checks.
- Good for: initial host profile before deeper scans.
- Study tip: compare `-sV`, `-sC`, and targeted NSE scripts for signal/noise tradeoffs.

### `rustscan`
- Strength: very fast TCP port discovery.
- Good for: quickly discovering candidate ports, then handing to `nmap`.
- Study tip: learn the pass-through model (`-- <nmap args>`).

### `masscan`
- Strength: highest speed scanning for large scope.
- Good for: broad discovery when scope is large and rate limits are explicit.
- Study tip: rate control is critical to avoid service disruption.

### `amass` and `subfinder`
- Strength: complementary subdomain intelligence.
- Good for: attack surface inventory and external reconnaissance.
- Study tip: run `subfinder` first (fast passive), then `amass` for depth.

### `gobuster`, `ffuf`, `dirb`
- Strength: discovering hidden paths, files, virtual hosts, and parameters.
- Good for: web content discovery prior to vulnerability tests.
- Study tip: tune wordlists/extensions and response filtering to reduce noise.

### `nikto`
- Strength: quick known web server misconfiguration checks.
- Good for: immediate web server hygiene findings.
- Study tip: use as a fast baseline; validate critical findings manually.

### `nuclei`
- Strength: scalable template-driven checks.
- Good for: repeatable vulnerability scanning across many targets.
- Study tip: start with severity filters, then tune template tags and exclusions.

### `sqlmap`
- Strength: deep SQL injection verification.
- Good for: confirming SQLi hypotheses from manual/fuzzer findings.
- Study tip: always begin with detection-focused options before riskier payloads.

### `hydra`, `john`, `hashcat`
- Strength: online (`hydra`) and offline (`john`/`hashcat`) auth-hardening validation.
- Good for: password policy audits and credential resilience exercises.
- Study tip: prefer offline testing where possible for safer, auditable workflows.

### `trivy`
- Strength: broad developer-security checks (containers, fs, IaC, secrets).
- Good for: CI/CD and pre-deploy checks.
- Study tip: test `trivy fs`, `trivy image`, and policy output formats.

### `prowler`
- Strength: cloud benchmark and posture auditing.
- Good for: periodic cloud control verification.
- Study tip: start with one framework/checkset, then expand to full baseline scans.

---

## 3) Example Workflows for Study

## Workflow A: External Attack Surface Mapping

Goal: Build a prioritized list of reachable hosts/services and likely weak points.

1. Passive discovery:
   - `subfinder -d example.com -silent > subdomains_subfinder.txt`
   - `amass enum -passive -d example.com -o subdomains_amass.txt`
2. Consolidate targets:
   - merge/deduplicate outputs
3. Port/service mapping:
   - `nmap -sV -iL targets.txt -oN nmap_services.txt`
4. Web triage:
   - `nikto -h http://target`
   - `nuclei -u http://target -severity medium,high`
5. Prioritize findings by exploitability and business impact.

When to use: early recon phase in pentests/bug bounty style assessments.

---

## Workflow B: Web Content and Input Discovery

Goal: Discover hidden routes and likely injectable parameters.

1. Directory baseline:
   - `gobuster dir -u http://target -w /usr/share/wordlists/dirb/common.txt`
2. Parameter/path fuzzing:
   - `ffuf -u http://target/FUZZ -w /usr/share/wordlists/dirb/common.txt`
3. Legacy cross-check:
   - `dirb http://target /usr/share/dirb/wordlists/common.txt`
4. Vulnerability correlation:
   - `nuclei -u http://target`
5. SQLi validation (only where strongly indicated):
   - `sqlmap -u "http://target/page.php?id=1" --batch`

When to use: web application mapping and hypothesis-driven vulnerability testing.

---

## Workflow C: Authentication Strength Assessment

Goal: Evaluate online and offline credential resilience in an authorized lab.

1. Online auth test (rate-limited and approved):
   - `hydra -L users.txt -P passwords.txt ssh://target`
2. Offline hash audit:
   - `john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt`
   - `hashcat -m <mode> -a 0 hashes.txt /usr/share/wordlists/rockyou.txt`
3. Report:
   - weak credential patterns
   - time-to-crack estimates
   - policy remediation recommendations

When to use: credential policy and identity control testing.

---

## Workflow D: Cloud/Container Baseline Security

Goal: Combine cloud posture checks with build artifact scanning.

1. Filesystem/container checks:
   - `trivy fs .`
   - `trivy image <image:tag>`
2. Cloud benchmark checks:
   - `prowler aws`
3. Correlate findings:
   - critical misconfigurations
   - exposed secrets
   - vulnerable package versions
4. Remediate and re-run for drift validation.

When to use: pre-release and periodic security assurance cycles.

---

## 4) HexStrike-Oriented Sequencing (CLI/MCP)

For guided HexStrike flows, follow this default order:

1. `server_health`
2. `analyze_target_intelligence`
3. `select_optimal_tools_ai`
4. `optimize_tool_parameters_ai`
5. `intelligent_smart_scan`
6. `get_process_dashboard`

This gives a reproducible AI-assisted path from target profiling to controlled execution.

---

## 5) Study Progression Plan

Suggested progression:

1. **Week 1-equivalent practice set**: `nmap`, `gobuster`, `nikto`, `nuclei`
2. **Week 2-equivalent practice set**: `ffuf`, `dirb`, `sqlmap`
3. **Week 3-equivalent practice set**: `hydra`, `john`, `hashcat`
4. **Week 4-equivalent practice set**: `trivy`, `prowler`, integrated workflows

Track for each practice run:
- objective
- command set used
- findings
- false positives
- remediation notes

---

## 6) Safety and Ethics Checklist

Before running any workflow:

- Confirm written authorization and scope.
- Use rate limits and safe defaults.
- Avoid disruptive scans against production unless explicitly approved.
- Log commands and outputs for traceability.
- Report findings responsibly with remediation guidance.

