# Multi-Step Query Demo

This directory contains demonstrations of SPARQLLM's multi-step query planning capabilities, where the LLM generates complex plans that chain multiple Graph Generating Functions (GGFs) together to answer questions requiring external data integration.

## Overview

Multi-step queries allow you to:
- **Chain web searches** with LLM extraction
- **Pass variables between steps** using CONCAT
- **Integrate data from multiple sources**
- **Handle complex questions** that require iterative data gathering

## Example: Restaurant Finder

The `restaurant_finder.py` demo shows a complete multi-step workflow:

1. **Web search** for conference location
2. **Fetch** conference website content
3. **LLM extract** city/country from content
4. **Web search** for restaurants using extracted location
5. **Fetch** restaurant pages
6. **LLM extract** price information
7. **Sort and filter** results

## Quick Start

### Prerequisites

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Choose your LLM provider**:

   **Option A: OpenAI (Recommended for quality)**
   ```bash
   export OPENAI_API_KEY=your-key-here
   ```

   **Option B: Ollama (Free, local)**
   ```bash
   # Start Ollama server
   ollama serve

   # Pull a model (if not already installed)
   ollama pull llama3.2
   ```

   **Option C: Groq (Fast, free tier)**
   ```bash
   export GROQ_API_KEY=your-key-here
   ```

### Running the Demo

#### Basic Usage

```bash
# Using Ollama (default)
python demo/multi_step/restaurant_finder.py

# Using OpenAI
python demo/multi_step/restaurant_finder.py --provider openai

# Using Groq
python demo/multi_step/restaurant_finder.py --provider groq
```

#### Interactive Mode

Step through execution with user confirmation at each step:

```bash
python demo/multi_step/restaurant_finder.py --provider ollama --interactive
```

This will:
- Show each step before execution
- Display estimated costs (LLM calls, web requests)
- Pause for confirmation before each step
- Allow skipping or aborting steps

#### Custom Questions

```bash
python demo/multi_step/restaurant_finder.py \
  --provider openai \
  --question "Find cheap hotels near PyCon 2024"
```

#### Save Generated Plans

```bash
# Save both plan and SPARQL
python demo/multi_step/restaurant_finder.py \
  --provider ollama \
  --save-plan plan.json \
  --save-sparql query.sparql
```

## What Gets Generated

### 1. Logical Plan (JSON)

The LLM generates a structured plan:

```json
{
  "version": "1.0",
  "steps": [
    {
      "id": "step1",
      "operation": "web_search",
      "ggf": {"name": "SEARCH", "args": {"query": "Web Conference 2024 location"}},
      "bindings": {"url": "?confUrl"}
    },
    {
      "id": "step2",
      "operation": "web_fetch",
      "ggf": {"name": "SNAP", "args": {"url": "?confUrl"}},
      "depends_on": ["step1"],
      "bindings": {"text": "?confText"}
    },
    ...
  ],
  "output": {
    "variables": ["restName", "avgPrice", "restUrl"],
    "order_by": [{"variable": "avgPrice", "order": "ASC"}],
    "limit": 5
  }
}
```

### 2. SPARQL Query

The plan is compiled to SPARQL with BIND + GRAPH patterns:

```sparql
PREFIX ggf: <http://example.org/ggf#>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?restName ?avgPrice ?restUrl
WHERE {
  BIND(ggf:SEARCH("Web Conference 2024 location", 2) AS ?g1)
  GRAPH ?g1 { ?result schema:url ?confUrl . }

  BIND(ggf:SNAP(?confUrl, 2000, true) AS ?g2)
  GRAPH ?g2 { ?page schema:text ?confText . }

  BIND(ggf:LLM(CONCAT("Extract city, country: ", ?confText)) AS ?g3)
  GRAPH ?g3 { ?event schema:location ?location . }

  BIND(ggf:SEARCH(CONCAT("cheap restaurants near ", ?location), 5) AS ?g4)
  GRAPH ?g4 { ?rest schema:name ?restName ; schema:url ?restUrl . }

  BIND(ggf:SNAP(?restUrl, 3000, true) AS ?g5)
  GRAPH ?g5 { ?menu schema:text ?menuText . }

  BIND(ggf:LLM(CONCAT("Extract avg price: ", ?menuText)) AS ?g6)
  GRAPH ?g6 { ?item schema:price ?avgPrice . }
}
ORDER BY ASC(?avgPrice)
LIMIT 5
```

