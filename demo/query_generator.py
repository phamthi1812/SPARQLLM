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

    def __init__(
        self,
        mode: str = 'plan',
        provider: str = 'openai',
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        config_path: Optional[str] = None,
        interactive: bool = False,
        use_multi_step: bool = False
    ):
        """
        Initialize query generator.

        Args:
            mode: 'plan' (two-stage) or 'direct' (legacy SPARQL generation)
            provider: 'openai' or 'ollama'
            model: LLM model name (auto-detected from config if not provided)
            api_key: Optional API key for OpenAI (reads from env if not provided)
            config_path: Path to config.ini for Ollama settings
            interactive: Enable step-by-step execution mode
            use_multi_step: Use multi-step system prompt for complex queries
        """
        self.mode = mode
        self.provider = provider
        self.llm_available = False
        self.client = None
        self.interactive = interactive
        self.use_multi_step = use_multi_step

        # Initialize LLM client based on provider
        if provider == 'openai':
            self._init_openai(model or 'gpt-4', api_key)
        elif provider == 'ollama':
            self._init_ollama(model, config_path or 'config.ini')
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'ollama'.")

        # Load prompts directory
        self.prompts_dir = Path(__file__).parent / "prompts"
        self.prompts_dir.mkdir(exist_ok=True)

        if mode == 'plan':
            # Load plan system prompt (standard or multi-step)
            if use_multi_step:
                prompt_path = self.prompts_dir / "plan_system_prompt_multi_step.txt"
            else:
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

    def _init_openai(self, model: str, api_key: Optional[str] = None):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            # Only initialize client if API key is available
            api_key_val = api_key or os.getenv('OPENAI_API_KEY')
            if api_key_val:
                self.client = OpenAI(api_key=api_key_val)
                self.model = model
                self.llm_available = True
                print(f"✓ OpenAI client initialized (model: {model})")
            else:
                print("Warning: OPENAI_API_KEY not set. LLM features disabled.")
                self.llm_available = False
                self.client = None
        except ImportError:
            print("Warning: openai library not installed. LLM features disabled.")
            print("Install with: pip install openai")
            self.llm_available = False
            self.client = None

    def _init_ollama(self, model: Optional[str] = None, config_path: str = 'config.ini'):
        """Initialize Ollama client using OpenAI-compatible API."""
        try:
            from openai import OpenAI
            from SPARQLLM.config import ConfigSingleton

            # Load config to get Ollama settings
            config = ConfigSingleton(config_path)
            ollama_url = config.config['Requests']['SLM-OLLAMA-URL']
            ollama_model = model or config.config['Requests']['SLM-OLLAMA-MODEL']

            # Convert Ollama generate endpoint to chat endpoint
            base_url = ollama_url.replace('/api/generate', '')
            if not base_url.endswith('/'):
                base_url += '/'
            base_url += 'v1'

            # Ollama doesn't require API key, but OpenAI client needs something
            self.client = OpenAI(
                base_url=base_url,
                api_key='ollama'  # Dummy key, Ollama ignores it
            )
            self.model = ollama_model
            self.llm_available = True
            print(f"✓ Ollama client initialized (model: {ollama_model}, url: {base_url})")

        except ImportError:
            print("Warning: openai library not installed. Install with: pip install openai")
            self.llm_available = False
            self.client = None
        except Exception as e:
            print(f"Warning: Failed to initialize Ollama client: {e}")
            print("Make sure Ollama is running: ollama serve")
            self.llm_available = False
            self.client = None

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

    @staticmethod
    def _validate_and_fix_plan(plan: dict) -> dict:
        """
        Validate and auto-fix common plan schema issues.

        Args:
            plan: Raw plan from LLM

        Returns:
            Fixed plan with all required fields
        """
        # Ensure version
        if 'version' not in plan:
            plan['version'] = '1.0'

        # Ensure steps array exists
        if 'steps' not in plan or not isinstance(plan['steps'], list):
            plan['steps'] = []

        # Fix each step
        for idx, step in enumerate(plan['steps']):
            # Add missing 'id' field
            if 'id' not in step:
                step['id'] = f'step{idx + 1}'

            # Ensure operation field exists
            if 'operation' not in step:
                step['operation'] = 'unknown'

            # Ensure ggf exists
            if 'ggf' not in step:
                step['ggf'] = {'name': 'UNKNOWN', 'args': {}}

            # Ensure bindings exists (can be empty)
            if 'bindings' not in step:
                step['bindings'] = {}

            # Ensure depends_on is a list
            if 'depends_on' not in step:
                step['depends_on'] = []
            elif not isinstance(step['depends_on'], list):
                step['depends_on'] = [step['depends_on']]

        # Ensure output section exists and has variables
        if 'output' not in plan or not plan['output'].get('variables'):
            # Extract variables from last step bindings
            if plan['steps']:
                last_step = plan['steps'][-1]
                variables = list(last_step.get('bindings', {}).keys())
                if not variables:
                    # Fall back to all bindings from all steps
                    variables = []
                    for step in plan['steps']:
                        variables.extend(list(step.get('bindings', {}).keys()))
                    # Remove duplicates while preserving order
                    seen = set()
                    variables = [v for v in variables if not (v in seen or seen.add(v))]

                plan['output'] = {
                    'variables': variables if variables else ['result'],
                    'distinct': True
                }
            else:
                plan['output'] = {'variables': ['result'], 'distinct': True}

        # Ensure output has at least one variable
        if not plan['output'].get('variables'):
            plan['output']['variables'] = ['result']

        return plan

    @staticmethod
    def _map_ggf_from_description(step: dict, user_question: str) -> dict:
        """
        Intelligently map a generic step description to actual GGF function calls.

        This handles cases where LLMs produce task decompositions instead of
        proper GGF function calls.

        Args:
            step: Step dict (possibly with UNKNOWN GGF)
            user_question: Original user question for context

        Returns:
            Updated step with proper GGF name and args
        """
        ggf = step.get('ggf', {})
        ggf_name = ggf.get('name', 'UNKNOWN')

        # If already has a valid GGF name, don't modify
        if ggf_name not in ['UNKNOWN', 'unknown', '']:
            return step

        # Get step description/operation for analysis
        description = step.get('description', '').lower()
        operation = step.get('operation', '').lower()
        combined_text = f"{description} {operation}"

        # Pattern matching for GGF selection
        # Priority: SEARCH → SNAP → LLM

        # Web search indicators
        search_keywords = ['search', 'find', 'query', 'look for', 'locate', 'discover',
                          'search engine', 'google', 'duckduckgo']
        if any(kw in combined_text for kw in search_keywords):
            # Extract query from user question or description
            query = user_question  # Default to full question
            step['ggf'] = {
                'name': 'SEARCH',
                'args': {'query': query, 'limit': 5}
            }
            step['operation'] = 'web_search'
            step['bindings'] = {'title': '?title', 'url': '?url'}
            return step

        # Web fetch / browser snapshot indicators
        fetch_keywords = ['fetch', 'get', 'retrieve', 'download', 'load page', 'visit',
                         'browser', 'snapshot', 'html', 'webpage']
        if any(kw in combined_text for kw in fetch_keywords):
            step['ggf'] = {
                'name': 'SNAP',
                'args': {'url': '?url', 'wait_ms': 2000, 'snippet_only': True}
            }
            step['operation'] = 'web_fetch'
            step['bindings'] = {'text': '?pageText'}
            return step

        # LLM extraction / processing indicators
        llm_keywords = ['extract', 'analyze', 'process', 'understand', 'parse', 'interpret',
                       'identify', 'determine', 'recognize', 'classify', 'review']
        if any(kw in combined_text for kw in llm_keywords):
            # Build generic prompt
            prompt_text = f"Analyze and extract relevant information from the provided text"
            step['ggf'] = {
                'name': 'LLM',
                'args': {'prompt': prompt_text}
            }
            step['operation'] = 'llm_extract'
            step['bindings'] = {'result': '?result'}
            return step

        # File/filesystem indicators
        file_keywords = ['file', 'directory', 'folder', 'path', 'read', 'load', 'csv']
        if any(kw in combined_text for kw in file_keywords):
            if 'csv' in combined_text:
                step['ggf'] = {
                    'name': 'SLM-CSV',
                    'args': {'path': 'data.csv'}
                }
                step['operation'] = 'read_filesystem'
            else:
                step['ggf'] = {
                    'name': 'SLM-READFILE',
                    'args': {'file': 'file.txt'}
                }
                step['operation'] = 'read_filesystem'
            step['bindings'] = {'content': '?content'}
            return step

        # Default: If still UNKNOWN, map to generic SEARCH
        # This ensures we always have a valid operation
        if ggf_name == 'UNKNOWN':
            step['ggf'] = {
                'name': 'SEARCH',
                'args': {'query': user_question, 'limit': 5}
            }
            step['operation'] = 'web_search'
            step['bindings'] = {'title': '?title', 'url': '?url'}

        return step

    @staticmethod
    def _auto_fix_plan_ggfs(plan: dict, user_question: str) -> dict:
        """
        Post-process plan to fix UNKNOWN GGFs using intelligent mapping.

        Args:
            plan: Plan with possibly generic/UNKNOWN GGFs
            user_question: Original user question

        Returns:
            Plan with GGFs mapped to actual functions
        """
        if 'steps' not in plan:
            return plan

        for step in plan['steps']:
            ggf_name = step.get('ggf', {}).get('name', '')
            if ggf_name in ['UNKNOWN', 'unknown', '']:
                # Try to infer GGF from step description/operation
                QueryGenerator._map_ggf_from_description(step, user_question)

        return plan

    @staticmethod
    def is_complex_query(question: str) -> bool:
        """
        Detect if a question requires multi-step processing.

        Args:
            question: User's natural language question

        Returns:
            True if query appears to need multi-step planning
        """
        # Keywords indicating multi-step complexity
        multi_step_keywords = [
            'find', 'compare', 'near', 'nearby', 'cheap', 'cheapest',
            'best', 'top', 'most', 'least', 'expensive', 'price',
            'extract and', 'search for', 'fetch', 'get information about',
            'what are the', 'which', 'how many', 'located', 'around',
            'conference', 'event', 'restaurant', 'hotel', 'store'
        ]

        question_lower = question.lower()

        # Check for multi-step indicators
        keyword_count = sum(1 for kw in multi_step_keywords if kw in question_lower)

        # Complex if:
        # - Contains 2+ multi-step keywords
        # - Or contains words suggesting external data fetching + comparison
        if keyword_count >= 2:
            return True

        # Check for patterns suggesting web search + extraction
        web_patterns = ['web conference', 'online', 'website', 'search for']
        comparison_patterns = ['compare', 'vs', 'versus', 'better than', 'cheaper than']

        has_web = any(pattern in question_lower for pattern in web_patterns)
        has_comparison = any(pattern in question_lower for pattern in comparison_patterns)

        return has_web or has_comparison

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

        # Call LLM with JSON mode enforcement
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=2000,
                response_format={"type": "json_object"}  # Force JSON output
            )

            plan_json = response.choices[0].message.content.strip()

            # Clean markdown artifacts
            plan_json = re.sub(r'^```json\s*\n', '', plan_json, flags=re.MULTILINE)
            plan_json = re.sub(r'^```\s*\n', '', plan_json, flags=re.MULTILINE)
            plan_json = re.sub(r'\n```$', '', plan_json)
            plan_json = plan_json.strip()

            # Parse JSON
            plan = json.loads(plan_json)

            # Validate and fix plan schema
            plan = self._validate_and_fix_plan(plan)

            # Auto-fix UNKNOWN GGFs using intelligent mapping
            plan = self._auto_fix_plan_ggfs(plan, user_question)

            return plan

        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nResponse: {plan_json[:200]}")
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {e}")

    def execute_step_by_step(self, plan: dict, sparql: str) -> bool:
        """
        Execute SPARQL query step-by-step with user interaction.

        Args:
            plan: Logical plan dict
            sparql: Generated SPARQL query

        Returns:
            True if execution completed, False if aborted
        """
        steps = plan.get('steps', [])
        print(f"\n{'='*80}")
        print(f"INTERACTIVE EXECUTION MODE")
        print(f"{'='*80}")
        print(f"\nTotal steps: {len(steps)}")

        # Estimate execution stats
        llm_steps = sum(1 for s in steps if 'llm' in s.get('operation', '').lower())
        web_steps = sum(1 for s in steps if 'web' in s.get('operation', '').lower()
                       or s.get('ggf', {}).get('name') in ['SEARCH', 'SNAP'])

        print(f"Estimated LLM calls: {llm_steps}")
        print(f"Estimated web requests: {web_steps}")
        print(f"Approximate execution time: {len(steps) * 2}s")
        print(f"\n{'='*80}\n")

        # Show query preview
        print("Generated SPARQL Query:")
        print("-" * 80)
        print(sparql)
        print("-" * 80 + "\n")

        # Step-by-step execution simulation (in reality, would execute via slm-run)
        for idx, step in enumerate(steps, 1):
            step_id = step.get('id', f'step{idx}')
            operation = step.get('operation', 'unknown')
            ggf_info = step.get('ggf', {})
            ggf_name = ggf_info.get('name', 'unknown')
            ggf_args = ggf_info.get('args', {})

            print(f"\n{'─'*80}")
            print(f"Step {idx}/{len(steps)}: {step_id}")
            print(f"{'─'*80}")
            print(f"Operation: {operation}")
            print(f"GGF: {ggf_name}")
            print(f"Arguments:")
            for key, value in ggf_args.items():
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                print(f"  {key}: {value_str}")

            if step.get('depends_on'):
                print(f"Depends on: {', '.join(step['depends_on'])}")

            # Prompt user
            print(f"\n{'─'*80}")
            choice = input("Continue? [y=yes, s=skip, a=abort]: ").strip().lower()

            if choice == 'a':
                print("\nExecution aborted by user.\n")
                return False
            elif choice == 's':
                print(f"Skipping {step_id}...\n")
                continue
            else:
                print(f"Executing {step_id}...")
                # In a real implementation, would execute this step via slm-run
                # For now, just simulate with a message
                print(f"✓ {step_id} completed (simulated)")

                # Show simulated results
                print(f"\nIntermediate results:")
                bindings = step.get('bindings', {})
                if bindings:
                    print(f"  Variables bound: {', '.join(bindings.keys())}")
                    print(f"  (Actual values would appear here after real execution)")

        print(f"\n{'='*80}")
        print("All steps completed!")
        print(f"{'='*80}\n")

        print("To execute the full query, use:")
        print(f"  slm-run -q '<your-sparql-query>'\n")

        return True

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

                    # If interactive mode, execute step-by-step
                    if self.interactive:
                        self.execute_step_by_step(plan, sparql)

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

    # Provider selection
    print("\nSelect LLM provider:")
    print("  1. OpenAI (GPT-4) [Requires OPENAI_API_KEY]")
    print("  2. Ollama (Local) [Requires ollama serve]")

    provider_choice = input("\nProvider [1/2]: ").strip() or "1"

    if provider_choice == "1":
        provider = 'openai'
        # Check for API key
        if not os.getenv('OPENAI_API_KEY'):
            print("\nWarning: OPENAI_API_KEY environment variable not set.")
            print("Set it with: export OPENAI_API_KEY=your-key-here")
            return
    elif provider_choice == "2":
        provider = 'ollama'
        print("\nUsing Ollama (make sure 'ollama serve' is running)")
    else:
        print("\nInvalid provider selection.")
        return

    # Mode selection
    print("\nSelect mode:")
    print("  1. Two-stage (plan + compile) [RECOMMENDED]")
    print("  2. Direct SPARQL generation [NOT IMPLEMENTED YET]")
    print("  3. Comparison mode [NOT IMPLEMENTED YET]")

    mode_choice = input("\nMode [1/2/3]: ").strip() or "1"

    if mode_choice == "1":
        # Get user question first to detect complexity
        print("\n" + "="*80)
        question = input("Enter your question: ").strip()

        if not question:
            print("No question provided. Exiting.")
            return

        # Auto-detect if multi-step prompt should be used
        use_multi_step = QueryGenerator.is_complex_query(question)

        if use_multi_step:
            print("\n[Auto-detected: Complex query - using multi-step planner]")
        else:
            print("\n[Auto-detected: Simple query - using standard planner]")

        # Ask about interactive mode
        interactive_choice = input("\nEnable step-by-step execution mode? [y/N]: ").strip().lower()
        interactive = (interactive_choice == 'y')

        # Two-stage mode
        generator = QueryGenerator(
            mode='plan',
            provider=provider,
            interactive=interactive,
            use_multi_step=use_multi_step
        )

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
