# HexStrike API - Blueprint Architecture

**Version:** 6.2.1
**Date:** 2025-10-26
**Status:** Complete - 100% Feature Parity ✅ (22 blueprints)

---

## Overview

HexStrike API has been refactored from a monolithic 17,289-line server file into 22 modular Flask blueprints, achieving **97.2% code reduction** in the main server (down to 478 lines) with 100% functional parity.

**Refactoring Results:**
- **Before:** 17,289 lines in single file (156 routes)
- **After:** 478 lines main server + 22 blueprint modules (156 routes)
- **Reduction:** 16,811 lines removed (97.2%)
- **Tests:** 920 passing ✅
- **Breaking changes:** 0 ✅
- **Feature parity:** 100% ✅

---

## Blueprint Structure

### Core System Blueprints

#### 1. **Files Blueprint** (`api/routes/files.py`)
**Routes:** 4
**Endpoints:**
- `POST /api/files/upload` - Upload file for analysis
- `POST /api/files/create` - Create file with content
- `GET /api/files/list` - List uploaded files
- `GET /api/files/read/<filename>` - Read file contents

**Dependencies:** `FileOperationsManager`

---

#### 2. **Visual Blueprint** (`api/routes/visual.py`)
**Routes:** 3
**Endpoints:**
- `GET /api/visual/banner` - Get HexStrike banner
- `GET /api/visual/progress-bar` - Render progress bar
- `GET /api/visual/vulnerability-card` - Render vulnerability card

**Dependencies:** `ModernVisualEngine`

---

#### 3. **Error Handling Blueprint** (`api/routes/error_handling.py`)
**Routes:** 7
**Endpoints:**
- `POST /api/error-handling/analyze` - Analyze error and suggest recovery
- `POST /api/error-handling/classify` - Classify error type
- `POST /api/error-handling/suggest-alternatives` - Suggest alternative tools
- `POST /api/error-handling/adjust-parameters` - Adjust parameters for retry
- `POST /api/error-handling/escalate` - Check if human escalation needed
- `GET /api/error-handling/degradation/status` - Get degradation status
- `POST /api/error-handling/degradation/trigger` - Trigger graceful degradation

**Dependencies:** `IntelligentErrorHandler`, `GracefulDegradationManager`, `execute_command_with_recovery`

---

#### 4. **Core Utilities Blueprint** (`api/routes/core.py`)
**Routes:** 6
**Endpoints:**
- `GET /health` - Health check with tool detection
- `POST /api/command` - Execute generic command
- `POST /api/payloads/generate` - Generate test payloads
- `GET /api/cache/stats` - Get cache statistics
- `POST /api/cache/clear` - Clear cache
- `GET /api/telemetry` - Get system telemetry

**Dependencies:** `execute_command`, `cache`, `telemetry`, `file_manager`

---

#### 5. **Processes Blueprint** (`api/routes/processes.py`)
**Routes:** 6
**Endpoints:**
- `GET /api/processes/list` - List active processes
- `GET /api/processes/status/<pid>` - Get process status
- `POST /api/processes/terminate/<pid>` - Terminate process
- `POST /api/processes/pause/<pid>` - Pause process
- `POST /api/processes/resume/<pid>` - Resume process
- `GET /api/processes/dashboard` - Process dashboard with visuals

**Dependencies:** `ProcessManager`

---

### Intelligence & Workflow Blueprints

#### 6. **Intelligence Blueprint** (`api/routes/intelligence.py`)
**Routes:** 6
**Endpoints:**
- `POST /api/intelligence/analyze` - Analyze target and suggest tools
- `POST /api/intelligence/optimize` - Optimize parameters
- `POST /api/intelligence/execute` - Execute with intelligent decisions
- `POST /api/intelligence/chain` - Discover attack chains
- `GET /api/intelligence/stats` - Get decision stats
- `POST /api/intelligence/feedback` - Provide execution feedback