### 3. Execution

Run the generated SPARQL:

```bash
slm-run -q "$(cat query.sparql)"
```

## Understanding Multi-Step Queries

### When to Use Multi-Step Mode

The system auto-detects complex queries based on keywords:
- **Location-based**: "near", "nearby", "located", "around"
- **Comparison**: "cheap", "best", "top", "most", "least"
- **Aggregation**: "find", "compare", "which", "what are"
- **External data**: "conference", "event", "restaurant", "hotel"

If your question contains 2+ of these indicators, multi-step mode activates automatically.

### Manual Override

Force multi-step mode in code:

```python
from demo.query_generator import QueryGenerator

generator = QueryGenerator(
    provider='ollama',
    use_multi_step=True  # Force multi-step
)
```

### Cost Considerations

Multi-step queries involve:
- **LLM calls**: ~$0.01-0.03 each, 1-2 seconds
- **Web requests**: Free but slower (1-3 seconds each)

Example restaurant query:
- 2 LLM calls (~$0.04, 3-4s)
- 7 web requests (~7-10s)
- **Total**: ~$0.04, 10-14 seconds

Use `--interactive` mode to control costs by approving each step.

## Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve

# Verify model is available
ollama list
```

### OpenAI API Errors

```bash
# Check API key is set
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Plan Generation Fails

If the LLM generates invalid JSON:
1. **Retry**: The system auto-retries up to 3 times
2. **Edit**: Select "edit" option to manually fix the plan
3. **Simplify**: Try a simpler question first
4. **Check prompt**: Ensure `plan_system_prompt_multi_step.txt` exists

### Compilation Errors

If plan compiles but execution fails:
1. **Check GGF names**: Must match catalog exactly (case-sensitive)
2. **Verify arguments**: GGF args must match expected types
3. **Dependencies**: Ensure `depends_on` references exist
4. **Variables**: Check bindings map to valid SPARQL variables

## Advanced Usage

### Creating Custom Multi-Step Queries

1. **Study the examples** in `demo/prompts/examples/`
2. **Follow patterns**:
   - Web search → Fetch → Extract → Search again
   - Use CONCAT for dynamic prompts
   - Minimize LLM calls (expensive)
   - Use LIMIT early to reduce processing

3. **Test incrementally**:
   ```bash
   # Start with simple query
   python demo/query_generator.py --provider ollama
   # Question: "Search for SPARQL tutorials"

   # Then try 2-step
   # Question: "Search for SPARQL tutorials and extract key topics"

   # Finally, complex multi-step
   # Question: "Find cheap restaurants near Web Conference 2024"
   ```

### Extending with New GGFs

To add custom data sources:

1. **Implement GGF** in `SPARQLLM/udf/`
2. **Register** in `config.ini` `[Associations]`
3. **Update catalog**: Run `python -m SPARQLLM.tools.generate_ggf_catalog`
4. **Test**: GGF should appear in catalog summary

See `SPARQLLM/udf/mcp/` for MCP-based GGF examples.

## Reference Examples

See `demo/prompts/examples/` for documented multi-step patterns:
- `restaurant_finder.json` - Full restaurant finder workflow
- More examples coming soon

## Support

Issues? Check:
1. `demo/prompts/plan_system_prompt_multi_step.txt` - LLM prompt
2. `SPARQLLM/compiler/physical_compiler.py` - Plan compilation
3. `SPARQLLM/udf/mcp/` - GGF implementations

Report bugs at: https://github.com/your-repo/SPARQLLM/issues
