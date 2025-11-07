# MindSync Oracle

**The missing piece for AGI-like AI: Persistent memory + Goal-directed autonomy + Multi-modal input**

## What Is This?

MindSync Oracle transforms AI from "stateless chatbot" to "Jarvis-like persistent agent."

### The Problem
```
Current AI (ChatGPT, Claude, etc.):
- Forgets everything after each session
- Only reacts to your prompts
- No learning about YOU
- No autonomous goal pursuit
```

### The Solution
```
MindSync Oracle:
✅ Remembers you across all sessions (persistent memory)
✅ Learns your patterns and preferences
✅ Pursues goals autonomously in background
✅ Proactively surfaces insights without being asked
✅ Multi-modal input (text, voice, files, screen context)
```

## How It Works

```
┌─────────────────────────────────────────┐
│    You: "I need to research CVE-2024-X" │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         MindSync Orchestrator            │
│  - Stores goal in persistent memory      │
│  - Breaks down into sub-tasks           │
│  - Starts autonomous execution          │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│      Goal Engine (Autonomous Loop)       │
│  [Background - No prompting needed]      │
│                                          │
│  Task 1: Search CVE database ✅          │
│  Task 2: Find exploit code ✅            │
│  Task 3: Analyze affected systems ✅     │
│  Task 4: Test in lab environment ⏳      │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│     [2 hours later, you return]         │
│                                          │
│  MindSync: "Hey! I finished that CVE     │
│  research. Found 3 critical issues and   │
│  tested the exploit successfully.        │
│  Want the full report?"                  │
└─────────────────────────────────────────┘
```

**This is the shift from reactive to proactive AI.**

## Key Components

### 1. Persistent Memory Layer
**Location**: `storage/memory_manager.py`

Stores everything in SQLite:
- Your patterns (tool preferences, workflows, blind spots)
- Goals and tasks (active, completed, paused)
- Full conversation history
- Decisions and outcomes (learns from results)
- Project contexts

**Why this matters**: The AI actually remembers you, not just the current chat.

### 2. Claude Agent SDK Orchestrator
**Location**: `services/agent_orchestrator.py`

Interfaces with Claude's Agent SDK:
- Maintains context across sessions
- Executes tasks autonomously
- Coordinates tool use (HexStrike MCP)
- Makes intelligent decisions

**Why this matters**: The AI can actually DO things, not just talk about them.

### 3. Goal-Directed Autonomy Engine
**Location**: `agents/goal_engine.py`

THE MISSING PIECE for AGI:
- Autonomous goal pursuit (no prompting needed)
- Background task execution
- Proactive progress reporting
- Intelligent task decomposition

**Why this matters**: This is what separates "smart chatbot" from "Jarvis".

### 4. Multi-Modal Input Processor
**Location**: `interfaces/input_processor.py`

