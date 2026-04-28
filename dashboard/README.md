# HexStrike AI Live Dashboard

Real-time monitoring tools for HexStrike AI penetration testing platform.

## Overview

The HexStrike AI Live Dashboard provides real-time monitoring of security testing processes with beautiful visual interfaces and comprehensive system metrics. This collection includes both Bash and Python implementations for maximum flexibility.

## Features

- 📊 **Real-time Process Monitoring** - Track active security tools and their progress
- 🎨 **Beautiful Visual Interface** - ANSI color-coded terminal UI with progress bars
- 📈 **System Metrics** - CPU, memory, and network connection monitoring
- ⚡ **Process Management** - Pause, resume, and terminate processes
- 🔄 **Auto-refresh** - Configurable refresh intervals
- 🐍 **Multiple Implementations** - Both Bash and Python versions available

## Files

- `hexstrike_dashboard.sh` - Bash implementation with basic monitoring
- `hexstrike_dashboard.py` - Full-featured Python implementation
- `README.md` - This documentation file

## Quick Start

### Python Version (Recommended)

```bash
# Basic usage - continuous monitoring
./hexstrike_dashboard.py

# Single snapshot
./hexstrike_dashboard.py --once

# Custom refresh interval (10 seconds)
./hexstrike_dashboard.py --refresh 10

# Custom API endpoint
./hexstrike_dashboard.py --api-base http://remote-server:8888
```

### Bash Version

```bash
# Run the bash dashboard
./hexstrike_dashboard.sh
```

## Python Usage Examples

### Interactive Monitoring
```bash
# Start live dashboard with default settings
python3 hexstrike_dashboard.py

# Monitor with 3-second refresh rate
python3 hexstrike_dashboard.py --refresh 3

# Connect to remote HexStrike server
python3 hexstrike_dashboard.py --api-base http://192.168.1.100:8888
```

### Process Management
```bash
# Get status of specific process
python3 hexstrike_dashboard.py --status 12345

# Terminate a process
python3 hexstrike_dashboard.py --terminate 12345

# Pause a process
python3 hexstrike_dashboard.py --pause 12345

# Resume a paused process
python3 hexstrike_dashboard.py --resume 12345
```

### One-shot Monitoring
```bash
# Get single dashboard snapshot
python3 hexstrike_dashboard.py --once
```

## Dashboard Features

### Visual Elements

The dashboard displays:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           HexStrike AI Live Dashboard                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 HEXSTRIKE LIVE DASHBOARD
├─────────────────────────────────────────────────────────────────────────────┤
│ PID 1234567 | running | nmap -sS target.com -p 1-65535                      │
│ PID 1234568 | running | nikto -h https://target.com                          │
│ PID 1234569 | running | gobuster dir -u https://target.com                   │
╰─────────────────────────────────────────────────────────────────────────────╯

📊 System Metrics:
   CPU Usage: 45.2%
   Memory Usage: 62.1%
   Active Connections: 1,247
   Total Processes: 3

🔄 Active Security Processes:
PID      Status     Runtime    Progress     Data       Command
------------------------------------------------------------------------------------------------
1234567  running    45.2m      85.4%        2.1MB      nmap -sS target.com -p 1-65535...
1234568  running    12.8m      92.1%        856KB      nikto -h https://target.com...
1234569  running    8.3m       76.3%        4.2MB      gobuster dir -u https://target.com...
```

### Progress Tracking

Each process shows:
- **PID** - Process identifier
- **Status** - Current state (running, paused, completed, failed)
- **Runtime** - How long the process has been running
- **Progress** - Completion percentage with visual progress bars
- **Data Processed** - Amount of data processed (formatted in B/KB/MB/GB)
- **Command** - The security tool command being executed

## Configuration

### Environment Variables

You can set these environment variables for default configuration:

```bash
export HEXSTRIKE_API_BASE="http://localhost:8888"
export HEXSTRIKE_REFRESH_INTERVAL="5"
```

### API Endpoints

The dashboard connects to these HexStrike API endpoints:

- `GET /health` - Server health check
- `GET /api/dashboard/live` - Live dashboard data
- `GET /api/processes/status/{pid}` - Process status
- `POST /api/processes/terminate/{pid}` - Terminate process
- `POST /api/processes/pause/{pid}` - Pause process
- `POST /api/processes/resume/{pid}` - Resume process

## Requirements

### Python Version
- Python 3.6+
- `requests` library
- `json` library (built-in)
- `argparse` library (built-in)

Install Python dependencies:
```bash
pip3 install requests
```

### Bash Version
- Bash 4.0+
- `curl` command
- `jq` command for JSON parsing

Install Bash dependencies:
```bash
# Ubuntu/Debian
sudo apt-get install curl jq

# RHEL/CentOS
sudo yum install curl jq
```

## Troubleshooting

### Common Issues

**Connection Refused**
```bash
❌ Cannot connect to HexStrike server at http://localhost:8888
```
- Ensure HexStrike AI server is running
- Check if the port is correct (default: 8888)
- Verify firewall settings

**Permission Denied**
```bash
./hexstrike_dashboard.py: Permission denied
```
- Make the script executable: `chmod +x hexstrike_dashboard.py`

**Missing Dependencies**
```bash
ModuleNotFoundError: No module named 'requests'
```
- Install Python dependencies: `pip3 install requests`

### Debug Mode

For debugging connection issues:

```bash
# Test API connectivity
curl -v http://localhost:8888/health

# Check if processes endpoint works
curl -s http://localhost:8888/api/dashboard/live | jq .
```

## Example Session

Here's what a typical monitoring session looks like:

```bash
$ ./hexstrike_dashboard.py
🚀 Starting HexStrike AI Live Dashboard...
📊 Checking server connection at http://localhost:8888...
✅ Connected to HexStrike server
🎯 Starting live dashboard monitoring...

# Dashboard displays with real-time updates every 5 seconds
# Shows running nmap, nikto, gobuster scans
# Displays progress bars and system metrics
# Press Ctrl+C to exit

👋 Dashboard monitoring stopped
```

## Integration

### With HexStrike AI

The dashboard integrates seamlessly with HexStrike AI penetration testing workflows:

1. **Start a penetration test** using HexStrike tools
2. **Monitor progress** with the live dashboard
3. **Manage processes** (pause/resume/terminate) as needed
4. **Track system resources** to optimize performance

### With CI/CD

Use the dashboard in automated testing pipelines:

```bash
# Start monitoring in background
./hexstrike_dashboard.py --once > dashboard_snapshot.txt

# Use in scripts
if ./hexstrike_dashboard.py --status $PID > /dev/null; then
    echo "Process is running"
fi
```

## Contributing

To contribute to the HexStrike AI Dashboard:

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Submit a pull request

## License

This project is part of the HexStrike AI penetration testing platform.

## Support

For support and questions:
- Check the HexStrike AI documentation
- Review troubleshooting section above
- Submit issues via GitHub

---

**Made with ❤️ for the cybersecurity community**