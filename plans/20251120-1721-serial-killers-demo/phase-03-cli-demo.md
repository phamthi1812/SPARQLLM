# Phase 3: Interactive CLI Demo

**Duration:** 2 days
**Dependencies:** Phase 2 (queries created)
**Status:** Not Started

---

## Objectives

1. Build interactive CLI for serial killers dataset exploration
2. Extend QueryGenerator with dataset-specific context
3. Implement preset questions (quick start)
4. Add cost estimation and query explanation
5. Support both two-stage compilation and direct SPARQL execution

---

## Architecture

```
serial_killers_demo.py
    ↓
QueryGenerator (extended with dataset context)
    ↓
[User Input] → Natural Language Question
    ↓
[Stage 1: Plan Generation] → JSON Logical Plan (LLM)
    ↓
[User Confirmation] → Display plan + cost + explanation
    ↓
[Stage 2: Compilation] → SPARQL Query (PhysicalCompiler)
    ↓
[Execution] → slm-run or direct evaluation
    ↓
[Results Display] → Table/CSV/JSON output
```

---

## Components

### Component 3.1: Serial Killers Demo Script

**File:** `demo/serial_killers/serial_killers_demo.py`

**Responsibilities:**
1. Load dataset context (stats, column names)
2. Present welcome message and menu
3. Handle preset questions vs free-form input
4. Manage two-stage compilation flow
5. Display results in readable format

