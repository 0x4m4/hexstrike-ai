# MindSync Oracle v8 - Ethical Guidelines & Usage Policy

## ⚠️ CRITICAL - AUTHORIZED ENVIRONMENTS ONLY ⚠️

v8 introduces XBOW-inspired vulnerability research capabilities including predictive exploitation chain analysis, CTF-solving agents, and automated vulnerability testing. These features are **STRICTLY** for authorized, ethical, and defensive security research purposes.

---

## Table of Contents

1. [Overview](#overview)
2. [Ethical Use Requirements](#ethical-use-requirements)
3. [Forbidden Activities](#forbidden-activities)
4. [v8 Components & Ethical Controls](#v8-components--ethical-controls)
5. [Authorization Documentation](#authorization-documentation)
6. [Compliance & Legal](#compliance--legal)
7. [Quick Start Guide](#quick-start-guide)
8. [Use Case Examples](#use-case-examples)

---

## Overview

**What is v8?**

MindSync Oracle v8 is an XBOW-inspired vulnerability research assistant that combines:
- v7's real-time threat intelligence (X firehose, Tor OSINT, unified threat hub)
- Predictive vulnerability chain analysis
- CTF-solving capabilities with HexStrike integration
- **MANDATORY** human-in-the-loop approval for all actions
- Hard scope enforcement
- Sandboxed execution (Docker/VM isolation)

**Inspiration: XBOW**

XBOW is an autonomous AI pentester that topped HackerOne leaderboards by discovering 1,000+ zero-day vulnerabilities. v8 adapts XBOW's pattern analysis and predictive chaining approach but adds **strict ethical controls**:

✅ **XBOW's Strengths (Adopted):**
- Predictive vulnerability chain analysis
- Pattern-based exploitation reasoning
- Multi-step attack path planning

❌ **XBOW's Risks (Mitigated):**
- Autonomous exploitation → **v8 requires human approval for EVERY action**
- Unrestricted target selection → **v8 enforces hard scope validation**
- Host execution → **v8 uses sandboxed Docker containers**

---

## Ethical Use Requirements

By using MindSync Oracle v8, you **MUST**:

✅ **Have proper authorization** for all security research activities
- Written authorization from system owner
- Signed engagement agreement (for red team exercises)
- CTF platform registration (for competitions)
- Bug bounty program participation (for bounty hunting)

✅ **Comply with all applicable laws** in your jurisdiction
- Computer Fraud and Abuse Act (CFAA) - US
- Computer Misuse Act - UK
- Equivalent laws in your country

✅ **Use defensively and educationally only**
- CTF competitions (HackTheBox, TryHackMe, CTFTime)
- Personal lab environments (owned infrastructure)
- Authorized red team engagements (written permission)
- Bug bounty research (manual submission)
- Educational security courses

✅ **Maintain human control**
- Approve EVERY action before execution
- Review all commands before running
- Understand impact of each step

✅ **Document your authorization**
- Maintain authorization records
- Log all activities to audit files
- Keep scope files up-to-date

✅ **Follow responsible disclosure**
- Report vulnerabilities privately to vendors
- Allow time for patching (90 days standard)
- Coordinate public disclosure

---

## Forbidden Activities

❌ **NEVER use v8 for**:

**Unauthorized Access:**
- Testing production systems without authorization
- Scanning internet ranges without permission
- Attacking systems you don't own or have permission to test
- Bypassing security controls on unauthorized systems

**Illegal Activities:**
- Computer intrusion (CFAA violations)
- Data theft or exfiltration
- Service disruption (DoS/DDoS)
- Malware deployment
- Identity theft or fraud

**Malicious Purposes:**
- Personal gain through unauthorized access
- Competitive advantage through corporate espionage
- Revenge or harassment
- Circumventing detection for malicious purposes

**Ethical Bypasses:**
- Disabling human-in-the-loop controls
- Ignoring scope restrictions
- Auto-approving actions
- Running tools outside sandbox

---

## v8 Components & Ethical Controls

### 1. Vulnerability Research Assistant (`vuln_research_assistant.py`)

**Purpose**: Analyze v7 threat intelligence and suggest vulnerability chains

**Ethical Controls**:
- SUGGESTIONS ONLY (no autonomous exploitation)
- Requires v7 threat hub data (validated sources)
- Pattern matching with confidence thresholds
- Cross-source validation boosts confidence
- No direct exploitation capabilities

**Configuration**:
```yaml
xbow_mode:
  vuln_research:
    min_confidence: 0.6               # Minimum confidence threshold
    patterns_enabled: true            # Use predefined patterns
    cross_source_boost: 0.15          # Boost for multi-source validation
```

**Acceptable Use**:
- Understanding emerging threat patterns
- Planning defensive strategies
- CTF challenge analysis
- Bug bounty target research (reconnaissance phase)

**Unacceptable Use**:
- Weaponizing suggestions for unauthorized targets
- Automated exploitation based on suggestions
- Mass scanning without authorization

---

### 2. Chain Predictor (`chain_predictor.py`)

**Purpose**: Predict likely exploitation paths BEFORE they become public exploits

**Ethical Controls**:
- PREDICTIONS ONLY (no execution)
- Temporal pattern analysis for early warning
- ETA estimation for exploit publication
- Validation tracking (learn from accuracy)
- Used for proactive defense planning

**Configuration**:
```yaml
xbow_mode:
  chain_predictor:
    min_confidence: 0.6               # Minimum confidence
    temporal_grouping: 3600           # Group threats within 1 hour
    eta_prediction: true              # Predict time to public exploit
```

**Acceptable Use**:
- Early threat detection for defense
- Prioritizing security research
- CTF challenge pattern prediction
- Understanding vulnerability evolution

**Unacceptable Use**:
- Predicting for offensive purposes
- Zero-day discovery for sale
- Exploitation before vendor notification

---

### 3. Human-in-the-Loop Controller (`human_in_loop_controller.py`)

**Purpose**: MANDATORY approval gates for ALL offensive actions

**⚠️ CRITICAL SAFEGUARD - NO BYPASSES ALLOWED ⚠️**

**Ethical Controls**:
- Approval prompt for EVERY action
- Timeout auto-rejects (no silent approval)
- Full context displayed (command, risk level, target)
- Audit logging to v8_audit.log
- No backdoors or override mechanisms
- Non-interactive mode = auto-reject

**Configuration**:
```yaml
xbow_mode:
  human_in_loop:
    enabled: true                     # REQUIRED - cannot disable
    approval_timeout: 300             # 5 minutes
    audit_log: "v8_audit.log"
    require_all_approvals: true       # Every action needs approval
```

**Action Types**:
- `reconnaissance`: Port scans, directory enumeration (LOW risk)
- `vulnerability_testing`: PoC testing, exploit attempts (MEDIUM risk)
- `exploitation`: Active exploitation, shell access (HIGH risk)
- `post_exploitation`: Privilege escalation, lateral movement (CRITICAL risk)
- `data_access`: Reading files, extracting data (HIGH/CRITICAL risk)

**Approval Flow**:
1. Tool proposes action with full details
2. User sees: type, risk level, target, command, context
3. User must explicitly type "Y" or "Yes" to approve
4. Action logged to audit file with timestamp, user, decision
5. If rejected or timeout, action is blocked

**Acceptable Use**:
- Review every action carefully
- Approve only authorized activities
- Understand command before approving

**Unacceptable Use**:
- Auto-approving without review
- Approving actions outside scope
- Bypassing approval mechanism

---

### 4. Scope Validator (`scope_validator.py`)

**Purpose**: Hard enforcement of authorized target scope

**⚠️ HARD REJECTION - NO UNAUTHORIZED TARGETS ⚠️**

**Ethical Controls**:
- Loads scope from `authorized_scope.yaml`
- Validates IP addresses (individual, CIDR ranges)
- Validates domains (exact, wildcard subdomains)
- Validates URLs (with path constraints)
- **Hard rejection** of out-of-scope targets
- Exclusion list support
- Authorization expiry checking

**Configuration**:
```yaml
xbow_mode:
  scope_validator:
    enabled: true                     # REQUIRED
    scope_file: "authorized_scope.yaml"
    audit_log: "scope_validation_audit.log"
    reject_out_of_scope: true         # Hard reject
```

**Scope File Format** (`authorized_scope.yaml`):
```yaml
authorization:
  granted_by: "Security Team Lead"
  granted_date: "2025-01-15"
  expires: "2025-12-31"
  purpose: "CTF Competition / Red Team Exercise"
  engagement_id: "ENG-2025-001"

targets:
  ip_addresses:
    - "192.168.1.100"                 # Specific IP
    - "10.0.0.0/24"                   # CIDR range

  domains:
    - "*.lab.local"                   # Wildcard subdomain
    - "testserver.company.com"        # Exact domain

  urls:
    - "https://vulnerable.app/test/*" # URL with path

  excluded:
    - "192.168.1.1"                   # Gateway - excluded
    - "prod.company.com"              # Production - excluded
```

**Acceptable Use**:
- Define clear scope boundaries
- Update scope file for each engagement
- Verify authorization before adding targets

**Unacceptable Use**:
- Adding unauthorized targets to scope
- Using wildcard scopes for internet ranges
- Testing before authorization granted

---

### 5. Sandbox Executor (`sandbox_executor.py`)

**Purpose**: Execute security tools in isolated Docker containers

**Ethical Controls**:
- All tools run in Docker containers (not host)
- Network isolation options (none/bridge/host)
- Resource limits (CPU, memory, time)
- Read-only root filesystem where possible
- No privileged mode
- Automatic cleanup after execution

**Configuration**:
```yaml
xbow_mode:
  sandbox:
    enabled: true                     # REQUIRED
    default_mode: true                # Always use sandbox
    image: "kalilinux/kali-rolling"   # Docker image
    network_mode: "bridge"            # Network isolation
    memory_limit: "1g"                # Memory limit
    cpu_limit: 2.0                    # CPU limit
    timeout: 300                      # 5 minute timeout
```

**Security Features**:
- Container isolation prevents host damage
- Network isolation prevents lateral movement
- Resource limits prevent DoS
- Automatic timeout prevents runaway processes
- Result extraction without host access

**Acceptable Use**:
- Running security tools safely
- Testing in isolated environment
- Protecting host system

**Unacceptable Use**:
- Disabling sandbox for "convenience"
- Running tools directly on host
- Privileged container access

---

### 6. CTF Lab Agent (`ctf_lab_agent.py`)

**Purpose**: Intelligent CTF-solving agent with HexStrike integration

**Ethical Controls**:
- Integrates ALL v8 safeguards (approval, scope, sandbox)
- Step-by-step challenge solving workflow
- HexStrike API for pentesting tools
- Automatic writeup generation
- Methodology documentation

**Configuration**:
```yaml
xbow_mode:
  ctf_agent:
    enabled: false                    # Enable when needed
    max_concurrent_challenges: 1
    auto_writeup: true
    flag_regex: "CTF\\{[^}]+\\}"
```

**Workflow**:
1. Challenge Analysis (parse description, extract hints)
2. Scope Validation (verify target authorized)
3. Reconnaissance (with approval: port scans, web enumeration)
4. Chain Prediction (predict exploitation path)
5. Exploitation Planning (step-by-step approach)
6. Execution (with approval for EACH step)
7. Flag Capture (extract and validate flag)
8. Writeup Generation (document methodology)

**Acceptable Use**:
- HackTheBox / TryHackMe challenges
- CTFTime competitions
- Personal lab testing
- Educational CTF exercises

**Unacceptable Use**:
- Real-world pentests without authorization
- Production systems
- Unauthorized bug bounty targets

---

## Authorization Documentation

### Before Enabling v8

Document the following:

**1. Purpose Statement**
- Why are you using v8?
- What is your specific use case?
- What is the expected outcome?

**2. Authorization**
- Who authorized this activity?
- Written permission obtained? (Y/N)
- Engagement agreement signed? (Y/N)
- CTF platform registered? (Y/N)

**3. Scope Definition**
- What targets are authorized?
- What is explicitly excluded?
- What are the time constraints?

**4. Legal Review**
- Has legal counsel reviewed? (Y/N)
- Compliant with local laws? (Y/N)
- Insurance coverage verified? (Y/N)

**5. Technical Controls**
- Human-in-loop enabled? (MUST be YES)
- Scope validator configured? (MUST be YES)
- Sandbox enabled? (MUST be YES)
- Audit logging active? (MUST be YES)

### Authorization Template

```markdown
# v8 Authorization Document

**Engagement ID**: ENG-2025-XXX
**Date**: 2025-XX-XX
**Authorized By**: [Name, Title]

## Purpose
[CTF Competition / Personal Lab / Red Team Exercise / Bug Bounty]

## Scope
**In-Scope Targets**:
- [IP addresses, domains, URLs]

**Out-of-Scope / Excluded**:
- [Production systems, infrastructure, etc.]

## Authorization
- [X] Written permission obtained
- [X] Scope file created: authorized_scope.yaml
- [X] Audit logging configured
- [X] All ethical controls enabled

## Duration
Start: 2025-XX-XX
End: 2025-XX-XX

## Compliance
- [X] Legal review completed
- [X] Complies with CFAA / local laws
- [X] Responsible disclosure policy accepted

**Signature**: ___________________
**Date**: 2025-XX-XX
```

---

## Compliance & Legal

### Legal Frameworks

**United States:**
- Computer Fraud and Abuse Act (CFAA)
- Electronic Communications Privacy Act (ECPA)
- State-specific computer crime laws

**United Kingdom:**
- Computer Misuse Act 1990

**European Union:**
- General Data Protection Regulation (GDPR) - for data handling
- National cybercrime laws

### Audit Requirements

- **Review logs monthly** (minimum)
- **Retain logs for compliance period** (check local laws)
- **Report suspicious activity immediately**
- **Document all engagements**
- **Keep authorization records**

### Incident Response

**If unauthorized access detected:**
1. Immediately stop all v8 activities
2. Review audit logs (v8_audit.log, scope_validation_audit.log)
3. Identify root cause
4. File incident report
5. Update controls to prevent recurrence
6. Notify legal counsel if required

**If scope violation detected:**
1. System auto-rejects via ScopeValidator
2. Review why target was attempted
3. Update scope file if legitimate
4. Document in incident log
5. Retrain user if necessary

---

## Quick Start Guide

### Step 1: Verify Authorization

Before enabling v8, confirm:
- [ ] You have written authorization
- [ ] You understand the legal implications
- [ ] You accept responsibility for your actions

### Step 2: Create Scope File

Create `authorized_scope.yaml`:

```yaml
authorization:
  granted_by: "Your Name"
  granted_date: "2025-11-07"
  expires: "2025-12-31"
  purpose: "CTF Competition - HackTheBox"
  engagement_id: "CTF-HTB-001"

targets:
  ip_addresses:
    - "10.10.10.100"  # HTB machine IP

  domains:
    - "*.htb.local"

  excluded:
    - "10.10.10.1"  # VPN gateway
```

### Step 3: Configure v8

Edit `config.yaml`:

```yaml
xbow_mode:
  enabled: true
  ethical_only: true  # REQUIRED

  human_in_loop:
    enabled: true
    approval_timeout: 300
    audit_log: "v8_audit.log"

  scope_validator:
    enabled: true
    scope_file: "authorized_scope.yaml"

  sandbox:
    enabled: true
    default_mode: true
```

### Step 4: Initialize v8 Components

```bash
cd mindsync_oracle
python mindsync_prod.py
```

### Step 5: Use CTF Agent

```python
from ctf_lab_agent import CTFLabAgent

agent = CTFLabAgent(
    threat_hub=threat_hub,
    memory_graph=memory_graph,
    config=config
)

result = agent.solve_challenge(
    target="10.10.10.100",
    challenge_type="web",
    description="WordPress plugin vulnerability"
)

print(f"Flag: {result['flag']}")
```

### Step 6: Monitor Activity

```bash
# Watch audit logs
tail -f v8_audit.log

# Check scope validations
tail -f scope_validation_audit.log
```

---

## Use Case Examples

### Example 1: HackTheBox CTF

**Authorization**: HTB platform subscription
**Scope**: HTB machine IPs (10.10.10.0/24, 10.129.0.0/16)
**Controls**: All enabled, bridge network for HTB VPN

```yaml
# authorized_scope.yaml
authorization:
  granted_by: "HackTheBox Platform"
  granted_date: "2025-11-07"
  expires: "2025-12-31"
  purpose: "CTF Competition - HackTheBox Labs"
  engagement_id: "HTB-SUBSCRIPTION-001"

targets:
  ip_addresses:
    - "10.10.10.0/24"
    - "10.129.0.0/16"
```

**Workflow**:
1. Connect to HTB VPN
2. Start HTB machine (e.g., 10.10.10.100)
3. Use v8 to analyze and solve
4. Approve each reconnaissance/exploit step
5. Submit flag on HTB platform

---

### Example 2: Personal Lab

**Authorization**: Self (own infrastructure)
**Scope**: Home lab network (192.168.1.0/24)
**Controls**: All enabled, network isolation

```yaml
# authorized_scope.yaml
authorization:
  granted_by: "Self (Lab Owner)"
  granted_date: "2025-11-07"
  expires: "2099-12-31"
  purpose: "Personal Security Research Lab"
  engagement_id: "PERSONAL-LAB-001"

targets:
  ip_addresses:
    - "192.168.1.0/24"

  excluded:
    - "192.168.1.1"   # Router
    - "192.168.1.10"  # NAS - production data
```

**Workflow**:
1. Set up vulnerable VMs (Metasploitable, DVWA, etc.)
2. Configure scope file for lab network
3. Use v8 for educational testing
4. Learn exploitation techniques safely

---

### Example 3: Authorized Red Team Engagement

**Authorization**: Written engagement agreement
**Scope**: Client-defined in-scope targets
**Controls**: All enabled, strict scope enforcement

```yaml
# authorized_scope.yaml
authorization:
  granted_by: "Client CISO - Jane Doe"
  granted_date: "2025-11-01"
  expires: "2025-11-30"
  purpose: "Authorized Red Team Exercise"
  engagement_id: "REDTEAM-CLIENT-2025-Q4"

targets:
  ip_addresses:
    - "203.0.113.0/24"  # Client test network

  domains:
    - "*.test.client.com"

  excluded:
    - "203.0.113.1"     # Client firewall
    - "prod.client.com" # Production (explicitly excluded)
```

**Workflow**:
1. Sign engagement agreement with client
2. Receive written authorization and scope definition
3. Configure v8 with client-approved scope
4. Conduct testing with human approval for each action
5. Document all activities for client report
6. Deliver findings and recommendations

---

### Example 4: Bug Bounty Research (HackerOne, Bugcrowd)

**Authorization**: Bug bounty program terms
**Scope**: Program-defined in-scope targets
**Controls**: All enabled, manual submission only

```yaml
# authorized_scope.yaml
authorization:
  granted_by: "Bug Bounty Program - Example Corp"
  granted_date: "2025-11-07"
  expires: "2026-11-07"
  purpose: "Bug Bounty Research (Manual Submission)"
  engagement_id: "BUGBOUNTY-EXAMPLECORP"

targets:
  domains:
    - "*.example.com"

  urls:
    - "https://app.example.com/*"

  excluded:
    - "status.example.com"  # Status page excluded by program
```

**Workflow**:
1. Read bug bounty program scope and rules
2. Configure v8 with program-approved targets
3. Use v8 for vulnerability research (reconnaissance, analysis)
4. Predict exploitation chains (DO NOT exploit without approval)
5. **MANUALLY** test predicted vulnerabilities
6. Submit findings through bug bounty platform (not automated)

**Important**: v8 for research ONLY. Manual testing and submission required.

---

## Questions & Support

**Ethical Concerns**: Review this document, consult legal counsel

**Technical Issues**: Check logs (v8_audit.log, mindsync.log)

**Authorization**: Contact your security team or legal department

**Bug Reports**: Open issue on GitHub (no exploit details in public issues)

---

## Acknowledgment

By enabling v8, you acknowledge:

- ✅ You have read and understood these guidelines
- ✅ You have proper authorization for your use case
- ✅ You will use v8 ethically and legally
- ✅ You accept full responsibility for your actions
- ✅ You will immediately report any violations
- ✅ You understand the legal implications (CFAA, etc.)
- ✅ You will maintain human control over all actions
- ✅ You will not bypass ethical safeguards

**If you cannot check all boxes above, DO NOT enable v8.**

---

**Last Updated**: 2025-11-07
**Version**: 8.0
**Status**: Production with Multi-Layer Ethical Safeguards Active

---

## Appendix: Comparison with XBOW

| Feature | XBOW (Original) | MindSync v8 (Ethical) |
|---------|----------------|----------------------|
| **Autonomy** | Fully autonomous | Human-in-loop (mandatory) |
| **Target Selection** | Unrestricted | Hard scope enforcement |
| **Execution** | Direct host | Sandboxed containers |
| **Approval** | None required | Every action requires approval |
| **Scope Control** | None | authorized_scope.yaml with hard rejection |
| **Audit Trail** | Unknown | Comprehensive (v8_audit.log) |
| **Use Case** | Offensive testing | Ethical research, CTF, authorized testing |
| **Legal Risk** | High (if misused) | Mitigated (with proper use) |

**Summary**: v8 takes XBOW's breakthrough AI reasoning for vulnerability analysis and adds **ethical controls** to make it safe for authorized research.

---

**Remember**: Powerful tools require responsible use. MindSync Oracle v8 is designed for ethical hackers, researchers, and defenders. Use it wisely. 🛡️
