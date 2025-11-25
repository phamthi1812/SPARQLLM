#!/usr/bin/env python3
"""
Serial Killers Demo - Natural Language to SPARQL

Demonstrates the full pipeline:
1. User asks natural language question
2. LLM generates JSON logical plan
3. Physical compiler translates to SPARQL with GGFs
4. Query executes and returns results

Usage:
    # Demo mode with predefined questions
    python demo/serial_killers/demo_nl_to_sparql.py

    # Interactive mode - ask your own question
    python demo/serial_killers/demo_nl_to_sparql.py --interactive

    # Specific question
    python demo/serial_killers/demo_nl_to_sparql.py --question "Who are the top 5 serial killers?"
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Add SPARQLLM to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from demo.query_generator import QueryGenerator
from SPARQLLM.compiler.physical_compiler import PhysicalCompiler

# Colors for terminal output
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
    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_step(step_num, text):
    print(f"{Colors.YELLOW}[STEP {step_num}] {text}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}\n")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}\n")

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

def demo_nl_to_sparql(question: str, execute: bool = True):
    """
    Run the full NL → SPARQL pipeline.

    Args:
        question: Natural language question
        execute: Whether to execute the generated query
    """

    print_header("Natural Language to SPARQL Pipeline Demo")
    print(f"{Colors.BOLD}Question:{Colors.END} {question}\n")

    # Step 1: Check Ollama
    print_step(1, "Checking Ollama availability")
    if not check_ollama():
        print_error("Ollama is not running!")
        print("Please start Ollama first:")
        print("  ollama serve")
        print("  ollama pull qwen2.5:3b")
        return False
    print_success("Ollama is running at http://localhost:11434")

    # Step 2: Generate JSON plan with LLM
    print_step(2, "LLM generates JSON logical plan")
    print(f"{Colors.BLUE}Using: Ollama (qwen2.5:3b){Colors.END}\n")

    try:
        # Load serial killers specific system prompt
        prompts_dir = Path(__file__).parent / 'prompts'
        prompt_file = prompts_dir / 'system_prompt_serial_killers.txt'

        if prompt_file.exists():
            with open(prompt_file, 'r') as f:
                system_prompt = f.read()
        else:
            print_error(f"System prompt not found: {prompt_file}")
            return False

        generator = QueryGenerator(mode='plan', provider='ollama')

        # Override the system prompt with our serial killers specific one
        generator.system_prompt = system_prompt

        print(f"📝 Sending question to LLM...")
        json_plan = generator.generate_plan(question)

        print_success("JSON Plan Generated")
        print(f"{Colors.BLUE}JSON Plan:{Colors.END}")
        print(json.dumps(json_plan, indent=2))
        print()

    except Exception as e:
        print_error(f"Failed to generate JSON plan: {e}")
        return False

    # Step 3: Compile to SPARQL
    print_step(3, "Physical compiler translates to SPARQL with GGFs")

    try:
        compiler = PhysicalCompiler()
        print(f"🔧 Compiling JSON plan to SPARQL...")
        sparql_query = compiler.compile(json_plan)

        print_success("SPARQL Query Generated")
        print(f"{Colors.BLUE}Generated SPARQL:{Colors.END}")
        print(sparql_query)
        print()

    except Exception as e:
        print_error(f"Failed to compile SPARQL: {e}")
        return False

    # Step 4: Execute query (if requested)
    if execute:
        print_step(4, "Execute SPARQL query")

        try:
            # Get the root directory
            root_dir = Path(__file__).parent.parent.parent

            # Execute via subprocess
            print(f"⚡ Running query with slm-run...")
            result = subprocess.run(
                ['bash', '-c', f'source venv312_new/bin/activate && slm-run -c config.ini -q \'{sparql_query}\''],
                cwd=root_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print_success("Query executed successfully")
                print(f"{Colors.BLUE}Results:{Colors.END}")
                print(result.stdout)
            else:
                print_error("Query execution failed")
                print(f"Error: {result.stderr}")
                return False

        except Exception as e:
            print_error(f"Failed to execute query: {e}")
            return False

    print_header("Pipeline Complete!")
    print(f"{Colors.GREEN}Summary:{Colors.END}")
    print(f"  1. ✓ Natural Language → LLM (Ollama)")
    print(f"  2. ✓ LLM → JSON Logical Plan")
    print(f"  3. ✓ Physical Compiler → SPARQL with GGFs")
    if execute:
        print(f"  4. ✓ SPARQL Execution → Results")
    print()

    return True

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Demo: Natural Language to SPARQL Query Generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo mode with menu
  python demo/serial_killers/demo_nl_to_sparql.py

  # Interactive mode
  python demo/serial_killers/demo_nl_to_sparql.py --interactive

  # Specific question
  python demo/serial_killers/demo_nl_to_sparql.py --question "Who are the top 10 serial killers?"

  # Generate query without executing
  python demo/serial_killers/demo_nl_to_sparql.py --question "..." --no-execute
        """
    )

    parser.add_argument('--interactive', action='store_true',
                       help='Interactive mode - ask your own question')
    parser.add_argument('--question', type=str,
                       help='Specific question to ask')
    parser.add_argument('--no-execute', action='store_true',
                       help='Generate query but do not execute')

    args = parser.parse_args()

    # Predefined demo questions
    demo_questions = [
        "Who are the top 10 serial killers with the most victims?",
        "How many serial killers were active in each decade?",
        "Which countries have the most serial killers?",
        "Show me serial killers from the United States in the 1970s",
        "Which serial killers had more than 50 victims?"
    ]

    # Determine which question to use
    if args.question:
        question = args.question
    elif args.interactive:
        print_header("Interactive Mode")
        print(f"{Colors.CYAN}Enter your question about serial killers:{Colors.END}")
        question = input("> ").strip()
        if not question:
            print_error("No question provided")
            return 1
    else:
        # Demo mode with menu
        print_header("Demo Mode - Select a Question")
        print(f"{Colors.CYAN}Available demo questions:{Colors.END}\n")

        for i, q in enumerate(demo_questions, 1):
            print(f"  {Colors.YELLOW}{i}.{Colors.END} {q}")

        print()
        try:
            selection = input(f"Select question (1-{len(demo_questions)}) or press Enter for #1: ").strip()
            if not selection:
                selection = 1
            else:
                selection = int(selection)

            if selection < 1 or selection > len(demo_questions):
                print_error(f"Invalid selection. Using question 1.")
                selection = 1

            question = demo_questions[selection - 1]

        except ValueError:
            print_error("Invalid input. Using question 1.")
            question = demo_questions[0]

    # Run the demo
    execute = not args.no_execute
    success = demo_nl_to_sparql(question, execute=execute)

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