**Dependencies:** `IntelligentDecisionEngine`, `tool_executors`

---

#### 7. **Bug Bounty Blueprint** (`api/routes/bugbounty.py`)
**Routes:** 6
**Endpoints:**
- `POST /api/bugbounty/target/add` - Add bug bounty target
- `GET /api/bugbounty/targets` - List all targets
- `POST /api/bugbounty/scan/start` - Start automated scan
- `GET /api/bugbounty/scan/status/<scan_id>` - Get scan status
- `GET /api/bugbounty/findings/<target_id>` - Get findings
- `POST /api/bugbounty/report/generate` - Generate report

**Dependencies:** `BugBountyWorkflowManager`, `BugBountyTarget`

---

#### 8. **CTF Blueprint** (`api/routes/ctf.py`)
**Routes:** 7
**Endpoints:**
- `POST /api/ctf/challenge/add` - Add CTF challenge
- `GET /api/ctf/challenges` - List challenges
- `POST /api/ctf/solve/start` - Start automated solve
- `GET /api/ctf/solve/status/<solve_id>` - Get solve status
- `GET /api/ctf/solve/result/<solve_id>` - Get solve result
- `POST /api/ctf/hint/generate` - Generate hint
- `GET /api/ctf/stats` - Get CTF stats

**Dependencies:** `CTFWorkflowManager`, `CTFToolset`, `CTFAutomator`, `CTFCoordinator`

---

#### 9. **Vulnerability Intelligence Blueprint** (`api/routes/vuln_intel.py`)
**Routes:** 5
**Endpoints:**
- `POST /api/vuln-intel/cve/analyze` - Analyze CVE for exploitability
- `POST /api/vuln-intel/exploit/generate` - Generate exploit code
- `POST /api/vuln-intel/correlate` - Find vulnerability correlations
- `GET /api/vuln-intel/trending` - Get trending CVEs
- `POST /api/vuln-intel/scan-for-vulns` - Scan target for known vulns

**Dependencies:** `CVEIntelligenceManager`, `ExploitGenerator`, `VulnerabilityCorrelator`

---

#### 10. **AI Blueprint** (`api/routes/ai.py`)
**Routes:** 2
**Endpoints:**
- `POST /api/ai/payload/generate` - Generate AI payload
- `POST /api/ai/payload/optimize` - Optimize payload for target

**Dependencies:** `AIPayloadGenerator`, `execute_command`

---

#### 11. **Python Environment Blueprint** (`api/routes/python_env.py`)
**Routes:** 2
**Endpoints:**
- `POST /api/python-env/create` - Create Python environment
- `POST /api/python-env/execute` - Execute code in environment

**Dependencies:** `PythonEnvironmentManager`, `file_manager`, `execute_command`

---

#### 12. **Process Workflows Blueprint** (`api/routes/process_workflows.py`)
**Routes:** 11
**Endpoints:**
- `POST /api/process/execute-async` - Execute command asynchronously
- `GET /api/process/get-task-result/<task_id>` - Get async task result
- `GET /api/process/pool-stats` - Get process pool statistics
- `GET /api/process/cache-stats` - Get workflow cache stats
- `POST /api/process/clear-cache` - Clear workflow cache
- `GET /api/process/resource-usage` - Get resource usage
- `GET /api/process/performance-dashboard` - Performance dashboard
- `POST /api/process/terminate-gracefully` - Graceful shutdown
- `GET /api/process/auto-scaling` - Get auto-scaling status
- `POST /api/process/scale-pool` - Scale process pool
- `GET /api/process/health-check` - Enhanced health check

**Dependencies:** `EnhancedProcessManager`

---

### Security Tools Blueprints

