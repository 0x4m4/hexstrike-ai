# HexStrike AI Installation Guide

## Prerequisites

- Python 3.10 or higher
- [UV](https://docs.astral.sh/uv/) package manager (recommended)
- Git

## Quick Start with UV (Recommended)

### 1. Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### 2. Clone and Install HexStrike AI

```bash
git clone https://github.com/hexstrike-ai/hexstrike.git
cd hexstrike-ai

# Install core dependencies only
uv pip install -e .

# Or install with specific capability groups
uv pip install -e '.[browser,security]'
```

## Dependency Groups

HexStrike AI uses UV's dependency groups to organize optional dependencies by functionality:

### 🌐 Browser Automation (`browser`)

For web application testing and browser automation:

```bash
uv pip install -e '.[browser]'
```

**Includes:**
- Selenium WebDriver
- Playwright
- WebDriver Manager
- requests-html
- lxml with html_clean

### 🔒 Security Tools (`security`)

For network security and penetration testing:

```bash
uv pip install -e '.[security]'
```

**Includes:**
- mitmproxy
- Scapy
- python-nmap
- Paramiko
- Cryptography

### 🔍 Binary Analysis (`binary`)

For reverse engineering and binary analysis:

```bash
uv pip install -e '.[binary]'
```

**Includes:**
- pwntools
- angr
- Capstone
- Keystone Engine
- Unicorn Engine

### 🕵️ Forensics (`forensics`)

For digital forensics and steganography:

```bash
uv pip install -e '.[forensics]'
```

**Includes:**
- Pillow
- python-magic
- exifread
- stegano

### 🔐 Cryptography (`crypto`)

For cryptographic analysis:

```bash
uv pip install -e '.[crypto]'
```

**Includes:**
- pycryptodome
- gmpy2

### 🌍 OSINT (`osint`)

For open-source intelligence gathering:

```bash
uv pip install -e '.[osint]'
```

**Includes:**
- Shodan
- Censys
- dnspython
- whois

### 🛠️ Development (`dev`)

For development and testing:

```bash
uv pip install -e '.[dev]'
```

**Includes:**
- pytest
- pytest-asyncio
- pytest-cov
- black
- flake8
- mypy

## Installation Combinations

### Install Multiple Groups

```bash
# Browser automation + Security tools
uv pip install -e '.[browser,security]'

# Full penetration testing suite
uv pip install -e '.[browser,security,binary]'

# Complete OSINT toolkit
uv pip install -e '.[browser,osint,forensics]'
```

### Install Everything

```bash
# Install all optional dependencies
uv pip install -e '.[all]'
```

## Running with UV

### Direct Execution

```bash
# Run with specific dependencies
uv run --with selenium --with scapy python your_script.py

# Run server
uv run hexstrike-server

# Run MCP client
uv run hexstrike-mcp
```

### Testing Installation

```bash
# Test all dependencies
uv run --with selenium --with webdriver-manager --with scapy --with 'requests-html' --with playwright --with 'lxml[html_clean]' --with python-nmap --with cryptography python test_browser_deps.py
```

## Traditional Installation (Alternative)

If you prefer using traditional Python virtual environments:

```bash
# Create virtual environment
python3 -m venv hexstrike-env
source hexstrike-env/bin/activate  # Linux/macOS
# or
hexstrike-env\Scripts\activate     # Windows

# Install with pip
pip install -e .
pip install -e '.[browser,security]'  # With optional groups
```

## Verification

After installation, verify everything works:

```bash
# Test CLI tools
hexstrike-server --help
hexstrike-mcp --help
hexstrike --help

# Test dependencies
python test_browser_deps.py
```

## System Requirements

### Browser Automation Requirements

For headless Chrome automation (mentioned in README):

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y chromium-browser chromium-chromedriver

# Or Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt-get update
sudo apt-get install -y google-chrome-stable

# macOS
brew install --cask google-chrome
brew install chromedriver

# Or use WebDriver Manager (automatic)
# This is included in the browser group and handles driver management automatically
```

### Security Tools Requirements

Some security tools may require additional system packages:

```bash
# Ubuntu/Debian
sudo apt-get install -y nmap masscan gobuster feroxbuster nuclei

# macOS
brew install nmap masscan gobuster feroxbuster nuclei
```

## Troubleshooting

### Common Issues

1. **Import errors after installation**:
   ```bash
   # Make sure you're using the correct Python environment
   which python
   uv run python -c "import sys; print(sys.path)"
   ```

2. **Browser automation issues**:
   ```bash
   # Install browser drivers
   uv run python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"
   ```

3. **Permission errors on macOS**:
   ```bash
   # Allow terminal access in System Preferences > Security & Privacy
   # Or run with appropriate permissions
   ```

### Debug Mode

```bash
# Enable debug logging
hexstrike-server --debug
hexstrike-mcp --debug
```

## Next Steps

After successful installation:

1. Start the HexStrike server: `uv run hexstrike-server`
2. Configure your AI agent (Claude, Cursor, etc.) to connect to the MCP server
3. Begin using HexStrike AI for security testing and analysis

For detailed usage examples, see the main [README.md](README.md).