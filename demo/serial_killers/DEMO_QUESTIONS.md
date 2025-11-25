# Demo Questions for Serial Killers Dataset

This document contains interesting questions for the Serial Killers demo that showcase different SPARQLLM capabilities.

## Category 1: Pure CSV Queries (No LLM/Web)
*Fast queries using only CSV data - demonstrates basic GGF functionality*

### Simple Aggregation
1. **Who are the top 10 serial killers with the most victims?**
   - Uses: SLM-CSV
   - Columns: name, victim_min, victim_max
   - Operations: ORDER BY DESC, LIMIT

2. **How many serial killers operated in each decade?**
   - Uses: SLM-CSV
   - Columns: decade
   - Operations: GROUP BY, COUNT

3. **Which countries have the most serial killers in the dataset?**
   - Uses: SLM-CSV
   - Columns: country
   - Operations: GROUP BY, COUNT, ORDER BY

### Filtering & Search
4. **List all serial killers from the United States active in the 1970s**
   - Uses: SLM-CSV
   - Columns: name, country, decade
   - Operations: FILTER (country, decade)

5. **Find serial killers with more than 50 confirmed victims**
   - Uses: SLM-CSV
   - Columns: name, victim_min, country
   - Operations: FILTER (victim_min > 50)

6. **Which serial killers were active for more than 20 years?**
   - Uses: SLM-CSV
   - Columns: name, year_start, year_end
   - Operations: FILTER (year_end - year_start > 20)

## Category 2: CSV + LLM Analysis
*Hybrid queries combining structured data with LLM extraction*

### Text Extraction from Notes
7. **What killing methods were most common in each decade?**
   - Uses: SLM-CSV, SLM-LLMGRAPH
   - LLM Task: Extract methods from notes field
   - Analysis: Group by decade, aggregate methods

8. **Extract the motivations of serial killers from the 1980s**
   - Uses: SLM-CSV, SLM-LLMGRAPH
   - LLM Task: Identify psychological motivations from notes
   - Operations: FILTER (decade = 1980s), extract motives

9. **Which serial killers used poison as a weapon?**
   - Uses: SLM-CSV, SLM-LLMGRAPH
   - LLM Task: Identify weapons/tools from notes
   - Operations: FILTER methods containing "poison"

10. **Identify serial killers who targeted specific victim demographics**
    - Uses: SLM-CSV, SLM-LLMGRAPH
    - LLM Task: Extract victim demographics (gender, age, occupation)
    - Analysis: Group by demographics

### Pattern Recognition
11. **Find similarities between serial killers from the same country**
    - Uses: SLM-CSV, SLM-LLMGRAPH
    - LLM Task: Compare methods, motivations, victim types
    - Analysis: Group by country, identify patterns

12. **What psychological profiles emerge from serial killers with 30+ victims?**
    - Uses: SLM-CSV, SLM-LLMGRAPH
    - LLM Task: Extract behavioral traits from notes
    - Operations: FILTER (victim_min > 30), cluster traits

## Category 3: CSV + Web Scraping
*Combining dataset with external web sources*

### Wikipedia Integration
13. **Get detailed Wikipedia summaries for the top 5 deadliest serial killers**
    - Uses: SLM-CSV, SLM-GETTEXT or SLM-BS4
    - Web Source: Wikipedia URLs from dataset
    - Operations: ORDER BY victim_max DESC, LIMIT 5, fetch Wikipedia

14. **Compare dataset information with Wikipedia articles for accuracy**
    - Uses: SLM-CSV, SLM-GETTEXT, SLM-LLMGRAPH
    - LLM Task: Compare structured data vs web content
    - Analysis: Identify discrepancies

15. **Extract additional facts about serial killers not in the CSV**
    - Uses: SLM-CSV, SLM-GETTEXT, SLM-LLMGRAPH
    - LLM Task: Extract new information from Wikipedia
    - Output: Enhanced dataset with web-scraped facts

### Cross-Reference Research
16. **Find news articles about specific serial killers using web search**
    - Uses: SLM-CSV, SLM-SEARCH (DuckDuckGo via MCP)
    - Operations: Generate search queries, fetch results
    - Analysis: Summarize media coverage

## Category 4: Complex Multi-Step Queries
*Advanced queries combining multiple GGFs*

### Comparative Analysis
17. **Compare killing methods between American and European serial killers**
    - Uses: SLM-CSV, SLM-LLMGRAPH
    - Steps:
      1. Filter by continent (US vs Europe)
      2. Extract methods from notes (LLM)
      3. Compare method frequencies
      4. Identify regional patterns

18. **How did serial killer profiles change over decades?**
    - Uses: SLM-CSV, SLM-LLMGRAPH
    - Steps:
      1. Group by decade
      2. Extract behavioral traits (LLM)
      3. Analyze evolution of methods, motivations
      4. Identify historical trends

### Anomaly Detection
19. **Find outliers: serial killers with unusual characteristics**
    - Uses: SLM-CSV, SLM-LLMGRAPH
    - LLM Task: Identify unusual methods, victim types, durations
    - Statistical: Compare to dataset averages

