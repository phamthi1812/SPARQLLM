#!/bin/bash
#
# Serial Killers Demo - Natural Language to SPARQL Query Generation
#
# This script demonstrates the full pipeline:
# 1. User asks natural language question
# 2. LLM generates JSON logical plan
# 3. Physical compiler translates to SPARQL with GGFs
# 4. Query executes and returns results
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$DEMO_DIR/../.." && pwd)"
VENV_PATH="$ROOT_DIR/venv312_new"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Serial Killers Demo - Query Generator${NC}"
echo -e "${CYAN}Natural Language → SPARQL with LLM${NC}"
echo -e "${CYAN}========================================${NC}\n"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}[1/4] Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"
cd "$ROOT_DIR"
echo -e "${GREEN}✓ Virtual environment activated${NC}\n"

# Check if Ollama is running
echo -e "${YELLOW}[2/4] Checking Ollama...${NC}"
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${RED}✗ Ollama is not running!${NC}"
    echo -e "${YELLOW}Please start Ollama first:${NC}"
    echo -e "  ollama serve"
    echo -e "  ollama pull qwen2.5:3b"
    exit 1
fi
echo -e "${GREEN}✓ Ollama is running${NC}\n"

# Interactive mode vs predefined questions
if [ "$1" == "--interactive" ]; then
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Interactive Mode${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    echo -e "${CYAN}Enter your question about serial killers:${NC}"
    read -p "> " USER_QUESTION

    echo -e "\n${YELLOW}[3/4] Generating query from your question...${NC}"
    echo -e "${CYAN}Question: $USER_QUESTION${NC}\n"

    # Run query generator
    python demo/query_generator.py --mode plan --provider ollama --question "$USER_QUESTION"

else
    # Demo mode with predefined questions
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Demo Mode - Predefined Questions${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    # Array of demo questions
    declare -a QUESTIONS=(
        "Who are the top 10 serial killers with the most victims?"
        "How many serial killers were active in each decade?"
        "Which countries have the most serial killers?"
    )

    # Select question
    if [ -z "$1" ]; then
        echo -e "${CYAN}Available demo questions:${NC}\n"
        for i in "${!QUESTIONS[@]}"; do
            echo -e "  ${YELLOW}$((i+1)).${NC} ${QUESTIONS[$i]}"
        done
        echo ""
        read -p "Select question (1-${#QUESTIONS[@]}) or press Enter for #1: " SELECTION
        SELECTION=${SELECTION:-1}
    else
        SELECTION=$1
    fi

    # Validate selection
    if ! [[ "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -lt 1 ] || [ "$SELECTION" -gt ${#QUESTIONS[@]} ]; then
        echo -e "${RED}Invalid selection. Using question 1.${NC}"
        SELECTION=1
    fi

    USER_QUESTION="${QUESTIONS[$((SELECTION-1))]}"

    echo -e "${YELLOW}[3/4] Generating query from natural language...${NC}"
    echo -e "${CYAN}Question: $USER_QUESTION${NC}\n"

    # Run query generator with the question
    echo -e "${BLUE}Running: python demo/query_generator.py --mode plan --provider ollama${NC}\n"

    # Create temporary Python script to run query generator
    cat > /tmp/run_query_gen.py << 'EOFPYTHON'
import sys
sys.path.insert(0, '/Users/e23e889b/Documents/2025/2025_11/SPARQLLM')

from demo.query_generator import QueryGenerator
import json

question = sys.argv[1]

print("=" * 80)
print("STEP 1: LLM GENERATES JSON LOGICAL PLAN")
print("=" * 80)

# Initialize query generator with Ollama
generator = QueryGenerator(mode='plan', provider='ollama')

# Generate JSON plan
print(f"\n📝 Sending question to Ollama (qwen2.5:3b)...")
json_plan = generator.generate(question)

print(f"\n✓ JSON Plan Generated:\n")
print(json.dumps(json_plan, indent=2))

print("\n" + "=" * 80)
print("STEP 2: PHYSICAL COMPILER TRANSLATES TO SPARQL")
print("=" * 80)

# Compile to SPARQL
from SPARQLLM.compiler.physical_compiler import PhysicalCompiler
compiler = PhysicalCompiler()

print(f"\n🔧 Compiling JSON plan to SPARQL with GGFs...")
sparql_query = compiler.compile(json_plan)

print(f"\n✓ Generated SPARQL Query:\n")
print(sparql_query)

# Save to file
output_file = '/tmp/generated_query.sparql'
with open(output_file, 'w') as f:
    f.write(sparql_query)
print(f"\n💾 Query saved to: {output_file}")

print("\n" + "=" * 80)
print("STEP 3: EXECUTE QUERY")
print("=" * 80)
EOFPYTHON

    # Run the Python script
    python /tmp/run_query_gen.py "$USER_QUESTION"

    # Execute the generated query
    echo -e "\n${YELLOW}[4/4] Executing generated SPARQL query...${NC}\n"

    if [ -f /tmp/generated_query.sparql ]; then
        echo -e "${BLUE}Running: slm-run -c config.ini -q <generated_query>${NC}\n"

        # Read and execute the query
        QUERY=$(cat /tmp/generated_query.sparql)
        slm-run -c config.ini -q "$QUERY"

        echo -e "\n${GREEN}✓ Query executed successfully!${NC}\n"
    else
        echo -e "${RED}✗ Generated query file not found${NC}"
        exit 1
    fi
fi

echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}Demo Complete!${NC}"
echo -e "${CYAN}========================================${NC}\n"

echo -e "${YELLOW}Pipeline Summary:${NC}"
echo -e "  1. Natural Language Question → LLM (Ollama)"
echo -e "  2. LLM → JSON Logical Plan"
echo -e "  3. Physical Compiler → SPARQL with GGFs"
echo -e "  4. SPARQL Execution → Results"
echo -e ""

# Cleanup
rm -f /tmp/run_query_gen.py /tmp/generated_query.sparql