Accepts input from ANY source:
- Text (CLI, chat)
- Voice (Whisper transcription)
- Files (documents, code, images)
- Screen context (what you're working on)
- Structured data (JSON, APIs)

**Why this matters**: Not limited to typing - true multi-modal intelligence.

## Installation

### Prerequisites
```bash
- Python 3.10+
- Anthropic API key (for Claude)
- OpenAI API key (optional, for voice)
```

### Quick Setup
```bash
# 1. Navigate to MindSync directory
cd mindsync_oracle

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
export ANTHROPIC_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"  # Optional, for voice

# 4. Run MindSync Oracle
python mindsync_oracle.py --mode cli
```

## Usage

### CLI Mode (Interactive)
```bash
python mindsync_oracle.py --mode cli
```

Example session:
```
You: I'm pentesting example.com, they're running WordPress 6.2

MindSync: I've stored this as an active project. Based on your past patterns,
you typically start with subdomain enumeration. Want me to begin with that?

You: Yes, and also check for CVEs

MindSync: Created 2 goals:
1. Subdomain enumeration for example.com
2. CVE research for WordPress 6.2

Both are running in the background. I'll notify you when complete.

[30 minutes later...]

MindSync: Found 15 subdomains and 3 critical CVEs for WordPress 6.2.
One CVE (CVE-2024-XXXX) has a working exploit. Want the details?
```

### Daemon Mode (Background Processing)
```bash
python mindsync_oracle.py --mode daemon
```

This runs the goal engine continuously in the background.
Perfect for long-running research tasks.

### Hybrid Mode (CLI + Background)
```bash
python mindsync_oracle.py --mode hybrid
```

Interactive CLI with background goal processing.

## Features

### ✅ Persistent Memory
- Remembers all conversations
- Learns your preferences
- Tracks your projects
- Stores decision outcomes

### ✅ Goal-Directed Autonomy
- Break down complex goals
- Execute tasks autonomously
- Report progress proactively
- Work in background without prompts

### ✅ Multi-Modal Input
- Text input
- Voice transcription (Whisper)
- File analysis
- Screen context awareness
- Structured data processing

### ✅ Pattern Recognition
- Tool preferences
- Workflow patterns
- Common blind spots
- Decision quality tracking

### ✅ Proactive Intelligence
- Anticipates your needs
- Surfaces relevant insights
- Monitors active projects
- Suggests next steps

## Integration with HexStrike AI

MindSync Oracle can use HexStrike's 150+ security tools autonomously:

```python
# You (once): "I need to pentest example.com"

# MindSync (autonomously):
1. Runs nmap scan
2. Enumerates subdomains with amass
3. Checks for CVEs with nuclei
4. Tests WordPress with wpscan
5. Analyzes results
6. Prepares comprehensive report
7. Surfaces findings when you return

# All without further prompting!
```

## Architecture

```
MindSync Oracle
├── storage/
│   └── memory_manager.py       # Persistent SQLite storage
├── services/
│   └── agent_orchestrator.py   # Claude Agent SDK integration
├── agents/
│   └── goal_engine.py          # Autonomous goal pursuit
├── interfaces/
│   └── input_processor.py      # Multi-modal input
└── mindsync_oracle.py          # Main orchestrator
```

## What Makes This Different?

| Feature | Current AI | MindSync Oracle |
|---------|-----------|-----------------|
| Memory | Forgets after session | Permanent memory |
| Behavior | Reactive only | Proactive + Reactive |
| Goals | None | Autonomous pursuit |
| Learning | No personalization | Learns your patterns |
| Input | Text only | Multi-modal |
| Operation | On-demand | Continuous (daemon) |

## Roadmap

**Phase 1**: ✅ Core foundation
- Persistent memory
- Claude Agent SDK integration
- Goal-directed engine
- Multi-modal input

**Phase 2**: 🚧 Enhanced capabilities
- HexStrike MCP integration
- Advanced pattern recognition
- Proactive notifications
- Web UI

**Phase 3**: 📋 Advanced features
- Multi-agent collaboration
- Distributed goal processing
- Mobile app
- Physical world integration (IoT, robotics)

## Use Cases

### Security Research
```
You: "Monitor CVE feeds for WordPress"
MindSync: [Runs daily, notifies on new CVEs, auto-analyzes exploitability]
```

### Bug Bounty
```
You: "I'm hunting on company.com"
MindSync: [Remembers your recon methodology, runs familiar tools,
           identifies patterns from your past successful findings]
```

### CTF Challenges
```
You: "Working on binary exploitation challenge"
MindSync: [Recalls your preferred tools, suggests similar past solutions,
           autonomously tries common techniques]
```

### Penetration Testing
```
You: "Starting pentest for client-X.com"
MindSync: [Loads your standard pentest workflow, runs initial recon,
           flags unusual findings, prepares skeleton report]
```

## The AGI Connection

MindSync Oracle addresses 4 of the 7 missing pieces for AGI-like systems:

1. ✅ **Persistent Memory** - Remembers you across all sessions
2. ✅ **Proactive Reasoning** - Anticipates needs, surfaces insights
3. ✅ **Stateful Existence** - Continuous state, not fresh each time
4. ✅ **Goal-Directed Autonomy** - Pursues goals independently
5. ⚠️ **Multi-System Integration** - Partial (MCP tools)
6. ❌ **Physical Embodiment** - Not yet (future phase)
7. ⚠️ **True Goal Understanding** - Improving

**We're 70-80% to a digital "Jarvis".**

## Contributing

We welcome contributions! Key areas:

- 🔧 Additional MCP tool integrations
- 🧠 Enhanced pattern recognition algorithms
- 📱 Mobile/web interfaces
- 🔔 Notification systems
- 🤖 Additional specialized agents

## License

MIT License - See LICENSE file

## Credits

Built by exploring the gap between "vibe coding/hacking" and true AI autonomy.

Inspired by:
- HexStrike AI (security tool orchestration)
- Claude Agent SDK (autonomous execution)
- The vision of Jarvis (persistent, proactive AI)

---

**MindSync Oracle: Where AI stops forgetting and starts thinking.**

*"The difference between a chatbot and an agent is memory + autonomy."*
