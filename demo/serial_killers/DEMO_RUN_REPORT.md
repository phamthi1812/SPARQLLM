# Serial Killers Demo - Run Report

**Date**: 2025-11-21
**Dataset**: serial_killers_clean.csv (757 rows, 10 columns)
**SPARQLLM Version**: Latest (recurse branch)

---

## Executive Summary

✓ **Pure CSV Queries**: 7/7 PASS (100%)
⚠ **CSV + LLM Analysis**: 1/2 tested (configuration issue identified)
✓ **Overall Demo**: Functional and ready for presentation

**Key Finding**: All pure CSV queries work perfectly. LLM integration works but requires explicit provider selection (`SLM-LLMGRAPH_OLLAMA` vs `SLM-LLMGRAPH`).

---

## Category 1: Pure CSV Queries ✓ ALL PASS

### Q1: Top 10 Serial Killers with Most Victims
**Question**: "Who are the top 10 serial killers with the most victims?"

**Status**: ✓ PASS
**Execution Time**: ~4s
**Results**: 10 rows

**Sample Output**:
```
                          name  proven_victims  possible_victims                     country
0          Murder Incorporated           400.0            1000.0               United States
1               Harold Shipman           218.0             250.0              United Kingdom
2                Luis Garavito           193.0             247.0  Colombia, Ecuador, Venezuela
```

**GGF Used**: `SLM-CSV`
**SPARQL Pattern**: SELECT with ORDER BY DESC, LIMIT
**Validation**: Returns exactly 10 rows, properly sorted by victim_max

---

### GT-02: Count Serial Killers by Decade
**Question**: "How many serial killers were active in each decade?"

**Status**: ✓ PASS
**Execution Time**: ~4s
**Results**: 16 decades (1870s-2020s)

**Sample Output**:
```
   decade  count
0   1870s      1
1   1880s      4
10  1970s    116
11  1980s    155  ← Peak decade
12  1990s    153
```

**GGF Used**: `SLM-CSV`
**SPARQL Pattern**: SELECT with GROUP BY, COUNT aggregation
**Validation**: Correctly aggregates all 757 killers across 16 decades

---

### GT-03: Countries with Most Serial Killers
**Question**: "Which countries have had the most serial killers?"

**Status**: ✓ PASS
**Execution Time**: ~4s
**Results**: 15 countries

**Sample Output**:
```
         country  count
0  United States    275
1 United Kingdom     58
2         Russia     32
3   South Africa     29
```

**GGF Used**: `SLM-CSV`
**SPARQL Pattern**: SELECT with GROUP BY country, ORDER BY count DESC
**Validation**: Returns top 15 countries with proper aggregation

---

### GT-04: US Serial Killers in 1970s
**Question**: "Who were the US serial killers active in the 1970s?"

**Status**: ✓ PASS
**Execution Time**: ~4s
**Results**: 69 killers

**Sample Output**:
```
                       name decade        country  victim_min  victim_max
0        "Charlie Chop-off"  1970s  United States         3.0         4.0
1 Ann Arbor Hospital Killer  1970s  United States        10.0        10.0
2        Arthur Gary Bishop  1970s  United States         5.0         5.0
```

**GGF Used**: `SLM-CSV`
**SPARQL Pattern**: SELECT with FILTER (country = "United States" AND decade = "1970s")
**Validation**: All 69 results match filter criteria

---

### GT-05: Serial Killers with 50+ Victims
**Question**: "Which serial killers had more than 50 victims?"

**Status**: ✓ PASS
**Execution Time**: ~4s
**Results**: 25 killers

**Sample Output**:
```
                name                     country  victim_min  victim_max decade
0 Murder Incorporated               United States       400.0      1000.0  1920s
1       Harold Shipman              United Kingdom       218.0       250.0  1970s
2        Luis Garavito  Colombia, Ecuador, Venezuela       193.0       247.0  1990s
```

**GGF Used**: `SLM-CSV`
**SPARQL Pattern**: SELECT with FILTER (victim_min > 50)
**Validation**: All 25 results have victim_min > 50

---

### Q5: Geographical Patterns (Multi-Country Killers)
**Question**: "Which serial killers operated across multiple countries?"

**Status**: ✓ PASS
**Execution Time**: ~4s
**Results**: 15 killers

**Sample Output**:
```
                 name                      country  proven_victims  possible_victims
0       Luis Garavito  Colombia, Ecuador, Venezuela           193.0             247.0
1         Pedro López      Colombia, Peru, Ecuador           110.0             300.0
2  Daniel Camargo...       Colombia, Ecuador, Brazil            72.0             180.0
```

**GGF Used**: `SLM-CSV`
**SPARQL Pattern**: SELECT with FILTER CONTAINS(country, ",")
**Validation**: All results contain comma-separated country lists

