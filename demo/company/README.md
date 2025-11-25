# Multi-CSV Demo: LLM-Generated SPARQL-GGF Queries

This demo showcases **LLM's ability to automatically generate SPARQL-GGF queries** that intelligently work with multiple CSV files, including:

✅ **Source Selection**: LLM knows which CSV file contains which information
✅ **JOIN Operations**: Automatically joins data across CSV files
✅ **UNION Queries**: Combines data from multiple sources
✅ **Data Integration**: Understands relationships and foreign keys
✅ **Smart Filtering**: Applies filters from the correct source

---

## Overview

**Data Sources:**
- `employees.csv` - 30 employees with salary, position, performance data
- `departments.csv` - 6 departments with budget, location, manager info

**Key Relationship:** `employees.department_id` ↔ `departments.department_id`

---

## Quick Start

### 1. Prerequisites

```bash
# Activate virtual environment
source venv312_new/bin/activate

# Install dependencies (if not already installed)
pip install openai

# Option A: Start Ollama (local, free)
ollama serve
ollama pull qwen2.5:7b

# Option B: Set OpenAI API key (cloud)
export OPENAI_API_KEY="your-key-here"
```

### 2. Run the Demo

```bash
python demo/company/demo_multi_csv.py
```

### 3. Ask Questions

The LLM will generate SPARQL-GGF queries automatically:

```
Question: What are the top 5 highest paid employees?
→ LLM generates query using employees.csv only

Question: Show employees in the Engineering department
→ LLM generates JOIN query between employees and departments

Question: What is the average salary in each department?
→ LLM generates JOIN + GROUP BY + AVG aggregation

Question: What are all the unique office locations?
→ LLM generates UNION query combining both CSVs
```

---

## Demo Capabilities

### 1. Single-Source Queries

**Question:** "What are the top 5 highest paid employees?"

**LLM Understanding:**
- Recognizes salary information is in `employees.csv`
- No need to load `departments.csv`

**Generated Query:**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?name ?salary WHERE {
    BIND(ggf:SLM-CSV("./demo/company/data/employees.csv") AS ?empGraph)

    GRAPH ?empGraph {
        ?row ex:name ?name .
        ?row ex:salary ?salary .
    }
}
ORDER BY DESC(?salary)
LIMIT 5
```

---

### 2. JOIN Queries (Multi-Source)

**Question:** "Show employees in the Engineering department with their salaries"

**LLM Understanding:**
- Employee names and salaries are in `employees.csv`
- Department names are in `departments.csv`
- Must JOIN on `department_id`

**Generated Query:**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?employee_name ?salary ?department_name WHERE {
    BIND(ggf:SLM-CSV("./demo/company/data/employees.csv") AS ?empGraph)
    BIND(ggf:SLM-CSV("./demo/company/data/departments.csv") AS ?deptGraph)

    # Get employee data
    GRAPH ?empGraph {
        ?emp ex:name ?employee_name .
        ?emp ex:salary ?salary .
        ?emp ex:department_id ?dept_id .
    }

    # JOIN with department data
    GRAPH ?deptGraph {
        ?dept ex:department_id ?dept_id .
        ?dept ex:department_name ?department_name .
    }

    # Filter for Engineering
    FILTER(?department_name = "Engineering")
}
ORDER BY DESC(?salary)
```

---

### 3. Aggregation with JOIN

**Question:** "What is the average salary in each department?"

**LLM Understanding:**
- Needs salaries from `employees.csv`
- Needs department names from `departments.csv`
- Must JOIN and then GROUP BY

**Generated Query:**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?department_name
       (COUNT(?name) AS ?employee_count)
       (AVG(?salary) AS ?avg_salary)
