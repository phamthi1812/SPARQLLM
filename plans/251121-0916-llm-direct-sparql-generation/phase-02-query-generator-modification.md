# Phase 2: Query Generator Modification

**Status:** Ready
**Estimated Effort:** 1-2 hours
**Dependencies:** Phase 1 (system prompt must exist)

---

## Objective

Modify `demo/query_generator.py` to support direct SPARQL generation mode.

---

## Changes Required

### 1. Update Mode Initialization (Lines 408-420)

**Current Code:**
```python
mode_choice = input("\nMode [1/2/3]: ").strip() or "1"

if mode_choice == "1":
    # Two-stage mode
    generator = QueryGenerator(mode='plan', provider=provider)
    # ... existing logic ...
```

**Add:**
```python
elif mode_choice == "2":
    # Direct SPARQL generation mode
    generator = QueryGenerator(mode='direct', provider=provider)

    # Get user question
    print("\n" + "="*80)
    question = input("Enter your question: ").strip()

    if not question:
        print("No question provided. Exiting.")
        return

    # Generate SPARQL directly
    print("\n[Direct Mode] Generating SPARQL query...")
    sparql = generator.generate_sparql(question)

    print("\n" + "="*80)
    print("Generated SPARQL:")
    print("="*80)
    print(sparql)
    print("="*80)

    # Ask if user wants to execute
    execute = input("\nExecute query? [Y/n]: ").strip().lower()
    if execute != 'n':
        print("\nExecuting via slm-run...")
        # Save to temp file and execute
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sparql', delete=False) as f:
            f.write(sparql)
            temp_path = f.name

        os.system(f"slm-run --config config.ini -f {temp_path} --debug")
        os.unlink(temp_path)
```

---

### 2. Add generate_sparql() Method

**Location:** After `generate_query()` method (around line 300)

**Implementation:**
```python
def generate_sparql(self, question: str, context: dict = None) -> str:
    """
    Generate SPARQL query directly (mode='direct').

    Args:
        question: Natural language question
        context: Optional context dict (e.g., dataset info)

    Returns:
        Valid SPARQL query string

    Raises:
        ValueError: If prompt file not found or LLM fails
    """
    # Load system prompt
    prompt_path = os.path.join(
        os.path.dirname(__file__),
        "serial_killers/prompts/direct_system_prompt.txt"
    )

    if not os.path.exists(prompt_path):
        raise ValueError(f"Direct mode prompt not found: {prompt_path}")

    with open(prompt_path, 'r') as f:
        system_prompt = f.read()

    # Build user message
    user_message = f"Question: {question}"

    if context:
        context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
        user_message += f"\n\nContext:\n{context_str}"

    # Call LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    if self.llm_type == 'ollama':
        response = self._call_ollama(messages)
    elif self.llm_type == 'openai':
        response = self._call_openai(messages)
    else:
        response = self._call_mlx(messages)

    # Strip markdown code fences
    sparql = self._clean_sparql_response(response)

    return sparql


def _clean_sparql_response(self, response: str) -> str:
    """Remove markdown fences and extra whitespace from LLM response."""
    sparql = response.strip()

    # Remove markdown code blocks
    if sparql.startswith("```sparql"):
        sparql = sparql[9:]  # Remove ```sparql
    elif sparql.startswith("```"):
        sparql = sparql[3:]  # Remove ```

    if sparql.endswith("```"):
        sparql = sparql[:-3]  # Remove trailing ```

    # Clean up whitespace
    sparql = sparql.strip()

    return sparql