**Interface:**
```python
#!/usr/bin/env python3
"""
Serial Killers Dataset - Interactive CLI Demo

Demonstrates SPARQLLM's two-stage compilation with real-world criminal dataset.
Uses local LLM (qwen2.5:3b) for zero-cost operation.

Usage:
    python demo/serial_killers/serial_killers_demo.py
"""

import json
import sys
from pathlib import Path
from typing import Optional

from demo.query_generator import QueryGenerator
from SPARQLLM.compiler import PhysicalCompiler, CostEstimator, Explainer


class SerialKillersDemo:
    """Interactive CLI for serial killers dataset exploration"""

    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.queries_dir = Path(__file__).parent / "queries"
        self.csv_path = self.data_dir / "serial_killers_clean.csv"
        self.stats_path = self.data_dir / "stats.json"

        # Load dataset context
        self.stats = self._load_stats()
        self.dataset_context = self._build_dataset_context()

        # Initialize query generator (local LLM via Ollama)
        self.generator = QueryGenerator(
            mode='plan',
            model='qwen2.5:3b',  # Local model
            api_key=None  # Use Ollama, no API key
        )

        # Initialize compiler components
        self.compiler = PhysicalCompiler()
        self.cost_estimator = CostEstimator()
        self.explainer = Explainer()

        # Preset questions
        self.preset_questions = self._load_preset_questions()

    def _load_stats(self) -> dict:
        """Load dataset statistics"""
        if self.stats_path.exists():
            with open(self.stats_path, 'r') as f:
                return json.load(f)
        else:
            return {
                "total_rows": "unknown",
                "temporal": {"earliest_year": "unknown", "latest_year": "unknown"},
                "victims": {"total": "unknown", "average": "unknown"}
            }

    def _build_dataset_context(self) -> dict:
        """Build context dict for query generation"""
        return {
            "dataset_name": "Wikipedia Serial Killers List",
            "csv_path": str(self.csv_path),
            "total_rows": self.stats.get("total_rows", "unknown"),
            "columns": ["name", "years_active", "decade", "victims", "methods", "notes", "wikipedia_url"],
            "time_range": f"{self.stats['temporal']['earliest_year']}-{self.stats['temporal']['latest_year']}",
            "total_victims": self.stats['victims']['total']
        }

    def _load_preset_questions(self) -> list:
        """Load preset questions with corresponding query files"""
        return [
            {
                "id": 1,
                "question": "Show me the top 10 serial killers by victim count",
                "plan_file": "plans/q1_top_victims.json",
                "sparql_file": "q1_top_victims.sparql",
                "description": "Basic CSV aggregation"
            },
            {
                "id": 2,
                "question": "How did killing methods change over decades?",
                "plan_file": "plans/q2_methods_by_decade.json",
                "sparql_file": "q2_methods_by_decade.sparql",
                "description": "Temporal analysis + LLM categorization"
            },
            {
                "id": 3,
                "question": "Get Wikipedia summary for Ted Bundy",
                "plan_file": "plans/q3_wikipedia_summary.json",
                "sparql_file": "q3_wikipedia_summary.sparql",
                "description": "CSV → web scraping"
            },
            {
                "id": 4,
                "question": "Extract specific methods from notes field",
                "plan_file": "plans/q4_extract_methods.json",
                "sparql_file": "q4_extract_methods.sparql",
                "description": "LLM extraction from unstructured text"
            },
            {
                "id": 5,
                "question": "Find unsolved cases with similar patterns",
                "plan_file": "plans/q5_unsolved_patterns.json",
                "sparql_file": "q5_unsolved_patterns.sparql",
                "description": "Multi-step reasoning (requires web search)",
                "requires_web": True
            },
            {
                "id": 6,
                "question": "Verify victim counts against Wikipedia",
                "plan_file": "plans/q6_verify_counts.json",
                "sparql_file": "q6_verify_counts.sparql",
                "description": "Cross-reference validation"
            }
        ]

    def display_welcome(self):
        """Display welcome message and dataset info"""
        print("\n" + "="*80)
        print("Serial Killers Dataset - Interactive CLI Demo")
        print("="*80)
        print("\nDataset: Wikipedia Serial Killers List (Kaggle)")
        print(f"Rows: {self.stats.get('total_rows', 'unknown')}")
        print(f"Time range: {self.dataset_context['time_range']}")
        print(f"Total victims: {self.stats['victims']['total']}")
        print(f"\nLLM: qwen2.5:3b (local, zero cost)")
        print("Mode: Two-stage compilation (Natural Language → JSON Plan → SPARQL)")
        print("="*80 + "\n")

    def display_menu(self):
        """Display main menu"""
        print("\nOptions:")
        print("  [1-6] - Run preset question")
        print("  [Q]   - Ask custom question (natural language)")
        print("  [L]   - List all preset questions")
        print("  [S]   - Show dataset statistics")
        print("  [H]   - Help")
        print("  [X]   - Exit")

    def list_preset_questions(self):
        """Display all preset questions"""
        print("\n" + "="*80)
        print("Preset Questions")
        print("="*80)
        for q in self.preset_questions:
            web_marker = " [WEB]" if q.get("requires_web") else ""
            print(f"\n[{q['id']}] {q['question']}{web_marker}")
            print(f"    Description: {q['description']}")
        print("\n" + "="*80)

    def show_stats(self):
        """Display dataset statistics"""
        print("\n" + "="*80)
        print("Dataset Statistics")
        print("="*80)
        print(json.dumps(self.stats, indent=2))
        print("="*80)

    def run_preset_question(self, question_id: int):
        """Execute a preset question"""
        # Find question
        question = next((q for q in self.preset_questions if q['id'] == question_id), None)
        if not question:
            print(f"\nError: Invalid question ID: {question_id}")
            return

        # Check web requirement
        if question.get('requires_web'):
            print("\nWarning: This query requires web search capability.")
            confirm = input("Continue? [y/N]: ").strip().lower()
            if confirm != 'y':
                print("Aborted.")
                return

        print(f"\n{'='*80}")
        print(f"Question: {question['question']}")
        print(f"{'='*80}\n")

        # Load preset plan
        plan_path = self.queries_dir / question['plan_file']
        if not plan_path.exists():
            print(f"Error: Plan file not found: {plan_path}")
            return

        with open(plan_path, 'r') as f:
            plan = json.load(f)

        # Display plan
        print("Logical Plan:")
        print(json.dumps(plan, indent=2))
        print()

        # Estimate cost
        cost = self.cost_estimator.estimate(plan)
        print(f"Estimated cost: {cost['latency_ms']}ms, {cost.get('api_calls', 0)} API calls")
        print()

        # Compile to SPARQL
        try:
            sparql = self.compiler.compile(plan)
            print("Compiled SPARQL:")
            print(sparql)
            print()
        except Exception as e:
            print(f"Compilation error: {e}")
            return

        # Ask to execute
        execute = input("Execute this query? [y/N]: ").strip().lower()
        if execute == 'y':
            self._execute_sparql(sparql, question['sparql_file'])

    def ask_custom_question(self):
        """Handle custom natural language question"""
        print("\n" + "="*80)
        question = input("Enter your question: ").strip()

        if not question:
            print("No question provided.")
            return

        print(f"{'='*80}\n")

        # Generate plan via LLM
        try:
            plan, sparql = self.generator.two_stage_flow(
                user_question=question,
                context=self.dataset_context,
                max_retries=3
            )

            if sparql:
                # Ask to execute
                execute = input("\nExecute this query? [y/N]: ").strip().lower()
                if execute == 'y':
                    self._execute_sparql(sparql, None)

        except Exception as e:
            print(f"\nError: {e}")

    def _execute_sparql(self, sparql: str, query_file: Optional[str]):
        """Execute SPARQL query via slm-run"""
        import subprocess
        import tempfile

        # Write query to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sparql', delete=False) as f:
            f.write(sparql)
            temp_path = f.name

        # Execute with slm-run
        print("\nExecuting query...")
        try:
            result = subprocess.run(
                ['slm-run', '--config', 'config.ini', '-f', temp_path, '--debug'],
                capture_output=True,
                text=True,
                timeout=120
            )

            print("\n" + "="*80)
            print("Results:")
            print("="*80)
            print(result.stdout)

            if result.stderr:
                print("\nDebug output:")
                print(result.stderr)

        except subprocess.TimeoutExpired:
            print("\nError: Query timeout (120s)")
        except Exception as e:
            print(f"\nExecution error: {e}")
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    def run(self):
        """Main CLI loop"""
        self.display_welcome()

        while True:
            self.display_menu()
            choice = input("\nSelect option: ").strip().upper()

            if choice in ['1', '2', '3', '4', '5', '6']:
                self.run_preset_question(int(choice))

            elif choice == 'Q':
                self.ask_custom_question()

            elif choice == 'L':
                self.list_preset_questions()

            elif choice == 'S':
                self.show_stats()

            elif choice == 'H':
                print("\nHelp: [documentation here]")

            elif choice == 'X':
                print("\nExiting. Thank you!")
                break

            else:
                print(f"\nInvalid choice: {choice}")


def main():
    """Entry point"""
    demo = SerialKillersDemo()
    demo.run()


if __name__ == "__main__":
    main()
```

