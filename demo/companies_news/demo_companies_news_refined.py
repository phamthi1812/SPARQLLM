#!/usr/bin/env python3
"""
Companies + Web News Demo with LLM Query Refinement

Enhanced version that allows LLM to refine queries when they fail or return no results.

Flow:
1. LLM generates SPARQL query from natural language
2. Execute query via sparqllm-ggf
3. If no results or error → provide feedback to LLM
4. LLM refines query and tries again
5. Repeat until success or max attempts

Usage:
    export GROQ_API_KEY="your-key"
    python demo/companies_news/demo_companies_news_refined.py
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple


class CompaniesNewsRefinedDemo:
    """Demo with iterative query refinement capabilities"""

    def __init__(self, provider: str = 'groq', model: Optional[str] = None, max_attempts: int = 3):
        """
        Initialize demo with refinement capabilities.

        Args:
            provider: 'groq', 'openai', or 'ollama'
            model: Optional model name
            max_attempts: Maximum refinement attempts (default: 3)
        """
        self.provider = provider
        self.max_attempts = max_attempts
        self.demo_dir = Path(__file__).parent
        self.data_dir = self.demo_dir / "data"

        # Load schema information
        schema_path = self.demo_dir / "schema.txt"
        with open(schema_path, 'r') as f:
            self.schema_info = f.read()

        # Initialize LLM client
        self._init_llm_client(provider, model)

        # System prompt for query generation
        self.system_prompt = self._build_system_prompt()

    def _init_llm_client(self, provider: str, model: Optional[str]):
        """Initialize LLM client based on provider."""
        try:
            from openai import OpenAI

            if provider == 'groq':
                api_key = os.getenv('GROQ_API_KEY')
                if not api_key:
                    raise ValueError("GROQ_API_KEY not set")
                self.client = OpenAI(
                    base_url='https://api.groq.com/openai/v1',
                    api_key=api_key
                )
                self.model = model or 'llama-3.3-70b-versatile'
                print(f"✓ Using Groq ({self.model})")

            elif provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not set")
                self.client = OpenAI(api_key=api_key)
                self.model = model or 'gpt-4'
                print(f"✓ Using OpenAI ({self.model})")

            elif provider == 'ollama':
                self.client = OpenAI(
                    base_url='http://localhost:11434/v1',
                    api_key='ollama'
                )
                self.model = model or 'qwen2.5:7b'
                print(f"✓ Using Ollama ({self.model})")

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except ImportError:
            raise RuntimeError("openai library not installed. Run: pip install openai")

    def _build_system_prompt(self) -> str:
        """Build system prompt with schema information."""
        return f"""You are a SPARQL-GGF query generator for SPARQLLM with multi-source capabilities.

Your task: Convert natural language questions into SPARQL queries that combine CSV data, web search, and LLM extraction.

{self.schema_info}

# Query Refinement Rules

When refining a query based on error feedback:
1. **Analyze the error message** - What went wrong?
2. **Check syntax** - Missing prefixes, wrong GGF functions?
3. **Check logic** - Filter before web search? Used subquery?
4. **Check data** - Correct file paths, column names, sector names?
5. **Simplify if needed** - Maybe web search isn't needed, CSV only?

Common issues:
- Missing FILTER in subquery before web search
- Wrong file path (should be ./demo/companies_news/data/companies.csv)
- Wrong GGF function name (ggf:SEARCH not ggf:SLM-WEBSEARCH)
- Wrong schema (schema: not ex:)
- Empty results = query syntax correct but logic wrong

