#!/usr/bin/env python3
"""
Companies + Web News Demo: CSV + Web Search + LLM Extraction

This demo showcases:
1. Loading company data from CSV
2. Searching web for live news/information
3. Using LLM to extract structured data from unstructured web content
4. Combining all three sources in SPARQL queries

Usage:
    export GROQ_API_KEY="your-key"
    python demo/companies_news/demo_companies_news.py
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class CompaniesNewsDemo:
    """Demo for CSV + Web Search + LLM extraction queries"""

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
                print("  Fast inference with free tier!")

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
                print("  Make sure Ollama is running: ollama serve")

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except ImportError:
            raise RuntimeError("openai library not installed. Run: pip install openai")

    def _build_system_prompt(self) -> str:
        """Build system prompt with schema information."""
        return f"""You are a SPARQL-GGF query generator for SPARQLLM with multi-source capabilities.

Your task: Convert natural language questions into SPARQL queries that combine CSV data, web search, and LLM extraction.

{self.schema_info}

# Additional SPARQL-GGF Syntax

## Web Search GGF
```sparql
# Search the web using SEARCH (DuckDuckGo) and get results as RDF
BIND(CONCAT("company name", " news 2024") AS ?search_query)
BIND(ggf:SEARCH(?search_query) AS ?webGraph)

GRAPH ?webGraph {{
    ?feed schema:dataFeedElement ?feedItem .
    ?feedItem schema:item ?item .
    ?item schema:name ?title .
    ?item schema:description ?snippet .
    BIND(?item AS ?url)  # The item's IRI is the URL
}}
```

## LLM Extraction GGF
```sparql
# Extract structured data from unstructured text using LLM
# Use SLM-LLMGRAPH_GROQ for fast inference (recommended)
BIND(CONCAT(
    "Extract funding information from: ", ?text,
    ". Return JSON-LD: {{\\"@context\\": \\"http://schema.org/\\", ",
    "\\"@type\\": \\"MonetaryAmount\\", ",
    "\\"amount\\": \\"...\\"}}
) AS ?llm_prompt)

BIND(ggf:SLM-LLMGRAPH_GROQ(?llm_prompt) AS ?llmGraph)
GRAPH ?llmGraph {{
    ?entity schema:description ?extracted_info .
}}
```

# Query Generation Rules

1. **CSV First**: Always load companies from CSV first
2. **Filter Early**: Use subquery with LIMIT before web search/LLM
3. **LIMIT is Critical**: Web search + LLM are slow, use LIMIT 3-5
4. **Truncate Text**: Use SUBSTR(?text, 1, 500) before sending to LLM
5. **Structured Prompts**: Tell LLM to return JSON-LD format
6. **Performance**: One web search = 1-2 sec, one LLM call = 2-5 sec

# Query Complexity Levels

**Level 1 - CSV Only:** Fast, no API calls
```sparql
SELECT ?company WHERE {{
    BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?g)
    GRAPH ?g {{ ?row ex:company_name ?company . }}
    FILTER(?sector = "AI")
}}
```

**Level 2 - CSV + Web:** Medium speed, web search needed
```sparql
SELECT ?company ?news_title WHERE {{
    BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?g)
    GRAPH ?g {{ ?row ex:company_name ?company . }}
    FILTER(?company = "OpenAI")

    BIND(CONCAT(?company, " news 2024") AS ?q)
    BIND(ggf:SEARCH(?q) AS ?web)
    GRAPH ?web {{
        ?feed schema:dataFeedElement ?feedItem .
        ?feedItem schema:item ?item .
        ?item schema:name ?news_title .
    }}
}}
LIMIT 5
```