#### 13. **Cloud Security Tools Blueprint** (`api/routes/tools_cloud.py`)
**Routes:** 12
**Tools:**
- `prowler` - AWS security assessment
- `trivy` - Container/IaC vulnerability scanner
- `scout-suite` - Multi-cloud security auditing
- `cloudmapper` - AWS network topology visualization
- `pacu` - AWS exploitation framework
- `kube-hunter` - Kubernetes penetration testing
- `kube-bench` - Kubernetes CIS benchmark
- `docker-bench-security` - Docker security audit
- `clair` - Container vulnerability static analysis
- `falco` - Runtime security monitoring
- `checkov` - IaC security scanning
- `terrascan` - Terraform security scanner

**Dependencies:** `execute_command`

---

#### 14. **Web Security Tools Blueprint** (`api/routes/tools_web.py`)
**Routes:** 5
**Tools:**
- `dirb` - Web content scanner
- `nikto` - Web server scanner
- `sqlmap` - SQL injection exploitation
- `wpscan` - WordPress security scanner
- `ffuf` - Fast web fuzzer

**Dependencies:** `execute_command`

---

#### 15. **Network Security Tools Blueprint** (`api/routes/tools_network.py`)
**Routes:** 15
**Tools:**
- `nmap` - Network mapper
- `rustscan` - Fast port scanner
- `masscan` - Mass IP port scanner
- `nmap-advanced` - Advanced Nmap with NSE
- `autorecon` - Automated reconnaissance
- `enum4linux` - SMB enumeration (legacy)
- `enum4linux-ng` - SMB enumeration (modern)
- `rpcclient` - RPC client for enumeration
- `nbtscan` - NetBIOS scanner
- `arp-scan` - ARP-based network scanner
- `responder` - LLMNR/NBT-NS/MDNS poisoner
- `netexec` - Network execution tool
- `amass` - Network mapping & attack surface discovery
- `subfinder` - Subdomain discovery
- `smbmap` - SMB enumeration tool

**Dependencies:** `execute_command`, `execute_command_with_recovery`

---

#### 16. **Exploitation Tools Blueprint** (`api/routes/tools_exploit.py`)
**Routes:** 5
**Tools:**
- `metasploit` - Penetration testing framework
- `hydra` - Password brute-forcing
- `john` - Password cracking (John the Ripper)
- `hashcat` - Advanced password recovery
- `msfvenom` - Payload generator

**Dependencies:** `execute_command`

---

#### 17. **Binary/Forensics Tools Blueprint** (`api/routes/tools_binary.py`)
**Routes:** 17 (expanded from 5)
**Tools:**
- `volatility` - Memory forensics
- `gdb` - GNU debugger
- `radare2` - Reverse engineering framework
- `binwalk` - Firmware analysis
- `ropgadget` - ROP gadget finder
- `checksec` - Binary security checker
- `xxd` - Hex dump tool
- `strings` - Extract strings from binaries
- `objdump` - Display object file information
- `ghidra` - Reverse engineering tool
- `pwntools` - CTF framework and exploit development
- `one-gadget` - One gadget RCE finder
- `libc-database` - Libc version identifier
- `gdb-peda` - Python Exploit Development Assistance for GDB
- `angr` - Binary analysis framework
- `ropper` - ROP gadget finder
- `pwninit` - CTF pwn challenge setup

**Dependencies:** `execute_command`

---

#### 18. **Advanced Web Tools Blueprint** (`api/routes/tools_web_advanced.py`)
**Routes:** 12
**Tools:**
- `gobuster` - Directory/DNS/vhost brute forcing
- `nuclei` - Template-based vulnerability scanner
- `feroxbuster` - Fast content discovery
- `dirsearch` - Web path scanner
- `httpx` - Fast HTTP toolkit
- `katana` - Crawling and spidering
- `gau` - Get All URLs (wayback)
- `waybackurls` - Wayback machine URLs
- `hakrawler` - Web crawler
- `dnsenum` - DNS enumeration
- `fierce` - DNS reconnaissance
- `wafw00f` - WAF detection

**Dependencies:** `execute_command`

---