---

### Component 3.2: Dataset-Specific Prompt

**File:** `demo/serial_killers/prompts/serial_killers_system_prompt.txt`

**Content:**
```
You are a SPARQLLM logical planner for the Wikipedia Serial Killers dataset.

## Dataset Context
- CSV file: ./demo/serial_killers/data/serial_killers_clean.csv
- Columns: name, years_active, decade, year_start, year_end, victims, victim_min, victim_max, methods, notes, wikipedia_url
- Rows: ~500 serial killers
- Time range: 1870-2020
- Total victims: ~3000+

## Common Query Patterns

### Aggregation (victims, counts)
- Use SLM-CSV to read the CSV
- Filter by victim_min/victim_max for numeric comparisons
- Order by victim_min DESC for top killers
- Use decade column for temporal grouping

### LLM Extraction (methods, categorization)
- Use SLM-CSV → LLM pipeline
- Extract structured info from 'methods' or 'notes' columns
- Ask LLM to categorize methods (poison, firearm, stabbing, etc.)
- Keep prompts concise for faster inference

### Web Scraping (Wikipedia)
- Use SLM-CSV → SLM-GETTEXT pipeline
- Get wikipedia_url from CSV first
- Then fetch page content with SLM-GETTEXT
- Limit to specific killers to avoid rate limits

### Multi-Step Reasoning
- Chain SLM-CSV → SEARCH → LLM
- Use CSV data as context for web searches
- Filter results with LLM verification
- Add LIMIT clauses to control execution time

## Important Rules
1. Always use CSV path: ./demo/serial_killers/data/serial_killers_clean.csv
2. Numeric victim comparisons: use victim_min or victim_max
3. Temporal queries: use decade, year_start, year_end columns
4. Web queries: check wikipedia_url is BOUND before using
5. LLM prompts: be specific, request concise outputs
6. Limit results with LIMIT clause (default 10-20)

{catalog_summary}

Now generate a logical plan for the user's question.
```

---

### Component 3.3: Enhanced QueryGenerator Integration

**Modification:** Extend `demo/query_generator.py` to support custom system prompts

**Change:**
```python
class QueryGenerator:
    def __init__(self, mode: str = 'plan', model: str = 'gpt-4',
                 api_key: Optional[str] = None,
                 custom_system_prompt: Optional[str] = None):  # NEW
        """
        Initialize query generator.

        Args:
            custom_system_prompt: Optional custom system prompt (overrides default)
        """
        # ... existing code ...

        if mode == 'plan':
            # Load system prompt
            if custom_system_prompt:
                self.system_prompt = custom_system_prompt  # NEW
            else:
                prompt_path = self.prompts_dir / "plan_system_prompt.txt"
                with open(prompt_path, 'r') as f:
                    self.system_prompt = f.read()

            # Inject catalog summary
            catalog_summary = self._generate_catalog_summary()
            self.system_prompt = self.system_prompt.replace(
                '{catalog_summary}',
                catalog_summary
            )
```

