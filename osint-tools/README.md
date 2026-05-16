# OSINT Tools for HexStrike AI

Comprehensive OSINT tool installation framework with 1,580+ resources from the catalog.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# List available categories
python install.py --list-categories

# Install all tools
python install.py

# Install specific category
python install.py --category username

# Dry run (test without changes)
python install.py --dry-run
```

## Configuration

### API Keys

1. Copy the template:
   ```bash
   cp config/.env.example config/.env
   ```

2. Add your API keys to `.env`:
   - SHODAN_API_KEY
   - HUNTER_API_KEY
   - HIBP_API_KEY
   - CENSYS_API_ID / CENSYS_API_SECRET
   - SECURITYTRAILS_API_KEY
   - INTELX_API_KEY
   - DEHASHED_API_KEY / DEHASHED_EMAIL

3. Never commit `.env` to git (already in .gitignore)

## Directory Structure

```
osint-tools/
├── install.py              # Main installation script
├── config/                 # Configuration files
│   ├── .env.example        # API key template
│   ├── settings.yaml       # Installation settings
│   └── catalog-links.json # Parsed catalog
├── tools/                  # Installed tools by category
├── datasets/               # Dataset references
├── papers/                # Academic papers
├── talks/                 # Video resources
└── docs/                  # Documentation
```

## Supported Categories

- Username Investigation (Maigret, Sherlock, etc.)
- Email Investigation (Holehe, GHunt, etc.)
- Automation & Recon (SpiderFoot, recon-ng, etc.)
- Social Media Intelligence (snscrape, Instaloader, etc.)
- Infrastructure Intelligence (Shodan, Censys, etc.)
- Breach & Leak Search (DeHashed, IntelX, etc.)
- Media & Archive Tools (ExifTool, Wayback, etc.)

## Documentation

See `docs/` directory for detailed guides.

## License

See HexStrike AI main project.