**Level 3 - CSV + Web + LLM:** Slow, use LIMIT aggressively
```sparql
SELECT ?company ?extracted_info WHERE {{
    {{
        SELECT ?company WHERE {{
            BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?g)
            GRAPH ?g {{ ?row ex:company_name ?company . }}
        }}
        LIMIT 3  # ← CRITICAL for performance
    }}

    BIND(ggf:SEARCH(CONCAT(?company, " funding")) AS ?web)
    GRAPH ?web {{
        ?feed schema:dataFeedElement ?feedItem .
        ?feedItem schema:item ?item .
        ?item schema:description ?snippet .
    }}

    BIND(CONCAT("Extract funding: ", SUBSTR(?snippet, 1, 500)) AS ?prompt)
    BIND(ggf:SLM-LLMGRAPH_GROQ(?prompt) AS ?llm)
    GRAPH ?llm {{ ?e schema:description ?extracted_info . }}
}}
```

# ⚠️ FEW-SHOT EXAMPLES: Learn from These Working Queries!

These are COMPLETE working queries for common questions. FOLLOW THESE PATTERNS EXACTLY!

## Example 1: "Tell me about Tesla" or "Find news about Tesla"

**USER QUESTION:** "Tell me about Tesla"

**CORRECT QUERY:**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
PREFIX schema: <https://schema.org/>

SELECT ?company_name ?news_title ?news_url WHERE {{
    # ← SUBQUERY filters to Tesla FIRST (only 1 company)
    {{
        SELECT ?company_name WHERE {{
            BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?csvGraph)
            GRAPH ?csvGraph {{
                ?row ex:company_name ?company_name .
            }}
            FILTER(?company_name = "Tesla")
        }}
    }}

    # Now web search executes ONLY for Tesla (1 search, not 15!)
    BIND(CONCAT(?company_name, " latest news 2024") AS ?search_query)
    BIND(ggf:SEARCH(?search_query) AS ?webGraph)

    GRAPH ?webGraph {{
        ?feed schema:dataFeedElement ?feedItem .
        ?feedItem schema:item ?item .
        ?item schema:name ?news_title .
        BIND(?item AS ?news_url)
    }}
}}
LIMIT 5
```

## Example 2: "What's happening with OpenAI?"

**USER QUESTION:** "What's happening with OpenAI?"

**CORRECT QUERY:**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
PREFIX schema: <https://schema.org/>

SELECT ?company ?title ?url ?snippet WHERE {{
    # ← SUBQUERY filters to OpenAI FIRST
    {{
        SELECT ?company WHERE {{
            BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?g)
            GRAPH ?g {{
                ?row ex:company_name ?company .
            }}
            FILTER(?company = "OpenAI")
        }}
    }}

    # Web search ONLY for OpenAI (1 search)
    BIND(CONCAT(?company, " news 2024") AS ?q)
    BIND(ggf:SEARCH(?q) AS ?web)
    GRAPH ?web {{
        ?feed schema:dataFeedElement ?feedItem .
        ?feedItem schema:item ?item .
        ?item schema:name ?title .
        ?item schema:description ?snippet .
        BIND(?item AS ?url)
    }}
}}
LIMIT 5
```

## Example 3: "Show me AI companies"

**USER QUESTION:** "Show me all AI companies"