20. **Which serial killers had the longest active periods?**
    - Uses: SLM-CSV
    - Columns: name, year_start, year_end, country
    - Operations: Calculate duration, ORDER BY DESC

## Category 5: Interactive Demo Scenarios
*Natural language questions for showcasing full pipeline*

### Simple Questions (Entry Level)
21. **"Who killed the most people?"**
    - Expected GGF: SLM-CSV
    - Expected Output: Top killer with victim count

22. **"How many serial killers were active in the 1990s?"**
    - Expected GGF: SLM-CSV
    - Expected Output: COUNT grouped by decade

23. **"List serial killers from Japan"**
    - Expected GGF: SLM-CSV
    - Expected Output: Filtered list by country

### Medium Complexity
24. **"What were the most common killing methods in the 1970s?"**
    - Expected GGFs: SLM-CSV, SLM-LLMGRAPH
    - Expected Output: Methods extracted from notes, grouped/counted

25. **"Tell me about Ted Bundy's crimes"**
    - Expected GGFs: SLM-CSV, SLM-GETTEXT (Wikipedia), SLM-LLMGRAPH
    - Expected Output: Summary combining CSV data + web scraping

26. **"Which countries had the most serial killers in the 1980s?"**
    - Expected GGF: SLM-CSV
    - Expected Output: Countries grouped/counted with decade filter

### Advanced Questions
27. **"Compare the methods used by serial killers in the US versus Europe across different decades"**
    - Expected GGFs: SLM-CSV, SLM-LLMGRAPH
    - Expected Steps:
      1. Filter by continent and decade
      2. Extract methods (LLM)
      3. Group and compare
      4. Identify trends

28. **"Find serial killers who used similar methods to Ted Bundy"**
    - Expected GGFs: SLM-CSV, SLM-LLMGRAPH
    - Expected Steps:
      1. Get Ted Bundy's methods
      2. Extract methods from all killers (LLM)
      3. Compare/rank similarity
      4. Return top matches

29. **"Create a timeline of serial killer activity by decade with victim counts"**
    - Expected GGF: SLM-CSV
    - Expected Output: Temporal aggregation with statistics

30. **"Which serial killers had the longest time between first and last victim?"**
    - Expected GGF: SLM-CSV
    - Expected Output: Duration calculation, ORDER BY DESC

## Category 6: Testing Edge Cases
*Questions to validate error handling and robustness*

### Missing Data
31. **"Find serial killers with unknown victim counts"**
    - Tests: NULL handling in victim_min/victim_max

32. **"Which serial killers don't have Wikipedia URLs?"**
    - Tests: OPTIONAL patterns, NULL detection

### Ambiguous Questions
33. **"Who was the worst serial killer?"**
    - Tests: Ambiguity resolution (worst = most victims? Most brutal? Longest active?)

34. **"Tell me about serial killers"**
    - Tests: Overly broad query handling

### Data Quality
35. **"Are there any duplicate entries in the dataset?"**
    - Tests: Data validation, DISTINCT operations

36. **"Find inconsistencies between victim_min and victim_max"**
    - Tests: Data quality checks (min > max)

## Recommended Demo Flow

### Phase 1: Warm-up (Pure CSV)
- Question 1: "Who are the top 10 serial killers with the most victims?"
- Question 4: "List all serial killers from the United States active in the 1970s"

### Phase 2: LLM Integration
- Question 7: "What killing methods were most common in each decade?"
- Question 8: "Extract the motivations of serial killers from the 1980s"

### Phase 3: Web Enhancement
- Question 13: "Get detailed Wikipedia summaries for the top 5 deadliest serial killers"

### Phase 4: Complex Analysis
- Question 17: "Compare killing methods between American and European serial killers"
- Question 18: "How did serial killer profiles change over decades?"

### Phase 5: Natural Language (Interactive)
- Let user ask free-form questions
- Showcase LLM → JSON → SPARQL pipeline

## Notes for Demo

- **Fast queries** (Category 1): Use for quick wins, show instant results
- **LLM queries** (Category 2): Explain 5-10 second delay, show value of analysis
- **Web queries** (Category 3): Demonstrate data enrichment beyond CSV
- **Complex queries** (Category 4): Showcase SPARQLLM's compositional power
- **Interactive** (Category 5): Let audience drive the demo

## Expected Performance

| Category | Avg Time | LLM Calls | Web Requests |
|----------|----------|-----------|--------------|
| Pure CSV | <1s      | 0         | 0            |
| CSV+LLM  | 5-15s    | 5-10      | 0            |
| CSV+Web  | 3-10s    | 0-1       | 1-5          |
| Complex  | 15-30s   | 10-20     | 0-5          |

---

**Dataset**: 757 serial killers with columns: name, country, years_active, victim_min, victim_max, decade, notes, wikipedia_url

**Generated**: 2025-11-21
**SPARQLLM Version**: 0.1.0
**Demo Branch**: llm-sparql-compiler