Generate ONLY the refined SPARQL query, no explanations."""

    def generate_query(
        self,
        question: str,
        conversation_history: list = None,
        show_prompts: bool = True
    ) -> str:
        """
        Generate SPARQL query from natural language question.

        Args:
            question: User's natural language question
            conversation_history: Previous query attempts and feedback
            show_prompts: Whether to display prompts

        Returns:
            Generated SPARQL query
        """
        if conversation_history is None:
            conversation_history = []

        print(f"\n{'='*80}")
        print(f"Question: {question}")
        if conversation_history:
            print(f"Attempt: {len([m for m in conversation_history if m['role'] == 'assistant']) + 1}")
        print(f"{'='*80}\n")

        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]

        if not conversation_history:
            # First attempt
            user_prompt = f"Generate a SPARQL query for this question:\n\n{question}"
            messages.append({"role": "user", "content": user_prompt})
        else:
            # Refinement attempt - use full conversation history
            messages.extend(conversation_history)

        if show_prompts:
            print("📤 Messages sent to LLM:")
            print("="*80)
            for i, msg in enumerate(messages):
                role = msg['role'].upper()
                content = msg['content']
                if i == 0 and len(content) > 500:
                    content = content[:500] + "\n... [truncated] ..."
                print(f"\n[{role}]\n{content}\n")
            print("="*80)
            print("\n🤖 Calling LLM...\n")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=1500
            )

            query = response.choices[0].message.content.strip()

            # Clean markdown artifacts
            if query.startswith("```sparql"):
                query = query.replace("```sparql", "", 1)
            if query.startswith("```"):
                query = query.replace("```", "", 1)
            if query.endswith("```"):
                query = query[:-3]

            query = query.strip()

            print("\n" + "="*80)
            print("Generated SPARQL Query:")
            print("="*80)
            print(query)
            print("="*80 + "\n")

            return query

        except Exception as e:
            print(f"Error generating query: {e}")
            raise

    def execute_query(self, sparql_query: str) -> Tuple[bool, str, str]:
        """
        Execute SPARQL query using slm-run.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.sparql',
            delete=False,
            prefix='companies_news_'
        ) as f:
            f.write(sparql_query)
            query_file = f.name

        try:
            print("Executing query with slm-run...\n")

            result = subprocess.run(
                ['python', '-m', 'SPARQLLM.cli.slm', '-c', 'config.ini', '-f', query_file],
                capture_output=True,
                text=True,
                timeout=120
            )

            print("="*80)
            print("Query Results:")
            print("="*80)

            if result.stdout:
                print(result.stdout)

            if result.stderr:
                print("\nStderr:")
                print(result.stderr)

            print("="*80 + "\n")

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = "Query execution timed out (120 seconds)"
            print(f"Error: {error_msg}")
            return False, "", error_msg
        except FileNotFoundError:
            error_msg = "Python or SPARQLLM module not found"
            print(f"Error: {error_msg}")
            return False, "", error_msg
        finally:
            if os.path.exists(query_file):
                os.unlink(query_file)

    def analyze_results(self, success: bool, stdout: str, stderr: str, query: str = "") -> Dict[str, any]:
        """
        Analyze execution results to determine if refinement is needed.
        Uses trace-based analysis to provide specific feedback.

        Returns:
            Dict with keys: needs_refinement, reason, feedback
        """
        # Check for obvious errors
        if not success:
            return {
                'needs_refinement': True,
                'reason': 'execution_error',
                'feedback': f"Query failed to execute. Error:\n{stderr}\n\nPlease fix the syntax or logic error."
            }

        # Check for empty results
        empty_patterns = [
            r'Empty DataFrame',
            r'Columns: \[\]',
            r'0 rows',
            r'\[\]',  # Empty list
        ]

        is_empty = any(re.search(pattern, stdout, re.IGNORECASE) for pattern in empty_patterns)

        # Also check if stdout is very short (likely no results)
        if len(stdout.strip()) < 50 and not stderr:
            is_empty = True

        if is_empty:
            # Trace-based feedback analysis
            feedback_parts = ["Query executed successfully but returned no results.\n"]

            # Analyze which GGF functions were used
            if "ggf:SLM-CSV" in query:
                feedback_parts.append("✓ CSV loading: Successful")

            if "ggf:SEARCH" in query or "ggf:SLM-WEBSEARCH" in query:
                if "MCP result:" in stdout:
                    feedback_parts.append("✓ Web search: Executed (but may need different keywords)")
                else:
                    feedback_parts.append("✗ Web search: May have failed or returned no results")

            # Check for common issues
            if "FILTER" in query:
                feedback_parts.append("⚠ FILTER conditions might be eliminating all results")

            if "GROUP BY" in query:
                feedback_parts.append("⚠ GROUP BY might be structured incorrectly")

            # Parse stdout for execution hints
            if "Named graph has" in stdout:
                triple_count = re.search(r'Named graph has (\d+) triples', stdout)
                if triple_count:
                    count = int(triple_count.group(1))
                    if count > 0:
                        feedback_parts.append(f"✓ Intermediate data: {count} triples loaded")
                    else:
                        feedback_parts.append("✗ Intermediate results: Empty graph")

            feedback_parts.append("\nSuggestions:")
            feedback_parts.append("1. Verify filter conditions match actual data values")
            feedback_parts.append("2. Check query logic and graph patterns")
            feedback_parts.append("3. Try simplifying the query to isolate the issue")

            return {
                'needs_refinement': True,
                'reason': 'empty_results',
                'feedback': "\n".join(feedback_parts)
            }

        # Check for warnings or issues in stderr
        if stderr and ('warning' in stderr.lower() or 'error' in stderr.lower()):
            # But if we got results, this might be okay
            if len(stdout.strip()) > 100:
                return {
                    'needs_refinement': False,
                    'reason': 'success_with_warnings',
                    'feedback': None
                }
            else:
                return {
                    'needs_refinement': True,
                    'reason': 'warnings_no_results',
                    'feedback': f"Query produced warnings and no results:\n{stderr}\n\nPlease check the query logic."
                }

        # Success!
        return {
            'needs_refinement': False,
            'reason': 'success',
            'feedback': None
        }

    def run_with_refinement(self, question: str, show_prompts: bool = True) -> Optional[Dict]:
        """
        Run question with automatic query refinement.

        Returns:
            Dict with keys: success, query, attempts, results
        """
        conversation_history = []
        attempts = []

        for attempt_num in range(1, self.max_attempts + 1):
            print(f"\n{'='*80}")
            print(f"🔄 ATTEMPT {attempt_num}/{self.max_attempts}")
            print(f"{'='*80}\n")

            # Generate query
            if attempt_num == 1:
                query = self.generate_query(question, show_prompts=show_prompts)
                # Add to conversation history
                conversation_history.append({
                    "role": "user",
                    "content": f"Generate a SPARQL query for this question:\n\n{question}"
                })
                conversation_history.append({
                    "role": "assistant",
                    "content": query
                })
            else:
                # Refinement attempt
                query = self.generate_query(
                    question,
                    conversation_history=conversation_history,
                    show_prompts=show_prompts
                )
                # Update conversation history with new query
                conversation_history.append({
                    "role": "assistant",
                    "content": query
                })

            # Execute query
            success, stdout, stderr = self.execute_query(query)

            # Analyze results (trace-based)
            analysis = self.analyze_results(success, stdout, stderr, query)

            # Store attempt
            attempts.append({
                'attempt': attempt_num,
                'query': query,
                'success': success,
                'stdout': stdout,
                'stderr': stderr,
                'analysis': analysis
            })

            # Check if we're done
            if not analysis['needs_refinement']:
                print("\n✅ SUCCESS! Query returned results.\n")
                return {
                    'success': True,
                    'query': query,
                    'attempts': attempts,
                    'results': stdout
                }

            # Need refinement
            if attempt_num < self.max_attempts:
                print(f"\n⚠️  {analysis['reason'].upper()}: Refinement needed")
                print(f"Reason: {analysis['feedback']}\n")

                # Add feedback to conversation for next attempt
                refinement_prompt = f"""{analysis['feedback']}

Original question: {question}

Please generate a refined SPARQL query that fixes the issue."""

                conversation_history.append({
                    "role": "user",
                    "content": refinement_prompt
                })
            else:
                print(f"\n❌ Max attempts ({self.max_attempts}) reached. Query still not working.\n")

        # Failed after max attempts
        return {
            'success': False,
            'query': query,
            'attempts': attempts,
            'results': None
        }


