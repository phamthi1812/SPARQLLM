# Web Search + LLM Integration Test Results

**Date:** 2025-11-21
**Test Suite:** SPARQL-GGF Web Search (SEARCH function) + LLM Extraction
**Objective:** Verify web search integration and LLM extraction capabilities

---

## Test Configuration

- **Search Provider:** DuckDuckGo (via MCP `SEARCH` alias)
- **LLM:** Ollama qwen2.5:3b (local)
- **SPARQLLM Version:** Current main branch
- **Python:** 3.12 (venv312_new)

---

## Test Results Summary

| Test | Description | Status | Notes |
|------|-------------|--------|-------|
| **Test 1** | Basic SEARCH function | ✅ PASSED | Returns 3 search results with title, URL, description |
| **Test 2** | CSV + SEARCH integration | ✅ PASSED | Successfully loads CSV, filters, and searches |
| **Test 3** | SEARCH + LLM extraction | ⚠️ PARTIAL | Search works, LLM extraction returns empty |
| **Test 4** | Full pipeline (CSV+SEARCH+LLM) | ⏳ PENDING | Not yet tested |

---

## Detailed Test Reports

### ✅ Test 1: Basic SEARCH Function

**Query:** Direct web search for "OpenAI GPT-4 2024"

**SPARQL:**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX schema: <https://schema.org/>

SELECT ?title ?url ?description WHERE {
    BIND(ggf:SEARCH("OpenAI GPT-4 2024") AS ?webGraph)

    GRAPH ?webGraph {
        ?feed schema:dataFeedElement ?feedItem .
        ?feedItem schema:item ?item .
        ?item schema:name ?title .
        ?item schema:description ?description .
        BIND(?item AS ?url)
    }
}
LIMIT 3
```

**Results:**
- **Returned:** 3 results
- **Execution Time:** ~1-2 seconds
- **Data Quality:** Good - relevant Chinese content from Zhihu

**Sample Output:**
```
title                                            url                         description
OpenAI 上线新一代编程神器 Codex...                https://www.zhihu.com/...  OpenAI训练codex-1的一个主要目标...
如何评价 OpenAI 发布的 GPT4.5...                https://www.zhihu.com/...  OpenAI刚刚发布了GPT4.5...
```

**✅ Conclusion:** SEARCH function works correctly with proper RDF structure

---

### ✅ Test 2: CSV + SEARCH Integration

**Query:** Load OpenAI from CSV, then search for news

**SPARQL:**
```sparql
SELECT ?company_name ?news_title ?news_url WHERE {
    BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:company_name ?company_name .
    }
    FILTER(?company_name = "OpenAI")

    BIND(CONCAT(?company_name, " latest developments 2024") AS ?search_query)
    BIND(ggf:SEARCH(?search_query) AS ?webGraph)

    GRAPH ?webGraph {
        ?feed schema:dataFeedElement ?feedItem .
        ?feedItem schema:item ?item .
        ?item schema:name ?news_title .
        BIND(?item AS ?news_url)
    }
}
LIMIT 5
```

**Results:**
- **Returned:** 3 results
- **CSV Loading:** ✅ Works
- **Search Integration:** ✅ Works
- **Execution Time:** ~2-3 seconds

**✅ Conclusion:** CSV + SEARCH integration works perfectly

---

### ⚠️ Test 3: SEARCH + LLM (Local Ollama)

**Query:** Search web, extract info with local LLM

**SPARQL:**
```sparql
SELECT ?news_title ?snippet ?extracted_info WHERE {
    BIND(ggf:SEARCH("OpenAI artificial intelligence 2024") AS ?webGraph)

    GRAPH ?webGraph {
        ?feed schema:dataFeedElement ?feedItem .
        ?feedItem schema:item ?item .
        ?item schema:name ?news_title .
        ?item schema:description ?snippet .
    }

    BIND(CONCAT(
        "Extract key information from this text about a product launch: ",
        SUBSTR(?snippet, 1, 400),
        ". Return JSON-LD: {\"@context\": \"http://schema.org/\", ",
        "\"@type\": \"Product\", ",
        "\"name\": \"product name\", ",
        "\"releaseDate\": \"release date\", ",
        "\"description\": \"brief description\"}"
    ) AS ?llm_prompt)

    BIND(ggf:SLM-LLMGRAPH(?llm_prompt) AS ?llmGraph)
    GRAPH ?llmGraph {
        ?entity schema:description ?extracted_info .
    }
}
LIMIT 2
```

**Results:**
- **Search Phase:** ✅ Returned 3 results
- **LLM Phase:** ❌ Empty extracted_info
- **Execution Time:** ~15-20 seconds
- **Error:** No visible errors, but LLM graph is empty

**Observations:**
1. Search results are retrieved successfully
2. LLM is called (4 DeprecationWarnings about ConjunctiveGraph → one per LLM call?)
3. But final DataFrame shows empty `extracted_info` column
4. This suggests LLM either:
   - Didn't return valid JSON-LD
   - Returned data that couldn't be parsed as RDF
   - Graph structure doesn't match the SPARQL pattern

**Possible Issues:**
1. **LLM Prompt:** May need better structured prompt
2. **LLM Model:** qwen2.5:3b might not be good at JSON-LD generation
3. **RDF Parsing:** LLM output might not be valid RDF
4. **Graph Pattern:** Pattern `?entity schema:description ?extracted_info` might not match LLM output

**⚠️ Conclusion:** Search works, but LLM extraction needs investigation

---

## Key Findings

### 🎯 What Works

1. **SEARCH Function (DuckDuckGo via MCP):**
   - ✅ Returns proper RDF structure
   - ✅ Nested DataFeed → DataFeedItem → WebPage structure
   - ✅ Fast (1-2 seconds per search)
   - ✅ Good result quality

2. **CSV + SEARCH Integration:**
   - ✅ Load companies from CSV
   - ✅ Filter by criteria
   - ✅ Dynamic search query generation
   - ✅ Results properly joined

3. **RDF Structure:**
   - ✅ Must use `PREFIX schema: <https://schema.org/>` (with https!)
   - ✅ Pattern: `?feed schema:dataFeedElement ?feedItem . ?feedItem schema:item ?item`

