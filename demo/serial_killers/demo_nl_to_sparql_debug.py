#!/usr/bin/env python3
"""
Debug version of NL→SPARQL demo with full logging
Shows:
- System prompt sent to LLM
- User question
- LLM response (raw)
- Parsed JSON plan
- Generated SPARQL
"""

import sys
import os
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from demo.query_generator import QueryGenerator
from SPARQLLM.compiler.physical_compiler import PhysicalCompiler

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.CYAN}{'='*100}{Colors.END}")
    print(f"{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'='*100}{Colors.END}\n")

def print_section(text):
    print(f"\n{Colors.YELLOW}{'─'*100}{Colors.END}")
    print(f"{Colors.YELLOW}{text}{Colors.END}")
    print(f"{Colors.YELLOW}{'─'*100}{Colors.END}\n")

def check_ollama():
    """Check if Ollama is running."""
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/tags'],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        return False

def demo_with_logging(question: str):
    """Run demo with full logging of LLM interaction."""

    print_header("DEBUG MODE - Natural Language to SPARQL with Full Logging")
    print(f"{Colors.BOLD}Question:{Colors.END} {question}\n")

    # Check Ollama
    print_section("STEP 1: Environment Check")
    if not check_ollama():
        print(f"{Colors.RED}✗ Ollama is not running!{Colors.END}")
        print("Start it with: ollama serve")
        return False
    print(f"{Colors.GREEN}✓ Ollama is running{Colors.END}\n")

    # Load system prompt
    print_section("STEP 2: Load System Prompt")
    prompts_dir = Path(__file__).parent / 'prompts'
    prompt_file = prompts_dir / 'system_prompt_serial_killers.txt'

    if not prompt_file.exists():
        print(f"{Colors.RED}✗ System prompt not found: {prompt_file}{Colors.END}")
        return False

    with open(prompt_file, 'r') as f:
        system_prompt = f.read()

    print(f"{Colors.GREEN}✓ Loaded:{Colors.END} {prompt_file}")
    print(f"{Colors.BLUE}Prompt length:{Colors.END} {len(system_prompt)} characters\n")

    print(f"{Colors.BOLD}System Prompt Preview (first 500 chars):{Colors.END}")
    print(f"{Colors.CYAN}{system_prompt[:500]}...{Colors.END}\n")

    # Initialize query generator
    print_section("STEP 3: Initialize Query Generator")
    try:
        generator = QueryGenerator(mode='plan', provider='ollama')
        generator.system_prompt = system_prompt
        print(f"{Colors.GREEN}✓ QueryGenerator initialized{Colors.END}")
        print(f"  Provider: ollama")
        print(f"  Model: {generator.model}")
        print(f"  Mode: plan\n")
    except Exception as e:
        print(f"{Colors.RED}✗ Failed to initialize: {e}{Colors.END}")
        return False

    # Generate JSON plan with full logging
    print_section("STEP 4: Send Question to LLM")

    print(f"{Colors.BOLD}User Question:{Colors.END}")
    print(f"{Colors.CYAN}{question}{Colors.END}\n")

    print(f"{Colors.YELLOW}Calling LLM...{Colors.END}\n")

    try:
        # Capture the LLM call
        import time
        start_time = time.time()

        json_plan = generator.generate_plan(question)

        elapsed = time.time() - start_time

        print(f"{Colors.GREEN}✓ LLM responded in {elapsed:.2f} seconds{Colors.END}\n")

    except Exception as e:
        print(f"{Colors.RED}✗ LLM call failed: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return False

    # Show LLM response
    print_section("STEP 5: LLM Response Analysis")

    print(f"{Colors.BOLD}Raw LLM Response (JSON Plan):{Colors.END}")
    print(f"{Colors.CYAN}{json.dumps(json_plan, indent=2)}{Colors.END}\n")

    # Analyze the plan
    print(f"{Colors.BOLD}Plan Analysis:{Colors.END}")

    # Check data sources
    if 'data_sources' in json_plan:
        print(f"{Colors.GREEN}✓ Has 'data_sources' key{Colors.END}")
        for i, ds in enumerate(json_plan['data_sources']):
            print(f"  Data Source {i+1}:")
            print(f"    Type: {ds.get('type', 'N/A')}")
            print(f"    Path: {ds.get('path', 'N/A')}")
            if ds.get('type') == 'csv':
                print(f"    {Colors.GREEN}✓ Correct: Using local CSV{Colors.END}")
            else:
                print(f"    {Colors.RED}✗ Wrong: Not using CSV{Colors.END}")
    else:
        print(f"{Colors.RED}✗ No 'data_sources' key found{Colors.END}")
        if 'steps' in json_plan:
            print(f"{Colors.YELLOW}⚠ Found 'steps' key - using old format{Colors.END}")
            for i, step in enumerate(json_plan['steps']):
                print(f"  Step {i+1}:")
                print(f"    Operation: {step.get('operation', 'N/A')}")
                if step.get('operation') == 'web_search':
                    print(f"    {Colors.RED}✗ PROBLEM: Using web_search instead of CSV{Colors.END}")

    # Check projections
    if 'projections' in json_plan:
        print(f"\n{Colors.GREEN}✓ Has 'projections' key{Colors.END}")
        print(f"  Columns: {[p.get('column') for p in json_plan['projections']]}")

    # Check filters
    if 'filters' in json_plan:
        print(f"\n{Colors.GREEN}✓ Has 'filters' key{Colors.END}")
        for f in json_plan['filters']:
            print(f"  Filter: {f.get('column')} {f.get('operator')} {f.get('value')}")

    # Check order/limit
    if 'order_by' in json_plan:
        print(f"\n{Colors.GREEN}✓ Has 'order_by' key{Colors.END}")
        for o in json_plan['order_by']:
            print(f"  Order: {o.get('column')} {o.get('direction')}")

    if 'limit' in json_plan:
        print(f"\n{Colors.GREEN}✓ Has 'limit' key: {json_plan['limit']}{Colors.END}")

    print()

    # Compile to SPARQL
    print_section("STEP 6: Compile JSON Plan to SPARQL")

    try:
        compiler = PhysicalCompiler()
        sparql_query = compiler.compile(json_plan)

        print(f"{Colors.GREEN}✓ Compilation successful{Colors.END}\n")
        print(f"{Colors.BOLD}Generated SPARQL Query:{Colors.END}")
        print(f"{Colors.CYAN}{sparql_query}{Colors.END}\n")

        # Analyze SPARQL
        print(f"{Colors.BOLD}SPARQL Analysis:{Colors.END}")
        if 'SLM-CSV' in sparql_query:
            print(f"{Colors.GREEN}✓ Uses SLM-CSV GGF (correct){Colors.END}")
        elif 'SEARCH' in sparql_query or 'SLM-GETTEXT' in sparql_query:
            print(f"{Colors.RED}✗ Uses web search GGF (wrong){Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠ Unknown GGF pattern{Colors.END}")

        if 'FILTER' in sparql_query:
            print(f"{Colors.GREEN}✓ Contains FILTER clause{Colors.END}")

        if 'ORDER BY' in sparql_query:
            print(f"{Colors.GREEN}✓ Contains ORDER BY clause{Colors.END}")

        print()

    except Exception as e:
        print(f"{Colors.RED}✗ Compilation failed: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return False

    # Execute query
    print_section("STEP 7: Execute SPARQL Query")

    try:
        root_dir = Path(__file__).parent.parent.parent

        print(f"{Colors.YELLOW}Executing query...{Colors.END}\n")

        result = subprocess.run(
            ['bash', '-c', f'source venv312_new/bin/activate && slm-run -c config.ini -q \'{sparql_query}\''],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ Query executed successfully{Colors.END}\n")
            print(f"{Colors.BOLD}Results:{Colors.END}")
            print(result.stdout)

            # Check if results make sense
            if 'Empty DataFrame' in result.stdout:
                print(f"\n{Colors.RED}⚠ WARNING: Query returned empty results{Colors.END}")
            elif 'serialzone.cz' in result.stdout or 'DuckDuckGo' in result.stdout:
                print(f"\n{Colors.RED}⚠ WARNING: Results are from web search, not CSV!{Colors.END}")
            else:
                print(f"\n{Colors.GREEN}✓ Results look correct (from CSV data){Colors.END}")
        else:
            print(f"{Colors.RED}✗ Query execution failed{Colors.END}")
            print(f"Error: {result.stderr}")

    except Exception as e:
        print(f"{Colors.RED}✗ Execution error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()

    print_section("ANALYSIS COMPLETE")

    return True

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Debug NL→SPARQL with full logging')
    parser.add_argument('--question', type=str,
                       default="Which serial killers had more than 50 victims?",
                       help='Question to test')

    args = parser.parse_args()

    demo_with_logging(args.question)

if __name__ == '__main__':
    main()
