# HexStrike AI MCP Usage Guide

## Overview

This guide demonstrates how to use the HexStrike AI MCP (Model Context Protocol) server with AI models like Google Gemini, Claude, or other MCP-compatible clients for cybersecurity operations and penetration testing.

## Prerequisites

### 1. Install HexStrike AI
```bash
# Clone and install HexStrike AI
git clone <repository-url>
cd hexstrike-ai

# Install with all dependencies
uv pip install -e '.[browser,security]'

# Or using pip
pip install -e '.[browser,security]'
```

### 2. Install MCP Client Tools

#### Option A: MCP Inspector (Visual Interface)
```bash
npx @modelcontextprotocol/inspector
```

#### Option B: Claude Desktop (Recommended)
1. Download Claude Desktop from Anthropic
2. Configure MCP server in Claude's settings

#### Option C: Custom MCP Client
```bash
# Install MCP SDK for Python
pip install mcp
```

## Configuration

### 1. Start HexStrike AI Server
```bash
# Start the main API server
uv run hexstrike-server --port 8888

# Or with debug mode
uv run hexstrike-server --debug --port 8888
```

### 2. Configure MCP Server

#### For Claude Desktop
Add to your Claude Desktop MCP configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "hexstrike-ai": {
      "command": "uv",
      "args": ["run", "hexstrike-mcp", "--server", "http://localhost:8888"],
      "cwd": "/path/to/hexstrike-ai"
    }
  }
}
```

#### For MCP Inspector
```bash
# Start HexStrike MCP server
uv run hexstrike-mcp --server http://localhost:8888

