package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

const version = "1.0.0"

// AttackID identifies one red-team scenario.
type AttackID string

const (
	AttackBaseline      AttackID = "01-baseline-trigger"
	AttackRaceDuplicate AttackID = "02-race-duplicate-sign"
	AttackFrontRun      AttackID = "03-front-run-drain"
	AttackReplay        AttackID = "04-replay-rescue-tx"
	AttackTOCTOU        AttackID = "05-toctou-nonce-bump"
	AttackCompromised   AttackID = "06-compromised-funder"
	AttackHardening     AttackID = "07-hardening-blocks-tamper"
)

// Outcome categorizes attack results.
type Outcome string

const (
	OutcomeVulnConfirmed Outcome = "VULN_CONFIRMED"
	OutcomeDefended      Outcome = "DEFENDED"
	OutcomeInconclusive  Outcome = "INCONCLUSIVE"
	OutcomeSkipped       Outcome = "SKIPPED"
)

// AttackResult is one battle test row.
type AttackResult struct {
	Scenario AttackID `json:"scenario"`
	Outcome  Outcome  `json:"outcome"`
	Detail   string   `json:"detail,omitempty"`
	Duration string   `json:"duration,omitempty"`
	ExitCode int      `json:"exit_code,omitempty"`
}

// BattleSummary aggregates statistics.
type BattleSummary struct {
	Total          int `json:"total"`
	VulnConfirmed  int `json:"vuln_confirmed"`
	Defended       int `json:"defended"`
	Inconclusive   int `json:"inconclusive"`
	Skipped        int `json:"skipped"`
	ReadinessScore int `json:"readiness_score"`
}

// BattleReport is persisted to artifacts/sandbox/battle-report.json.
type BattleReport struct {
	Timestamp       string          `json:"timestamp"`
	AgentVersion    string          `json:"agent_version,omitempty"`
	RepoRoot        string          `json:"repo_root,omitempty"`
	Summary         BattleSummary   `json:"summary"`
	Vulnerabilities []string        `json:"vulnerabilities"`
	Runs            []AttackResult  `json:"runs"`
	Prerequisites   map[string]bool `json:"prerequisites,omitempty"`
}

// Agent orchestrates the sandbox battle suite.
type Agent struct {
	repoRoot string
	verbose  bool
	attacks  []AttackID
}

var DefaultAttacks = []AttackID{
	AttackBaseline,
	AttackRaceDuplicate,
	AttackFrontRun,
	AttackReplay,
	AttackTOCTOU,
	AttackCompromised,
	AttackHardening,
}

var resultLine = regexp.MustCompile(`\[RESULT\]\s+(\S+)\s+→\s+(\S+)`)

// NewAgent resolves repository root and initializes the agent.
func NewAgent(repoDir string, verbose bool) (*Agent, error) {
	root, err := resolveRepoRoot(repoDir)
	if err != nil {
		return nil, err
	}
	return &Agent{repoRoot: root, verbose: verbose, attacks: DefaultAttacks}, nil
}

