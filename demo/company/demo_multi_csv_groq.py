#!/usr/bin/env python3
"""
Multi-CSV Demo with GROQ support: Fast LLM-generated SPARQL queries

Usage:
    export GROQ_API_KEY="your-key"
    python demo/company/demo_multi_csv_groq.py
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class MultiCSVDemo:
    """Demo for LLM-generated SPARQL queries across multiple CSV files"""

    def __init__(self, provider: str = 'groq', model: Optional[str] = None):
        """
        Initialize demo.

        Args:
            provider: 'groq', 'openai', or 'ollama'
            model: Optional model name (defaults based on provider)
        """
        self.provider = provider
        self.demo_dir = Path(__file__).parent
        self.data_dir = self.demo_dir / "data"

        # Load schema information
        schema_path = self.demo_dir / "schema_advanced.txt"
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
                # Groq uses OpenAI-compatible API
                self.client = OpenAI(
                    base_url='https://api.groq.com/openai/v1',
                    api_key=api_key
                )
                # Groq's best models for code generation
                self.model = model or 'llama-3.3-70b-versatile'
                print(f"✓ Using Groq ({self.model})")
                print("  Fast inference with free tier!")

            elif provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not set")
                self.client = OpenAI(api_key=api_key)
                self.model = model or 'gpt-4'
                print(f"✓ Using OpenAI ({self.model})")

            elif provider == 'ollama':
                # Use OpenAI-compatible API
                self.client = OpenAI(
                    base_url='http://localhost:11434/v1',
                    api_key='ollama'  # Dummy key
                )
                self.model = model or 'qwen2.5:7b'
                print(f"✓ Using Ollama ({self.model})")
                print("  Make sure Ollama is running: ollama serve")

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except ImportError:
            raise RuntimeError("openai library not installed. Run: pip install openai")

    def _build_system_prompt(self) -> str:
        """Build system prompt with schema information."""
        return f"""You are a SPARQL-GGF query generator for SPARQLLM.

Your task: Convert natural language questions into SPARQL queries that use Graph Generating Functions (GGFs).

# Available Data Sources

{self.schema_info}

# SPARQL-GGF Syntax

## Loading CSV Files
Use the SLM-CSV GGF to load CSV files as RDF graphs:

```sparql
BIND(ggf:SLM-CSV("./path/to/file.csv") AS ?graphName)
```

Each CSV row becomes a blank node with properties based on column names.
Column "employee_id" becomes predicate ex:employee_id

## Querying a Single CSV
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?salary WHERE {{
    BIND(ggf:SLM-CSV("./demo/company/data/employees.csv") AS ?empGraph)

    GRAPH ?empGraph {{
        ?row ex:name ?name .
        ?row ex:salary ?salary .
    }}

    FILTER(?salary > 80000)
}}
ORDER BY DESC(?salary)
LIMIT 10
```

## Joining Two CSV Files
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?employee_name ?department_name ?salary WHERE {{
    # Load both CSV files
    BIND(ggf:SLM-CSV("./demo/company/data/employees.csv") AS ?empGraph)
    BIND(ggf:SLM-CSV("./demo/company/data/departments.csv") AS ?deptGraph)

    # Get employee data
    GRAPH ?empGraph {{
        ?emp ex:name ?employee_name .
        ?emp ex:salary ?salary .
        ?emp ex:department_id ?dept_id .
    }}

    # JOIN: Match on department_id
    GRAPH ?deptGraph {{
        ?dept ex:department_id ?dept_id .
        ?dept ex:department_name ?department_name .
    }}
}}
ORDER BY ?department_name
```

## Aggregation with GROUP BY
```sparql
SELECT ?department_name
       (COUNT(?name) AS ?employee_count)
       (AVG(?salary) AS ?avg_salary)
WHERE {{
    BIND(ggf:SLM-CSV("./demo/company/data/employees.csv") AS ?empGraph)
    BIND(ggf:SLM-CSV("./demo/company/data/departments.csv") AS ?deptGraph)

    GRAPH ?empGraph {{
        ?emp ex:name ?name .
        ?emp ex:salary ?salary .
        ?emp ex:department_id ?dept_id .
    }}

    GRAPH ?deptGraph {{
        ?dept ex:department_id ?dept_id .
        ?dept ex:department_name ?department_name .
    }}
}}
GROUP BY ?department_name
ORDER BY DESC(?avg_salary)
```

## UNION (Combine from Multiple Sources)
```sparql
SELECT DISTINCT ?location WHERE {{
    {{
        BIND(ggf:SLM-CSV("./demo/company/data/employees.csv") AS ?empGraph)
        GRAPH ?empGraph {{
            ?row ex:location ?location .
        }}
    }}
    UNION
    {{
        BIND(ggf:SLM-CSV("./demo/company/data/departments.csv") AS ?deptGraph)
        GRAPH ?deptGraph {{
            ?row ex:location ?location .
        }}
    }}
}}
ORDER BY ?location
```

