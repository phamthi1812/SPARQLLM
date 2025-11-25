# Getting Started: Web Search + CSV Demo

Quick start guide for the Companies + Web News demo using SPARQL-GGF.

---

## ✅ What Works Now

1. **CSV Data Loading** - Load company data from CSV files
2. **Web Search (DuckDuckGo)** - Search the web using `SEARCH()` function
3. **CSV + Web Integration** - Combine local CSV data with live web search

---

## 🚀 Quick Start

### 1. Activate Virtual Environment

```bash
cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM
source venv312_new/bin/activate
```

### 2. Run Test Queries

```bash
# Test 1: Basic web search
python -m SPARQLLM.cli.slm -f demo/companies_news/test_queries/test_1_basic_search.sparql

# Test 2: CSV + Web search (RECOMMENDED)
python -m SPARQLLM.cli.slm -f demo/companies_news/test_queries/test_2_csv_plus_search.sparql
```

### 3. Run Interactive Demo

```bash
# Set Groq API key (for LLM query generation)
# Get your API key from https://console.groq.com/keys
export GROQ_API_KEY="your_groq_api_key_here"

# Run demo
python demo/companies_news/demo_companies_news.py
```

---

## 📖 Example Queries

### Query 1: List Companies (CSV Only)

```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?company_name ?sector WHERE {
    BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:company_name ?company_name .
        ?row ex:sector ?sector .
    }
}
```

### Query 2: Search for OpenAI News (CSV + Web)

```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
PREFIX schema: <https://schema.org/>

SELECT ?company_name ?news_title ?news_url WHERE {
    # Get OpenAI from CSV
    BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:company_name ?company_name .
    }
    FILTER(?company_name = "OpenAI")

    # Search for news
    BIND(CONCAT(?company_name, " latest news 2024") AS ?search_query)
    BIND(ggf:SEARCH(?search_query) AS ?webGraph)

    # Extract results (IMPORTANT: nested structure!)
    GRAPH ?webGraph {
        ?feed schema:dataFeedElement ?feedItem .
        ?feedItem schema:item ?item .
        ?item schema:name ?news_title .
        BIND(?item AS ?news_url)
    }
}
LIMIT 5
```

---

## 🔑 Key Points

### ✅ Must-Know Rules

1. **Schema Prefix:** Always use `PREFIX schema: <https://schema.org/>` (with **https**!)

2. **SEARCH RDF Structure:** Results are nested:
   ```sparql
   GRAPH ?webGraph {
       ?feed schema:dataFeedElement ?feedItem .
       ?feedItem schema:item ?item .
       ?item schema:name ?title .
       ?item schema:description ?snippet .
   }
   ```

3. **Sector Names:** Use exact names from CSV:
   - ✅ "Technology", "Artificial Intelligence"
   - ❌ "Tech", "AI"

4. **Performance:** Web search takes 1-2 seconds per query

---

## ⚠️ Known Limitations

### LLM Extraction (Experimental)

**Status:** ⚠️ Not working reliably with local Ollama

**Issue:** `SLM-LLMGRAPH` returns empty results when extracting from web search snippets

**Workaround:**
- Use CSV + Web queries (these work perfectly!)
- For LLM extraction, try `SLM-LLMGRAPH_GROQ` instead of local Ollama
- Wait for debugging/improvements

---

## 📁 Project Structure

```
demo/companies_news/
├── README.md              # Full documentation
├── GETTING_STARTED.md     # This file (quick start)
├── TEST_RESULTS.md        # Test results and findings
├── schema.txt             # Data schema and patterns
├── demo_companies_news.py # Interactive demo
├── run_tests.sh           # Test runner script
├── data/
│   └── companies.csv      # 15 tech companies
├── queries/
│   ├── q1_list_ai_companies.sparql
│   └── q2_search_openai_news.sparql  # ✅ Working example
└── test_queries/
    ├── test_1_basic_search.sparql     # ✅ Working
    ├── test_2_csv_plus_search.sparql  # ✅ Working
    ├── test_3_search_plus_llm_local.sparql  # ⚠️ Partial
    └── test_4_full_pipeline.sparql    # ⏳ Pending
```

---

## 💡 Recommended Questions for Demo

Start with these working examples:

**CSV Only (Fast):**
- "List all companies in the Technology sector"
- "Which companies are based in San Francisco?"

**CSV + Web (Medium, 2-3 sec):**
- "Find recent news about OpenAI"
- "Search for articles about Tesla"
- "Get latest information on NVIDIA"

**Advanced (Avoid for now):**
- ❌ Queries with LLM extraction (not reliable yet)

---

## 🐛 Troubleshooting

### Empty Results

**Problem:** Query returns empty DataFrame

**Solutions:**
1. Check sector name is exact (e.g., "Technology" not "Tech")
2. Verify schema prefix uses `https://schema.org/`
3. Ensure SEARCH graph pattern includes nested structure:
   ```sparql
   ?feed schema:dataFeedElement ?feedItem .
   ?feedItem schema:item ?item .
   ```

### Web Search Not Working

**Problem:** DuckDuckGo search returns no results

**Solutions:**
1. Check internet connection
2. Try broader search terms
3. Check MCP server is configured in config.ini

### LLM Extraction Returns Empty

**Problem:** `SLM-LLMGRAPH` returns empty extracted_info

**Status:** Known issue - under investigation

**Workaround:** Avoid LLM extraction queries for now

---

## 📚 Next Steps

1. **Learn More:** Read `README.md` for full documentation
2. **View Tests:** Check `TEST_RESULTS.md` for detailed test reports
3. **Customize:** Edit `companies.csv` to add your own data
4. **Explore:** Try modifying `schema.txt` patterns

---

## 🆘 Getting Help

**Issues:**
- Test results: `TEST_RESULTS.md`
- Full docs: `README.md`
- Schema patterns: `schema.txt`

**Working Examples:**
- `test_2_csv_plus_search.sparql` - Fully working CSV + Web query
- `q2_search_openai_news.sparql` - Example query for demo

---

**Status:** ✅ Ready for CSV + Web Search queries
**Updated:** 2025-11-21
