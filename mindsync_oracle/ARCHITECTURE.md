# MindSync Oracle + Claude Agent SDK Architecture

## Vision
Transform from "stateless AI with tools" to "persistent, goal-directed AI agent" - the missing piece for AGI-like capabilities.

## Core Innovation
**Persistent Memory + Autonomous Goal Pursuit + Multi-Modal Input**

### The Gap This Fills
- ❌ **Current AI**: Stateless, reactive, forgets everything
- ✅ **MindSync**: Persistent memory, proactive, learns patterns
- ✅ **Claude Agent SDK**: Autonomous task execution, goal-directed
- ✅ **Combined**: Jarvis-like AI that remembers you, anticipates needs, pursues goals autonomously

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MindSync Oracle Core                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────┐      ┌──────────────────┐              │
│  │  Multi-Modal   │      │  Claude Agent     │              │
│  │  Input Layer   │─────▶│  SDK Orchestrator │              │
│  └────────────────┘      └──────────────────┘              │
│   - Text                          │                          │
│   - Voice (Whisper)               │                          │
│   - Files                         ▼                          │
│   - Screen Context        ┌──────────────────┐              │
│                           │  Goal-Directed    │              │
│                           │  Autonomy Engine  │              │
│                           └──────────────────┘              │
│                                   │                          │
│                                   ▼                          │
│                    ┌─────────────────────────┐              │
│                    │   Specialized Agents     │              │
│                    ├─────────────────────────┤              │
│                    │ • Pattern Recognition   │              │
│                    │ • Perspective Analysis  │              │
│                    │ • Goal Decomposition    │              │
│                    │ • Proactive Research    │              │
│                    │ • Decision Support      │              │
│                    └─────────────────────────┘              │
│                                   │                          │
│                                   ▼                          │
│                    ┌─────────────────────────┐              │
│                    │  Persistent Memory       │              │
│                    ├─────────────────────────┤              │
│                    │ • User patterns (SQLite) │              │
│                    │ • Conversation history   │              │
│                    │ • Goals & tasks          │              │
│                    │ • Decisions & outcomes   │              │
│                    │ • Project context        │              │
│                    └─────────────────────────┘              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Multi-Modal Input Layer (`interfaces/`)
**Purpose**: Accept input from any source, not just voice

**Inputs**:
- **Text**: Direct chat/CLI input
- **Voice**: Whisper API transcription
- **Files**: Documents, code, images
- **Screen Context**: What user is currently working on
- **Structured Data**: JSON, CSV, APIs

**Output**: Normalized `InputEvent` objects

### 2. Claude Agent SDK Orchestrator (`services/agent_orchestrator.py`)
**Purpose**: Central brain using Claude's Agent SDK for autonomous operation

**Capabilities**:
- Receives all inputs from multi-modal layer
- Maintains conversation context
- Spawns specialized sub-agents as needed
- Coordinates tool use (e.g., HexStrike tools)
- Makes autonomous decisions

**Key Difference from Standard Claude**:
- Persistent across sessions
- Can run continuously in background
- Initiates tasks without prompts

### 3. Goal-Directed Autonomy Engine (`agents/goal_engine.py`)
**Purpose**: THE missing piece - proactive goal pursuit

**What It Does**:
```python
# User mentions a goal once
user: "I need to learn about CVE-2024-1234"

# Agent autonomously:
1. Decomposes goal into sub-tasks
2. Researches vulnerability details
3. Finds exploit code
4. Analyzes affected systems
5. Prepares report
6. Proactively presents findings when user returns

# No further prompting needed!
```

**Implementation**:
- Uses Claude Agent SDK's task loop
- Stores goals in persistent memory
- Checks progress on background schedule
- Surfaces results proactively

### 4. Specialized Agents (`agents/`)

**PatternRecognitionAgent**:
- Learns user behavior patterns
- "You always scan ports 80,443,8080 - want me to default to that?"

**PerspectiveAnalysisAgent**:
- Identifies blind spots
- "You're focused on web vulns, but this target has exposed SMB"

**GoalDecompositionAgent**:
- Breaks vague goals into actionable tasks
- "Learn pentesting" → [setup lab, practice scanning, try CTF, etc.]

**ProactiveResearchAgent**:
- Background research on user's projects
- "New CVE affecting your target from last week"

**DecisionSupportAgent**:
- Analyzes past decisions, suggests improvements
- "Last 3 times you chose Gobuster over Feroxbuster, but Ferox found more"

### 5. Persistent Memory Layer (`storage/`)

**Technology**: SQLite + JSON documents