def _call_ollama(self, messages: list) -> str:
    """Call Ollama LLM (existing method, ensure it exists)."""
    # Check if method exists, if not, implement
    import requests

    url = f"{self.base_url}/api/chat"
    payload = {
        "model": self.model_name,
        "messages": messages,
        "stream": False
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()

    return response.json()["message"]["content"]


def _call_openai(self, messages: list) -> str:
    """Call OpenAI LLM (existing method, ensure it exists)."""
    from openai import OpenAI

    client = OpenAI(api_key=self.api_key)
    response = client.chat.completions.create(
        model=self.model_name,
        messages=messages,
        temperature=0.1  # Low temperature for consistent SPARQL generation
    )

    return response.choices[0].message.content


def _call_mlx(self, messages: list) -> str:
    """Call MLX local LLM (existing method, ensure it exists)."""
    # Combine messages into single prompt
    prompt = ""
    for msg in messages:
        if msg["role"] == "system":
            prompt += f"System: {msg['content']}\n\n"
        elif msg["role"] == "user":
            prompt += f"User: {msg['content']}\n\n"

    prompt += "Assistant: "

    # Call MLX (implementation depends on existing setup)
    response = self.mlx_model.generate(prompt)
    return response
```

---

### 3. Update __init__ to Support Direct Mode

**Current __init__ signature:**
```python
def __init__(self, mode='plan', provider='ollama'):
    self.mode = mode
    # ... existing initialization ...
```

**Add validation:**
```python
def __init__(self, mode='plan', provider='ollama'):
    if mode not in ['plan', 'direct']:
        raise ValueError(f"Invalid mode: {mode}. Must be 'plan' or 'direct'")

    self.mode = mode
    self.provider = provider

    # Initialize LLM based on provider
    if provider == 'ollama':
        self.llm_type = 'ollama'
        self.base_url = "http://localhost:11434"
        self.model_name = "llama3.2:latest"
    elif provider == 'openai':
        self.llm_type = 'openai'
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = "gpt-4"
    else:
        self.llm_type = 'mlx'
        # ... existing MLX setup ...

    print(f"[QueryGenerator] Initialized with mode={mode}, provider={provider}")
```

---

## Testing Strategy

### Unit Test (manual)

**Test File:** `tests/test_query_generator_direct.py`

```python
import sys
sys.path.insert(0, './demo')
from query_generator import QueryGenerator

def test_direct_mode_initialization():
    """Test direct mode can be initialized."""
    generator = QueryGenerator(mode='direct', provider='ollama')
    assert generator.mode == 'direct'
    print("✓ Direct mode initialization")


def test_generate_sparql():
    """Test SPARQL generation."""
    generator = QueryGenerator(mode='direct', provider='ollama')

    question = "Show me the top 5 serial killers by victim count"
    sparql = generator.generate_sparql(question)

    # Validate output
    assert "PREFIX ggf:" in sparql, "Missing PREFIX ggf"
    assert "PREFIX ex:" in sparql, "Missing PREFIX ex"
    assert "BIND(ggf:SLM-CSV" in sparql, "Missing GGF call"
    assert "GRAPH" in sparql, "Missing GRAPH clause"
    assert "LIMIT" in sparql, "Missing LIMIT (top N query)"

    print("✓ SPARQL generation")
    print(sparql)


def test_markdown_cleaning():
    """Test markdown fence removal."""
    generator = QueryGenerator(mode='direct', provider='ollama')

    # Simulate LLM response with markdown
    response = """```sparql
PREFIX ggf: <http://ggf.org/>
SELECT ?s WHERE { ?s ?p ?o }
```"""

    cleaned = generator._clean_sparql_response(response)

    assert not cleaned.startswith("```")
    assert "PREFIX ggf:" in cleaned
    print("✓ Markdown cleaning")


if __name__ == '__main__':
    test_direct_mode_initialization()
    test_markdown_cleaning()
    test_generate_sparql()
    print("\n✅ All tests passed")
```

---

### Integration Test (manual)

**Run:**
```bash
cd demo
python query_generator.py
# Select: 2 (Direct SPARQL generation)
# Enter: "Who are the top 10 deadliest serial killers?"
# Expected: Valid SPARQL query displayed
```

**Validation Checklist:**
- [ ] Prompt loads successfully
- [ ] LLM generates response
- [ ] Markdown fences removed
- [ ] SPARQL contains PREFIX declarations
- [ ] SPARQL contains BIND + GRAPH pattern
- [ ] Query references serial_killers_clean.csv

---

## Error Handling

**Add try-catch blocks:**
```python
def generate_sparql(self, question: str, context: dict = None) -> str:
    try:
        # ... existing logic ...
        return sparql

    except FileNotFoundError as e:
        raise ValueError(f"Prompt file not found: {e}")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"LLM API call failed: {e}")

    except Exception as e:
        raise ValueError(f"SPARQL generation failed: {e}")
```

---

## Code Quality

**Pre-commit checks:**
1. Run linter: `flake8 demo/query_generator.py`
2. Type hints: Ensure all methods have proper type annotations
3. Docstrings: All new methods have clear docstrings
4. No debug prints: Remove or use logging module

---

## Success Criteria

- ✅ `mode='direct'` initialization works
- ✅ `generate_sparql()` method implemented
- ✅ Markdown cleaning works correctly
- ✅ Manual test passes (generates valid SPARQL)
- ✅ Error handling for missing prompt file
- ✅ No breaking changes to plan mode

---

## Files Modified

- `demo/query_generator.py` (+80-100 lines)

---

## Next Steps

Proceed to Phase 3 (Validation Layer) after manual testing confirms SPARQL generation works.
