# Phase 3: Enhanced Query Generator

**Duration:** 2 weeks
**Dependencies:** Phase 1 (GGF Catalog), Phase 2 (Compiler)
**Owner:** Frontend + LLM Integration Developer

---

## Context

Existing `demo/query_generator.py`: LLM directly generates SPARQL (one-shot).
Target: Two-stage UI - (1) LLM generates logical plan, (2) Show plan + cost + explanation, (3) User confirms → compile → execute.

**Benefit:** User sees reasoning before execution, can abort expensive queries, learns SPARQLLM patterns.

---

## Overview

Extend existing demo with:
1. **Plan Generation Mode:** LLM outputs JSON plan (not SPARQL)
2. **Plan Visualization:** Display steps, cost estimate, natural language explanation
3. **Interactive Confirmation:** User approves/rejects before compilation
4. **Execution Pipeline:** Compile plan → SPARQL → execute → show provenance
5. **Comparison Mode:** Run same question via (a) direct SPARQL, (b) compiler, (c) manual baseline

**Key Files:**
- `demo/query_generator.py` (existing, 440 lines) → extend with two-stage flow
- `demo/prompts/plan_system_prompt.txt` (new) → instruct LLM to output JSON
- `demo/ui/plan_viewer.py` (new) → rich console visualization

---

## Key Insights (from Research)

1. **User confirmation critical** (researcher-01 L62-70): Iterative refinement requires human-in-loop for complex queries.
2. **Cost transparency builds trust**: Show token/latency estimates before execution (common LLM UX pattern).
3. **Comparison validates compiler**: Side-by-side (direct vs compiled) proves optimization value.

---

## Requirements

### Functional
- [ ] LLM generates valid JSON plans (90%+ success rate)
- [ ] Plan viewer displays: steps, dependencies, cost, explanation
- [ ] User can approve/edit/reject plan before execution
- [ ] Compilation errors shown with retry option (max 3 attempts)
- [ ] Results include provenance (which GGFs called, duration, cost)
- [ ] Comparison mode: run same query 3 ways (direct/compiled/manual)

### Non-Functional
- [ ] UI responsive (plan display <1s after LLM response)
- [ ] Keyboard navigation (approve=y, reject=n, edit=e)
- [ ] Error messages actionable (suggest fixes)
- [ ] Works in terminal (no GUI dependencies)

---

## Architecture

### 1. Enhanced System Prompt (Plan Mode)

**File:** `demo/prompts/plan_system_prompt.txt`

```text
You are a SPARQLLM logical planner. Generate JSON execution plans from user questions.

## Task
Convert natural language question → logical plan (JSON) with steps, dependencies, GGF calls.

## Logical Plan Schema
{
  "version": "1.0",
  "steps": [
    {
      "id": "stepN",
      "operation": "read_filesystem|llm_extract|web_search|vector_search|sql_query|join|filter|aggregate",
      "ggf": {
        "name": "GGF_NAME",
        "args": { ... }
      },
      "depends_on": ["step1", "step2"],
      "bindings": { "varName": "?sparqlVar" }
    }
  ],
  "output": {
    "variables": ["var1", "var2"],
    "distinct": true,
    "order_by": [{"variable": "var1", "order": "ASC"}]
  }
}

## Available GGFs (from catalog)
{catalog_summary}

## Rules
1. Each step must reference a GGF from the catalog
2. Use "depends_on" to chain steps (step2 depends on step1 output)
3. Bindings map step outputs to SPARQL variables
4. Operations match GGF data source: filesystem → read_filesystem, etc.
5. Keep plans simple (YAGNI): 3-5 steps for most queries
6. Return ONLY valid JSON, no markdown blocks or explanations

## Examples
[Few-shot examples here - 3 examples covering filesystem, LLM, web, hybrid]
```

### 2. Plan Viewer UI (Terminal)

**File:** `demo/ui/plan_viewer.py`

