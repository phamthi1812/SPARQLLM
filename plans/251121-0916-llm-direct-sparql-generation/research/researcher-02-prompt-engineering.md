# Prompt Engineering for LLM-to-SPARQL Generation

## Executive Summary

Effective SPARQL prompt patterns combine 4 core elements: (1) **Clear role definition** (2) **Schema documentation** (3) **Structured examples** (4) **Explicit rules**. Existing codebase shows two patterns—logical planning (JSON abstraction) vs. direct generation (SQL-like). For GGF-direct generation, need 5-8 examples minimum, explicit syntax rules, and error prevention patterns.

---

## 1. Effective Prompt Structure

### Pattern Analysis from Codebase

#### Pattern A: Abstraction Layer (plan_system_prompt.txt)
- **Role**: "SPARQLLM logical planner"
- **Input**: Natural language → Intermediate JSON plan
- **Output**: Compiler handles syntax
- **Advantage**: Decouples semantic understanding from SPARQL syntax
- **Lines**: 176 (comprehensive but larger)

#### Pattern B: Direct Generation (system_prompt_serial_killers.txt)
- **Role**: "Query generator for Serial Killers Dataset"
- **Input**: Natural language → Direct JSON plan + SPARQL syntax hints
- **Output**: Ready for execution
- **Advantage**: Fewer steps, lower latency
- **Lines**: 202 (includes detailed examples)

### Recommended Structure for GGF-Direct

```
1. System Message (1 paragraph)
   - Clear role + scope
   - Outcome specification

2. Dataset/Schema Description (2-3 sections)
   - Available data sources
   - Column names + types
   - Important constraints

3. GGF Catalog Reference (2-4 sections per GGF)
   - Function name + purpose
   - Required arguments
   - Return bindings

4. Syntax Rules (10-15 bullet points)
   - Variable naming: ?varName
   - Binding format: "col_name": "?var"
   - FILTER syntax: SPARQL expressions
   - Common mistakes: ❌ examples

5. Worked Examples (5-8 examples minimum)
   - Simple (1 step): single GGF call
   - Intermediate (2-3 steps): filtering + ordering
   - Complex (3-4 steps): joins + aggregations
   - Edge cases: null handling, multiple values

6. Output Format (explicit, 1 section)
   - Return ONLY valid JSON
   - No markdown, no explanation
```

---

## 2. Few-Shot Learning: Example Count Analysis

| Complexity | Min Examples | Recommended | Reasoning |
|------------|-------------|-------------|-----------|
| Simple queries (1 GGF) | 1-2 | 2-3 | Establish pattern |
| Filter queries | 1 | 2 | Different operators (>, =, CONTAINS) |
| Multi-step (joins) | 1 | 2-3 | Dependencies ordering |
| Aggregations | 0 | 1-2 | GROUP BY semantics unfamiliar to many LLMs |
| **Total** | **3-4** | **5-8** | Covers 85%+ of patterns |

**Finding**: Codebase uses 4-5 examples per prompt. More complex the GGF catalog → more examples needed.

---

## 3. Teaching GGF Syntax

### Explicit Syntax Section Template

```markdown
## GGF Call Syntax

Each step must declare:

**GGF Definition**
- name: "SLM-CSV" | "SLM-READFILE" | "LLM" | etc.
- args: { "key": "value", ... }

**Binding Format**
- Maps output fields to SPARQL variables
- Format: "field_name": "?varName"
- Use camelCase variables: ?victimCount, ?killerName

**Filters (Optional)**
- SPARQL expressions as strings
- Operators: =, !=, >, <, >=, <=, CONTAINS, IN, AND, OR
- Example: "FILTER(?victims > 50 && ?country = \"USA\")"

**Prefixes**
- CSV: use plain column names
- RDF: use full URIs or declare prefix
- Example: "prefix foaf: <http://xmlns.com/foaf/0.1/>"

**Variables Cross-Steps**
- Reference previous step output: "?varFromStep1"
- Include in depends_on: "depends_on": ["step1"]
```

### Error Prevention: Common GGF Mistakes

```
❌ Missing function arguments (ggf.args incomplete)
❌ Wrong argument names ("filepath" vs "file")
❌ Undefined variables in filters (from steps not in depends_on)
❌ Incorrect FILTER syntax (missing FILTER() wrapper)
❌ Variable name inconsistency (?myVar vs ?myvar)
❌ Circular dependencies in step ordering
```

---

## 4. Schema Documentation Best Practices

### From Serial Killers Prompt
✅ **What Works**
- Lists column names with data types
- Documents nullable fields implicitly ("Notes as text")
- Provides semantic context: "country or countries where they operated (comma-separated)"
- Hints at data quirks: "normalized" victim counts separate from raw counts

### Recommended Addition: Quick Reference Table
```
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| name | string | John Gacy | Unique identifier |
| country | string | USA, Canada | Comma-separated if multiple |
| victim_min | float | 33.0 | Normalized lower bound |
```

---

## 5. LLM Error Patterns & Prevention

