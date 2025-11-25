#!/usr/bin/env python3
"""
Restaurant Finder Demo - Multi-Step Query Example

Demonstrates LLM-driven multi-step query planning:
1. Search web for conference location
2. Extract location from conference website
3. Search for restaurants near that location
4. Extract price information
5. Sort and filter results

Usage:
    python demo/multi_step/restaurant_finder.py --provider openai
    python demo/multi_step/restaurant_finder.py --provider ollama --interactive
    python demo/multi_step/restaurant_finder.py --provider groq
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from demo.query_generator import QueryGenerator
from demo.ui.plan_viewer import display_error, display_success


def main():
    """Run restaurant finder demo"""
    parser = argparse.ArgumentParser(description="Restaurant Finder Multi-Step Demo")
    parser.add_argument(
        '--provider',
        choices=['openai', 'ollama', 'groq'],
        default='ollama',
        help='LLM provider to use (default: ollama)'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Enable step-by-step execution mode'
    )
    parser.add_argument(
        '--question',
        type=str,
        default="Find cheap restaurants near the Web Conference 2024",
        help='Question to ask (default: restaurant finder)'
    )
    parser.add_argument(
        '--save-plan',
        type=str,
        help='Save generated plan to file (JSON)'
    )
    parser.add_argument(
        '--save-sparql',
        type=str,
        help='Save generated SPARQL to file'
    )

    args = parser.parse_args()

    # Print header
    print("\n" + "="*80)
    print("Restaurant Finder Demo - Multi-Step Query Planning")
    print("="*80)
    print(f"\nProvider: {args.provider}")
    print(f"Question: {args.question}")
    print(f"Interactive mode: {'Yes' if args.interactive else 'No'}")
    print("="*80 + "\n")

    # Check provider-specific requirements
    if args.provider == 'openai':
        if not os.getenv('OPENAI_API_KEY'):
            print("Error: OPENAI_API_KEY environment variable not set.")
            print("Set it with: export OPENAI_API_KEY=your-key-here")
            sys.exit(1)
        print("✓ OpenAI API key found")

    elif args.provider == 'ollama':
        print("Note: Make sure Ollama is running: ollama serve")
        print("      Recommended model: llama3.2 or llama3.1\n")

    elif args.provider == 'groq':
        if not os.getenv('GROQ_API_KEY'):
            print("Warning: GROQ_API_KEY not set. May use fallback provider.")
        # For Groq, we might need to add specific client initialization
        print("Note: Groq support may require additional configuration")

    # Initialize generator with multi-step prompt
    try:
        generator = QueryGenerator(
            mode='plan',
            provider=args.provider,
            interactive=args.interactive,
            use_multi_step=True  # Force multi-step for this demo
        )
    except Exception as e:
        display_error(f"Failed to initialize query generator: {e}", "error")
        sys.exit(1)

    # Execute two-stage flow
    try:
        print("\nGenerating multi-step logical plan...\n")
        plan, sparql = generator.two_stage_flow(args.question)

        if not plan or not sparql:
            display_error("Query generation aborted or failed", "error")
            sys.exit(1)

        # Save plan if requested
        if args.save_plan:
            with open(args.save_plan, 'w') as f:
                json.dump(plan, f, indent=2)
            display_success(f"Plan saved to: {args.save_plan}")

        # Save SPARQL if requested
        if args.save_sparql:
            with open(args.save_sparql, 'w') as f:
                f.write(sparql)
            display_success(f"SPARQL saved to: {args.save_sparql}")

        # Display final SPARQL
        if not args.interactive:
            print("\n" + "="*80)
            print("Generated SPARQL Query:")
            print("="*80)
            print(sparql)
            print("="*80 + "\n")

        # Show execution instructions
        print("\n" + "="*80)
        print("Next Steps:")
        print("="*80)
        print("\nTo execute this query:")
        print(f"  1. Save the SPARQL query to a file:")
        print(f"     python {__file__} --provider {args.provider} --save-sparql query.sparql")
        print(f"\n  2. Execute with slm-run:")
        print(f"     slm-run -q \"$(cat query.sparql)\"")
        print(f"\n  3. Or execute directly:")
        print(f"     python -m SPARQLLM.cli.slm run '<your-query-here>'")
        print("\n" + "="*80 + "\n")

        # Display plan statistics
        steps = plan.get('steps', [])
        print("Plan Statistics:")
        print(f"  Total steps: {len(steps)}")
        print(f"  Web searches: {sum(1 for s in steps if s.get('operation') == 'web_search')}")
        print(f"  Web fetches: {sum(1 for s in steps if s.get('operation') == 'web_fetch')}")
        print(f"  LLM extractions: {sum(1 for s in steps if s.get('operation') == 'llm_extract')}")

        output_vars = plan.get('output', {}).get('variables', [])
        print(f"  Output variables: {', '.join(output_vars)}")
        print()

        display_success("Demo completed successfully!")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.\n")
        sys.exit(0)

    except Exception as e:
        display_error(f"Demo failed: {e}", "error")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
