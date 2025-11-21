# LLM as Query Compiler: State-of-Art & SPARQLLM Positioning

## 1. Text-to-SPARQL Advances (2024-2025)

**Semantic Parsing Performance:**
- COT-SPARQL (2024): F1 89.36% (VQuAnDa), 70.45% (QALD-9) via chain-of-thought with entity/relation injection
- Learning to Refine (Nov 2025): Agentic RL learns refinement policy—recovers from syntax errors, adapts query structure
- Success factors: Few-shot similarity-based example selection beats random retrieval; query complexity inversely correlates with accuracy

**Model Effectiveness:**
- Mixtral 8x7B, Llama-3 70B, CodeLlama 70B, GPT-4, Claude tested; no single winner across domains
- Error patterns: Missing relations in multi-hop graphs; over/under-specified FILTER clauses; incomplete UNION handling
- In-context learning + RAG validation from endpoint schema significantly improves syntactic correctness

## 2. Compilation Architecture: Two Stages Matter

**Logical Plan → Physical Plan (CAESURA, GALOIS models):**
- **Logical stage**: LLM constructs sequence of steps (intent recognition) independent of data source
- **Physical stage**: Choose operators per logical step; execute incrementally with feedback
- **Why this works**: Decouples reasoning from execution; enables error recovery; adapts to runtime metrics

**Critical insight for SPARQLLM:** GGFs naturally fit physical stage—each function call is a concrete operator. The gap: no explicit logical planning. SPARQLLM users manually craft both layers in queries.

## 3. Declarative > Imperative for Agent Plans

**Relational algebra as intermediate representation:**
- SQL/SPARQL (declarative) allows optimizer reordering, pushdown filters, parallel execution
- Imperative plans lock execution order; LLM-generated agent traces often serialize unnecessarily
- Example: "Get all publications by author X from DB Y" → logical UNION of both sources, optimizer chooses best join strategy

**For SPARQLLM:** Expressing compositions via SPARQL patterns (not hardcoded function sequences) enables future optimization passes.

## 4. Cost Models for Heterogeneous Sources

**The scaling challenge:**
- LLM call (1-10s, $0.01-$1) vs file read (ms, free) vs vector search (100-500ms) → vastly different profiles
- Traditional cardinality-based cost models fail; need latency-aware estimation

**Emerging strategies (from Calcite, LlamaIndex patterns):**
1. **Push filters early**: Reduce graph materialization before expensive ops (LLM calls)
2. **Caching layer**: Store LLM call results; reuse for similar inputs
3. **Parallelization**: CAESURA/LLMCompiler design subqueries for parallel execution, not serial ReAct steps
4. **Adaptive sampling**: Request k-best from LLM; rank by cost-adjusted relevance

**For SPARQLLM:** GGF cost is opaque. Need function-level cardinality hints or bounded result sizes to enable filter pushdown.

## 5. SPARQL-Generate vs SPARQL-Anything: Why SPARQLLM is Different

| Aspect | SPARQL-Generate | SPARQL-Anything | SPARQLLM |
|--------|-----------------|-----------------|----------|
| **Model** | Template-based RDF output | Facade-X meta-model (uniform abstraction) | Graph Generating Functions (computation-centric) |
| **Source Types** | Static docs (XML/JSON/CSV) | Static docs + remote APIs | LLMs, vector DB, web search, files, custom APIs |
| **Extension** | Learn new syntax constructs | Implement Facade-X transformer | Register Python function |
| **Execution** | SPARQL engine decides | SERVICE operator override | Lazy eval in custom evaluator |
| **Dynamic Cost** | Fixed per format | Fixed per format | Per-call variability (LLM throttle, API SLA) |
| **Error Recovery** | Schema validation only | Schema validation only | Iterative refinement possible (agentic) |

**Unique position:** SPARQLLM's GGF model is computation-first, not data-transformation-first. Enables neuro-symbolic workflows (RAG, multi-hop reasoning) that SPARQL-Generate/Anything don't target.

## 6. Multi-hop Reasoning & Error Handling

**Recent pattern (2025):**
1. Generate SPARQL → execute → get results/empty/syntax error
2. Interpret feedback (schema mismatch? missing relations?)
3. Refine query via LLM with error context
4. Iterate until fix-point or budget exhausted

**ByoKG-RAG (July 2025):** Multi-strategy entity linking + iterative refinement reduces linking errors. Key: explicit verification step before next hop.

**For SPARQLLM:** Opportunity to encode error recovery directly in GGF design—e.g., ggf:LLM_REFINE(?query, ?error) → returns corrected query graph.

## 7. Why Existing Solutions Don't Solve SPARQLLM's Problem

**LangChain/LlamaIndex agents:**
- Serial multi-step tools (ReAct pattern); no cost-aware parallelization
- No built-in SPARQL generation; user supplies tools manually
- No integrated error feedback loop with query executor

**Apache Calcite (federated SQL):**
- Static data source costs; dynamic LLM calling not modeled
- Assumes predicate pushdown works; filters on LLM output need bounds

**SPARQL-Generate/Anything:**
- Designed for static data transformation, not generative AI workloads
- No notion of LLM-as-operator with variable latency/cost

**LLM-as-QueryCompiler gap:** No existing system combines:
- Declarative query language (SPARQL) with computation operators (LLM, vector DB)
- Cost-aware optimization for mixed latencies
- Agentic error refinement within query execution

## Actionable Insights for SPARQLLM

1. **Logical planner abstraction:** Build layer that translates text intent → SPARQL pattern before GGF calls. Enable query rewriting/optimization.

2. **Cost hint protocol:** Allow UDFs to declare `cost_estimate(args) → (latency, tokens/records)`. Use for filter pushdown and parallelization hints.

3. **Error handler registry:** Let GGFs signal recoverable errors (e.g., "unknown entity"). Inject error into query context for automatic refinement attempt.

4. **Caching decorator:** Transparent LLM result memoization by input hash; critical for multi-hop graphs with repeated entities.

5. **Multi-path execution:** Generate N candidate SPARQL patterns; execute in parallel with cost-weighted pruning (e.g., stop slow paths if first finishes).

## Unresolved Questions

1. How to estimate LLM output cardinality for filter pushdown without sampling?
2. Can SPARQL semantics express iterative refinement loops without external agentic control?
3. What's the cost threshold where parallel execution beats serial for SPARQL GGF composition?
4. How to design cost models that work across vastly different latency regimes (ms to 10s)?
