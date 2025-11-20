# Phase 2: Two-Stage Compiler Architecture

**Duration:** 3 weeks
**Dependencies:** Phase 1 (GGF Catalog)
**Owner:** Backend + LLM Integration Developer

---

## Context

Current: LLM directly generates SPARQL (one-shot, brittle, no optimization).
Target: Two-stage compilation - (1) LLM generates logical plan (JSON), (2) Template expander compiles to SPARQL.

**Benefit:** Decouples reasoning (LLM) from execution (query optimizer), enables cost estimation + user confirmation before execution.

---

## Overview

Build compiler pipeline:
1. **Stage 1 (Logical Planner):** LLM produces JSON plan with steps, dependencies, filters, join conditions
2. **Stage 2 (Physical Compiler):** Python template expander translates plan → SPARQL query with BIND/GRAPH patterns
3. **Cost Estimator:** Predict latency + token budget from plan + catalog metadata
4. **Explainer:** Convert plan to natural language for user confirmation

**Analogy:** SQL optimizer generates logical plan → query planner chooses physical operators.

---

## Key Insights (from Research)

1. **Logical/Physical separation works** (researcher-01 L17-22): CAESURA/GALOIS models decouple intent from execution. Enables error recovery, incremental feedback.
2. **Declarative > Imperative** (researcher-01 L25-32): SPARQL patterns allow optimizer reordering (vs locked sequence in agent traces).
3. **Cost models need latency-awareness** (researcher-01 L36-47): LLM call (1-10s) vs file read (ms) → traditional cardinality models fail.
4. **Error recovery loops** (researcher-01 L62-70): LLM refines plan on syntax/execution errors. Max 3 iterations.

---

## Requirements

### Functional
- [ ] Logical plan schema (JSON): steps, deps, filters, joins, GGF calls
- [ ] Compiler generates valid SPARQL from 90%+ of plans
- [ ] Cost estimator predicts latency within 30% MAE (mean absolute error)
- [ ] Explainer produces 2-4 sentence natural language summary
- [ ] Error recovery: re-plan on validation/execution failures (max 3 retries)

### Non-Functional
- [ ] Compilation latency <500ms (plan → SPARQL)
- [ ] Support 20+ concurrent compilations (multi-user demo)
- [ ] Backward compatible: existing SPARQL queries still work

---

## Architecture

### 1. Logical Plan Schema (JSON)

**File:** `SPARQLLM/compiler/schema/logical_plan.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SPARQLLM Logical Plan",
  "type": "object",
  "required": ["version", "steps", "output"],
  "properties": {
    "version": {
      "type": "string",
      "const": "1.0"
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "operation", "ggf"],
        "properties": {
          "id": { "type": "string", "pattern": "^step[0-9]+$" },
          "operation": {
            "type": "string",
            "enum": ["read_filesystem", "llm_extract", "web_search", "vector_search", "sql_query", "join", "filter", "aggregate"]
          },
          "ggf": {
            "type": "object",
            "required": ["name", "args"],
            "properties": {
              "name": { "type": "string" },
              "args": { "type": "object" }
            }
          },
          "depends_on": {
            "type": "array",
            "items": { "type": "string" }
          },
          "bindings": {
            "type": "object",
            "description": "Variable bindings produced by this step"
          },
          "filters": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    },
    "output": {
      "type": "object",
      "required": ["variables"],
      "properties": {
        "variables": {
          "type": "array",
          "items": { "type": "string" }
        },
        "distinct": { "type": "boolean", "default": false },
        "limit": { "type": "integer" },
        "order_by": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "variable": { "type": "string" },
              "order": { "type": "string", "enum": ["ASC", "DESC"] }
            }
          }
        }
      }
    }
  }
}
```

**Example Logical Plan:**

```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-READDIR",
        "args": { "path": "./data", "filter": "*.txt" }
      },
      "bindings": { "fileUri": "?fileUri" }
    },
    {
      "id": "step2",
      "operation": "read_filesystem",
      "ggf": {
        "name": "SLM-READFILE",
        "args": { "file": "?fileUri", "maxChars": -1 }
      },
      "depends_on": ["step1"],
      "bindings": { "content": "?content" }
    },
    {
      "id": "step3",
      "operation": "llm_extract",
      "ggf": {
        "name": "LLM",
        "args": {
          "prompt": "Extract JSON-LD Event from: {?content}"
        }
      },
      "depends_on": ["step2"],
      "bindings": { "event": "?event", "eventName": "?eventName", "eventDate": "?eventDate" }
    }
  ],
  "output": {
    "variables": ["eventName", "eventDate"],
    "distinct": true,
    "order_by": [{"variable": "eventDate", "order": "ASC"}]
  }
}
```

