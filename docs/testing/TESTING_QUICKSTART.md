# HexStrike Testing Quick Start

Get up and running with HexStrike tests in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

## Quick Setup

### 1. Install Dependencies (1 minute)

```bash
# Install test requirements
pip install -r requirements-test.txt

# Or if you need main requirements too
pip install -r requirements.txt -r requirements-test.txt
```

### 2. Run Your First Tests (30 seconds)

```bash
# Run all tests
pytest

# Or use the test runner script
./run_tests.sh
```

That's it! You're now running HexStrike tests.

## Common Commands

### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests (fastest)
pytest -m unit

# Run specific test file
pytest tests/unit/test_core/test_cache.py

# Run with verbose output
pytest -v

# Run in parallel (faster)
pytest -n auto
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=hexstrike_server

# Generate HTML report
pytest --cov=hexstrike_server --cov-report=html

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Using the Test Runner

```bash
# Run all tests with coverage
./run_tests.sh

# Run only unit tests
./run_tests.sh unit

# Run only core tests
./run_tests.sh core

# Run fast tests only
./run_tests.sh fast
```

## Writing Your First Test

Create a new test file:

```python
# tests/unit/test_mycomponent.py

import pytest
from hexstrike_server import MyComponent

class TestMyComponent:
    """Test MyComponent functionality"""

    def test_initialization(self):
        """Test component initializes correctly"""
        component = MyComponent()
        assert component is not None

    def test_basic_function(self):
        """Test basic function"""
        component = MyComponent()
        result = component.do_something()
        assert result == expected_value
```

Run your new test:

```bash
pytest tests/unit/test_mycomponent.py -v
```

## Using Fixtures

Fixtures are pre-configured test data and mocks. Use them to simplify your tests:

```python
def test_with_mock_subprocess(mock_subprocess):
    """Test using subprocess mock"""
    # Subprocess is automatically mocked
    result = execute_command("nmap target.com")
    assert result is not None


def test_with_sample_data(sample_nmap_output):
    """Test using sample nmap output"""
    ports = parse_nmap_output(sample_nmap_output)
    assert len(ports) > 0


def test_with_flask_client(client):
    """Test Flask endpoint"""
    response = client.get('/api/status')
    assert response.status_code == 200
```

Available fixtures:
- `mock_subprocess` - Mock subprocess execution
- `mock_tool_execution` - Mock security tool execution
- `sample_nmap_output` - Sample nmap output
- `sample_gobuster_output` - Sample gobuster output
- `sample_sqlmap_output` - Sample sqlmap output
- `client` - Flask test client
- `temp_dir` - Temporary directory
- `frozen_time` - Fixed time for testing
- Many more in `tests/conftest.py`

## Test Organization

```
tests/
├── unit/              # Unit tests (fast, isolated)
│   └── test_core/     # Core component tests
├── integration/       # Integration tests (slower)
├── fixtures/          # Test data files
└── helpers/           # Test utilities
    ├── mocks.py       # Mock utilities
    └── test_utils.py  # Helper functions
```

## Next Steps

1. Read the [full testing guide](TESTING.md) for detailed information
2. Look at existing tests for examples:
   - `tests/unit/test_core/test_visual.py`
   - `tests/unit/test_core/test_cache.py`
   - `tests/unit/test_core/test_telemetry.py`
3. Check available fixtures in `tests/conftest.py`
4. Review test utilities in `tests/helpers/`

## Troubleshooting

### Tests won't run

```bash
# Make sure dependencies are installed
pip install -r requirements-test.txt

# Check Python version (3.8+ required)
python --version
```

### Import errors

```bash
# Make sure you're in the project root
cd /path/to/hexstrike-official

# Run tests from project root
pytest
```

### Slow tests

```bash
# Run tests in parallel
pytest -n auto

# Run only fast tests
pytest -m "not slow"
```

## Need Help?

- Check [TESTING.md](TESTING.md) for comprehensive documentation
- Look at existing tests for examples
- Review fixtures in `tests/conftest.py`

Happy Testing! 🚀