#### 19. **Parameter Discovery Tools Blueprint** (`api/routes/tools_parameters.py`)
**Routes:** 8
**Tools:**
- `arjun` - HTTP parameter discovery
- `paramspider` - Parameter miner
- `x8` - Hidden parameter discovery
- `wfuzz` - Web application fuzzer
- `dotdotpwn` - Directory traversal fuzzer
- `anew` - Tool to add new lines to files
- `qsreplace` - Query string replacer
- `uro` - URL deduplication tool

**Dependencies:** `execute_command`

---

#### 20. **API Security Tools Blueprint** (`api/routes/tools_api.py`)
**Routes:** 4
**Tools:**
- `api-fuzzer` - API endpoint fuzzer
- `graphql-scanner` - GraphQL vulnerability scanner
- `jwt-analyzer` - JWT token analyzer
- `api-schema-analyzer` - API schema security analyzer

**Dependencies:** `execute_command`

---

#### 21. **Forensics Tools Blueprint** (`api/routes/tools_forensics.py`)
**Routes:** 5
**Tools:**
- `volatility3` - Memory forensics framework (v3)
- `foremost` - File carving tool
- `steghide` - Steganography tool
- `exiftool` - Metadata reader/writer
- `hashpump` - Hash length extension attack tool

**Dependencies:** `execute_command`

---

#### 22. **Web Testing Frameworks Blueprint** (`api/routes/tools_web_frameworks.py`)
**Routes:** 3
**Advanced Features:**
- `http-framework` - Advanced HTTP testing (uses HTTPTestingFramework class)
- `browser-agent` - Browser automation (uses BrowserAgent class with Selenium)
- `burpsuite-alternative` - Burp Suite alternative interface

**Dependencies:** `execute_command`, `HTTPTestingFramework`, `BrowserAgent`

---

## Blueprint Registration Pattern

All blueprints follow the same initialization pattern:

```python
# 1. Import blueprint module
from api.routes import (
    files_bp, visual_bp, core_bp, intelligence_bp,
    # ... etc
)

# 2. Initialize blueprint with dependencies (dependency injection)
files_routes.init_app(file_manager)
core_routes.init_app(execute_command, cache, telemetry, file_manager)
intelligence_routes.init_app(decision_engine, tool_executors)
# ... etc

# 3. Register blueprint with Flask app
app.register_blueprint(files_bp)
app.register_blueprint(core_bp)
app.register_blueprint(intelligence_bp)
# ... etc
```

---

## Migration Benefits

### Code Organization
- **Before:** All routes in single 17,289-line file
- **After:** 22 focused modules, each <650 lines
- **Maintainability:** ✅ Easy to locate and modify specific functionality

### Separation of Concerns
- Core utilities separated from tools
- Intelligence/workflows separated from execution
- Cloud/web/network/exploit/binary tools categorized
- Advanced web tools separated from basic tools
- API security, parameter discovery, and forensics categorized

### Testing
- Each blueprint can be tested independently
- Mock dependencies via `init_app()` pattern
- 920 tests passing with zero breaking changes
- 100% functional parity achieved ✅

### Scalability
- Add new tools by creating/extending blueprints
- No need to modify main server file
- Clear blueprint template to follow
- Modular architecture allows easy expansion

---

## API Documentation

For complete API endpoint documentation with request/response examples, see:
- Testing examples: `tests/unit/test_tools/`
- Route implementations: `api/routes/`
- CHANGELOG: `CHANGELOG.md`

---

## Refactoring Complete

✅ **All routes migrated** - 156/156 routes (100%)
✅ **All classes extracted** - 56/56 classes (100%)
✅ **22 blueprints created** - Organized by functionality
✅ **100% feature parity** - No missing components
✅ **Zero breaking changes** - 920 tests passing
✅ **97.2% code reduction** - Main server: 17,289 → 478 lines

**Status:** Production ready with complete modular architecture
