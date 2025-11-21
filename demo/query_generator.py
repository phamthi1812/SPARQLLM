#!/usr/bin/env python3
"""
SPARQLLM Query Generator with Two-Stage Compilation

Generates SPARQL queries from natural language using:
1. Plan Mode: LLM → JSON logical plan → compile → SPARQL → execute
2. Direct Mode: LLM → SPARQL → execute (legacy)

Usage:
    python demo/query_generator.py
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from SPARQLLM.compiler import PhysicalCompiler, CostEstimator, Explainer
from SPARQLLM.catalog.query import (
    load_catalog,
    find_ggfs_by_source,
    get_catalog_summary
)
from demo.ui.plan_viewer import (
    display_plan,
    prompt_user_confirmation,
    display_error,
    display_success
)


class QueryGenerator:
    """Generate SPARQL queries from natural language questions"""

    def __init__(self, mode: str = 'plan', model: str = 'gpt-4', api_key: Optional[str] = None):
        """
        Initialize query generator.

        Args:
            mode: 'plan' (two-stage) or 'direct' (legacy SPARQL generation)
            model: LLM model name
            api_key: Optional API key (reads from env if not provided)
        """
        self.mode = mode
        self.model = model

        # Initialize LLM client (OpenAI compatible)
        try:
            from openai import OpenAI
            # Only initialize client if API key is available
            api_key_val = api_key or os.getenv('OPENAI_API_KEY')
            if api_key_val:
                self.client = OpenAI(api_key=api_key_val)
                self.llm_available = True
            else:
                print("Warning: OPENAI_API_KEY not set. LLM features disabled.")
                self.llm_available = False
                self.client = None
        except ImportError:
            print("Warning: openai library not installed. LLM features disabled.")
            print("Install with: pip install openai")
            self.llm_available = False
            self.client = None

        # Load prompts directory
        self.prompts_dir = Path(__file__).parent / "prompts"
        self.prompts_dir.mkdir(exist_ok=True)

        if mode == 'plan':
            # Load plan system prompt
            prompt_path = self.prompts_dir / "plan_system_prompt.txt"
            if not prompt_path.exists():
                raise FileNotFoundError(f"System prompt not found: {prompt_path}")

            with open(prompt_path, 'r') as f:
                self.system_prompt = f.read()

            # Load catalog and inject summary into prompt
            self.catalog = load_catalog()
            catalog_summary = self._generate_catalog_summary()
            self.system_prompt = self.system_prompt.replace(
                '{catalog_summary}',
                catalog_summary
            )

            # Initialize compiler components
            self.compiler = PhysicalCompiler()
            self.cost_estimator = CostEstimator()
            self.explainer = Explainer()

    def _generate_catalog_summary(self) -> str:
        """
        Generate compact catalog summary for LLM prompt.

        Returns:
            Formatted text summary (max ~500 tokens)
        """
        summary_parts = []

        # Get catalog statistics
        stats = get_catalog_summary()
        summary_parts.append(f"**Total GGFs**: {stats['total_ggfs']}")
        summary_parts.append("")

        # List by data source
        for source in ['filesystem', 'llm', 'web', 'vector', 'mcp', 'graph']:
            ggfs = find_ggfs_by_source(source)
            if ggfs:
                summary_parts.append(f"**{source.upper()} Operations:**")
                for ggf in ggfs[:10]:  # Limit to 10 per source
                    name = ggf['name']
                    desc = ggf.get('description') or 'No description'
                    # Truncate long descriptions
                    if desc and len(desc) > 80:
                        desc = desc[:77] + "..."
                    latency = f"{ggf['latency_ms']}ms" if ggf.get('latency_ms') else "N/A"
                    summary_parts.append(f"  - {name}: {desc} (latency: {latency})")
                if len(ggfs) > 10:
                    summary_parts.append(f"  ... and {len(ggfs) - 10} more")
                summary_parts.append("")

        return '\n'.join(summary_parts)

    def generate_plan(self, user_question: str, context: Optional[Dict] = None) -> dict:
        """
        Generate logical plan (JSON) from user question via LLM.

        Args:
            user_question: Natural language question
            context: Optional context (file paths, config, etc.)

        Returns:
            dict: Logical plan conforming to logical_plan.json schema

        Raises:
            ValueError: If LLM outputs invalid JSON
            RuntimeError: If LLM call fails
        """
        if not self.llm_available:
            raise RuntimeError("LLM client not initialized. Install openai library.")

        # Build user prompt
        prompt_parts = [f"Question: {user_question}"]

        if context:
            prompt_parts.append("\nContext:")
            for key, value in context.items():
                prompt_parts.append(f"  {key}: {value}")

        prompt_parts.append("\nGenerate a logical plan for this question.")
        user_prompt = '\n'.join(prompt_parts)

        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=2000
            )

            plan_json = response.choices[0].message.content.strip()

            # Clean markdown artifacts
            plan_json = re.sub(r'^```json\s*\n', '', plan_json, flags=re.MULTILINE)
            plan_json = re.sub(r'^```\s*\n', '', plan_json, flags=re.MULTILINE)
            plan_json = re.sub(r'\n```$', '', plan_json)
            plan_json = plan_json.strip()

            # Parse JSON
            plan = json.loads(plan_json)
            return plan

        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nResponse: {plan_json[:200]}")
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {e}")

    def two_stage_flow(
        self,
        user_question: str,
        context: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Tuple[Optional[dict], Optional[str]]:
        """
        Execute two-stage compilation with user confirmation.

        Args:
            user_question: Natural language question
            context: Optional context dict
            max_retries: Maximum retry attempts for plan generation

        Returns:
            (plan, sparql) tuple, or (None, None) if aborted
        """
        print(f"\n{'='*80}")
        print(f"Question: {user_question}")
        print(f"{'='*80}\n")

        for attempt in range(max_retries):
            try:
                # Stage 1: Generate logical plan
                print(f"Generating logical plan (attempt {attempt + 1}/{max_retries})...")

                plan = self.generate_plan(user_question, context)

                # Estimate cost
                cost = self.cost_estimator.estimate(plan)

                # Generate explanation
                explanation = self.explainer.explain(plan, cost)

                # Display plan to user
                display_plan(plan, cost, explanation)

                # User confirmation
                choice = prompt_user_confirmation()

                if choice == 'reject':
                    print("\nRegenerating plan...\n")
                    continue

                elif choice == 'edit':
                    plan = self._edit_plan_interactive(plan)
                    # Recompute cost/explanation after edit
                    cost = self.cost_estimator.estimate(plan)
                    explanation = self.explainer.explain(plan, cost)

                elif choice == 'quit':
                    print("\nAborted by user.\n")
                    return None, None

                # Stage 2: Compile to SPARQL
                print("\nCompiling plan to SPARQL...")

                try:
                    sparql = self.compiler.compile(plan)
                    display_success("Plan compiled successfully!")
                    return plan, sparql

                except Exception as e:
                    display_error(f"Compilation failed: {e}", "error")
                    if attempt < max_retries - 1:
                        print("Retrying...\n")
                        continue
                    else:
                        raise

            except ValueError as e:
                display_error(f"Invalid plan: {e}", "error")
                if attempt < max_retries - 1:
                    print("Retrying...\n")
                    continue
                else:
                    raise

            except Exception as e:
                display_error(f"Unexpected error: {e}", "error")
                raise

        raise RuntimeError(f"Failed to generate valid plan after {max_retries} attempts")

    def _edit_plan_interactive(self, plan: dict) -> dict:
        """
        Open plan JSON in editor for manual editing.

        Args:
            plan: Original plan dict

        Returns:
            Modified plan dict
        """
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            prefix='sparqllm_plan_'
        ) as f:
            json.dump(plan, f, indent=2)
            temp_path = f.name

        # Determine editor
        editor = os.environ.get('EDITOR', 'nano')

        print(f"\nOpening plan in {editor}...")
        print(f"Edit the JSON and save/exit to continue.\n")

        try:
            # Open editor
            subprocess.run([editor, temp_path], check=True)

            # Read modified plan
            with open(temp_path, 'r') as f:
                modified_plan = json.load(f)

            print("\nPlan updated successfully.")
            return modified_plan

        except subprocess.CalledProcessError as e:
            display_error(f"Editor exited with error: {e}", "error")
            return plan  # Return original on error

        except json.JSONDecodeError as e:
            display_error(f"Invalid JSON after edit: {e}", "error")
            return plan  # Return original on error

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)


def main():
    """Interactive query generator CLI"""
    print("\n" + "="*80)
    print("SPARQLLM Query Generator - Two-Stage Compilation")
    print("="*80)

    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("\nWarning: OPENAI_API_KEY environment variable not set.")
        print("LLM features will be unavailable.")
        print("Set it with: export OPENAI_API_KEY=your-key-here\n")

    # Mode selection
    print("\nSelect mode:")
    print("  1. Two-stage (plan + compile) [RECOMMENDED]")
    print("  2. Direct SPARQL generation [NOT IMPLEMENTED YET]")
    print("  3. Comparison mode [NOT IMPLEMENTED YET]")

    mode_choice = input("\nMode [1/2/3]: ").strip() or "1"

    if mode_choice == "1":
        # Two-stage mode
        generator = QueryGenerator(mode='plan')

        # Get user question
        print("\n" + "="*80)
        question = input("Enter your question: ").strip()

        if not question:
            print("No question provided. Exiting.")
            return

        # Optional context
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

        # Execute two-stage flow
        try:
            plan, sparql = generator.two_stage_flow(question, context if context else None)

            if sparql:
                print("\n" + "="*80)
                print("Generated SPARQL Query:")
                print("="*80)
                print(sparql)
                print("="*80 + "\n")

                # Ask if user wants to execute
                execute = input("Execute this query? [y/N]: ").strip().lower()
                if execute == 'y':
                    print("\nQuery execution not implemented in this demo.")
                    print("Use: slm-run -q '<query>' to execute manually.")

        except Exception as e:
            display_error(f"Fatal error: {e}", "error")
            return

    elif mode_choice in ["2", "3"]:
        print(f"\nMode {mode_choice} not yet implemented.")
        print("Only two-stage mode is available in this version.")

    else:
        print("\nInvalid mode selection.")

    print("\nThank you for using SPARQLLM Query Generator!\n")


if __name__ == "__main__":
    main()
