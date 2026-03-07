#!/bin/bash

# HexStrike Test Runner Script
# Runs tests with coverage reporting and optional CI/CD integration

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MIN_COVERAGE=${MIN_COVERAGE:-80}
TEST_SUITE=${1:-all}
PARALLEL=${PARALLEL:-auto}
VERBOSE=${VERBOSE:-}

# Print banner
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  ${GREEN}HexStrike Test Suite Runner${NC}                                ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
print_info "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_info "Python version: $PYTHON_VERSION"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    print_error "Python 3.8 or higher is required"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "No virtual environment detected. It's recommended to use a virtual environment."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Exiting. Please activate a virtual environment and try again."
        exit 1
    fi
fi

# Install/verify dependencies
print_info "Checking test dependencies..."
if ! python3 -c "import pytest" 2>/dev/null; then
    print_warning "pytest not found. Installing test dependencies..."
    pip install -r requirements-test.txt
else
    print_success "Test dependencies are installed"
fi

# Clean up old test artifacts
print_info "Cleaning up old test artifacts..."
rm -rf .pytest_cache
rm -rf htmlcov
rm -rf .coverage
rm -f tests/test_output.log
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
print_success "Cleanup complete"

# Determine which tests to run
TEST_PATH="tests/"
TEST_MARKERS=""

case $TEST_SUITE in
    all)
        print_info "Running all tests..."
        ;;
    unit)
        print_info "Running unit tests only..."
        TEST_PATH="tests/unit/"
        TEST_MARKERS="-m unit"
        ;;
    integration)
        print_info "Running integration tests only..."
        TEST_PATH="tests/integration/"
        TEST_MARKERS="-m integration"
        ;;
    core)
        print_info "Running core component tests only..."
        TEST_PATH="tests/unit/test_core/"
        ;;
    fast)
        print_info "Running fast tests only (excluding slow tests)..."
        TEST_MARKERS="-m 'not slow'"
        ;;
    *)
        print_info "Running tests from: $TEST_SUITE"
        TEST_PATH="$TEST_SUITE"
        ;;
esac

# Build pytest command
PYTEST_CMD="python3 -m pytest"
PYTEST_ARGS=(
    "$TEST_PATH"
    "-v"
    "--tb=short"
    "--color=yes"
)

# Add markers if specified
if [ -n "$TEST_MARKERS" ]; then
    PYTEST_ARGS+=($TEST_MARKERS)
fi

# Add parallel execution
if [ "$PARALLEL" != "off" ]; then
    PYTEST_ARGS+=("-n" "$PARALLEL")
    print_info "Parallel execution enabled (workers: $PARALLEL)"
fi

# Add coverage options
PYTEST_ARGS+=(
    "--cov=hexstrike_server"
    "--cov=hexstrike_mcp"
    "--cov-report=html"
    "--cov-report=term-missing"
    "--cov-report=xml"
    "--cov-fail-under=$MIN_COVERAGE"
)

# Add verbose flag if set
if [ -n "$VERBOSE" ]; then
    PYTEST_ARGS+=("-vv" "-s")
fi

# Display configuration
echo ""
print_info "Test Configuration:"
echo "  Test Suite: $TEST_SUITE"
echo "  Test Path: $TEST_PATH"
echo "  Min Coverage: ${MIN_COVERAGE}%"
echo "  Parallel Workers: $PARALLEL"
echo ""

# Run tests
print_info "Starting test execution..."
echo ""

START_TIME=$(date +%s)

if $PYTEST_CMD "${PYTEST_ARGS[@]}"; then
    TEST_RESULT=0
    print_success "All tests passed!"
else
    TEST_RESULT=$?
    print_error "Some tests failed!"
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
print_info "Test execution completed in ${DURATION}s"

# Display coverage summary
if [ -f .coverage ]; then
    echo ""
    print_info "Coverage Summary:"
    echo ""
    python3 -m coverage report --skip-empty | tail -n 5
fi

# Check if HTML coverage report was generated
if [ -d htmlcov ]; then
    print_success "HTML coverage report generated: htmlcov/index.html"
    echo ""
    print_info "To view the report, run:"
    echo "  ${BLUE}open htmlcov/index.html${NC}  # macOS"
    echo "  ${BLUE}xdg-open htmlcov/index.html${NC}  # Linux"
fi

# Generate test report summary
echo ""
print_info "Test Summary:"
TOTAL_TESTS=$(grep -E "^(tests/|=)" .pytest_cache/.pytest_status 2>/dev/null | wc -l || echo "N/A")
echo "  Total Tests: $TOTAL_TESTS"

if [ $TEST_RESULT -eq 0 ]; then
    echo ""
    print_success "╔════════════════════════════════════════════════════════════════╗"
    print_success "║  ALL TESTS PASSED ✓                                           ║"
    print_success "╚════════════════════════════════════════════════════════════════╝"
else
    echo ""
    print_error "╔════════════════════════════════════════════════════════════════╗"
    print_error "║  TESTS FAILED ✗                                               ║"
    print_error "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    print_info "To re-run only failed tests:"
    echo "  ${BLUE}pytest --lf${NC}"
    echo ""
    print_info "To run with more verbosity:"
    echo "  ${BLUE}VERBOSE=1 ./run_tests.sh${NC}"
fi

echo ""

# Exit with test result code
exit $TEST_RESULT
