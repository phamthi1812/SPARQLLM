# Product Extraction Issue - Companies News Demo

**Date:** 2025-11-21
**Demo:** `demo/companies_news/demo_companies_news_refined.py`
**Question:** "what are the products that tech companies in San Francisco sell?"

## Environment Issue (Fixed)

**Problem:** Pandas/numpy binary incompatibility in miniforge3 Python 3.10
```
ValueError: numpy.dtype size changed, may indicate binary incompatibility
```

**Solution:** Use `venv312_new` (Python 3.12.11) instead

## Query Generation Issue (Active)

**Problem:** Query extracts web page titles instead of actual product names

**Generated Query Pattern:**
```sparql
GRAPH ?webGraph {
    ?item schema:name ?product .  # Gets page TITLE
}
```

**Result:**
```
company_name    product
OpenAI          Home - State Industrial Products
OpenAI          Carpet - State Industrial Products
Anthropic       Anthropic Stock $177.33
```

**Expected:**
```
company_name    product
OpenAI          ChatGPT
Anthropic       Claude
```

## Root Cause

Web search returns `schema:name` = page title, not product name.
Search result descriptions might contain product info but not extracted.

## Fix Options

1. Use `schema:description` field
2. Add `ggf:SLM-EXTRACT` to extract products from descriptions
3. Use `ggf:WEB-FETCH` for full page content

## Status

- ✅ Environment: Fixed (use venv312_new)
- ✅ Query execution: Working
- ✅ CSV filtering: Correct (SF companies)
- ✅ Web search: Working via MCP DuckDuckGo
- ❌ Product extraction: Wrong data extracted