WHERE {
    BIND(ggf:SLM-CSV("./demo/company/data/employees.csv") AS ?empGraph)
    BIND(ggf:SLM-CSV("./demo/company/data/departments.csv") AS ?deptGraph)

    GRAPH ?empGraph {
        ?emp ex:name ?name .
        ?emp ex:salary ?salary .
        ?emp ex:department_id ?dept_id .
    }

    GRAPH ?deptGraph {
        ?dept ex:department_id ?dept_id .
        ?dept ex:department_name ?department_name .
    }
}
GROUP BY ?department_name
ORDER BY DESC(?avg_salary)
```

---

### 4. UNION Queries

**Question:** "What are all the unique office locations across the company?"

**LLM Understanding:**
- Employees have locations
- Departments have locations
- Need to combine both with UNION

**Generated Query:**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT DISTINCT ?location WHERE {
    {
        BIND(ggf:SLM-CSV("./demo/company/data/employees.csv") AS ?empGraph)
        GRAPH ?empGraph {
            ?row ex:location ?location .
        }
    }
    UNION
    {
        BIND(ggf:SLM-CSV("./demo/company/data/departments.csv") AS ?deptGraph)
        GRAPH ?deptGraph {
            ?row ex:location ?location .
        }
    }
}
ORDER BY ?location
```

---

### 5. Complex Multi-Source Integration

**Question:** "Find employees with performance rating above 4.5 in departments with budget over 1.5 million"

**LLM Understanding:**
- Performance rating is in `employees.csv`
- Budget is in `departments.csv`
- Must JOIN and apply filters from both sources

**Generated Query:**
```sparql
PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>

SELECT ?employee_name ?position ?performance_rating
       ?department_name ?dept_budget
WHERE {
    BIND(ggf:SLM-CSV("./demo/company/data/employees.csv") AS ?empGraph)
    BIND(ggf:SLM-CSV("./demo/company/data/departments.csv") AS ?deptGraph)

    GRAPH ?empGraph {
        ?emp ex:name ?employee_name .
        ?emp ex:position ?position .
        ?emp ex:performance_rating ?performance_rating .
        ?emp ex:department_id ?dept_id .
    }

    GRAPH ?deptGraph {
        ?dept ex:department_id ?dept_id .
        ?dept ex:department_name ?department_name .
        ?dept ex:budget ?dept_budget .
    }

    # Filters from both sources
    FILTER(?performance_rating > 4.5)
    FILTER(?dept_budget > 1500000)
}
ORDER BY DESC(?performance_rating)
```

---

## Sample Questions

See `sample_questions.txt` for a comprehensive list of test questions covering:

**Category 1:** Single-source queries (no JOIN)
**Category 2:** Basic JOIN queries
**Category 3:** Aggregation with JOIN
**Category 4:** UNION queries
**Category 5:** Multi-condition cross-source queries
**Category 6:** Data integration tests

### Quick Test Questions

```bash
# Test 1: Single source
What are the top 5 highest paid employees?

# Test 2: JOIN
Show employees in the Engineering department with their salaries

# Test 3: Aggregation
What is the average salary in each department?

# Test 4: UNION
What are all the unique office locations?

# Test 5: Complex integration
Find employees with performance rating above 4.5 in departments with budget over 1.5 million

# Test 6: Manager lookup
Show me all department managers with their employee details
```

---

## How It Works

### 1. Schema Awareness

The LLM is provided with schema information (`schema.txt`) that includes:
- Available CSV files and their columns
- Data relationships (foreign keys)
- JOIN patterns
- Source selection rules

### 2. Query Generation Pipeline

```
User Question
    ↓
LLM with Schema Context
    ↓
SPARQL-GGF Query Generation
    ↓
Query Execution (slm-run)
    ↓
Results Display
```

### 3. LLM Decision Making

The LLM must decide:
- **Which CSV(s) to load**: employees.csv, departments.csv, or both?
- **How to JOIN**: What's the join key? (department_id)
- **Where to filter**: Apply filters in correct GRAPH pattern
- **Aggregation strategy**: GROUP BY which columns?
- **Result ordering**: ORDER BY which fields?

---

## File Structure

