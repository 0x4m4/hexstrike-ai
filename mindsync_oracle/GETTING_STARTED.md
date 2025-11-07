# Getting Started with MindSync Oracle

## What You Just Built

You've created **MindSync Oracle** - an AI system that addresses the fundamental gap between "smart chatbot" and "AGI-like agent."

### The 4 Missing Pieces You Solved:

1. ✅ **Persistent Memory** - AI that actually remembers you
2. ✅ **Goal-Directed Autonomy** - AI that pursues goals without constant prompting
3. ✅ **Multi-Modal Input** - Not just text, but voice, files, screen context
4. ✅ **Proactive Intelligence** - AI that anticipates needs and surfaces insights

## Quick Start

### 1. Install Dependencies

```bash
cd mindsync_oracle
pip install -r requirements.txt
```

**Note**: Some dependencies (like anthropic, openai) require API keys.

### 2. Set Up API Keys

```bash
# Required for Claude Agent SDK
export ANTHROPIC_API_KEY="your-anthropic-key"

# Optional for voice input
export OPENAI_API_KEY="your-openai-key"
```

### 3. Run the Demo

```bash
python demo.py
```

This demonstrates all 5 core capabilities without requiring API keys.

### 4. Try Interactive Mode

```bash
# CLI mode (once you have ANTHROPIC_API_KEY)
python mindsync_oracle.py --mode cli

# Daemon mode (background processing)
python mindsync_oracle.py --mode daemon

# Hybrid mode (both)
python mindsync_oracle.py --mode hybrid
```

## Architecture Overview

```
mindsync_oracle/
├── storage/
│   └── memory_manager.py          # Persistent SQLite memory
│
├── services/
│   └── agent_orchestrator.py      # Claude Agent SDK integration
│
├── agents/
│   └── goal_engine.py              # Autonomous goal pursuit
│
├── interfaces/
│   └── input_processor.py          # Multi-modal input handling
│
├── mindsync_oracle.py              # Main orchestrator
├── demo.py                         # Capability demonstrations
├── requirements.txt                # Dependencies
├── README.md                       # Full documentation
├── ARCHITECTURE.md                 # Technical architecture
└── GETTING_STARTED.md              # This file
```

## How It Works

### 1. Persistent Memory

**Without MindSync:**
```
Session 1:
You: "I'm pentesting example.com"
AI: "Great! How can I help?"
[Session ends - all context lost]

Session 2:
You: "What was I working on?"
AI: "I don't have that information"
```

**With MindSync:**
```
Session 1:
You: "I'm pentesting example.com"
AI: "Noted. I've created a project context."
[Session ends - context saved to SQLite]

Session 2:
You: "What was I working on?"
AI: "You're pentesting example.com. You ran nmap
     and found 3 open ports. Want to continue?"
```

### 2. Goal-Directed Autonomy

**Without MindSync:**
```
You: "Research CVE-2024-1234"
AI: "Here's what I found: [info]"
[Done - no further action]
```

**With MindSync:**
```
You: "Research CVE-2024-1234"
AI: "I've created a research goal with 4 sub-tasks.
     Working on it now..."

[2 hours later, you're away]
AI: [Autonomously: finds CVE details, locates exploit
     code, tests in lab, prepares report]

[You return]
AI: "Hey! Finished that CVE research. Found working
     exploit and tested successfully. Want the report?"
```

### 3. Multi-Modal Input

```python
# Text
oracle.chat("Scan example.com")

# Voice
oracle.voice_input("audio.wav")  # Transcribed via Whisper

# Files
oracle.file_input("targets.txt")  # Analyzed and processed

# Screen Context
processor.process_screen_context({
    "active_window": "Terminal",
    "clipboard": "192.168.1.1"
})
```

### 4. Pattern Learning

After using MindSync for a while:

```
AI: "I've noticed you always start with subdomain
     enumeration using amass. Should I run that first?"

AI: "You tend to miss API endpoints in your scans.
     Want me to add that to your workflow?"

AI: "Last 3 pentests, you preferred Feroxbuster over
     Gobuster. Setting that as default?"
```

### 5. Proactive Intelligence

```
[You're working on project X]

[AI autonomously in background:]
- Monitors for new CVEs affecting project X
- Checks if target has new exposed services
- Compares findings against vulnerability databases
- Surfaces high-priority items immediately

[Notification when you return:]
AI: "New critical finding for project X:
     CVE-2024-YYYY affects the WordPress version
     you identified. Exploit is public. Want details?"
```

## Integration with HexStrike AI

MindSync Oracle can use HexStrike's 150+ security tools:

```python
# In agent_orchestrator.py, load HexStrike tools:

from hexstrike_mcp import mcp

mcp_tools = {
    "nmap_scan": mcp.tools.nmap_scan,
    "nuclei_scan": mcp.tools.nuclei_scan,
    "gobuster_scan": mcp.tools.gobuster_scan,
    # ... all 150+ tools
}

orchestrator = ClaudeAgentOrchestrator(
    memory,
    mcp_tools=mcp_tools
)
```

