#!/bin/bash
# Test script for advanced demo

cd /Users/e23e889b/Documents/2025/2025_11/SPARQLLM

echo "Testing Advanced Demo with Ollama"
echo "=================================="
echo ""
echo "Question: Find employees whose salary is above the average salary in their department"
echo ""

# Run with Ollama (option 1)
echo "1" | python demo/company/demo_advanced.py << EOF
Find employees whose salary is above the average salary in their department
quit
EOF
