# Shared CEO Query Issue

**Date:** 2025-11-21
**Question:** "what companies have the same ceo and who are they, do they have social account?"

## Expected Data

CSV has 2 companies with same CEO:
```
Tesla,Automotive,Austin,2003,Elon Musk,...
SpaceX,Aerospace,Hawthorne,2002,Elon Musk,...
```

## Problem

**Result:** Only Tesla appeared (missing SpaceX)

## Root Cause: Invalid SPARQL Structure

**LLM-Generated Query (WRONG):**
```sparql
SELECT ?ceo ?company_name WHERE {
    BIND(ggf:SLM-CSV(...) AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:company_name ?company_name .
        ?row ex:ceo ?ceo .
    }
}
GROUP BY ?ceo
HAVING (COUNT(DISTINCT ?company_name) > 1)
```

**Issue:** Selects `?company_name` but only groups by `?ceo`
- In standard SPARQL, non-aggregated variables must be in GROUP BY
- Engine returns arbitrary company (Tesla) instead of all companies

## Corrected Query

```sparql
SELECT ?ceo ?company_name WHERE {
    # Get all companies
    BIND(ggf:SLM-CSV(...) AS ?csvGraph)
    GRAPH ?csvGraph {
        ?row ex:company_name ?company_name .
        ?row ex:ceo ?ceo .
    }

    # Filter: only CEOs with multiple companies
    {
        SELECT ?ceo WHERE {
            BIND(ggf:SLM-CSV(...) AS ?csvGraph2)
            GRAPH ?csvGraph2 {
                ?row2 ex:company_name ?comp .
                ?row2 ex:ceo ?ceo .
            }
        }
        GROUP BY ?ceo
        HAVING (COUNT(?comp) > 1)
    }
}
```

**Result:** ✅ Both SpaceX and Tesla returned

## Additional Issue: Social Account Extraction

Same problem as product extraction:
- Extracts `schema:description` = page descriptions
- Not actual social media URLs
- Needs LLM extraction or structured parsing

## Status

- ❌ Query structure: Invalid GROUP BY usage
- ✅ Corrected query: Works properly
- ❌ Social accounts: Extracts descriptions, not URLs