### 2. Physical Compiler (Plan → SPARQL)

**File:** `SPARQLLM/compiler/physical_compiler.py`

```python
"""
Compile logical plan (JSON) to SPARQL query with GGF calls.
"""

import json
from typing import Dict, List
from jinja2 import Template

class PhysicalCompiler:
    def __init__(self, catalog):
        """
        Args:
            catalog: GGF catalog (from Phase 1) for signature validation
        """
        self.catalog = catalog

    def compile(self, logical_plan: dict) -> str:
        """
        Translate logical plan to SPARQL.

        Returns:
            str: Valid SPARQL query with PREFIX, BIND, GRAPH clauses
        """
        self._validate_plan(logical_plan)
        steps = logical_plan['steps']
        output = logical_plan['output']

        # Build dependency graph
        dep_graph = self._build_dependency_graph(steps)

        # Generate SPARQL clauses
        prefixes = self._generate_prefixes()
        binds = []
        graphs = []

        for step in self._topological_sort(dep_graph):
            bind_clause, graph_clause = self._compile_step(step)
            binds.append(bind_clause)
            if graph_clause:
                graphs.append(graph_clause)

        # Build SELECT clause
        select_vars = ' '.join(f'?{v}' for v in output['variables'])
        distinct = 'DISTINCT ' if output.get('distinct', False) else ''
        order_clause = self._build_order_clause(output.get('order_by', []))
        limit_clause = f"LIMIT {output['limit']}" if output.get('limit') else ''

        # Assemble query
        query = f"""{prefixes}

SELECT {distinct}{select_vars} WHERE {{
{chr(10).join('    ' + b for b in binds)}

{chr(10).join('    ' + g for g in graphs)}
}}
{order_clause}
{limit_clause}
"""
        return query.strip()

    def _validate_plan(self, plan: dict):
        """Validate against JSON schema + catalog."""
        # Check version
        if plan.get('version') != '1.0':
            raise ValueError(f"Unsupported plan version: {plan.get('version')}")

        # Validate each step's GGF exists in catalog
        for step in plan['steps']:
            ggf_name = step['ggf']['name']
            if not self._ggf_exists(ggf_name):
                raise ValueError(f"Unknown GGF: {ggf_name}")

    def _ggf_exists(self, name: str) -> bool:
        """Check if GGF in catalog."""
        # Query catalog from Phase 1
        pass

    def _build_dependency_graph(self, steps: List[dict]) -> dict:
        """Build adjacency list for topological sort."""
        graph = {}
        for step in steps:
            graph[step['id']] = step.get('depends_on', [])
        return graph

    def _topological_sort(self, graph: dict) -> List[dict]:
        """Return steps in execution order."""
        # Kahn's algorithm
        pass

    def _compile_step(self, step: dict) -> tuple[str, str]:
        """
        Generate BIND + GRAPH clauses for single step.

        Returns:
            (bind_clause, graph_clause)
        """
        ggf = step['ggf']
        op = step['operation']

        # Example: filesystem read
        if op == 'read_filesystem':
            if ggf['name'] == 'SLM-READDIR':
                path = ggf['args']['path']
                var = step['bindings'].get('fileUri', 'fileUri')
                bind = f'BIND(URI(ggf:SLM-FILE("{path}")) AS ?dir)'
                bind2 = f'BIND(ggf:SLM-READDIR(?dir, ?dir) AS ?dirGraph)'
                graph = f'''GRAPH ?dirGraph {{
        ?dir ex:has_path ?{var} .
        FILTER(STRENDS(STR(?{var}), ".txt"))
    }}'''
                return f'{bind}\n    {bind2}', graph

        # Example: LLM extraction
        if op == 'llm_extract':
            prompt_template = ggf['args']['prompt']
            # Replace {?var} with SPARQL variables
            prompt_sparql = prompt_template.replace('{?content}', '?content')
            bind = f'BIND(ggf:LLM("{prompt_sparql}") AS ?llmGraph)'
            bindings = step['bindings']
            graph_patterns = []
            for var_name, sparql_var in bindings.items():
                if var_name == 'eventName':
                    graph_patterns.append(f'?event schema:name {sparql_var}')
                elif var_name == 'eventDate':
                    graph_patterns.append(f'?event schema:startDate {sparql_var}')
            graph = f'''GRAPH ?llmGraph {{
        ?event a schema:Event .
        {' . '.join(graph_patterns)}
    }}'''
            return bind, graph

        # More operation types...
        pass

    def _generate_prefixes(self) -> str:
        """Standard SPARQL prefixes."""
        return """PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
PREFIX schema: <https://schema.org/>"""

    def _build_order_clause(self, order_specs: List[dict]) -> str:
        """Generate ORDER BY clause."""
        if not order_specs:
            return ''
        order_items = []
        for spec in order_specs:
            var = spec['variable']
            direction = spec.get('order', 'ASC')
            order_items.append(f'{direction}(?{var})')
        return f"ORDER BY {' '.join(order_items)}"
```

