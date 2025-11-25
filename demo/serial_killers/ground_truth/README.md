# Ground Truth Queries - Serial Killers Demo

This directory contains validated ground truth queries for evaluating the accuracy of LLM-generated queries in the serial killers demo.

## Purpose

These queries serve as:
1. **Baseline for accuracy evaluation** - Compare LLM-generated queries against proven correct queries
2. **Demo validation** - Ensure dataset and GGFs work correctly
3. **Performance benchmarks** - Measure query execution time
4. **Test suite** - Automated testing for regression

## Query Inventory

| ID | Question | Category | Complexity | Avg Time | Rows |
|----|----------|----------|------------|----------|------|
| gt_01 | Top 10 serial killers with most victims | Pure CSV | Simple | ~4s | 10 |
| gt_02 | Count serial killers by decade | Pure CSV | GROUP BY | ~4s | 16 |
| gt_03 | Countries with most serial killers | Pure CSV | GROUP BY | ~4s | 15 |
| gt_04 | US serial killers in 1970s | Pure CSV | FILTER | ~4s | 11 |
| gt_05 | Serial killers with 50+ victims | Pure CSV | FILTER | ~4s | 25 |

## Test Results (2025-11-21)

**Run**: `python run_ground_truth.py`

### Results Summary

✅ **All queries execute successfully**
- Total Queries: 5
- Success Rate: 100%
- Average Execution Time: 3.9s
- Total Test Time: ~20s

### Validated Outputs

#### GT-01: Top Victims
```
name                          country                        victim_min  victim_max
Murder Incorporated           United States                     400.0      1000.0
The Skin Hunters              Poland                              5.0       620.0
Charles Cullen                United States                      29.0       400.0
Pedro López                   Colombia, Peru, Ecuador           110.0       300.0
...
```
✅ Returns exactly 10 rows ordered by victim_max DESC

#### GT-02: Decade Count
```
decade   count
1820s    1
1830s    3
1840s    5
1850s    9
...
```
✅ Returns 16 decades with proper aggregation

#### GT-03: Country Count
```
country          count
United States    247
United Kingdom   51
Germany          27
...
```
✅ Returns top 15 countries ordered by count DESC

#### GT-04: US 1970s
```
name                  decade  country        victim_min  victim_max
Angelo Buono Jr.      1970s   United States     10.0       12.0
...
```
✅ Returns 11 US serial killers from 1970s

#### GT-05: High Victims
```
name                  country          victim_min  victim_max  decade
Murder Incorporated   United States       400.0      1000.0    1930s
...
```
✅ Returns 25 serial killers with victim_min > 50

## Usage

### Run All Tests
```bash
cd demo/serial_killers
python run_ground_truth.py
```

### Run Single Query
```bash
source venv312_new/bin/activate
slm-run -c config.ini -f ground_truth/gt_01_top_victims.sparql
```

### Check Results
```bash
ls -la ground_truth/results/
cat ground_truth/results/summary_report.json
```

## Files

- `gt_*.sparql` - Ground truth SPARQL queries
- `run_ground_truth.py` - Test runner script
- `results/` - Query results and metadata
  - `gt_*_result.csv` - Query output (DataFrame)
  - `gt_*_metadata.json` - Execution metadata (time, rows, validation)
  - `summary_report.json` - Overall test summary

## Accuracy Evaluation Process

### Step 1: Generate Test Query
User asks: "Who are the top 10 serial killers with the most victims?"

LLM generates JSON plan → Compiler produces SPARQL

### Step 2: Execute Both Queries
- Ground truth query (gt_01): Known correct
- Generated query: From LLM pipeline

### Step 3: Compare Results
Compare DataFrames:
- **Exact match**: 100% accuracy
- **Partial match**: Calculate similarity score
- **Different**: Analyze discrepancies

### Step 4: Score Calculation
```python
accuracy_score = {
    'row_match': len(intersection) / len(union),
    'column_match': matching_columns / total_columns,
    'order_match': top_k_overlap(k=10),
    'semantic_match': llm_equivalence_check()
}
```

## Expected Accuracy Targets

| Query Type | Target Accuracy | Notes |
|------------|-----------------|-------|
| Simple SELECT | 95%+ | Basic filtering, sorting |
| GROUP BY | 90%+ | Aggregation queries |
| Complex JOIN | 85%+ | Multi-step patterns |
| LLM Hybrid | 80%+ | Semantic variation expected |

## Known Issues

1. **OPTIONAL columns** - Some columns may be NULL, affecting parsing
2. **ORDER BY** - Ties may result in different orderings
3. **GROUP BY** - Aggregation counts should match exactly
4. **FILTER** - String matching case-sensitivity

## Future Ground Truth Queries

Planned additions:
- **gt_06**: Serial killers active > 20 years (duration calculation)
- **gt_07**: Methods extraction with LLM (CSV + LLM hybrid)
- **gt_08**: Wikipedia summaries for top killers (CSV + Web)
- **gt_09**: Geographical patterns by decade (Complex aggregation)
- **gt_10**: Similarity analysis (Graph algorithms)

## Maintenance

Ground truth queries should be:
1. **Reviewed** - Manually verified for correctness
2. **Updated** - When dataset changes
3. **Extended** - Add new queries as demo evolves
4. **Documented** - Clear expected behavior

## References

- Dataset: `../data/serial_killers_clean.csv` (757 rows)
- Demo Questions: `../DEMO_QUESTIONS.md`
- Query Generator: `../../query_generator.py`
- Physical Compiler: `../../../SPARQLLM/compiler/physical_compiler.py`

---

**Last Updated**: 2025-11-21
**Test Status**: ✅ All Passing
**Dataset Version**: serial_killers_clean.csv (757 rows, 11 columns)