Then the autonomous agent can use them:

```
You: "I need to pentest example.com"

AI: [Autonomously:]
    1. Runs amass for subdomain enum
    2. Runs nmap on discovered hosts
    3. Runs nuclei for vulnerability scan
    4. Runs gobuster for directory discovery
    5. Analyzes all results
    6. Prepares comprehensive report

    [All without further prompting!]
```

## Use Cases

### Security Research
```bash
python mindsync_oracle.py --mode daemon

# In another terminal:
python -c "
from mindsync_oracle import MindSyncOracle
oracle = MindSyncOracle()
oracle.add_goal('Monitor CVE feeds for WordPress daily')
"

# Now MindSync runs in background, checking CVEs,
# and notifies you of relevant findings
```

### Bug Bounty
```python
oracle = MindSyncOracle()

# Set up a program
await oracle.chat("I'm hunting on bugcrowd.com/company-x")

# MindSync remembers:
# - Your recon methodology
# - Tools you prefer
# - Common blind spots
# - Previous successful techniques

# Next session:
await oracle.chat("Continue where we left off")
# AI knows exactly what you were doing!
```

### CTF Challenges
```python
# MindSync learns your CTF patterns:
# - Crypto: you use factordb first
# - Web: you check for SQLi via sqlmap
# - Binary: you prefer pwntools + gdb-gef

await oracle.chat("New CTF challenge: [binary]")
# AI suggests your usual approach automatically
```

## Advanced Features

### Custom Agents

You can create specialized agents:

```python
class CustomSecurityAgent:
    def __init__(self, memory_manager):
        self.memory = memory_manager

    async def analyze(self, target):
        # Your custom logic
        pass

# Register with orchestrator
orchestrator.register_agent("custom_sec", CustomSecurityAgent(memory))
```

### Background Monitoring

```python
# Create a monitoring goal
oracle.add_goal(
    "Monitor example.com for changes daily",
    priority="medium"
)

# MindSync will:
# - Run periodic scans
# - Detect changes (new ports, services, subdomains)
# - Alert on significant findings
# - Build a timeline of changes
```

### Decision Learning

```python
# MindSync tracks your decisions
memory.store_decision(
    "Which tool for directory discovery?",
    options=["gobuster", "feroxbuster", "dirsearch"],
    chosen_option="feroxbuster",
    reasoning="Faster and better results"
)

# Later, update outcome
memory.update_decision_outcome(
    decision_id=1,
    outcome="Found 15 directories, including admin panel",
    outcome_quality="good"
)

# Next time:
# AI learns that feroxbuster works well for you
```

## Next Steps

### Phase 1: Core Setup (Now)
- ✅ Set up persistent memory
- ✅ Integrate Claude Agent SDK
- ✅ Implement goal autonomy
- ✅ Add multi-modal input

### Phase 2: Integration (Next)
- [ ] Connect HexStrike MCP tools
- [ ] Add proactive notifications
- [ ] Implement background scheduling
- [ ] Create web UI

### Phase 3: Advanced (Future)
- [ ] Multi-agent collaboration
- [ ] Distributed processing
- [ ] Mobile app
- [ ] Voice-always-on mode

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### "Whisper client not initialized"
```bash
# This is only needed for voice input
export OPENAI_API_KEY="your-key-here"
pip install openai
```

### "Module not found"
```bash
# Make sure you're in the right directory
cd mindsync_oracle
python -m pip install -r requirements.txt
```

### Database locked
```bash
# If SQLite is locked, stop all MindSync processes
pkill -f mindsync_oracle
rm mindsync_memory.db-journal  # If exists
```

## FAQ

**Q: Does this actually work without the full Claude Agent SDK?**
A: The demo works fully offline. The Claude integration requires an API key and is designed for the Agent SDK features when available.

**Q: How is this different from ChatGPT with memory?**
A: ChatGPT memory is summary-based and limited. MindSync has:
- Full persistent database
- Autonomous goal pursuit
- Pattern learning
- Proactive behavior
- Multi-modal input

**Q: Can I use this with other AI models (GPT-4, local LLMs)?**
A: Yes! The orchestrator can be adapted. Just swap out the ClaudeAgentOrchestrator with a GPTOrchestrator or LocalLLMOrchestrator.

**Q: Is my data private?**
A: Yes! Everything is stored locally in SQLite. No data leaves your machine unless you make API calls to Claude/OpenAI.

**Q: How much does it cost to run?**
A: Only when you use Claude API. The demo and memory system are free.

## Resources

- **Full Documentation**: README.md
- **Architecture Details**: ARCHITECTURE.md
- **Demo Script**: demo.py
- **Main Code**: mindsync_oracle.py

## Community

Want to contribute or discuss?

- GitHub: (your repo)
- Discord: (your discord)
- Issues: Report bugs and request features

---

**You've just built the future of AI agents. Welcome to the post-chatbot era.**