func resolveRepoRoot(explicit string) (string, error) {
	if explicit != "" {
		abs, err := filepath.Abs(explicit)
		if err != nil {
			return "", err
		}
		if !isHexstrikeRepo(abs) {
			return "", fmt.Errorf("%s is not a hexstrike-ai repository root", abs)
		}
		return abs, nil
	}
	cwd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	dir := cwd
	for {
		if isHexstrikeRepo(dir) {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", fmt.Errorf("could not locate hexstrike-ai root; use -d flag")
}

func isHexstrikeRepo(dir string) bool {
	for _, m := range []string{"hexstrike_server.py", "project_manifest.json", "scripts/sandbox"} {
		if _, err := os.Stat(filepath.Join(dir, m)); err != nil {
			return false
		}
	}
	return true
}

// RunBattle executes prerequisites, setup, 7 attacks, report.
func (a *Agent) RunBattle() (int, error) {
	a.printBanner("🎯 HexStrike Battle Agent Started")

	a.log("Verifying prerequisites...")
	prereqs := a.verifyPrerequisites()
	if !a.allPrereqsOK(prereqs) {
		return 1, fmt.Errorf("missing prerequisites — install Foundry: curl -L https://foundry.paradigm.xyz | bash && foundryup")
	}

	a.log("Setting up sandbox environment...")
	if err := a.setupEnvironment(); err != nil {
		return 1, err
	}
	a.log("    ✓ Environment ready")

	a.rule()
	a.log("Launching battle test suite (7 attacks)...")
	a.rule()

	runs := a.runAllTests()
	report := a.buildReport(prereqs, runs)
	if err := a.writeReport(report); err != nil {
		return 1, err
	}
	a.printReport(report)

	exitCode := 0
	if report.Summary.ReadinessScore < 50 {
		exitCode = 1
	}
	return exitCode, nil
}

func (a *Agent) verifyPrerequisites() map[string]bool {
	tools := []string{"bash", "python3", "anvil", "cast", "curl"}
	out := make(map[string]bool, len(tools))
	for _, tool := range tools {
		_, err := exec.LookPath(tool)
		out[tool] = err == nil
		prefix := "    ✗"
		if out[tool] {
			prefix = "    ✓"
		}
		fmt.Printf("%s %s\n", prefix, tool)
	}
	return out
}

func (a *Agent) allPrereqsOK(prereqs map[string]bool) bool {
	for _, ok := range prereqs {
		if !ok {
			return false
		}
	}
	return true
}

func (a *Agent) setupEnvironment() error {
	sandbox := filepath.Join(a.repoRoot, "scripts", "sandbox")
	artifacts := filepath.Join(a.repoRoot, "artifacts", "sandbox")
	if err := os.MkdirAll(artifacts, 0o755); err != nil {
		return err
	}

	// Clear per-run redteam report so scripts append fresh results.
	_ = os.Remove(filepath.Join(artifacts, "redteam-report.json"))

	scripts := []string{"start-anvil.sh", "setup-anvil-env.sh"}
	for _, name := range scripts {
		script := filepath.Join(sandbox, name)
		if _, err := os.Stat(script); err != nil {
			return fmt.Errorf("%s missing", name)
		}
		cmd := exec.Command("bash", script)
		cmd.Dir = a.repoRoot
		out, err := cmd.CombinedOutput()
		if a.verbose {
			fmt.Print(string(out))
		}
		if err != nil {
			return fmt.Errorf("%s failed: %w\n%s", name, err, string(out))
		}
	}

	// Optional sandbox Python deps (httpx for rpc_interceptor).
	req := filepath.Join(sandbox, "requirements-sandbox.txt")
	if _, err := os.Stat(req); err == nil {
		cmd := exec.Command("python3", "-m", "pip", "install", "-q", "-r", req)
		cmd.Dir = a.repoRoot
		_ = cmd.Run()
	}
	return nil
}

func (a *Agent) runAllTests() []AttackResult {
	results := make([]AttackResult, 0, len(a.attacks))
	for i, attack := range a.attacks {
		fmt.Printf("\n[%d/%d] Running: %s\n", i+1, len(a.attacks), attack)
		fmt.Println("─────────────────────────────────")
		start := time.Now()
		result := a.runAttack(attack)
		result.Duration = time.Since(start).Round(time.Millisecond).String()
		results = append(results, result)
		a.printAttackResult(result)
	}
	return results
}

func (a *Agent) runAttack(attack AttackID) AttackResult {
	script := filepath.Join(a.repoRoot, "scripts", "sandbox", "redteam", string(attack)+".sh")
	result := AttackResult{Scenario: attack}

	if _, err := os.Stat(script); err != nil {
		result.Outcome = OutcomeSkipped
		result.Detail = "attack script missing"
		return result
	}

	cmd := exec.Command("bash", script)
	cmd.Dir = a.repoRoot
	out, err := cmd.CombinedOutput()
	result.ExitCode = 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			result.ExitCode = exitErr.ExitCode()
		} else {
			result.ExitCode = 1
		}
	}

	if a.verbose && len(out) > 0 {
		fmt.Println(string(out))
	}

	parsed := parseAttackOutput(string(out))
	result.Outcome = parsed.Outcome
	result.Detail = parsed.Detail
	return result
}

type parsedOutcome struct {
	Outcome Outcome
	Detail  string
}

func parseAttackOutput(output string) parsedOutcome {
	var last parsedOutcome
	for _, line := range strings.Split(output, "\n") {
		if m := resultLine.FindStringSubmatch(line); len(m) == 3 {
			raw := strings.ToUpper(m[2])
			detail := ""
			if idx := strings.Index(line, "("); idx > 0 {
				detail = strings.Trim(strings.TrimSuffix(strings.TrimSpace(line[idx:]), ")"), "() ")
			}
			last = parsedOutcome{Outcome: normalizeOutcome(raw), Detail: detail}
		}
	}
	if last.Outcome != "" {
		return last
	}
	return parsedOutcome{Outcome: OutcomeInconclusive, Detail: "no [RESULT] marker in script output"}
}

