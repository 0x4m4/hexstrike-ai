# OSINT Tools Installation Guide

## Prerequisites

- Python 3.8+
- Git
- pip
- Internet connection

## Installation Steps

### 1. Install Python Dependencies

```bash
cd osint-tools
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional but Recommended)

```bash
cp config/.env.example config/.env
# Edit .env with your actual API keys
```

### 3. Run Installation

```bash
# Full installation
python install.py

# Or specific category
python install.py --category username

# Test first
python install.py --dry-run
```

## Platform-Specific Notes

### Kali Linux
Most tools pre-installed. Just run:
```bash
python install.py
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install git python3-pip
python install.py
```

### macOS
```bash
brew install git python3
python install.py
```

## Verification

After installation, verify tools:
```bash
python install.py --list-categories
```