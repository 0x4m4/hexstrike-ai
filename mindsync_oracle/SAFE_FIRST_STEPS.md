# MindSync Oracle - Safe First Steps Guide

**For when you built a 16,500 line autonomous AI agent and you're rightfully scared to run it.** 😅

---

## Your Fear is Valid

You built:
- Autonomous goal execution (runs 24/7)
- Real-time threat monitoring (X + Tor + CVE feeds)
- Offensive security tools (via HexStrike)
- XBOW-inspired vulnerability research
- Federated swarm coordination

**Being scared is the CORRECT response.** This deserves careful testing.

---

## The Safe Testing Strategy

### **Principle**: Start passive, work up to active

**Level 1**: Read-only observation (can't break anything)
**Level 2**: Manual tool execution (you control everything)
**Level 3**: Autonomous monitoring (goals with safe boundaries)
**Level 4**: Active security testing (with all safeguards)

**Timeline**: 1 week per level minimum

---

## Level 1: Passive Observation (Week 1)

**Goal**: Let MindSync observe and remember, but take NO actions

### **Step 1.1: Start with Memory Only**

```bash
cd mindsync_oracle

# Edit config.yaml - DISABLE everything active
```

**Config for Level 1**:
```yaml
# Disable ALL autonomous features
goals:
  check_interval_seconds: 9999999  # Effectively disabled

hexstrike:
  enabled: false  # No tool execution

xai:
  enabled: false  # No Grok yet

llm_router:
  intelligence: "claude"  # Claude only for now
  tools: "claude"

deep_x:
  enabled: false  # No X researcher tracking

swarm:
  enabled: false  # No federation

realtime_x:
  enabled: false  # No live X monitoring

tor_osint:
  enabled: false  # No Tor

unified_threat_hub:
  enabled: false  # No threat correlation

xbow_mode:
  enabled: false  # No vulnerability research

v9_orchestration:
  enabled: false  # No MCP/parallel

# ONLY enable basic memory
database:
  path: "mindsync_memory.db"
  graph_path: "mindsync_graph.pkl"
  backup_enabled: true
```

### **Step 1.2: Test Basic Memory**

```python
# test_basic_memory.py
from mindsync_oracle.memory import MemoryManager

# Initialize
memory = MemoryManager(db_path="test_memory.db")

# Store a simple fact
memory.store_conversation("user", "MindSync, remember: My test lab IP is 192.168.1.100")
memory.store_conversation("assistant", "Stored. Your test lab IP is 192.168.1.100")

# Retrieve
history = memory.get_recent_conversations(limit=10)
print("Memory test:", history)

# Check patterns
patterns = memory.get_patterns()
print("Patterns learned:", patterns)
```

**Expected**: Memory stores and retrieves. No actions taken.

**If this fails**: Fix before proceeding.

### **Step 1.3: Test Memory Graph (v3)**

```python
# test_memory_graph.py
from mindsync_oracle.hybrid_memory_graph import HybridMemoryGraph

graph = HybridMemoryGraph()

# Add some test nodes
graph.add_entity("CVE-2025-TEST", "cve", {"severity": "HIGH", "description": "Test vulnerability"})
graph.add_entity("WordPress", "software", {"version": "5.8"})
graph.add_relationship("CVE-2025-TEST", "WordPress", "affects", weight=0.9)

# Query
vulns = graph.find_related_entities("WordPress", relationship_type="affects")
print("Found vulnerabilities:", vulns)

# Save graph
graph.save()
```

**Expected**: Graph operations work. File saved to mindsync_graph.pkl.

**Safety**: This is 100% local, no external connections.

---

## Level 2: Manual Tool Execution (Week 2)

**Goal**: Use MindSync to execute tools, but YOU initiate everything

### **Step 2.1: Enable HexStrike (Manual Mode)**

**Prerequisites**:
- HexStrike server running on localhost:8888
- Test target ready (your own VM/container)

**Config**:
```yaml
hexstrike:
  enabled: true
  server_url: "http://localhost:8888"
  timeout_seconds: 300
  auto_load_tools: true

# Goals still disabled
goals:
  check_interval_seconds: 9999999
```

### **Step 2.2: Test One Tool**

```python
# test_hexstrike_manual.py
from mindsync_oracle.hexstrike_integration import HexStrikeClient

client = HexStrikeClient(server_url="http://localhost:8888")

# Discover tools
tools = client.list_tools()
print("Available tools:", tools)

# Execute ONE safe tool (whoami on localhost)
result = client.execute_tool("whoami", target="localhost")
print("Result:", result)
```

**Expected**: Tool executes, result returns, stored in memory.

**Safety Check**:
- Only run on YOUR infrastructure
- Start with read-only tools (whoami, uname, etc.)
- NO scanning of external IPs yet

### **Step 2.3: Test v9 MCP Integration (Read-Only)**

```python
# test_mcp_nist.py
from mindsync_oracle.mcp_integration import MCPIntegration
import asyncio

async def test_nist():
    mcp = MCPIntegration(config={
        'mcp': {
            'nist': {'enabled': True}
        }
    })

    # Query a real CVE (read-only, public API)
    result = await mcp.nist_cve_lookup("CVE-2024-1086")
    print("CVE Details:", result)

asyncio.run(test_nist())
```

**Expected**: NIST API returns CVE data, no side effects.

**Safety**: Public read-only API, no authentication needed.

---

## Level 3: Autonomous Monitoring (Week 3)

**Goal**: Let MindSync work autonomously, but with SAFE goals only

### **Step 3.1: Enable Goals (Limited)**

**Config**:
```yaml
goals:
  check_interval_seconds: 300  # Check every 5 minutes
  max_concurrent_goals: 1      # ONE goal at a time
  auto_decompose: false        # No automatic sub-goals
  proactive_reporting: true

# Still keep these disabled
hexstrike:
  enabled: false  # No tool execution in autonomous mode yet

xbow_mode:
  enabled: false  # No vulnerability research yet
```

### **Step 3.2: Create Safe Goal**

```python
# test_safe_goal.py
from mindsync_oracle.goal_engine import GoalEngine

engine = GoalEngine(memory, config)

# Safe goal: Monitor a CVE (read-only)
goal = engine.create_goal(
    description="Monitor CVE-2024-1086 for new discussions",
    goal_type="monitoring",
    constraints={
        'read_only': True,
        'no_tool_execution': True,
        'check_interval_minutes': 30
    }
)

print(f"Goal created: {goal.id}")
print("MindSync will check every 30 minutes and report findings.")
```

**Expected**: Goal runs in background, reports updates, takes NO actions.

**Monitor**:
```bash
tail -f mindsync.log
```

**If goal misbehaves**: Kill process, check logs, fix before proceeding.

### **Step 3.3: Enable v7 Threat Monitoring (NIST Only)**

**Config**:
```yaml
unified_threat_hub:
  enabled: true  # Enable threat correlation
  auto_goal_confidence_threshold: 0.95  # Very high threshold
  auto_goal_min_sources: 3  # Need 3+ sources
  auto_goal_cooldown: 86400  # 24 hour cooldown

# Enable ONLY NIST feed (no X, no Tor yet)
# This requires code modification to disable X/Tor feeds
# For safety, comment out X/Tor collection in unified_threat_hub.py
```

**Why NIST only**: Public, read-only, well-documented API. No risk.

**Test**:
- Let it run for 24 hours
- Check what threats it detects
- Verify no auto-goals created (threshold is very high)

---

## Level 4: Active Testing (Week 4+)

**Goal**: Use offensive security features, but with ALL safeguards active

### **Step 4.1: Enable v8 XBOW (Safeguards ON)**

**Prerequisites**:
- Create `authorized_scope.yaml` with ONLY your test infrastructure
- Understand every line of V8_ETHICAL_GUIDELINES.md

**Config**:
```yaml
xbow_mode:
  enabled: true
  ethical_only: true  # REQUIRED

  human_in_loop:
    enabled: true  # MANDATORY
    approval_timeout: 300

  scope_validator:
    enabled: true  # MANDATORY
    scope_file: "authorized_scope.yaml"

  sandbox:
    enabled: true  # MANDATORY
    default_mode: true
    image: "kalilinux/kali-rolling"
    network_mode: "none"  # Fully isolated
```

**Scope File** (`authorized_scope.yaml`):
```yaml
authorization:
  granted_by: "You"
  granted_date: "2025-11-10"
  expires: "2025-12-31"
  purpose: "Personal Lab Testing"
  engagement_id: "TEST-001"

targets:
  ip_addresses:
    - "127.0.0.1"           # Localhost only
    - "192.168.1.100"       # Your test VM

  domains:
    - "*.test.local"        # Local domains only

  excluded:
    - "192.168.1.1"         # Router - never touch
```

### **Step 4.2: Test v8 CTF Agent (Safest Active Feature)**

**Why CTF Agent is safest**:
- Designed for authorized environments (HackTheBox, etc.)
- Every step requires human approval
- Sandboxed execution
- Clear scope validation

**Test on HackTheBox**:
```python
# test_ctf_agent.py
from mindsync_oracle.ctf_lab_agent import CTFLabAgent

# Prerequisites: HackTheBox VPN connected, machine IP known

agent = CTFLabAgent(
    threat_hub=None,  # Optional
    memory_graph=graph,
    hexstrike_client=hexstrike,
    config=config
)

# Solve ONE easy HTB machine
result = agent.solve_challenge(
    target="10.10.10.27",  # HTB machine IP
    challenge_type="web",
    description="Easy web challenge - SQL injection suspected"
)

# Agent will:
# 1. Validate scope (HTB IP in authorized_scope.yaml)
# 2. Analyze challenge
# 3. Request approval for EACH step
# 4. Execute in sandbox
# 5. Capture flag
# 6. Generate writeup

print(f"Flag: {result['flag']}")
```

**Safety During Test**:
- ✅ You approve every action
- ✅ Scope validator blocks unauthorized IPs
- ✅ Sandbox contains all tool execution
- ✅ Audit log records everything
- ✅ You can abort at any time

### **Step 4.3: Monitor Yourself**

**During Level 4 testing, actively monitor**:

```bash
# Terminal 1: Watch audit logs
tail -f v8_audit.log

# Terminal 2: Watch scope validation
tail -f scope_validation_audit.log

# Terminal 3: Watch main logs
tail -f mindsync.log

# Terminal 4: Check running containers
watch -n 1 'docker ps'
```

**Red flags to watch for**:
- ❌ Out-of-scope targets attempted
- ❌ Unapproved actions executing
- ❌ Sandbox bypass attempts
- ❌ Unexpected network connections

**If you see red flags**: STOP, investigate, fix before continuing.

---

## Emergency Stop Procedures

### **If Something Goes Wrong**

**Immediate Actions**:
```bash
# 1. Kill MindSync process
pkill -f mindsync_prod.py

# 2. Stop all Docker containers
docker stop $(docker ps -q)

# 3. Disconnect from VPN (if testing on HTB)
# Varies by VPN client

# 4. Check audit logs
cat v8_audit.log | tail -n 50
cat scope_validation_audit.log | tail -n 50
```

**Investigate**:
```bash
# What was MindSync trying to do?
grep "ERROR" mindsync.log

# What got blocked by scope validator?
grep "REJECTED" scope_validation_audit.log

# What actions were approved/rejected?
grep "APPROVED\|REJECTED" v8_audit.log
```

**Before Restarting**:
- Identify root cause
- Fix configuration
- Add additional safeguards
- Test in even more isolated environment

---

## Safety Checklist Before Each Level

### **Before Level 1** (Passive Observation):
- [ ] Database path configured (local only)
- [ ] No external API keys configured yet
- [ ] All autonomous features disabled in config

### **Before Level 2** (Manual Tools):
- [ ] HexStrike server running (isolated network)
- [ ] Test VM/container ready (YOUR infrastructure only)
- [ ] No production IPs in any configs
- [ ] Goals still disabled

### **Before Level 3** (Autonomous Monitoring):
- [ ] Understand goal engine behavior
- [ ] Safe monitoring goal defined (read-only)
- [ ] Log monitoring setup (tail -f)
- [ ] Kill switch tested (pkill)

### **Before Level 4** (Active Testing):
- [ ] Read V8_ETHICAL_GUIDELINES.md completely
- [ ] authorized_scope.yaml created (test IPs ONLY)
- [ ] All safeguards enabled (human-in-loop, scope, sandbox)
- [ ] Docker installed and tested
- [ ] Audit log monitoring active
- [ ] Emergency stop procedure practiced
- [ ] Backup of configs made

---

## Confidence Building Exercises

### **Exercise 1: Scope Validator Test**

**Goal**: Verify scope validator ACTUALLY blocks unauthorized targets

```python
# test_scope_enforcement.py
from mindsync_oracle.scope_validator import ScopeValidator

validator = ScopeValidator(scope_file="authorized_scope.yaml")

# Test 1: In-scope IP (should pass)
assert validator.validate_target("192.168.1.100") == True

# Test 2: Out-of-scope IP (should FAIL)
assert validator.validate_target("8.8.8.8") == False

# Test 3: Excluded IP (should FAIL even if in range)
assert validator.validate_target("192.168.1.1") == False

print("✅ Scope validator working correctly")
```

### **Exercise 2: Human-in-Loop Test**

**Goal**: Verify approval system ACTUALLY blocks without consent

```python
# test_approval_gate.py
from mindsync_oracle.human_in_loop_controller import HumanInLoopController, Action

controller = HumanInLoopController()

action = Action(
    action_type="reconnaissance",
    description="Test action - should require approval",
    command="whoami",
    risk_level="low"
)

# Non-interactive mode (should auto-reject)
approved = controller.request_approval(action, interactive=False)
assert approved == False, "ERROR: Action approved without human interaction!"

print("✅ Human-in-loop blocking correctly")
```

### **Exercise 3: Sandbox Test**

**Goal**: Verify tools ACTUALLY run in containers, not on host

```python
# test_sandbox_isolation.py
from mindsync_oracle.sandbox_executor import SandboxExecutor
import asyncio

async def test():
    executor = SandboxExecutor(image="alpine:latest", network_mode="none")

    # Try to access host filesystem (should FAIL in container)
    result = await executor.execute("cat /etc/hostname", timeout=10)

    # Verify it's container hostname, not host
    assert result.stdout != open('/etc/hostname').read(), "ERROR: Not sandboxed!"

    print("✅ Sandbox isolation working correctly")

asyncio.run(test())
```

**Run these tests BEFORE Level 4**. If any fail, DO NOT proceed.

---

## Gradual Feature Enablement

**After completing all 4 levels safely, enable features one at a time**:

### **Week 5: Enable Grok (v4 Multi-LLM)**
- Add XAI_API_KEY
- Test Grok vs Claude routing
- Monitor for unexpected behavior

### **Week 6: Enable v5 Deep X (Social OSINT)**
- Start with small researcher set (5-10)
- Monitor X API usage
- Verify no rate limit violations

### **Week 7: Enable v6 Swarm (Multi-Oracle)**
- Start with 2 oracles (not 10)
- Test local coordination
- Verify consensus mechanism

### **Week 8: Enable v7 Full Threat Hub**
- Add X monitoring (start with 1-2 keywords)
- Tor OSINT (ethical mode, approved domains only)
- Cross-source correlation

**Principle**: Add ONE major feature per week. Monitor for issues before adding next.

---

## Signs You're Ready for Production

After 8+ weeks of safe testing:

✅ **Memory**: Stores/retrieves correctly, no corruption
✅ **Goals**: Execute autonomously without runaway behavior
✅ **Tools**: Execute in sandbox, results as expected
✅ **Safeguards**: Scope validator blocks unauthorized, human-in-loop works
✅ **Monitoring**: Logs are clean, no unexpected errors
✅ **Performance**: Acceptable speed, no resource exhaustion
✅ **Understanding**: You know what every component does
✅ **Confidence**: You trust the system (but verify)

**If any item is unchecked**: Not ready for production yet.

---

## What "Production Ready" Means

For MindSync Oracle:
- Run autonomously for 24+ hours without issues
- Goals complete successfully
- All safeguards working as designed
- Audit logs clean and understandable
- You sleep well knowing it's running

**Production ≠ Fully Autonomous on the Internet**

Even in "production":
- Keep scope tightly controlled (authorized targets only)
- Monitor logs regularly
- Review audit trails
- Human approval for high-risk actions
- Gradual expansion of trust

---

## Final Advice

### **From someone who just helped you build this**:

1. **Your fear is healthy**. Keep it. Paranoia is a feature in security tools.

2. **Start SMALL**. Level 1 (passive observation) for a full week minimum. Boring is good.

3. **Trust the safeguards**. We built 5 layers for a reason. Test them BEFORE Level 4.

4. **Document everything**. When something weird happens (it will), you'll want logs.

5. **No production testing**. EVER. Only test on infrastructure you own or are explicitly authorized for.

6. **Ask for help**. If something seems wrong, stop and investigate. No shame in caution.

7. **Enjoy the journey**. You built something genuinely impressive. Test it safely, use it ethically.

---

## Resources

- **V8_ETHICAL_GUIDELINES.md**: Read before Level 4
- **V10_PARLIAMENT_PROPOSAL.md**: Future enhancements (after validation)
- **config.yaml**: Your control panel (start conservative)
- **authorized_scope.yaml.example**: Template for Level 4

**Support**: If stuck, check logs first. Most issues are config-related.

---

**Status**: Ready for Level 1 when you are
**Timeline**: Minimum 4 weeks (1 week per level)
**Outcome**: Confidence in a 16,500 line system you built yourself

**You got this. Start small. Move carefully. MindSync will be there when you're ready.** 🛡️