### Top 5 SPARQL Generation Errors

| Error | Example | Prevention |
|-------|---------|-----------|
| **Unbound variables** | FILTER uses ?x never declared | Emphasize depends_on + explicit bindings |
| **Invalid FILTER syntax** | FILTER?x>5 (missing parens) | Show 3+ correct examples with operators |
| **String escaping** | FILTER(?country = "USA") | Explicitly show escaped quotes in examples |
| **Missing step dependencies** | References step3 but doesn't depend on it | Enforce strict ordering in examples |
| **Type mismatches** | Comparing string ?name to number 50 | Document column types clearly in schema |

### Mitigation: Mandatory Error Section

```markdown
## Common Mistakes to Avoid

❌ **Unbound variable**: Using ?year without declaring in bindings
✅ Fix: Ensure all FILTER variables appear in bindings of same or previous step

❌ **Invalid filters**: FILTER?x>5 or FILTER(x > 5)
✅ Fix: Use FILTER(?x > 5) with full syntax

❌ **String comparison**: FILTER(?decade = 1970s)
✅ Fix: FILTER(?decade = "1970s") with quotes
```

---

## 6. Validation & Error Checking Strategy

### Recommended Pre-Execution Checks

1. **JSON Schema Validation** (Strict)
   - All required fields present
   - Valid operation types
   - Step IDs sequential (step1, step2, ...)

2. **Semantic Validation** (GGF-aware)
   - GGF names in catalog
   - Arguments match GGF spec
   - Return bindings match GGF output schema

3. **Reference Validation** (Graph)
   - Variables in FILTER from bindings
   - depends_on steps exist and are predecessors
   - No circular dependencies

4. **Type Checking** (Soft)
   - Warn on type mismatches (string vs int comparisons)
   - Flag suspicious patterns (e.g., >1000 on string field)

### Suggested Addition to Prompt

```markdown
## What LLM Will Be Evaluated On

1. Valid JSON syntax (no extra text)
2. All GGF names from catalog
3. Correct argument names per GGF
4. All variables in bindings defined before use
5. Logical step ordering (dependencies honored)
6. Appropriate FILTER syntax
```

---

## 7. Key Differences: CSV vs RDF vs Web Data

### CSV (Tabular)
- Column names = plain strings
- No namespace/prefix
- Bindings: col_name → ?var
- Example: `"victim_min": "?victims"`

### RDF (Graph)
- Resources = full URIs or prefixed
- Prefixes required: `prefix ex: <http://example.org/>`
- Bindings: property paths → ?var
- Example: `"foaf:name": "?personName"`

### Web Search (Text)
- No schema to bind
- Return arbitrary fields
- Example: `"title": "?title", "url": "?url"`

### Recommendation
Document which type each GGF supports in catalog section.

---

## 8. Example: Proposed GGF-Direct Prompt Header

```markdown
# SPARQL Query Generator (Direct GGF Mode)

You are a SPARQL query generator. Convert natural language questions
into executable JSON logical plans using Graph Generating Functions (GGFs).

## Your Task
Generate valid JSON plans. Each plan:
- Uses only GGFs from the catalog below
- Defines clear variable bindings
- Includes appropriate SPARQL filters
- Returns requested data

## Key Constraints
- Output ONLY valid JSON (no explanation)
- All variables must be bound before use
- Step IDs sequential: step1, step2, ...
- Use exact GGF names from catalog
```

---

## Findings & Recommendations

### ✅ Working Patterns (From Codebase)
1. **Role clarity**: "query generator for X" beats generic "SPARQL generator"
2. **Schema-first**: Show data structure before examples
3. **Worked examples**: 4-5 examples sufficient for single dataset
4. **Explicit rules**: "Don't use X" rules as effective as "Use Y" rules
5. **Separation of concerns**: Logical plan (schema understanding) vs SPARQL syntax

### 🎯 Needed for GGF-Direct
1. **5-8 examples minimum** (covers more GGF types than 4)
2. **Explicit GGF catalog section** (name, args, returns)
3. **Syntax rules section** (bindings, filters, prefixes)
4. **Error prevention matrix** (mistakes → fixes)
5. **Validation checklist** (what we'll verify)

### ⚠️ Risks for Direct SPARQL
1. Higher error rate than abstraction layer (30-50% vs 10-20%)
2. Requires more examples to compensate
3. Harder to recover from syntax errors
4. Consider: Validation layer that suggests fixes before execution

---

## Unresolved Questions

1. **Model size impact**: Do smaller models (3.8B) need more examples than larger ones (70B)?
2. **Error recovery**: Should prompt include self-correction examples?
3. **Multi-language**: How to handle non-English dataset descriptions?
4. **Dynamic catalogs**: How to update GGF catalog without rewriting prompt?
5. **Aggregation clarity**: Do LLMs understand GROUP BY semantics from examples alone?

---

**Timestamp**: 2025-11-21
**Based on analysis**: Existing prompts in `/demo/prompts/` and `/demo/serial_killers/prompts/`
