# MindSync Oracle - Quick Start Guide

## Installation (30 seconds)

```bash
cd mindsync_oracle

# Install dependencies
pip install -r requirements.txt

# Set API key (required for Claude)
export ANTHROPIC_API_KEY="your-key-here"

# Optional: for voice input
export OPENAI_API_KEY="your-openai-key"
```

## Usage

### Option 1: Interactive Mode (Recommended)

```bash
python mindsync_prod.py
```

This starts the interactive CLI where you can chat and manage goals.

**Example session:**
```
You: I'm pentesting example.com, WordPress 6.2

MindSync: Goal created (ID: 1)

I'll work on this autonomously and notify you when complete.

Priority: medium
Status: Queued for execution

---

[Later...]

🔔 Goal Completed ✅
'I'm pentesting example.com, WordPress 6.2'

Results: Found 3 vulnerabilities...
```

### Option 2: Daemon Mode (Background Processing)

```bash
python mindsync_prod.py --daemon
```

Runs in background, processes goals autonomously.

### Option 3: Quick Goal (Add and Exit)

```bash
python mindsync_prod.py --goal "Research CVE-2024-1234" --priority high
```

Adds goal to the queue and exits.

## CLI Commands

Inside interactive mode:

```
/goals      - List active goals
/context    - Show what AI knows about you
/status     - System status
/add-goal   - Add a goal interactively
/help       - Show help
/quit       - Exit
```

## Configuration

Edit `config.yaml` to customize:

```yaml
# Enable/disable features
hexstrike:
  enabled: true              # Use HexStrike tools

scheduler:
  enabled: true              # Background monitoring

# Notifications
notifications:
  enabled: true
  methods:
    - desktop               # Desktop notifications
    - terminal              # Terminal output
```

## Features Walkthrough

### 1. Persistent Memory

```bash
# Session 1
You: I'm working on acme.com

# Session 2 (hours later)
You: What was I working on?
MindSync: You're working on acme.com. Last time you...
```

**It actually remembers!**

### 2. Autonomous Goals

```bash
You: I need to research CVE-2024-1234 and test exploit

# MindSync autonomously:
# 1. Searches CVE database
# 2. Finds exploit code
# 3. Tests in lab
# 4. Generates report
# 5. Notifies you when done

# All without further prompting!
```

### 3. Multi-Modal Input

```python
from mindsync_prod import MindSyncOracleProduction

oracle = MindSyncOracleProduction()
await oracle.start()

# Text
await oracle.chat("Scan example.com")

# Voice (if OpenAI key set)
# Processes audio files via Whisper

# Files
# Can analyze documents, code, etc.
```

### 4. Tool Integration

With HexStrike enabled, MindSync can autonomously use:
- nmap, nuclei, gobuster, sqlmap
- amass, subfinder (subdomain enum)
- ghidra, radare2 (binary analysis)
- 150+ security tools total

### 5. Proactive Intelligence

```bash
# You're working on project X
# MindSync monitors in background:

🔔 New CVE Alert: CVE-2024-XXXX
Severity: CRITICAL
Affected: WordPress 6.2 on example.com

[View Details] [Test Exploit] [Ignore]
```

## Testing Without API Key

Set in config.yaml:
```yaml
development:
  mock_api_calls: true
```

This enables demo mode - all features work except real Claude API calls.

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "No tools available"
Check HexStrike is running:
```bash
# In hexstrike-ai directory
python hexstrike_server.py
```

Then enable in `config.yaml`:
```yaml
hexstrike:
  enabled: true
  server_url: "http://localhost:8888"
```

### Desktop notifications not working
Install system dependencies:
```bash
# Linux
sudo apt install libnotify-bin

# Mac
# Built-in (osascript)

# Windows
pip install win10toast
```

## Example Workflows

### Bug Bounty Hunting
```bash
python mindsync_prod.py

You: I'm hunting on example.com, looking for XSS

MindSync: Goal created. I'll run subdomain enum, crawl for parameters,
          and test for XSS vectors. I'll notify you with findings.

# Works autonomously while you do other things
# Notifies when vulnerabilities found
```

### CVE Research
```bash
python mindsync_prod.py --goal "Monitor CVE feeds for WordPress daily" --priority high

# MindSync checks every 6 hours
# Notifies on new critical CVEs
# All autonomous
```

### Pentesting
```bash
You: Pentest target.com, they're running Apache Tomcat 9.0

MindSync: Created project context. Based on your past pentests,
          I'm running nmap, nuclei, and checking for known Tomcat CVEs.

# Learns your methodology
# Suggests based on patterns
# Automates repetitive tasks
```

## Next Steps

1. **Try the demo**: `python demo.py` (no API key needed)
2. **Run interactive mode**: `python mindsync_prod.py`
3. **Add your first goal**: Use `/add-goal` command
4. **Watch it work autonomously**: Check `/goals` to see progress
5. **Explore context**: Use `/context` to see what it learned about you

## What Makes This Different?

**Traditional AI:**
- Forgets everything after session
- Only reacts to prompts
- No autonomous behavior
- Starts fresh each time

**MindSync Oracle:**
- ✅ Remembers across all sessions
- ✅ Learns your patterns
- ✅ Pursues goals autonomously
- ✅ Proactively surfaces insights
- ✅ Works in background

**This is the AGI architecture.**

## More Info

- Full documentation: `README.md`
- Architecture details: `ARCHITECTURE.md`
- Getting started guide: `GETTING_STARTED.md`

---

**Ready? Let's go:**

```bash
python mindsync_prod.py
```

Welcome to the future of AI agents.