### 3. Cost Estimator

**File:** `SPARQLLM/compiler/cost_estimator.py`

```python
"""
Estimate query cost from logical plan + catalog metadata.
"""

from typing import Dict

class CostEstimator:
    def __init__(self, catalog):
        self.catalog = catalog

    def estimate(self, logical_plan: dict) -> Dict[str, float]:
        """
        Predict query cost.

        Returns:
            {
                'latency_ms': estimated P50 latency,
                'tokens': total token consumption,
                'api_calls': number of external API calls
            }
        """
        total_latency = 0
        total_tokens = 0
        api_calls = 0

        for step in logical_plan['steps']:
            ggf_name = step['ggf']['name']
            metadata = self._get_ggf_metadata(ggf_name)

            # Latency: sum of serial steps, max of parallel branches
            # TODO: detect parallel opportunities via dependency graph
            latency = metadata.get('latency_ms', 100)  # default 100ms
            total_latency += latency

            # Tokens: sum of all LLM calls
            if metadata.get('data_sources') and 'llm' in metadata['data_sources']:
                tokens = metadata.get('tokens', 500)
                total_tokens += tokens
                api_calls += 1

            # Other API calls (web search, vector DB)
            if metadata.get('data_sources') and metadata['data_sources'] != ['filesystem']:
                api_calls += 1

        return {
            'latency_ms': total_latency,
            'tokens': total_tokens,
            'api_calls': api_calls,
            'cost_usd': self._estimate_cost_usd(total_tokens)
        }

    def _get_ggf_metadata(self, name: str) -> dict:
        """Fetch metadata from catalog (Phase 1)."""
        # Query catalog: SELECT ?latency ?tokens WHERE { ggf:{name} ... }
        pass

    def _estimate_cost_usd(self, tokens: int) -> float:
        """Estimate USD cost for LLM tokens (Groq pricing)."""
        # Groq: ~$0.10 per 1M tokens (llama-3.3-70b)
        return (tokens / 1_000_000) * 0.10
```

### 4. Natural Language Explainer

**File:** `SPARQLLM/compiler/explainer.py`

```python
"""
Convert logical plan to natural language explanation.
"""

class Explainer:
    def explain(self, logical_plan: dict, cost: dict) -> str:
        """
        Generate 2-4 sentence summary.

        Example output:
        "This query will: (1) Read 5 text files from ./data, (2) Extract event
        information using LLM (Groq), (3) Return event names and dates sorted by date.
        Estimated cost: 2500 tokens (~$0.0003), 3 seconds."
        """
        steps = logical_plan['steps']
        output = logical_plan['output']

        # Summarize operations
        ops = [self._describe_step(s) for s in steps]
        steps_text = ', '.join(f'({i+1}) {op}' for i, op in enumerate(ops))

        # Output description
        out_vars = ', '.join(output['variables'])

        # Cost summary
        cost_text = f"{cost['tokens']} tokens (~${cost['cost_usd']:.4f}), {cost['latency_ms']/1000:.1f} seconds"

        return f"""This query will: {steps_text}. Returns: {out_vars}. Estimated cost: {cost_text}."""

    def _describe_step(self, step: dict) -> str:
        """Convert step to natural language."""
        op = step['operation']
        ggf = step['ggf']

        if op == 'read_filesystem':
            if ggf['name'] == 'SLM-READDIR':
                return f"list files in {ggf['args']['path']}"
            if ggf['name'] == 'SLM-READFILE':
                return "read file contents"
        if op == 'llm_extract':
            return "extract structured data with LLM"
        if op == 'web_search':
            return f"search web for '{ggf['args'].get('query', '...')}'"
        if op == 'vector_search':
            return "find similar documents (vector search)"

        return op.replace('_', ' ')
```

### 5. Error Recovery Loop

**File:** `SPARQLLM/compiler/error_recovery.py`