# Important Rules

1. **Always use correct file paths**: ./demo/company/data/employees.csv and ./demo/company/data/departments.csv
2. **Use correct prefixes**: PREFIX ggf: <http://ggf.org/> and PREFIX ex: <http://example.org/>
3. **Column to predicate mapping**: CSV column "employee_id" → ex:employee_id
4. **JOIN syntax**: Use the same variable (?dept_id) in both GRAPH patterns to join
5. **Load only necessary CSVs**: Don't load departments.csv if the question only needs employee data
6. **FILTER placement**: Put FILTER clauses AFTER all triple patterns in the WHERE clause for better readability
7. **UNION syntax - CRITICAL**: Each pattern in UNION MUST have its own {{ }} braces inside WHERE:
   CORRECT:   WHERE {{ {{ pattern1 }} UNION {{ pattern2 }} }}
   WRONG:     WHERE {{ pattern1 }} UNION {{ pattern2 }}
8. **Return ONLY the SPARQL query**: No explanations, no markdown code blocks, just the raw SPARQL

Generate a valid SPARQL-GGF query for the user's question."""

    def generate_query(self, question: str, show_prompts: bool = True) -> str:
        """Generate SPARQL query from natural language question."""
        print(f"\n{'='*80}")
        print(f"Question: {question}")
        print(f"{'='*80}\n")

        # Build user prompt
        user_prompt = f"Generate a SPARQL query for this question:\n\n{question}"

        if show_prompts:
            print("📤 SYSTEM PROMPT (sent to LLM):")
            print("="*80)
            if len(self.system_prompt) > 1000:
                print(self.system_prompt[:1000] + "\n... [truncated, see schema_advanced.txt for full prompt] ...")
            else:
                print(self.system_prompt)
            print("="*80)
            print(f"\n📤 USER PROMPT (sent to LLM):")
            print("="*80)
            print(user_prompt)
            print("="*80)
            print("\n🤖 Calling LLM to generate SPARQL query...\n")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=1000
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

    def execute_query(self, sparql_query: str) -> bool:
        """Execute SPARQL query using slm-run."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.sparql',
            delete=False,
            prefix='company_demo_'
        ) as f:
            f.write(sparql_query)
            query_file = f.name

        try:
            print("Executing query with slm-run...\n")

            result = subprocess.run(
                ['python', '-m', 'SPARQLLM.cli.slm', '-c', 'config.ini', '-f', query_file],
                capture_output=True,
                text=True,
                timeout=60
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

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print("Error: Query execution timed out")
            return False
        except FileNotFoundError:
            print("Error: Python or SPARQLLM module not found. Make sure you're in the correct directory.")
            return False
        finally:
            if os.path.exists(query_file):
                os.unlink(query_file)

    def run_question(self, question: str, execute: bool = True) -> Optional[str]:
        """Run a complete question through the demo."""
        try:
            query = self.generate_query(question)
            if execute:
                self.execute_query(query)
            return query
        except Exception as e:
            print(f"Error: {e}")
            return None


def main():
    """Interactive demo CLI"""
    print("\n" + "="*80)
    print("Multi-CSV Demo: LLM-Generated SPARQL-GGF Queries")
    print("="*80)
    print("\nThis demo shows how LLM can automatically generate SPARQL queries that:")
    print("  1. Know which CSV file contains which data")
    print("  2. Join data across multiple CSV files")
    print("  3. Perform unions and data integration")
    print("\nData sources:")
    print("  - employees.csv (30 employees)")
    print("  - departments.csv (6 departments)")
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
            print("Set it with: export OPENAI_API_KEY=your-key-here")
            return
        provider = 'openai'
    elif provider_choice == "3":
        provider = 'ollama'
    else:
        print("\nInvalid choice. Using Groq.")
        provider = 'groq'

    # Initialize demo
    try:
        demo = MultiCSVDemo(provider=provider)
    except Exception as e:
        print(f"\nError initializing demo: {e}")
        return

    # Interactive mode
    print("\n" + "="*80)
    print("Enter questions (or 'quit' to exit)")
    print("Example questions:")
    print("  - What are the top 5 highest paid employees?")
    print("  - Show employees in the Engineering department")
    print("  - What is the average salary in each department?")
    print("  - What are all the unique office locations?")
    print("="*80 + "\n")

    while True:
        try:
            question = input("Question: ").strip()

            if not question:
                continue

            if question.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            demo.run_question(question, execute=True)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
