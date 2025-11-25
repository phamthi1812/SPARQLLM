# Companies + Web News Demo

**Multi-Source Data Integration:** CSV (local) + Web Search (live) + LLM Extraction (AI)

## 🎯 What This Demo Shows

Combine **3 data sources** in a single SPARQL query:
1. 📊 **CSV file** - Structured company data (local)
2. 🌐 **Web search** - Live news and articles (online)
3. 🤖 **LLM extraction** - Extract structured info from unstructured text (AI)

---

## 📁 Demo Structure

```
demo/companies_news/
├── README.md                 # This file
├── schema.txt                # Schema + patterns for LLM
├── demo_companies_news.py    # Main demo script (TODO)
├── data/
│   └── companies.csv         # 15 tech companies
└── queries/
    ├── q1_list_ai_companies.sparql
    ├── q2_search_openai_news.sparql
    └── q3_extract_funding_news.sparql
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# 1. Groq API key (for LLM extraction)
export GROQ_API_KEY="your-key"

# 2. Make sure web search is configured in config.ini
# (uses DuckDuckGo by default)
```

### Run Demo

```bash
python demo/companies_news/demo_companies_news.py
```

---

## 📊 Data: companies.csv

**15 tech companies:**
- **AI**: OpenAI, Anthropic
- **Tech Giants**: Google, Microsoft, Meta, Amazon, Apple
- **Semiconductors**: NVIDIA
- **Automotive**: Tesla
- **Enterprise**: Salesforce
- **Streaming**: Netflix
- **Transportation**: Uber, SpaceX
- **Hospitality**: Airbnb
- **FinTech**: Stripe

**Columns:** company_name, sector, headquarters, founded, ceo, description, website

---

## 💡 Example Queries

### Level 1: CSV Only

**Question:** "List all AI companies founded after 2020"

**Generated SPARQL:**
```sparql
SELECT ?company_name ?founded WHERE {
    BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?g)
    GRAPH ?g {
        ?row ex:company_name ?company_name .
        ?row ex:sector ?sector .
        ?row ex:founded ?founded .
    }
    FILTER(?sector = "Artificial Intelligence" && ?founded > 2020)
}
```

**Results:**
- Anthropic (2021)

---

### Level 2: CSV + Web Search

**Question:** "Find recent news about OpenAI"

**Generated SPARQL:**
```sparql
SELECT ?company_name ?news_title ?url WHERE {
    # Get company from CSV
    BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:company_name ?company_name .
    }
    FILTER(?company_name = "OpenAI")

    # Search web
    BIND(CONCAT(?company_name, " latest news 2024") AS ?query)
    BIND(ggf:SLM-WEBSEARCH(?query) AS ?webGraph)
    GRAPH ?webGraph {
        ?result schema:name ?news_title .
        ?result schema:url ?url .
    }
}
LIMIT 5
```

**Results:**
- Live news articles about OpenAI from web search

---

### Level 3: CSV + Web + LLM Extraction

**Question:** "What recent funding have AI companies received?"

**Data Flow:**
```
companies.csv
  ↓ Filter (AI companies)
  ↓ LIMIT 3
Web Search ("Company funding news 2024")
  ↓ Get snippets
LLM Extract (funding amount, investors)
  ↓ Return structured JSON-LD
Combined Results
```

**Generated SPARQL:**
```sparql
SELECT ?company_name ?funding_info WHERE {
    # Step 1: Get AI companies
    {
        SELECT ?company_name WHERE {
            BIND(ggf:SLM-CSV("./demo/companies_news/data/companies.csv") AS ?g)
            GRAPH ?g {
                ?row ex:company_name ?company_name .
                ?row ex:sector "Artificial Intelligence" .
            }
        }
        LIMIT 3
    }

    # Step 2: Search for funding news
    BIND(CONCAT(?company_name, " funding news 2024") AS ?query)
    BIND(ggf:SLM-WEBSEARCH(?query) AS ?webGraph)
    GRAPH ?webGraph {
        ?result schema:description ?snippet .
    }

    # Step 3: Extract structured info with LLM
    BIND(CONCAT(
        "Extract funding info: ", SUBSTR(?snippet, 1, 500),
        ". Return JSON-LD with amount and investors."
    ) AS ?prompt)
    BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?llmGraph)
    GRAPH ?llmGraph {
        ?funding schema:description ?funding_info .
    }
}
```