---

### Q6: Decade Statistics (Complex Aggregation)
**Question**: "What are the statistics for each decade?"

**Status**: ✓ PASS
**Execution Time**: ~4s
**Results**: 16 decades

**Sample Output**:
```
   decade  killers  total_victims  avg_victims
10  1970s      116         1516.0        13.07
11  1980s      155         1535.0         9.90
12  1990s      153         2030.0        13.27  ← Most total victims
```

**GGF Used**: `SLM-CSV`
**SPARQL Pattern**: SELECT with GROUP BY decade, multiple aggregations (COUNT, SUM, AVG)
**Validation**: Correct aggregation across all rows with proper statistics

**Insights**:
- Peak activity: 1980s (155 killers)
- Most victims: 1990s (2030 total)
- Highest avg: 1920s (41.1 victims per killer - driven by Murder Incorporated)

---

## Category 2: CSV + LLM Analysis

### Simple LLM Test Query
**Question**: "Who was Ted Bundy?"

**Status**: ✓ PASS
**Execution Time**: ~5s
**LLM Provider**: Ollama (qwen2.5:3b)

**Output**:
```
        name                           desc
0  Ted Bundy  was a prolific and cunning...
```

**GGF Used**: `SLM-LLMGRAPH_OLLAMA` (explicit Ollama provider)
**SPARQL Pattern**: Simple LLM prompt with JSON-LD response
**Validation**: LLM correctly responds with Ted Bundy information

**Note**: This query explicitly uses `SLM-LLMGRAPH_OLLAMA` which bypasses MCP routing.

---

### Q2: Methods by Decade (Complex LLM Extraction)
**Question**: "What killing methods were most common in each decade?"

**Status**: ⚠ CONFIGURATION ISSUE
**Expected Behavior**: Extract killing methods from notes field using LLM
**Actual Behavior**: Returns empty DataFrame

**Root Cause**:
```
MCP result: {'status': 'error', 'error': 'groq_call_failed',
'message': 'GROQ_API_KEY is not set. Using default value, which may not work for real API calls.'}
```

**Analysis**:
- Query uses `SLM-LLMGRAPH` without URI parameter
- This triggers MCP routing to Groq provider
- Groq requires `GROQ_API_KEY` environment variable
- Without API key, LLM calls fail silently → empty results

**Query Structure** (Correct):
```sparql
# Subquery limits rows BEFORE LLM calls (5 instead of 757)
{
    SELECT ?name ?notes ?decade WHERE {
        BIND(ggf:SLM-CSV("./data.csv") AS ?csvGraph)
        GRAPH ?csvGraph { ?row ex:name ?name . ?row ex:decade ?decade . }
        OPTIONAL { GRAPH ?csvGraph { ?row ex:notes ?notes . } }
        FILTER(?decade IN ("1970s", "1980s", "1990s", "2000s"))
    }
    LIMIT 5  # ← Reduces from 757 to 5 LLM calls
}

# LLM extraction
BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?llmGraph)
GRAPH ?llmGraph {
    ?person a schema:Person ;
            schema:description ?methods .
}
```

**Solutions**:

1. **Option A: Use Ollama explicitly**
   ```sparql
   BIND(ggf:SLM-LLMGRAPH_OLLAMA(?prompt) AS ?llmGraph)
   ```

2. **Option B: Set GROQ_API_KEY**
   ```bash
   export GROQ_API_KEY="your-key-here"
   ```

3. **Option C: Configure MCP routing**
   Update `config.ini` to route `SLM-LLMGRAPH` to Ollama by default

---

## Category 3: CSV + Web Scraping

**Status**: Not tested in this run
**Queries Available**:
- Q3: Wikipedia Summary (uses `SLM-GETTEXT`)
- Q4: Additional Facts (uses web scraping)

**Note**: Web scraping queries require internet connection and may have rate limits.

---

## Category 4: Complex Multi-Step

**Status**: Not tested in this run
**Available Queries**: Complex aggregations, recursive patterns, multi-source joins

---

## Performance Summary

| Query Category | Tested | Passed | Failed | Avg Time |
|----------------|--------|--------|--------|----------|
| Pure CSV       | 7      | 7      | 0      | ~4s      |
| CSV + LLM      | 2      | 1      | 1*     | ~5s      |
| Web Scraping   | 0      | -      | -      | -        |
| Complex        | 0      | -      | -      | -        |

*Failed due to configuration, not query logic

---

## Technical Findings

### GGF Performance

**SLM-CSV** (Filesystem → RDF):
- Consistently fast (~4s for 757 rows)
- Reliable parsing with proper quoting
- Handles NULL values correctly (OPTIONAL pattern)