**CORRECT QUERY (CSV only, no subquery needed):**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?company_name ?sector ?location WHERE {{
    BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?g)
    GRAPH ?g {{
        ?row ex:company_name ?company_name .
        ?row ex:sector ?sector .
        ?row ex:location ?location .
    }}
    FILTER(?sector = "Artificial Intelligence")
}}
```

# Important Rules

## ⚠️ CRITICAL RULE #1: ALWAYS Use Subquery When Filtering Before Web Search or LLM!

**WHY:** SPARQL executes ALL BIND operations FIRST, THEN applies FILTER. Without subquery, you'll search ALL 15 companies even if you only want 1!

**WRONG** (searches all 15 companies):
```sparql
BIND(ggf:SLM-CSV("companies.csv") AS ?g)
GRAPH ?g {{ ?row ex:company_name ?company . }}
FILTER(?company = "Tesla")  # ← TOO LATE!
BIND(ggf:SEARCH(CONCAT(?company, " news")) AS ?web)  # ← Already searched ALL 15!
```

**CORRECT** (searches only Tesla):
```sparql
{{  # ← Subquery filters FIRST
    SELECT ?company WHERE {{
        BIND(ggf:SLM-CSV("companies.csv") AS ?g)
        GRAPH ?g {{ ?row ex:company_name ?company . }}
        FILTER(?company = "Tesla")
    }}
}}
BIND(ggf:SEARCH(CONCAT(?company, " news")) AS ?web)  # ← Only 1 search!
```

**WHEN TO USE SUBQUERY:**
- Question asks about a SPECIFIC company (Tesla, OpenAI, etc.) → USE SUBQUERY
- Question asks about ALL companies or a category → No subquery needed

## Other Rules

2. **Always use correct file path**: ./demo/companies_news/data/companies.csv
3. **Use correct prefixes**: PREFIX ggf: <http://ggf.org/>, PREFIX ex: <http://example.org/>, PREFIX schema: <https://schema.org/>
4. **Column mapping**: company_name → ex:company_name, sector → ex:sector, etc.
5. **Use exact sector names**: "Artificial Intelligence", "Technology" (NOT "Tech" or "AI")
6. **Web search**: Use ggf:SEARCH() with nested RDF pattern (dataFeedElement → item)
7. **LLM extraction**: Use ggf:SLM-LLMGRAPH_GROQ() for fast inference
8. **LIMIT with web/LLM**: Always use LIMIT (3-5) when combining CSV with web/LLM
9. **Truncate text**: SUBSTR(?text, 1, 500) before LLM
10. **JSON-LD prompts**: Tell LLM to return structured JSON-LD
11. **Return ONLY the SPARQL query**: No explanations, no markdown

Generate a valid SPARQL-GGF query for the user's question."""

    def generate_query(self, question: str, show_prompts: bool = True) -> str:
        """Generate SPARQL query from natural language question."""
        print(f"\n{'='*80}")
        print(f"Question: {question}")
        print(f"{'='*80}\n")

        user_prompt = f"Generate a SPARQL query for this question:\n\n{question}"

        if show_prompts:
            print("📤 SYSTEM PROMPT (sent to LLM):")
            print("="*80)
            if len(self.system_prompt) > 1000:
                print(self.system_prompt[:1000] + "\n... [truncated, see schema.txt for full prompt] ...")
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

    def execute_query(self, sparql_query: str) -> bool:
        """Execute SPARQL query using slm-run."""
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
                timeout=120  # Longer timeout for web + LLM
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
            print("Error: Query execution timed out (web search + LLM can be slow)")
            return False
        except FileNotFoundError:
            print("Error: Python or SPARQLLM module not found.")
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
    print("Companies + Web News Demo: Multi-Source Data Integration")
    print("="*80)
    print("\nThis demo shows how to combine 3 data sources:")
    print("  1. 📊 CSV data (companies.csv)")
    print("  2. 🌐 Web search (live news)")
    print("  3. 🤖 LLM extraction (structured info from text)")
    print("\nData: 15 tech companies (OpenAI, Google, Tesla, etc.)")
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

    # Initialize demo
    try:
        demo = CompaniesNewsDemo(provider=provider)
    except Exception as e:
        print(f"\nError initializing demo: {e}")
        return

    # Interactive mode
    print("\n" + "="*80)
    print("Enter questions (or 'quit' to exit)")
    print("\nExample questions:")
    print("\n📊 CSV Only (Fast):")
    print("  - List all AI companies")
    print("  - Which companies are in San Francisco?")
    print("\n🌐 CSV + Web Search (Medium):")
    print("  - Find recent news about OpenAI")
    print("  - Search for Tesla articles")
    print("\n🤖 CSV + Web + LLM (Slow, use LIMIT!):")
    print("  - What funding have AI companies received? (LIMIT 3)")
    print("  - Find product launches from tech companies (LIMIT 3)")
    print("\n⚠️  Note: Web + LLM queries are slow. Start with CSV-only questions!")
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