# In another terminal, start MCP Inspector
npx @modelcontextprotocol/inspector
```

### 3. Using with Google Gemini API

Create a custom MCP client script:

```python
#!/usr/bin/env python3
"""
HexStrike AI + Gemini MCP Client
Demonstrates using HexStrike AI tools with Google Gemini
"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

async def main():
    # Connect to HexStrike MCP server
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "hexstrike-mcp", "--server", "http://localhost:8888"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize MCP session
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available HexStrike tools: {len(tools.tools)}")
            
            # Example: Use Gemini to decide which tools to use
            prompt = """
            I need to perform reconnaissance on a target domain 'example.com'.
            Based on these available cybersecurity tools, suggest which ones to use:
            
            Available tools:
            """
            
            for tool in tools.tools:
                prompt += f"- {tool.name}: {tool.description}\n"
            
            # Get Gemini's recommendation
            response = model.generate_content(prompt)
            print(f"Gemini recommendation: {response.text}")
            
            # Example tool execution (replace with actual tool name)
            # result = await session.call_tool("nmap_scan", {
            #     "target": "example.com",
            #     "scan_type": "quick"
            # })
            # print(f"Tool result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Usage Examples

### Example 1: Basic Reconnaissance Workflow

1. **Start the servers:**
```bash
# Terminal 1: Start HexStrike API server
uv run hexstrike-server

# Terminal 2: Start MCP server
uv run hexstrike-mcp --server http://localhost:8888
```

2. **Connect with Claude Desktop:**
   - Open Claude Desktop
   - Start a new conversation
   - Ask: "What cybersecurity tools are available through HexStrike AI?"

3. **Example conversation:**
```
User: "I need to perform reconnaissance on domain 'target.com'. What tools should I use?"

Claude: "I can help you with reconnaissance using HexStrike AI tools. Let me check what's available...

[Claude will list available tools and suggest a workflow]

I recommend starting with:
1. Domain enumeration using subfinder
2. Port scanning with nmap
3. Web technology detection with httpx

Would you like me to execute these tools?"

User: "Yes, please start with domain enumeration."

Claude: "I'll run the subfinder tool for domain enumeration..."
[Executes tool and shows results]
```

### Example 2: Vulnerability Assessment

```python
# vulnerability_assessment.py
import asyncio
from mcp_client import HexStrikeMCPClient

async def vulnerability_assessment(target):
    client = HexStrikeMCPClient()
    
    # Step 1: Port scan
    ports = await client.call_tool("nmap_scan", {
        "target": target,
        "scan_type": "comprehensive"
    })
    
    # Step 2: Web vulnerability scan
    web_vulns = await client.call_tool("nuclei_scan", {
        "target": target,
        "templates": "web-vulnerabilities"
    })
    
    # Step 3: SSL/TLS analysis
    ssl_analysis = await client.call_tool("testssl", {
        "target": target
    })
    
    return {
        "ports": ports,
        "web_vulnerabilities": web_vulns,
        "ssl_analysis": ssl_analysis
    }
```

### Example 3: Automated Penetration Testing

```bash
#!/bin/bash
# automated_pentest.sh

# Set target
TARGET="example.com"

# Start HexStrike servers
uv run hexstrike-server &
SERVER_PID=$!

sleep 5

uv run hexstrike-mcp --server http://localhost:8888 &
MCP_PID=$!

sleep 3

# Run automated assessment using AI
python3 << EOF
import asyncio
from mcp_gemini_client import run_automated_assessment

asyncio.run(run_automated_assessment("$TARGET"))
EOF

# Cleanup
kill $MCP_PID $SERVER_PID
```

## Environment Variables

```bash
# Required for Gemini integration
export GEMINI_API_KEY="your-gemini-api-key-here"

# Optional: HexStrike configuration
export HEXSTRIKE_SERVER_URL="http://localhost:8888"
export HEXSTRIKE_TIMEOUT="300"
export HEXSTRIKE_DEBUG="false"
```

## Testing and Verification

### 1. Health Check
```bash
# Check if HexStrike API server is running
curl http://localhost:8888/health

# Expected response:
# {"status": "ok", "message": "HexStrike AI API Server is running"}
```

### 2. MCP Protocol Test
```bash
# Test MCP initialization
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | uv run hexstrike-mcp --server http://localhost:8888
```

### 3. Tool Listing Test
```python
# test_tools.py
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_tools():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "hexstrike-mcp", "--server", "http://localhost:8888"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            
            print(f"Found {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

if __name__ == "__main__":
    asyncio.run(test_tools())
```

## Troubleshooting

### Common Issues

1. **"Module not found" errors:**
```bash
# Install missing dependencies
uv pip install -e '.[browser,security]'
```

2. **MCP connection issues:**
```bash
# Check if HexStrike server is running
curl http://localhost:8888/health

# Restart MCP server with debug
uv run hexstrike-mcp --server http://localhost:8888 --debug
```

3. **Missing security tools:**
```bash
# Install common penetration testing tools
brew install nmap nuclei subfinder httpx
# or
sudo apt-get install nmap
```

### Debug Mode

```bash
# Enable debug logging
export HEXSTRIKE_DEBUG=true
uv run hexstrike-server --debug
uv run hexstrike-mcp --server http://localhost:8888 --debug
```

## Security Considerations

⚠️ **Important Security Notes:**

1. **Only use on authorized targets** - Ensure you have permission to test
2. **Network isolation** - Run in isolated environments when possible
3. **API key security** - Never commit API keys to version control
4. **Tool permissions** - Some tools require elevated privileges
5. **Rate limiting** - Be mindful of API rate limits

## Advanced Usage

### Custom Tool Integration

```python
# custom_tool_example.py
from hexstrike_mcp import HexStrikeMCP

class CustomReconTool:
    def __init__(self):
        self.mcp = HexStrikeMCP()
    
    async def comprehensive_recon(self, target):
        """Perform comprehensive reconnaissance"""
        results = {}
        
        # Subdomain enumeration
        results['subdomains'] = await self.mcp.call_tool('subfinder', {
            'domain': target
        })
        
        # Port scanning
        results['ports'] = await self.mcp.call_tool('nmap', {
            'target': target,
            'options': '-sS -sV -O'
        })
        
        # Web technology detection
        results['tech'] = await self.mcp.call_tool('httpx', {
            'target': target,
            'tech_detect': True
        })
        
        return results
```

### Integration with Other AI Models

```python
# multi_model_integration.py
import openai
import anthropic
import google.generativeai as genai
from hexstrike_mcp_client import HexStrikeMCPClient

class MultiModelPentester:
    def __init__(self):
        self.hexstrike = HexStrikeMCPClient()
        self.openai_client = openai.OpenAI()
        self.anthropic_client = anthropic.Anthropic()
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.gemini = genai.GenerativeModel('gemini-pro')
    
    async def collaborative_assessment(self, target):
        """Use multiple AI models for comprehensive assessment"""
        
        # Get tool recommendations from different models
        tools = await self.hexstrike.list_tools()
        
        # GPT-4 for strategic planning
        strategy = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "user",
                "content": f"Plan a penetration test for {target} using these tools: {tools}"
            }]
        )
        
        # Claude for detailed execution
        # Gemini for result analysis
        
        return strategy
```