### ⚠️ Issues Found

1. **LLM Query Generation - Missing Subqueries:**
   - 🔴 **CRITICAL**: LLM generates queries that filter AFTER web search, not before
   - **Impact**: Searching for 1 company → executes 15 web searches!
   - **Example**: "Search for Tesla" → searches all 15 companies, wastes 15-30 seconds
   - **Fix**: Updated schema.txt and demo prompt with prominent subquery warnings
   - **Status**: ✅ Fixed in prompts, needs testing

2. **LLM Extraction (SLM-LLMGRAPH):**
   - ⚠️ Empty results when extracting from web search snippets
   - ⚠️ No error messages (silent failure)
   - ⚠️ Unclear if issue is prompt, model, or RDF parsing

3. **Schema Documentation:**
   - ⚠️ Initial examples were wrong (missing nested structure)
   - ✅ Now fixed in schema.txt

### 📝 Recommendations

1. **For LLM Extraction:**
   - Test `SLM-LLMGRAPH_GROQ` instead of local Ollama
   - Simplify LLM prompt (less complex JSON-LD)
   - Add debug logging to see LLM raw output
   - Try larger model (qwen2.5:7b) for better JSON generation

2. **For Demo:**
   - Start with CSV + SEARCH queries (these work!)
   - Add LLM extraction as advanced/optional feature
   - Warn users about LLM extraction reliability

3. **For Schema:**
   - ✅ Already updated with correct RDF patterns
   - Add example of successful LLM extraction once working

---

## Next Steps

1. **Investigate LLM Extraction:**
   - [ ] Test with Groq (SLM-LLMGRAPH_GROQ)
   - [ ] Check llmgraph_ollama.py for debugging
   - [ ] Simplify prompt to just return simple key-value pairs
   - [ ] Test standalone LLM query without web search

2. **Update Demo:**
   - [x] Fix schema.txt with correct SEARCH patterns
   - [x] Fix all example queries
   - [ ] Add working examples to README
   - [ ] Update system prompt in demo_companies_news.py

3. **Documentation:**
   - [ ] Add troubleshooting guide
   - [ ] Document known limitations
   - [ ] Add performance benchmarks

---

## Files Updated

- ✅ `schema.txt` - Fixed SEARCH RDF patterns
- ✅ `test_1_basic_search.sparql` - Working
- ✅ `test_2_csv_plus_search.sparql` - Working
- ✅ `test_3_search_plus_llm_local.sparql` - Partial (search works)
- ✅ `test_4_full_pipeline.sparql` - Updated structure
- ✅ `run_tests.sh` - Test runner script
- ✅ `TEST_RESULTS.md` - This document

---

## Conclusion

**Web Search (SEARCH function) is fully operational and working well.** CSV + SEARCH integration is solid and ready for production use.

**LLM extraction needs investigation** - the infrastructure is there, but extraction returns empty results. This is likely a prompt engineering or model capability issue rather than a fundamental SPARQLLM problem.

**Recommendation:** Ship demo with CSV + SEARCH functionality now, and add LLM extraction as experimental feature once debugging is complete.