```python
"""
Rich console UI for visualizing logical plans.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax
import json

console = Console()

def display_plan(plan: dict, cost: dict, explanation: str):
    """
    Show logical plan with dependencies, cost, explanation.
    """
    # Header
    console.print(Panel.fit(
        "[bold cyan]Logical Plan Generated[/bold cyan]",
        border_style="cyan"
    ))

    # Explanation
    console.print("\n[bold]Query Explanation:[/bold]")
    console.print(f"  {explanation}\n")

    # Cost estimate
    cost_table = Table(show_header=False, box=None)
    cost_table.add_row("[yellow]Estimated Latency[/yellow]", f"{cost['latency_ms']/1000:.1f}s")
    cost_table.add_row("[yellow]Token Usage[/yellow]", f"{cost['tokens']} tokens")
    cost_table.add_row("[yellow]API Calls[/yellow]", str(cost['api_calls']))
    cost_table.add_row("[yellow]Cost (USD)[/yellow]", f"${cost['cost_usd']:.4f}")
    console.print(Panel(cost_table, title="Cost Estimate", border_style="yellow"))

    # Execution steps (dependency tree)
    tree = Tree("[bold]Execution Steps[/bold]")
    step_nodes = {}
    for step in plan['steps']:
        step_id = step['id']
        ggf = step['ggf']['name']
        op = step['operation'].replace('_', ' ').title()
        label = f"[green]{step_id}[/green]: {op} ([cyan]{ggf}[/cyan])"

        # Find parent nodes
        deps = step.get('depends_on', [])
        if not deps:
            node = tree.add(label)
        else:
            parent = step_nodes[deps[0]]  # Attach to first dependency
            node = parent.add(label)

        step_nodes[step_id] = node

    console.print(tree)

    # Raw JSON (collapsible)
    console.print("\n[dim]Raw Plan JSON:[/dim]")
    syntax = Syntax(json.dumps(plan, indent=2), "json", theme="monokai", line_numbers=True)
    console.print(syntax)

def prompt_user_confirmation() -> str:
    """
    Ask user to approve/reject/edit plan.

    Returns:
        'approve', 'reject', or 'edit'
    """
    console.print("\n[bold cyan]Actions:[/bold cyan]")
    console.print("  [y] Approve and execute")
    console.print("  [n] Reject and regenerate")
    console.print("  [e] Edit plan manually")
    console.print("  [q] Quit")

    choice = console.input("[bold]Your choice:[/bold] ").lower().strip()
    return {
        'y': 'approve',
        'n': 'reject',
        'e': 'edit',
        'q': 'quit'
    }.get(choice, 'approve')
```

### 3. Extended Query Generator

**File:** `demo/query_generator.py` (modifications)