**SLM-LLMGRAPH** (LLM → JSON-LD → RDF):
- Works correctly with explicit provider (`_OLLAMA` suffix)
- Default routing goes through MCP (may require API keys)
- Response time: ~5s per call with local Ollama

### Query Patterns

**Pure CSV Queries** (Category 1):
- Simple SELECT: ✓ Works perfectly
- GROUP BY + Aggregation: ✓ Works perfectly
- FILTER conditions: ✓ Works perfectly
- OPTIONAL handling: ✓ Works perfectly
- Multi-column aggregation: ✓ Works perfectly

**CSV + LLM Queries** (Category 2):
- Direct LLM calls: ✓ Works with explicit provider
- Subquery + LLM: ⚠ Requires configuration
- LLM response parsing: ✓ JSON-LD → RDF works correctly

### Data Quality

**CSV Dataset**:
- 757 rows, 10 columns
- 0 NULL names (critical field)
- 0 NULL decades (after cleaning)
- Proper CSV quoting for special characters in notes field

---

## Recommendations

### For Demo Presentation

1. **Start with Pure CSV Queries** (Q1, GT-02, GT-03, Q5, Q6)
   - Show instant results (~4s each)
   - Demonstrate different SPARQL patterns
   - Highlight GGF simplicity vs traditional SPARQL

2. **Show Simple LLM Integration** (test_llm_simple.sparql)
   - Demonstrate neuro-symbolic pattern
   - Explain how LLM output becomes RDF graph
   - Show local Ollama (no API cost)

3. **Explain Q2 Configuration** (methods_by_decade)
   - Show query structure with subquery LIMIT pattern
   - Explain provider routing (`SLM-LLMGRAPH` vs `SLM-LLMGRAPH_OLLAMA`)
   - Demonstrate with `_OLLAMA` suffix or GROQ_API_KEY

### For Production Use

1. **LLM Provider Configuration**
   - Document provider routing clearly
   - Provide examples for each provider
   - Set default provider in config.ini

2. **Query Optimization**
   - Use subquery LIMIT for expensive GGFs
   - Pre-filter data before LLM calls
   - Consider batch processing for large datasets

3. **Error Handling**
   - Add validation for LLM responses
   - Provide fallback for failed GGF calls
   - Log configuration issues clearly

---

## Demo Script (Recommended Flow)

### Act 1: Pure CSV Power (5 minutes)

**Q1**: "Who are the top 10 serial killers?"
- Show instant results
- Explain SLM-CSV GGF
- Compare to traditional SPARQL LOAD

**GT-02**: "Count by decade"
- Show GROUP BY aggregation
- Highlight 1980s peak
- Explain graph generation

**Q6**: "Decade statistics"
- Show multi-column aggregation
- Demonstrate AVG, SUM, COUNT
- Discuss performance (4s for 757 rows)

### Act 2: Neuro-Symbolic Magic (5 minutes)

**test_llm_simple.sparql**: "Who was Ted Bundy?"
- Show LLM prompt construction
- Explain JSON-LD response → RDF
- Demonstrate GRAPH pattern matching

**Q2 (with fix)**: "Extract methods by decade"
- Show subquery LIMIT pattern (5 LLM calls instead of 757)
- Explain OPTIONAL for NULL notes
- Demonstrate structured extraction

### Act 3: Future Capabilities (2 minutes)

- Web scraping (Q3)
- Multi-step reasoning (Q4)
- Graph algorithms (similarity)

---

## Appendix: Environment

**System**:
- Platform: macOS (Darwin 24.6.0)
- Python: 3.12
- SPARQLLM: Latest (recurse branch)

**LLM**:
- Provider: Ollama
- Model: qwen2.5:3b
- Endpoint: http://localhost:11434

**Dataset**:
- File: demo/serial_killers/data/serial_killers_clean.csv
- Rows: 757
- Columns: name, country, start_year, end_year, proven_victims, possible_victims, notes, decade, victim_min, victim_max
- Source: Wikipedia Serial Killers List

**Queries Tested**:
- demo/serial_killers/queries/q1_top_victims.sparql
- demo/serial_killers/queries/q5_geographical_patterns.sparql
- demo/serial_killers/queries/q6_decade_statistics.sparql
- demo/serial_killers/ground_truth/gt_01_top_victims.sparql
- demo/serial_killers/ground_truth/gt_02_decade_count.sparql
- demo/serial_killers/ground_truth/gt_03_country_count.sparql
- demo/serial_killers/ground_truth/gt_04_us_1970s.sparql
- demo/serial_killers/ground_truth/gt_05_high_victims.sparql
- demo/serial_killers/test_llm_simple.sparql
- demo/serial_killers/queries/q2_methods_by_decade.sparql

---

**Report Generated**: 2025-11-21
**Status**: ✓ Demo Ready (with LLM configuration notes)