```python
"""
Iterative refinement on compilation/execution errors.
"""

class ErrorRecoveryLoop:
    def __init__(self, llm_client, compiler, max_retries=3):
        self.llm = llm_client
        self.compiler = compiler
        self.max_retries = max_retries

    def compile_with_retry(self, user_question: str, context: dict) -> tuple[dict, str]:
        """
        Generate plan → compile → validate. Retry on errors.

        Returns:
            (logical_plan, sparql_query)
        """
        errors = []

        for attempt in range(self.max_retries):
            # Generate logical plan via LLM
            plan = self._generate_plan(user_question, context, errors)

            # Validate plan
            try:
                self.compiler._validate_plan(plan)
            except ValueError as e:
                errors.append(f"Validation error: {e}")
                continue

            # Compile to SPARQL
            try:
                sparql = self.compiler.compile(plan)
                return plan, sparql
            except Exception as e:
                errors.append(f"Compilation error: {e}")
                continue

        raise RuntimeError(f"Failed to generate valid plan after {self.max_retries} attempts")

    def _generate_plan(self, question: str, context: dict, errors: List[str]) -> dict:
        """Call LLM to generate logical plan JSON."""
        # Build prompt with catalog, examples, error feedback
        # Return parsed JSON plan
        pass
```

---

## Implementation Steps

### Week 1: Schema + Compiler Core

1. **Day 1-2:** Define logical plan schema (JSON)
   - Create JSON Schema with validation rules
   - Document 8 operation types (read_filesystem, llm_extract, etc.)
   - Write 5 example plans (simple → complex)

2. **Day 3-5:** Implement physical compiler
   - Build dependency graph + topological sort
   - Implement `_compile_step` for 4 core operations
   - Test: plan → SPARQL roundtrip for 10 examples

### Week 2: Cost Estimation + Explanation

3. **Day 6-7:** Build cost estimator
   - Query catalog for GGF latency/token metadata
   - Implement serial/parallel latency aggregation
   - Test: estimate cost for 10 example plans (compare actual runs in Phase 4)

4. **Day 8-9:** Natural language explainer
   - Template-based descriptions for each operation type
   - Test: explain 10 example plans (human readability check)

5. **Day 10:** Integration testing
   - End-to-end: plan → compile → estimate → explain
   - Validate against existing demo queries

### Week 3: Error Recovery + Optimization

6. **Day 11-13:** Error recovery loop
   - Implement retry logic with error feedback
   - Test: inject invalid GGF names, missing deps
   - Verify: recovers in ≤3 retries for 80%+ of errors

7. **Day 14-15:** Optimization + Edge Cases
   - Detect parallel execution opportunities (independent steps)
   - Handle OPTIONAL, UNION, FILTER pushdown
   - Test: complex queries (5+ steps, 3+ dependencies)

---

## Todo List

- [ ] Define logical plan JSON schema (8 operation types)
- [ ] Write 5 example plans (annotated)
- [ ] Implement dependency graph builder + topological sort
- [ ] Code `_compile_step` for 4 core operations (filesystem, LLM, web, vector)
- [ ] Build cost estimator (query catalog, aggregate latency/tokens)
- [ ] Implement natural language explainer
- [ ] Create error recovery loop (max 3 retries)
- [ ] Test: plan → SPARQL compilation (10 examples)
- [ ] Test: cost estimation accuracy (compare to Phase 4 runs)
- [ ] Document compiler API + extension points

---

## Success Criteria

1. Compiler generates valid SPARQL from 90%+ of plans (10/10 test examples)
2. Cost estimation MAE <30% (mean absolute error vs actual execution)
3. Explainer output human-readable (80%+ user comprehension in Phase 4 survey)
4. Error recovery: 80%+ of invalid plans fixed in ≤3 retries
5. Compilation latency <500ms (plan → SPARQL)

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Template expansion brittle (edge cases) | High | Extensive unit tests; fallback to manual query |
| Cost model inaccurate (LLM variability) | Medium | Use P50 not mean; user-adjustable weights |
| Dependency cycles (invalid plans) | Medium | Cycle detection in topological sort; LLM feedback |
| Backward compatibility break | Low | Feature flag; parallel old/new paths |

---

## Security Considerations

- **Plan validation**: Reject plans with arbitrary code execution attempts
- **GGF whitelist**: Only catalog-registered functions allowed
- **SPARQL injection**: Sanitize user inputs in plan args
- **Token limits**: Enforce max tokens per query (prevent cost bombs)

---

## Unresolved Questions

1. Should compiler optimize plans (e.g., filter pushdown) or trust LLM output?
2. How to handle dynamic GGFs not in catalog (user-defined functions)?
3. Parallel execution: detect automatically or require explicit plan annotation?
4. Error recovery: LLM self-corrects or escalate to user?
