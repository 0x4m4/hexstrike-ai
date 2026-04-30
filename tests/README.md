# HexStrike Test Suite

## Test Coverage Status

### Core Module Tests

- **core.visual**: 53 tests, 100% coverage
- **core.cache**: Tests available
- **core.telemetry**: Tests available

### Tools Module Tests

- **tools.base**: 33 tests, 98% coverage
- **tools.network.nmap**: 55 tests, 100% coverage

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific module tests
pytest tests/unit/test_core/test_visual.py

# Run with coverage
pytest tests/unit/test_core/test_visual.py --cov=core.visual --cov-report=term-missing
```

## Test Organization

- `tests/unit/` - Unit tests for individual modules
- `tests/integration/` - Integration tests
- `tests/fixtures/` - Test fixtures and data
- `tests/helpers/` - Test utilities and helpers