```
demo/company/
├── README.md                    # This file
├── demo_multi_csv.py           # Main demo script
├── schema.txt                   # Schema information for LLM
├── sample_questions.txt         # Test questions
└── data/
    ├── employees.csv            # Employee data (30 rows)
    └── departments.csv          # Department data (6 rows)
```

---

## Data Schema

### employees.csv
```
employee_id, name, department_id, salary, hire_date, position,
location, email, years_experience, performance_rating
```
**30 employees** across 6 departments

### departments.csv
```
department_id, department_name, location, budget, manager_id,
established_year, floor, building, description
```
**6 departments**: Engineering, Marketing, Finance, HR, Sales, Operations

**Relationship:** `employees.department_id` = `departments.department_id`

---

## Configuration

### Using Ollama (Local, Free)

```bash
# Start Ollama
ollama serve

# Pull model
ollama pull qwen2.5:7b

# Run demo (select option 1)
python demo/company/demo_multi_csv.py
```

### Using OpenAI (Cloud)

```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Run demo (select option 2)
python demo/company/demo_multi_csv.py
```

---

## Expected Results

### Query: "What are the top 5 highest paid employees?"

```
                name  salary
0  Wendy Edwards  155000
1     Liam Garcia  145000
2  Victor Evans   135000
3     Emma Davis   125000
4  Carol White    110000
```

### Query: "What is the average salary in each department?"

```
     department_name  employee_count  avg_salary
0  Finance                       4   98500.00
1  Engineering                   6   92500.00
2  Sales                         5   89600.00
3  Marketing                     5   78800.00
4  Operations                    3   77000.00
5  Human Resources               3   78333.33
```

---

## Extending the Demo

### Add a Third CSV File

1. Create new CSV (e.g., `projects.csv`)
2. Update `schema.txt` with new schema info
3. Add relationship information
4. Test with questions requiring 3-way JOINs

### Add LLM-Based Analysis

Combine CSV queries with LLM analysis:

```sparql
# After querying employees + departments
BIND(CONCAT("Analyze this employee: ", ?name,
            " in ", ?dept_name,
            " with salary ", STR(?salary)) AS ?prompt)

BIND(ggf:SLM-LLMGRAPH_OLLAMA(?prompt) AS ?llmGraph)

GRAPH ?llmGraph {
    ?analysis schema:description ?insight .
}
```

---

## Troubleshooting

### Issue: LLM doesn't generate valid SPARQL

**Solution:** Check that schema.txt is being loaded correctly. The demo provides the schema in the system prompt.

### Issue: Query returns empty results

**Possible causes:**
- Column name mismatch (check CSV headers)
- Wrong file paths
- JOIN condition incorrect

**Debug:**
```bash
# Check CSV structure
head -2 demo/company/data/employees.csv
head -2 demo/company/data/departments.csv

# Run query manually
slm-run -c config.ini -q "your query here"
```

### Issue: Ollama connection refused

**Solution:**
```bash
# Make sure Ollama is running
ollama serve

# Check connection
curl http://localhost:11434/api/tags
```

---

## Success Criteria

✅ LLM correctly identifies which CSV contains which data
✅ LLM generates proper JOIN conditions using department_id
✅ LLM applies filters to the correct source (employee vs department filters)
✅ LLM generates UNION queries when combining data
✅ LLM uses aggregations (COUNT, AVG, SUM) with GROUP BY
✅ LLM generates efficient queries (doesn't load unnecessary CSVs)

---

## Next Steps

1. **Run the demo**: `python demo/company/demo_multi_csv.py`
2. **Try sample questions** from `sample_questions.txt`
3. **Inspect generated queries** to see how LLM understands the schema
4. **Modify CSVs** to add your own data
5. **Add more data sources** (projects, customers, etc.)

---

## Related Documentation

- Main SPARQLLM README: `../../README.md`
- Serial Killers Demo (single CSV): `../serial_killers/README.md`
- Query Generator: `../../demo/query_generator.py`
- SPARQL-GGF Syntax: See system prompt in `demo_multi_csv.py`

---

**Last Updated:** 2025-11-21