def main():
    """Interactive demo CLI with refinement"""
    print("\n" + "="*80)
    print("Companies + Web News Demo: WITH QUERY REFINEMENT")
    print("="*80)
    print("\nEnhanced version that automatically refines queries when they fail!")
    print("\nFeatures:")
    print("  ✓ Detects execution errors and empty results")
    print("  ✓ Provides feedback to LLM about what went wrong")
    print("  ✓ LLM refines query and tries again (max 3 attempts)")
    print("  ✓ Learns from failures to generate better queries")
    print("="*80 + "\n")

    # Provider selection
    print("Select LLM provider:")
    print("  1. Groq (Fast, Free Tier) [RECOMMENDED]")
    print("  2. OpenAI (GPT-4)")
    print("  3. Ollama (Local)")

    provider_choice = input("\nProvider [1/2/3]: ").strip() or "1"

    if provider_choice == "1":
        if not os.getenv('GROQ_API_KEY'):
            print("\nError: GROQ_API_KEY not set")
            print("Get a free API key at: https://console.groq.com")
            print("Then: export GROQ_API_KEY=your-key-here")
            return
        provider = 'groq'
    elif provider_choice == "2":
        if not os.getenv('OPENAI_API_KEY'):
            print("\nError: OPENAI_API_KEY not set")
            return
        provider = 'openai'
    elif provider_choice == "3":
        provider = 'ollama'
    else:
        provider = 'groq'

    # Max attempts
    max_attempts_input = input("\nMax refinement attempts [3]: ").strip()
    max_attempts = int(max_attempts_input) if max_attempts_input else 3

    # Initialize demo
    try:
        demo = CompaniesNewsRefinedDemo(provider=provider, max_attempts=max_attempts)
    except Exception as e:
        print(f"\nError initializing demo: {e}")
        return

    # Interactive mode
    print("\n" + "="*80)
    print("Enter questions (or 'quit' to exit)")
    print("\nExample questions:")
    print("  - Tell me about Tesla")
    print("  - Find news about OpenAI")
    print("  - What AI companies are there?")
    print("  - Show me tech companies in San Francisco")
    print("="*80 + "\n")

    while True:
        try:
            question = input("Question: ").strip()

            if not question:
                continue

            if question.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            result = demo.run_with_refinement(question, show_prompts=True)

            if result['success']:
                print(f"\n✅ Success after {len(result['attempts'])} attempt(s)")
            else:
                print(f"\n❌ Failed after {len(result['attempts'])} attempts")
                print("\nAll attempted queries:")
                for att in result['attempts']:
                    print(f"\n--- Attempt {att['attempt']} ---")
                    print(att['query'][:200] + "...")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