```python
# Existing imports + new ones
from SPARQLLM.compiler.physical_compiler import PhysicalCompiler
from SPARQLLM.compiler.cost_estimator import CostEstimator
from SPARQLLM.compiler.explainer import Explainer
from SPARQLLM.catalog.query import load_catalog
from demo.ui.plan_viewer import display_plan, prompt_user_confirmation
import json

class QueryGenerator:
    def __init__(self, mode='plan'):
        """
        Args:
            mode: 'plan' (two-stage) or 'direct' (original SPARQL generation)
        """
        self.mode = mode
        # ... existing init ...

        if mode == 'plan':
            # Load system prompt for plan generation
            with open(PROMPTS_DIR / "plan_system_prompt.txt") as f:
                self.system_prompt = f.read()

            # Load catalog summary (inject into prompt)
            catalog = load_catalog()
            self.catalog_summary = self._summarize_catalog(catalog)
            self.system_prompt = self.system_prompt.replace(
                '{catalog_summary}',
                self.catalog_summary
            )

            # Initialize compiler components
            self.compiler = PhysicalCompiler(catalog)
            self.cost_estimator = CostEstimator(catalog)
            self.explainer = Explainer()

    def _summarize_catalog(self, catalog) -> str:
        """Generate compact catalog summary for LLM context."""
        # Query catalog for all GGFs, group by data source
        # Return formatted text (max 500 tokens)
        pass

    def generate_plan(self, user_question: str, context: dict) -> dict:
        """Generate logical plan (JSON) via LLM."""
        prompt = self.build_plan_prompt(user_question, context)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=2000
        )

        plan_json = response.choices[0].message.content.strip()
        # Clean markdown artifacts
        plan_json = re.sub(r'^```json\s*\n', '', plan_json)
        plan_json = re.sub(r'\n```$', '', plan_json)

        return json.loads(plan_json)

    def two_stage_flow(self, user_question: str, context: dict):
        """
        Execute two-stage compilation with user confirmation.
        """
        max_retries = 3
        for attempt in range(max_retries):
            # Stage 1: Generate logical plan
            print(f"{Fore.CYAN}Generating logical plan (attempt {attempt+1}/{max_retries})...{Style.RESET_ALL}")
            try:
                plan = self.generate_plan(user_question, context)
            except Exception as e:
                print(f"{Fore.RED}Plan generation failed: {e}{Style.RESET_ALL}")
                if attempt < max_retries - 1:
                    continue
                else:
                    raise

            # Estimate cost
            cost = self.cost_estimator.estimate(plan)

            # Generate explanation
            explanation = self.explainer.explain(plan, cost)

            # Display plan
            display_plan(plan, cost, explanation)

            # User confirmation
            choice = prompt_user_confirmation()

            if choice == 'reject':
                print(f"{Fore.YELLOW}Regenerating plan...{Style.RESET_ALL}")
                continue
            elif choice == 'edit':
                # Open plan JSON in editor (nano/vim)
                plan = self._edit_plan_interactive(plan)
            elif choice == 'quit':
                print(f"{Fore.YELLOW}Aborted by user{Style.RESET_ALL}")
                return None, None

            # Stage 2: Compile to SPARQL
            try:
                sparql = self.compiler.compile(plan)
                return plan, sparql
            except Exception as e:
                print(f"{Fore.RED}Compilation failed: {e}{Style.RESET_ALL}")
                if attempt < max_retries - 1:
                    print(f"{Fore.YELLOW}Retrying...{Style.RESET_ALL}")
                    continue
                else:
                    raise

        raise RuntimeError(f"Failed to generate valid plan after {max_retries} attempts")

    def _edit_plan_interactive(self, plan: dict) -> dict:
        """Open plan JSON in editor, return modified version."""
        import tempfile, subprocess
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(plan, f, indent=2)
            temp_path = f.name

        # Open in editor
        editor = os.environ.get('EDITOR', 'nano')
        subprocess.run([editor, temp_path])

        # Read modified plan
        with open(temp_path) as f:
            modified_plan = json.load(f)

        os.unlink(temp_path)
        return modified_plan


def main():
    """Enhanced main flow with mode selection."""
    # ... existing setup ...

    # Ask user for mode
    print(f"\n{Fore.CYAN}Select mode:{Style.RESET_ALL}")
    print("  1. Two-stage (plan + compile)")
    print("  2. Direct SPARQL generation")
    print("  3. Comparison mode (run both)")

    mode_choice = input(f"{Fore.CYAN}Mode: {Style.RESET_ALL}").strip()

    if mode_choice == '1':
        generator = QueryGenerator(mode='plan')
        plan, sparql = generator.two_stage_flow(question, context)
        if sparql:
            # Execute + display results
            success, stdout, stderr = execute_query(sparql, debug=False)
            # ... existing result display ...

    elif mode_choice == '2':
        # Existing direct generation flow
        generator = QueryGenerator(mode='direct')
        # ... existing code ...

    elif mode_choice == '3':
        # Comparison mode
        run_comparison(question, context)
```

### 4. Comparison Mode

**File:** `demo/comparison.py`

```python
"""
Compare three execution paths for same query.
"""

import time
from query_generator import QueryGenerator, execute_query