**What Gets Stored**:
```sql
-- User patterns
CREATE TABLE user_patterns (
    id INTEGER PRIMARY KEY,
    pattern_type TEXT,  -- tool_preference, workflow, blind_spot
    pattern_data JSON,
    confidence REAL,
    last_seen TIMESTAMP
);

-- Goals & tasks
CREATE TABLE goals (
    id INTEGER PRIMARY KEY,
    goal_text TEXT,
    status TEXT,  -- active, completed, paused
    sub_tasks JSON,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Conversations
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    input_text TEXT,
    agent_response TEXT,
    context JSON,
    timestamp TIMESTAMP
);

-- Decisions & outcomes
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    decision_context TEXT,
    options JSON,
    chosen_option TEXT,
    outcome TEXT,
    outcome_quality TEXT,  -- good, bad, neutral
    timestamp TIMESTAMP
);
```

**Privacy**: Local-only, encrypted at rest, user-controlled retention

## How It All Works Together

### Example Flow: Autonomous CVE Research

**1. User Input (Multi-Modal)**:
```
User (voice): "I'm working on a pentest for acme.com, they're running WordPress 6.2"
```

**2. Input Processing**:
- Voice → Whisper → Text
- Text → InputEvent → Agent Orchestrator

**3. Agent Orchestrator**:
- Checks persistent memory: "User has project: acme.com"
- Spawns PatternRecognitionAgent: "User scans WordPress sites, typical pattern detected"
- Spawns GoalDecompositionAgent: "Pentest → [recon, vuln scan, exploit]"
- Stores goal in database

**4. Goal-Directed Autonomy**:
```python
# Agent runs autonomously in background
while goal_active:
    - Check for WordPress 6.2 CVEs (new ones appear daily)
    - Run WPScan via HexStrike MCP
    - Analyze results
    - If high-severity found → notify user immediately
    - If medium → add to report
    - Update goal progress
```

**5. Proactive Output** (2 hours later):
```
Agent: "Hey! While you were away, I found 3 vulnerabilities in WordPress 6.2:
- CVE-2024-XXXX (CRITICAL): SQL injection in plugin X
- CVE-2024-YYYY (HIGH): XSS in theme Y
- Already ran exploit scan - site IS vulnerable to CVE-XXXX

Want me to prepare the full pentest report?"
```

**6. Learning**:
- Stores: "User appreciated proactive CVE monitoring"
- Pattern: "For WordPress sites, auto-check CVEs"
- Next time: Does it without being asked

## Integration with HexStrike AI

MindSync uses HexStrike's MCP tools but adds:
- **Memory**: Remembers what you scanned, found, decided
- **Proactivity**: Re-scans targets for new CVEs without prompting
- **Learning**: Adapts to your pentesting style
- **Autonomy**: Pursues goals in background

```python
# HexStrike alone
user: "Scan example.com"
AI: <runs nmap> "Here are results"
[conversation ends, memory lost]

# MindSync + HexStrike
user: "I'm pentesting example.com"
AI: <stores project context>
    <runs nmap, nuclei, gobuster>
    <learns you prefer Feroxbuster>
    "Results saved. I'll monitor for changes daily."
[2 days later]
AI: "New port opened on example.com - port 8080. Investigated: Jenkins server. Checking CVEs..."
```

## Technical Implementation

### Dependencies
- `anthropic` - Claude API with Agent SDK
- `sqlite3` - Persistent storage
- `openai` - Whisper for voice
- `fastmcp` - MCP tool integration (HexStrike)
- `APScheduler` - Background task scheduling

### Key Files
- `services/agent_orchestrator.py` - Claude Agent SDK integration
- `agents/goal_engine.py` - Autonomous goal pursuit
- `agents/pattern_agent.py` - Pattern recognition
- `agents/proactive_agent.py` - Proactive research
- `storage/memory_manager.py` - Persistent memory
- `interfaces/input_processor.py` - Multi-modal input
- `mindsync_oracle.py` - Main orchestrator

## What This Achieves

**Before** (Current AI + Tools):
- Smart but stateless
- Reactive only
- No learning
- Forgets everything

**After** (MindSync Oracle):
- Persistent memory of YOU
- Proactive preparation
- Pattern learning
- Autonomous goal pursuit
- ← **This is the AGI architecture shift**

## Deployment Modes

**1. CLI Mode**:
```bash
python mindsync_oracle.py --mode cli
> "I need to research CVE-2024-1234"
```

**2. Voice Mode**:
```bash
python mindsync_oracle.py --mode voice
[Continuous listening, Whisper transcription]
```

**3. Daemon Mode** (The Game Changer):
```bash
python mindsync_oracle.py --daemon
# Runs in background
# Monitors goals
# Surfaces findings proactively via notifications
```

**4. Hybrid Mode**:
```bash
# API server + Web UI + Background daemon
python mindsync_oracle.py --server --daemon
# Access via browser, background processing continues
```

## Next Steps

1. ✅ Architecture design
2. Build persistent memory layer
3. Integrate Claude Agent SDK
4. Create goal-directed autonomy engine
5. Add multi-modal input processors
6. Implement specialized agents
7. Test with real-world scenarios
8. Deploy as daemon for true proactive operation

---

**This is how we go from "vibe hacking" to true AI autonomy.**
