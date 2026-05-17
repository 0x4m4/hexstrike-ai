# OSINT Automation Framework

Phase 1 MVP - CLI, REST API, Web Dashboard, Workflow Engine

## Quick Start

### Docker
```bash
docker-compose up
```

### Manual
```bash
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## CLI Usage

```bash
# Install CLI
pip install -e .

# Run search
osint-cli search target123

# List tools
osint-cli list-tools

# Run specific tool
osint-cli run-tool maigret target123
```

## API Endpoints

- `POST /api/v1/search` - Run OSINT search
- `GET /api/v1/search/{id}` - Get search results
- `GET /api/v1/tools` - List available tools
- `POST /api/v1/tools/{name}/run` - Run specific tool
- `GET /api/v1/history` - Get search history

## Web UI

Visit http://localhost:8000 for the web dashboard.

## Configuration

Edit `config/settings.yaml` or use environment variables:
- DATABASE_URL
- API_HOST, API_PORT
- API_KEYS_ENABLED
- LOCAL_AUTH_ENABLED