func normalizeOutcome(raw string) Outcome {
	switch raw {
	case "VULN_CONFIRMED":
		return OutcomeVulnConfirmed
	case "DEFENDED", "BLOCKED":
		return OutcomeDefended
	case "INCONCLUSIVE", "NO_SIGN", "PARTIAL", "SKIP":
		return OutcomeInconclusive
	default:
		return OutcomeInconclusive
	}
}

func (a *Agent) buildReport(prereqs map[string]bool, runs []AttackResult) BattleReport {
	summary := BattleSummary{Total: len(runs)}
	vulns := make([]string, 0)

	for _, r := range runs {
		switch r.Outcome {
		case OutcomeVulnConfirmed:
			summary.VulnConfirmed++
			vulns = append(vulns, fmt.Sprintf("%s: %s", r.Scenario, shortDetail(r.Detail)))
		case OutcomeDefended:
			summary.Defended++
		case OutcomeInconclusive:
			summary.Inconclusive++
		case OutcomeSkipped:
			summary.Skipped++
		}
	}

	score := 50 + summary.VulnConfirmed*3 + summary.Defended*5 - summary.Inconclusive*10
	if score < 0 {
		score = 0
	}
	if score > 100 {
		score = 100
	}
	summary.ReadinessScore = score

	return BattleReport{
		Timestamp:       time.Now().UTC().Format(time.RFC3339),
		AgentVersion:    version,
		RepoRoot:        a.repoRoot,
		Summary:         summary,
		Vulnerabilities: vulns,
		Runs:            runs,
		Prerequisites:   prereqs,
	}
}

func shortDetail(d string) string {
	d = strings.TrimSpace(d)
	if len(d) > 120 {
		return d[:117] + "..."
	}
	return d
}

func (a *Agent) writeReport(report BattleReport) error {
	path := filepath.Join(a.repoRoot, "artifacts", "sandbox", "battle-report.json")
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	if err := enc.Encode(report); err != nil {
		return err
	}
	fmt.Printf("\n💾 Report saved to: %s\n", path)
	return nil
}

func (a *Agent) printReport(report BattleReport) {
	a.rule()
	fmt.Println("📊 BATTLE REPORT")
	a.rule()
	fmt.Printf("Timestamp: %s\n\n", report.Timestamp)
	fmt.Println("📈 SUMMARY:")
	fmt.Printf("  Total Tests:      %d\n", report.Summary.Total)
	fmt.Printf("  Vulnerabilities:  %d ⚠️\n", report.Summary.VulnConfirmed)
	fmt.Printf("  Defended:         %d ✓\n", report.Summary.Defended)
	fmt.Printf("  Inconclusive:     %d ?\n", report.Summary.Inconclusive)
	if report.Summary.Skipped > 0 {
		fmt.Printf("  Skipped:          %d\n", report.Summary.Skipped)
	}
	fmt.Println()
	fmt.Println("🎯 READINESS SCORE:")
	status := readinessLabel(report.Summary.ReadinessScore)
	fmt.Printf("  %d/100 %s\n", report.Summary.ReadinessScore, status)
	if len(report.Vulnerabilities) > 0 {
		fmt.Println()
		fmt.Println("🔴 FOUND VULNERABILITIES:")
		for _, v := range report.Vulnerabilities {
			fmt.Printf("  • %s\n", v)
		}
	}
	fmt.Println()
	fmt.Println("📋 DETAILED RESULTS:")
	for i, r := range report.Runs {
		fmt.Printf("  %d. %s %s → %s\n", i+1, outcomeIcon(r.Outcome), r.Scenario, r.Outcome)
	}
}

func readinessLabel(score int) string {
	switch {
	case score >= 70:
		return "✅ READY FOR TESTNET"
	case score >= 50:
		return "⚠️ NEEDS HARDENING"
	default:
		return "❌ NOT READY"
	}
}

func (a *Agent) printAttackResult(r AttackResult) {
	fmt.Printf("%s %s → %s\n", outcomeIcon(r.Outcome), r.Scenario, r.Outcome)
}

func outcomeIcon(o Outcome) string {
	switch o {
	case OutcomeVulnConfirmed:
		return "⚠"
	case OutcomeDefended:
		return "✓"
	case OutcomeSkipped:
		return "○"
	default:
		return "?"
	}
}

func (a *Agent) printBanner(title string) {
	fmt.Println()
	fmt.Println(title)
	a.rule()
}

func (a *Agent) rule() {
	fmt.Println("════════════════════════════════════════════════════════")
}

func (a *Agent) log(msg string) {
	fmt.Printf("[*] %s\n", msg)
}
