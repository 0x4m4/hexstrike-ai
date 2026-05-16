# HexStrike AI Project Mandates

## Contextual Precedence
- This file defines foundational mandates for the HexStrike AI project.
- Global and project-specific instructions are supplementary to these mandates.

## Engineering Standards
- **macOS Compatibility:** Ensure all tools and paths are compatible with macOS.
- **Wordlist Management:** Use relative paths for wordlists (`./wordlists/`) with fallback to system paths.
- **Tool Robustness:** The MCP server should gracefully handle missing tools by reporting them in health checks and suggesting alternatives.
- **Color Consistency:** Maintain the "Blood-Red" offensive intelligence theme in all outputs.

## Development Workflow
- **Server-First:** Always ensure `hexstrike_server.py` is running before testing the MCP client.
- **Security First:** Never hardcode credentials. Use environment variables for API keys.
- **Testing:** Test MCP tools using JSON-RPC requests via stdin/stdout or curl to the backend API.
