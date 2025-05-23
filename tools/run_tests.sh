#!/bin/bash
# Test runner script for repository scanner
# Usage: ./run_tests.sh [options]
#   Options:
#     --all         Run all tests
#     --unit        Run only unit tests
#     --error       Run only error handling tests
#     --coverage    Run tests with coverage report
#     --verbose     Run with verbose output
#     --ci          Run in CI mode (fail on any warning/error)
#     --help        Show this help message

# Default values
RUN_ALL=false
RUN_UNIT=false
RUN_ERROR=false
RUN_COVERAGE=false
VERBOSE=""
CI_MODE=false

# Set up colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
if [ $# -eq 0 ]; then
    RUN_ALL=true
else
    for arg in "$@"; do
        case $arg in
            --all)
                RUN_ALL=true
                ;;
            --unit)
                RUN_UNIT=true
                ;;
            --error)
                RUN_ERROR=true
                ;;
            --coverage)
                RUN_COVERAGE=true
                ;;
            --verbose)
                VERBOSE="-v"
                ;;
            --ci)
                CI_MODE=true
                ;;
            --help)
                echo "Test runner for repository scanner"
                echo ""
                echo "Usage: ./run_tests.sh [options]"
                echo "  Options:"
                echo "    --all         Run all tests (default if no options specified)"
                echo "    --unit        Run only unit tests"
                echo "    --error       Run only error handling tests"
                echo "    --coverage    Run tests with coverage report"
                echo "    --verbose     Run with verbose output"
                echo "    --ci          Run in CI mode (fail on any warning/error)"
                echo "    --help        Show this help message"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $arg${NC}"
                echo "Use --help for usage information."
                exit 1
                ;;
        esac
    done
fi

# If none of the test types are specified, run all
if [[ "$RUN_ALL" == "false" && "$RUN_UNIT" == "false" && "$RUN_ERROR" == "false" ]]; then
    RUN_ALL=true
fi

# Navigate to the project root directory (assuming script is in tools/)
cd "$(dirname "$0")/.." || { echo "Failed to navigate to project root"; exit 1; }

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}         Repository Scanner Test Runner               ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo ""

# Check if pipenv is installed
if ! command -v pipenv &> /dev/null; then
    echo -e "${RED}Error: pipenv is not installed.${NC}"
    echo "Please install pipenv using: pip install pipenv"
    exit 1
fi

# Run tests with appropriate options
if [[ "$RUN_COVERAGE" == "true" ]]; then
    echo -e "${YELLOW}Installing coverage dependencies...${NC}"
    pipenv install pytest-cov --dev
    COVERAGE_ARGS="--cov=. --cov-report=term --cov-report=html"
else
    COVERAGE_ARGS=""
fi

# Counter for failed tests
FAILED_TESTS=0

run_test() {
    local test_file=$1
    local test_description=$2
    
    echo -e "${YELLOW}Running $test_description...${NC}"
    
    if [[ "$RUN_COVERAGE" == "true" ]]; then
        pipenv run pytest $test_file $VERBOSE $COVERAGE_ARGS
    else
        pipenv run pytest $test_file $VERBOSE
    fi
    
    local result=$?
    if [ $result -ne 0 ]; then
        echo -e "${RED}$test_description failed with exit code $result${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    else
        echo -e "${GREEN}$test_description passed!${NC}"
    fi
    
    return $result
}

# Run tests based on flags
if [[ "$RUN_ALL" == "true" || "$RUN_ERROR" == "true" ]]; then
    # Run error handling tests
    run_test "test_error_handling.py" "Error handling tests"
fi

if [[ "$RUN_ALL" == "true" || "$RUN_UNIT" == "true" ]]; then
    # Check if any unit tests exist
    if ls test_*.py 2>/dev/null | grep -v "test_error_handling.py" > /dev/null; then
        # Run all other unit tests
        for test_file in $(find . -name "test_*.py" -not -name "test_error_handling.py"); do
            run_test "$test_file" "Unit tests for $(basename "$test_file" .py)"
        done
    else
        echo -e "${YELLOW}No additional unit tests found.${NC}"
    fi
fi

# Print summary
echo ""
echo -e "${BLUE}======================================================${NC}"
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}All tests passed successfully!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED_TESTS test suite(s) failed.${NC}"
    exit 1
fi