#!/bin/bash

# Test runner for websearch + LLM integration tests
# Tests all combinations: SEARCH alone, CSV+SEARCH, SEARCH+LLM, Full pipeline

cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM

echo "========================================"
echo "Web Search + LLM Integration Tests"
echo "========================================"
echo ""

# Check if Ollama is running
echo "📋 Checking Ollama status..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "❌ Ollama is NOT running"
    echo "   Start it with: ollama serve"
    echo ""
fi

echo ""
echo "========================================"
echo "Test 1: Basic SEARCH function"
echo "========================================"
echo "Query: Direct web search for 'OpenAI GPT-4 2024'"
echo ""
python -m SPARQLLM.cli.slm demo/companies_news/test_queries/test_1_basic_search.sparql
echo ""
read -p "Press Enter to continue to Test 2..."

echo ""
echo "========================================"
echo "Test 2: CSV + SEARCH integration"
echo "========================================"
echo "Query: Load OpenAI from CSV, search for news"
echo ""
python -m SPARQLLM.cli.slm demo/companies_news/test_queries/test_2_csv_plus_search.sparql
echo ""
read -p "Press Enter to continue to Test 3..."

echo ""
echo "========================================"
echo "Test 3: SEARCH + LLM (Local Ollama)"
echo "========================================"
echo "Query: Search web, extract info with local LLM"
echo "⚠️  This will be slow (5-10 sec per LLM call)"
echo ""
python -m SPARQLLM.cli.slm demo/companies_news/test_queries/test_3_search_plus_llm_local.sparql
echo ""
read -p "Press Enter to continue to Test 4..."

echo ""
echo "========================================"
echo "Test 4: Full Pipeline (CSV + SEARCH + LLM)"
echo "========================================"
echo "Query: AI companies → search news → extract with LLM"
echo "⚠️  This will be VERY slow (multiple LLM calls)"
echo ""
python -m SPARQLLM.cli.slm demo/companies_news/test_queries/test_4_full_pipeline.sparql

echo ""
echo "========================================"
echo "✅ All tests completed!"
echo "========================================"
