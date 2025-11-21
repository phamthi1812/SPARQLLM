#!/usr/bin/env python3
"""
Comparison Mode: Evaluate Different Execution Paths

Compares three approaches to answering the same question:
1. Two-stage compiler (plan → compile → execute)
2. Direct SPARQL generation (LLM → SPARQL)
3. Manual baseline (pre-written query)

Measures: correctness, latency, cost, user satisfaction
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


console = Console() if RICH_AVAILABLE else None


class ComparisonRunner:
    """Run comparison between different query execution paths"""

    def __init__(self):
        """Initialize comparison runner"""
        self.results = {}

    def run_comparison(
        self,
        question: str,
        context: Optional[Dict] = None,
        include_manual: bool = False
    ) -> Dict:
        """
        Execute query via multiple paths and compare results.

        Args:
            question: Natural language question
            context: Optional context dict
            include_manual: Whether to include manual baseline

        Returns:
            Dict with results from each path
        """
        results = {}

        print("\n" + "="*80)
        print("COMPARISON MODE")
        print("="*80)
        print(f"\nQuestion: {question}\n")

        # Path 1: Two-stage compiler
        print("[1/3] Two-Stage Compiler...")
        try:
            from demo.query_generator import QueryGenerator

            generator_plan = QueryGenerator(mode='plan')
            start = time.time()
            plan, sparql_compiled = generator_plan.two_stage_flow(
                question,
                context,
                max_retries=1  # Single attempt for comparison
            )
            elapsed = time.time() - start

            results['two_stage'] = {
                'success': sparql_compiled is not None,
                'time_seconds': elapsed,
                'query': sparql_compiled,
                'plan': plan,
                'method': 'Two-Stage Compiler'
            }

        except Exception as e:
            results['two_stage'] = {
                'success': False,
                'error': str(e),
                'time_seconds': 0,
                'method': 'Two-Stage Compiler'
            }

        # Path 2: Direct SPARQL generation (placeholder)
        print("\n[2/3] Direct SPARQL Generation...")
        results['direct'] = {
            'success': False,
            'error': 'Not implemented',
            'time_seconds': 0,
            'method': 'Direct SPARQL'
        }
        print("  (Not implemented - would use LLM → SPARQL directly)")

        # Path 3: Manual baseline (if provided)
        if include_manual:
            print("\n[3/3] Manual Baseline...")
            manual_query = self._load_manual_baseline(question)
            if manual_query:
                results['manual'] = {
                    'success': True,
                    'query': manual_query,
                    'time_seconds': 0,  # Instantaneous (pre-written)
                    'method': 'Manual Baseline'
                }
            else:
                results['manual'] = {
                    'success': False,
                    'error': 'No manual baseline available',
                    'time_seconds': 0,
                    'method': 'Manual Baseline'
                }
        else:
            print("\n[3/3] Manual Baseline... (skipped)")

        # Display results
        self._display_comparison_results(results)

        return results

    def _load_manual_baseline(self, question: str) -> Optional[str]:
        """
        Load pre-written manual query for comparison.

        Args:
            question: Natural language question

        Returns:
            SPARQL query string or None if not found
        """
        # Check for manual baseline file
        baselines_dir = Path(__file__).parent / "baselines"
        if not baselines_dir.exists():
            return None

        # Create filename from question (sanitized)
        filename = question.lower()[:50].replace(' ', '_').replace('?', '')
        baseline_path = baselines_dir / f"{filename}.sparql"

        if baseline_path.exists():
            with open(baseline_path, 'r') as f:
                return f.read()

        return None

    def _display_comparison_results(self, results: Dict):
        """Display comparison results in formatted table"""

        if RICH_AVAILABLE:
            self._display_comparison_rich(results)
        else:
            self._display_comparison_plain(results)

    def _display_comparison_rich(self, results: Dict):
        """Display comparison using Rich table"""
        console.print("\n")
        console.print(Panel.fit(
            "[bold cyan]Comparison Results[/bold cyan]",
            border_style="cyan"
        ))

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Method", style="cyan", width=20)
        table.add_column("Success", style="green", width=10)
        table.add_column("Time (s)", justify="right", style="yellow", width=10)
        table.add_column("Notes", style="dim", width=30)

        for method_key, result in results.items():
            method_name = result['method']
            success = "✓" if result['success'] else "✗"
            success_style = "green" if result['success'] else "red"
            time_str = f"{result['time_seconds']:.2f}" if result['success'] else "N/A"
            notes = result.get('error', 'OK') if not result['success'] else "OK"

            table.add_row(
                method_name,
                f"[{success_style}]{success}[/{success_style}]",
                time_str,
                notes
            )

        console.print(table)

        # Display generated queries
        console.print("\n[bold]Generated Queries:[/bold]\n")

        for method_key, result in results.items():
            if result['success'] and result.get('query'):
                console.print(Panel(
                    result['query'],
                    title=f"[cyan]{result['method']}[/cyan]",
                    border_style="cyan"
                ))

    def _display_comparison_plain(self, results: Dict):
        """Display comparison using plain text"""
        print("\n" + "="*80)
        print("COMPARISON RESULTS")
        print("="*80)

        for method_key, result in results.items():
            print(f"\n{result['method']}:")
            print(f"  Success: {'Yes' if result['success'] else 'No'}")
            print(f"  Time: {result['time_seconds']:.2f}s")
            if not result['success']:
                print(f"  Error: {result.get('error', 'Unknown')}")
            if result.get('query'):
                print(f"  Query length: {len(result['query'])} chars")

        print("\n" + "="*80)


def main():
    """Interactive comparison mode CLI"""
    print("\n" + "="*80)
    print("SPARQLLM Comparison Mode")
    print("="*80)

    # Get question
    question = input("\nEnter your question: ").strip()
    if not question:
        print("No question provided. Exiting.")
        return

    # Get context
    context = {}
    add_context = input("Add context? [y/N]: ").strip().lower()
    if add_context == 'y':
        print("\nEnter context (key=value, empty line to finish):")
        while True:
            line = input("  ").strip()
            if not line:
                break
            if '=' in line:
                key, value = line.split('=', 1)
                context[key.strip()] = value.strip()

    # Include manual baseline?
    include_manual = input("\nInclude manual baseline? [y/N]: ").strip().lower() == 'y'

    # Run comparison
    runner = ComparisonRunner()
    try:
        results = runner.run_comparison(
            question,
            context if context else None,
            include_manual=include_manual
        )

        print("\nComparison complete!")

    except Exception as e:
        print(f"\nError during comparison: {e}")
        return

    print("\nThank you for using SPARQLLM Comparison Mode!\n")


if __name__ == "__main__":
    main()