**Usage in SerialKillersDemo:**
```python
# Load custom prompt
prompt_path = Path(__file__).parent / "prompts" / "serial_killers_system_prompt.txt"
with open(prompt_path, 'r') as f:
    custom_prompt = f.read()

# Initialize generator with custom prompt
self.generator = QueryGenerator(
    mode='plan',
    model='qwen2.5:3b',
    custom_system_prompt=custom_prompt
)
```

---

### Component 3.4: Results Formatting

**Utility:** `demo/serial_killers/utils/format_results.py`

**Functions:**
```python
import pandas as pd
from typing import List, Dict

def format_table(results: List[Dict], max_width: int = 80) -> str:
    """Format query results as ASCII table"""
    if not results:
        return "No results."

    df = pd.DataFrame(results)
    return df.to_string(index=False, max_colwidth=max_width)

def format_csv(results: List[Dict]) -> str:
    """Format results as CSV"""
    if not results:
        return ""

    df = pd.DataFrame(results)
    return df.to_csv(index=False)

def format_json(results: List[Dict], indent: int = 2) -> str:
    """Format results as JSON"""
    import json
    return json.dumps(results, indent=indent)
```

---

### Component 3.5: Error Handling & User Guidance

**Features:**
1. **Dataset validation on startup:**
   - Check CSV exists
   - Validate column names
   - Warn if stats.json missing

2. **Query validation before execution:**
   - Check GGFs available
   - Warn about web search requirements
   - Estimate execution time

3. **Helpful error messages:**
   - CSV not found → show download instructions
   - Ollama not running → show setup instructions
   - Query timeout → suggest adding LIMIT

**Example:**
```python
def validate_environment(self):
    """Check environment setup"""
    issues = []

    # Check CSV
    if not self.csv_path.exists():
        issues.append("Dataset not found. Run: python demo/serial_killers/setup/download_data.py")

    # Check Ollama
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code != 200:
            issues.append("Ollama not running. Start with: ollama serve")
    except:
        issues.append("Ollama not running. Start with: ollama serve")

    # Check model
    # ... (check qwen2.5:3b available)

    if issues:
        print("\nSetup issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        print()

    return len(issues) == 0
```

---

## Implementation Tasks

### Task 3.1: Create Demo Script
- [ ] Implement `SerialKillersDemo` class
- [ ] Main menu loop
- [ ] Preset question execution
- [ ] Custom question handling
- [ ] Results display

### Task 3.2: Create Custom Prompt
- [ ] Write dataset-specific system prompt
- [ ] Include column schema
- [ ] Add query pattern examples
- [ ] Embed common pitfalls

### Task 3.3: Extend QueryGenerator
- [ ] Add `custom_system_prompt` parameter
- [ ] Test with serial killers prompt
- [ ] Validate local LLM integration (Ollama)

### Task 3.4: Build Utilities
- [ ] Results formatting functions
- [ ] Environment validation
- [ ] Error message templates

### Task 3.5: Test Interactive Flow
- [ ] Test all preset questions
- [ ] Test custom question generation
- [ ] Test error handling
- [ ] Test results display

---

## Deliverables

### Scripts
- [ ] `demo/serial_killers/serial_killers_demo.py` - Main CLI script
- [ ] `demo/serial_killers/utils/format_results.py` - Results formatting
- [ ] `demo/serial_killers/utils/validate_env.py` - Environment checks

### Prompts
- [ ] `demo/serial_killers/prompts/serial_killers_system_prompt.txt` - Custom prompt

### Documentation
- [ ] CLI usage guide in README
- [ ] Screenshot/demo session transcript
- [ ] Troubleshooting section

---

## Verification Commands

```bash
# Test CLI startup
python demo/serial_killers/serial_killers_demo.py

# Test preset question (Q1 - simple CSV)
# In demo CLI:
# > Select option: 1
# > Execute this query? [y/N]: y

# Test custom question
# In demo CLI:
# > Select option: Q
# > Enter your question: Who had the most victims?
# > Execute this query? [y/N]: y

# Test environment validation
python -c "
from demo.serial_killers.serial_killers_demo import SerialKillersDemo
demo = SerialKillersDemo()
assert demo.validate_environment()
print('Environment OK')
"
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Local LLM plan generation fails | High | Add retry logic, fallback to preset questions |
| Ollama not installed/running | High | Clear setup instructions, environment validation |
| Results too large for terminal | Medium | Add pagination, save to file option |
| Query execution timeout | Medium | Add timeout warnings, suggest LIMIT clauses |
| Custom prompt too long (token limit) | Low | Compress catalog summary, remove redundancy |

---

## Next Steps

After Phase 3 completion:
1. Document CLI usage in Phase 4 README
2. Create demo session transcript for documentation
3. Test CLI with naive users (Phase 5)
4. Collect feedback on UX improvements