---

## 🎯 Use Cases

### Business Intelligence
- Track competitor news
- Monitor funding rounds
- Identify partnerships
- Track product launches

### Market Research
- Industry trend analysis
- Company performance tracking
- Executive changes
- M&A activity

### Investment Research
- Startup funding tracking
- Valuation changes
- IPO news
- Earnings reports

---

## ⚡ Performance Tips

### 1. Use LIMIT Aggressively
```sparql
# Bad: Searches for all 15 companies (slow!)
SELECT ?company_name ?news WHERE {
    BIND(ggf:SLM-CSV(...) AS ?g)
    GRAPH ?g { ?row ex:company_name ?company_name . }
    BIND(ggf:SLM-WEBSEARCH(?company_name) AS ?web)  # 15 searches!
}

# Good: Only searches for 3 companies (fast!)
SELECT ?company_name ?news WHERE {
    {
        SELECT ?company_name WHERE {
            BIND(ggf:SLM-CSV(...) AS ?g)
            GRAPH ?g { ?row ex:company_name ?company_name . }
        }
        LIMIT 3  # ← Only 3 searches
    }
    BIND(ggf:SLM-WEBSEARCH(?company_name) AS ?web)
}
```

### 2. Filter Before Searching
```sparql
# Filter CSV first, then search
{
    SELECT ?company_name WHERE {
        BIND(ggf:SLM-CSV(...) AS ?g)
        GRAPH ?g {
            ?row ex:company_name ?company_name .
            ?row ex:sector ?sector .
        }
        FILTER(?sector = "Artificial Intelligence")  # ← Filter first
    }
    LIMIT 3
}
BIND(ggf:SLM-WEBSEARCH(...) AS ?web)
```

### 3. Truncate Text for LLM
```sparql
# Don't send entire article to LLM
BIND(CONCAT(
    "Extract info: ",
    SUBSTR(?long_text, 1, 500),  # ← Only first 500 chars
    ". Return JSON-LD..."
) AS ?prompt)
```

---

## 🔧 Configuration

### Web Search Setup

Edit `config.ini`:
```ini
[Associations]
SLM-WEBSEARCH = SPARQLLM.udf.websearch

[Requests]
# DuckDuckGo (default, no API key needed)
WEBSEARCH_ENGINE = duckduckgo

# Or Google (requires API key)
WEBSEARCH_ENGINE = google
GOOGLE_API_KEY = your-key
GOOGLE_CX = your-cx
```

### LLM Extraction Setup

**Option 1: Groq (Recommended)**
```bash
export GROQ_API_KEY="gsk_..."
# Use SLM-LLMGRAPH in queries (auto-detects Groq)
```

**Option 2: Ollama (Local)**
```bash
ollama serve
ollama pull qwen2.5:7b
# Use SLM-LLMGRAPH_OLLAMA in queries
```

---

## 📝 Sample Questions

Try these questions with the demo:

**CSV Only:**
- "List all companies in the Artificial Intelligence sector"
- "Which companies are headquartered in San Francisco?"
- "Show companies founded between 2000 and 2010"

**CSV + Web:**
- "Find recent news about Tesla"
- "Search for articles about NVIDIA"
- "Get latest information on Anthropic"

**CSV + Web + LLM:**
- "What funding have AI companies received recently?"
- "Find recent product launches from tech companies"
- "Extract partnership announcements for cloud companies"
- "Get recent CEO changes in tech companies"

---

## 🎓 Learning Objectives

After this demo, you'll understand:
1. ✅ How to combine CSV data with live web search
2. ✅ How to use LLM to extract structured data from unstructured text
3. ✅ How to optimize queries for performance (LIMIT, filtering)
4. ✅ How to handle multi-source data integration in SPARQL

---

## 🚧 Limitations

- **Web search is slow** (1-2 sec per query)
- **LLM extraction is slow** (2-5 sec per call)
- **Results vary** (depends on search results and LLM)
- **Rate limits** (Groq free tier: 30 req/min)

**Best practices:**
- Use LIMIT to reduce API calls
- Filter CSV data before searching
- Test with small datasets first

---

## 📚 Related Demos

- **company/** - Multi-CSV demo (employees + departments)
- **serial_killers/** - Single CSV with LLM analysis

---

**Status:** Ready to test! 🚀
**Last Updated:** 2025-11-21
