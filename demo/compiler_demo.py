#!/usr/bin/env python3
"""
SPARQLLM Compiler Demo

Demonstrates the two-stage compilation process:
1. Logical Plan (JSON) → Physical Plan (SPARQL)
2. Cost Estimation
3. Natural Language Explanation
"""

import json
from SPARQLLM.compiler import PhysicalCompiler, CostEstimator, Explainer


# Example logical plan: Read files → Extract events with LLM → Return sorted results
EXAMPLE_PLAN = {
    "version": "1.0",
    "steps": [
        {
            "id": "step1",
            "operation": "read_filesystem",
            "ggf": {
                "name": "SLM-READDIR",
                "args": {"path": "./data", "filter": "*.txt"}
            },
            "bindings": {"fileUri": "?fileUri"}
        },
        {
            "id": "step2",
            "operation": "read_filesystem",
            "ggf": {
                "name": "SLM-READFILE",
                "args": {"file": "?fileUri"}
            },
            "depends_on": ["step1"],
            "bindings": {"content": "?content"}
        },
        {
            "id": "step3",
            "operation": "llm_extract",
            "ggf": {
                "name": "LLM",
                "args": {
                    "prompt": "Extract event name and date from this text: ?content"
                }
            },
            "depends_on": ["step2"],
            "bindings": {"eventName": "?eventName", "eventDate": "?eventDate"}
        }
    ],
    "output": {
        "variables": ["eventName", "eventDate"],
        "distinct": True,
        "order_by": [{"variable": "eventDate", "order": "ASC"}]
    }
}


def main():
    print("=== SPARQLLM Two-Stage Compiler Demo ===\n")

    # Initialize compiler components
    compiler = PhysicalCompiler()
    estimator = CostEstimator()
    explainer = Explainer()

    # Display logical plan
    print("1. Logical Plan (JSON):")
    print(json.dumps(EXAMPLE_PLAN, indent=2))
    print()

    # Compile to SPARQL
    print("2. Physical Plan (SPARQL):")
    try:
        sparql = compiler.compile(EXAMPLE_PLAN)
        print(sparql)
        print()
    except Exception as e:
        print(f"Compilation error: {e}")
        return

    # Estimate cost
    print("3. Cost Estimate:")
    cost = estimator.estimate(EXAMPLE_PLAN)
    print(f"   Latency: {cost['latency_ms']}ms ({cost['latency_ms']/1000:.2f}s)")
    print(f"   Tokens: {cost['tokens']}")
    print(f"   API Calls: {cost['api_calls']}")
    print(f"   Cost (USD): ${cost['cost_usd']:.4f}")
    print(f"   Category: {cost['cost_category']}")
    if cost['parallel_groups']:
        print(f"   Parallel Groups: {cost['parallel_groups']}")
    print()

    # Generate explanation
    print("4. Natural Language Explanation:")
    explanation = explainer.explain(EXAMPLE_PLAN, cost)
    print(f"   {explanation}")
    print()

    # Additional examples
    print("=== Additional Examples ===\n")

    # Simple filesystem query
    simple_plan = {
        "version": "1.0",
        "steps": [
            {
                "id": "step1",
                "operation": "read_filesystem",
                "ggf": {
                    "name": "SLM-CSV",
                    "args": {"file": "./data/cities.csv"}
                },
                "bindings": {"city": "?city", "population": "?pop"}
            }
        ],
        "output": {
            "variables": ["city", "pop"],
            "order_by": [{"variable": "pop", "order": "DESC"}],
            "limit": 10
        }
    }

    print("Example: Simple CSV Query")
    print(explainer.explain(simple_plan, estimator.estimate(simple_plan)))
    print()

    # Web search query
    search_plan = {
        "version": "1.0",
        "steps": [
            {
                "id": "step1",
                "operation": "web_search",
                "ggf": {
                    "name": "SEARCH",
                    "args": {"query": "SPARQL query optimization techniques"}
                },
                "bindings": {"title": "?title", "url": "?url"}
            }
        ],
        "output": {
            "variables": ["title", "url"],
            "limit": 5
        }
    }

    print("Example: Web Search Query")
    print(explainer.explain(search_plan, estimator.estimate(search_plan)))
    print()

    print("=== Demo Complete ===")


if __name__ == "__main__":
    main()