def run_comparison(question: str, context: dict):
    """
    Execute query via:
    1. Direct SPARQL generation (existing)
    2. Two-stage compiler (new)
    3. Manual baseline (pre-written query)
    """
    results = {}

    # Path 1: Direct SPARQL
    print("\n[1/3] Direct SPARQL Generation...")
    gen_direct = QueryGenerator(mode='direct')
    start = time.time()
    sparql_direct = gen_direct.generate_query(question, context)
    success1, stdout1, stderr1 = execute_query(sparql_direct)
    results['direct'] = {
        'time': time.time() - start,
        'success': success1,
        'output': stdout1,
        'query': sparql_direct
    }

    # Path 2: Two-stage compiler
    print("\n[2/3] Two-Stage Compiler...")
    gen_plan = QueryGenerator(mode='plan')
    start = time.time()
    plan, sparql_compiled = gen_plan.two_stage_flow(question, context)
    success2, stdout2, stderr2 = execute_query(sparql_compiled)
    results['compiled'] = {
        'time': time.time() - start,
        'success': success2,
        'output': stdout2,
        'query': sparql_compiled,
        'plan': plan
    }

    # Path 3: Manual baseline (if available)
    # Load from pre-written queries for test suite
    manual_query = load_manual_baseline(question)
    if manual_query:
        print("\n[3/3] Manual Baseline...")
        start = time.time()
        success3, stdout3, stderr3 = execute_query(manual_query)
        results['manual'] = {
            'time': time.time() - start,
            'success': success3,
            'output': stdout3,
            'query': manual_query
        }

    # Display comparison table
    display_comparison_results(results)
```

---

## Implementation Steps

### Week 1: Plan Generation + UI

1. **Day 1-2:** Create plan system prompt
   - Write prompt template with catalog injection
   - Add 3 few-shot examples (simple/medium/complex)
   - Test: LLM generates valid JSON for 5 example questions

2. **Day 3-4:** Build plan viewer UI
   - Implement `display_plan` (rich console output)
   - Add dependency tree visualization
   - Test: display 5 example plans (readability check)

3. **Day 5:** Integrate with query generator
   - Extend `QueryGenerator.__init__` for plan mode
   - Implement `generate_plan` method
   - Test: end-to-end plan generation

### Week 2: Confirmation + Comparison

4. **Day 6-7:** User confirmation flow
   - Implement `prompt_user_confirmation` (approve/reject/edit)
   - Add interactive plan editor (nano/vim integration)
   - Test: edit plan, recompile, execute

5. **Day 8-9:** Two-stage flow integration
   - Implement `two_stage_flow` with retry logic
   - Connect plan → compile → execute pipeline
   - Test: 10 example queries end-to-end

6. **Day 10:** Comparison mode
   - Build `comparison.py` (run 3 paths)
   - Create comparison results table (time, success, output diff)
   - Test: 5 queries (verify correctness, measure speedup)

---

## Todo List

- [ ] Write plan system prompt with catalog summary
- [ ] Add 3 few-shot examples (filesystem, LLM, hybrid)
- [ ] Implement catalog summarizer (inject into prompt)
- [ ] Build plan viewer UI (rich console)
- [ ] Add dependency tree visualization
- [ ] Implement `generate_plan` method
- [ ] Create user confirmation prompt (approve/reject/edit)
- [ ] Add interactive plan editor (nano/vim)
- [ ] Implement `two_stage_flow` with retry logic
- [ ] Build comparison mode (direct vs compiled vs manual)
- [ ] Test: 10 example queries end-to-end
- [ ] Document UI controls + keyboard shortcuts

---

## Success Criteria

1. LLM generates valid JSON plans (90%+ success, 10/10 test questions)
2. Plan viewer displays within 1s of LLM response
3. User confirmation flow intuitive (80%+ first-time users succeed)
4. Comparison mode: compiled path ≤1.5x direct path latency
5. Zero crashes on invalid plans (graceful error messages)

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM outputs invalid JSON | High | Strict prompt engineering; retry with error feedback |
| UI sluggish (large plans) | Medium | Paginate step display; collapse raw JSON by default |
| User confused by plan editor | Medium | Add inline help text; show example edits |
| Comparison mode biased (cherry-picked examples) | Low | Use Phase 4 test suite (20 diverse queries) |

---

## Security Considerations

- **Plan editor**: Validate JSON after edit (prevent code injection)
- **Cost limits**: Warn if cost > $1 before execution
- **Timeout**: Abort plan generation if LLM takes >30s

---

## Unresolved Questions

1. Should plan editor support graphical DAG view (requires GUI) or terminal only?
2. How to handle very long explanations (>200 words) - truncate or paginate?
3. Comparison mode: include cost comparison or just latency?
