#!/bin/bash
#
# Test Multi-Step Query System with All Providers
#
# This script validates the multi-step query implementation by running
# the restaurant finder demo with different LLM providers.
#
# Usage:
#   ./demo/multi_step/test_providers.sh [quick|full]
#
# Modes:
#   quick - Test basic functionality only (default)
#   full  - Test all providers and save outputs

set -e  # Exit on error

MODE=${1:-quick}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/demo/multi_step/test_output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "Multi-Step Query Provider Tests"
echo "=================================="
echo "Mode: $MODE"
echo "Project root: $PROJECT_ROOT"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Test questions
SIMPLE_QUESTION="Search for SPARQL tutorials"
COMPLEX_QUESTION="Find cheap restaurants near the Web Conference 2024"

# Function to test a provider
test_provider() {
    local provider=$1
    local question=$2
    local test_name=$3

    echo ""
    echo "──────────────────────────────────────────"
    echo "Testing: $provider - $test_name"
    echo "──────────────────────────────────────────"

    # Check prerequisites
    if [ "$provider" = "openai" ]; then
        if [ -z "$OPENAI_API_KEY" ]; then
            echo -e "${YELLOW}⚠ Skipping OpenAI (OPENAI_API_KEY not set)${NC}"
            return 0
        fi
    elif [ "$provider" = "ollama" ]; then
        if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo -e "${YELLOW}⚠ Skipping Ollama (server not running)${NC}"
            echo "  Start with: ollama serve"
            return 0
        fi
    elif [ "$provider" = "groq" ]; then
        if [ -z "$GROQ_API_KEY" ]; then
            echo -e "${YELLOW}⚠ Skipping Groq (GROQ_API_KEY not set)${NC}"
            return 0
        fi
    fi

    # Run test
    local output_file="$OUTPUT_DIR/${provider}_${test_name}.log"
    local plan_file="$OUTPUT_DIR/${provider}_${test_name}_plan.json"
    local sparql_file="$OUTPUT_DIR/${provider}_${test_name}_query.sparql"

    echo "Running test..."
    if python "$SCRIPT_DIR/restaurant_finder.py" \
        --provider "$provider" \
        --question "$question" \
        --save-plan "$plan_file" \
        --save-sparql "$sparql_file" \
        > "$output_file" 2>&1; then

        echo -e "${GREEN}✓ Test passed${NC}"

        # Validate outputs
        if [ -f "$plan_file" ]; then
            echo "  ✓ Plan generated: $plan_file"
            # Check if valid JSON
            if python -m json.tool "$plan_file" > /dev/null 2>&1; then
                echo "  ✓ Plan is valid JSON"
            else
                echo -e "${RED}  ✗ Plan is invalid JSON${NC}"
                return 1
            fi
        else
            echo -e "${RED}  ✗ Plan file not created${NC}"
            return 1
        fi

        if [ -f "$sparql_file" ]; then
            echo "  ✓ SPARQL generated: $sparql_file"
            # Check if contains expected patterns
            if grep -q "PREFIX ggf:" "$sparql_file"; then
                echo "  ✓ SPARQL contains GGF prefix"
            else
                echo -e "${YELLOW}  ⚠ SPARQL missing GGF prefix${NC}"
            fi
        else
            echo -e "${RED}  ✗ SPARQL file not created${NC}"
            return 1
        fi

        echo "  Full output: $output_file"
        return 0

    else
        echo -e "${RED}✗ Test failed${NC}"
        echo "  Error output:"
        tail -n 20 "$output_file" | sed 's/^/    /'
        return 1
    fi
}

# Main test execution
if [ "$MODE" = "quick" ]; then
    echo "Running quick validation tests..."
    echo ""

    # Test with Ollama only (most likely to be available locally)
    test_provider "ollama" "$SIMPLE_QUESTION" "simple"

    echo ""
    echo "=================================="
    echo "Quick test completed!"
    echo "=================================="
    echo ""
    echo "To run full tests with all providers:"
    echo "  $0 full"
    echo ""

elif [ "$MODE" = "full" ]; then
    echo "Running full provider tests..."
    echo ""

    PASSED=0
    FAILED=0
    SKIPPED=0

    # Test each provider with simple and complex questions
    for provider in ollama openai groq; do
        for test in simple complex; do
            if [ "$test" = "simple" ]; then
                question="$SIMPLE_QUESTION"
            else
                question="$COMPLEX_QUESTION"
            fi

            if test_provider "$provider" "$question" "$test"; then
                ((PASSED++))
            else
                if [ $? -eq 0 ]; then
                    ((SKIPPED++))
                else
                    ((FAILED++))
                fi
            fi
        done
    done

    echo ""
    echo "=================================="
    echo "Full Test Results"
    echo "=================================="
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"
    echo -e "${YELLOW}Skipped: $SKIPPED${NC}"
    echo ""

    if [ $FAILED -gt 0 ]; then
        echo "Some tests failed. Check output files in $OUTPUT_DIR"
        exit 1
    else
        echo "All tests passed!"
        exit 0
    fi

else
    echo "Invalid mode: $MODE"
    echo "Usage: $0 [quick|full]"
    exit 1
fi
