# Using Groq for Multi-CSV Demo

**Groq is FASTER and has a FREE TIER!** 🚀

## Why Groq?

✅ **Very fast inference** (much faster than OpenAI)
✅ **Free tier** (no credit card required)
✅ **Better models** than small Ollama (llama-3.1-70b)
✅ **Better syntax following** than qwen2.5:7b

---

## Quick Setup (2 minutes)

### Step 1: Get Free Groq API Key

1. Go to: https://console.groq.com
2. Sign up (free, no credit card)
3. Go to API Keys section
4. Create new API key
5. Copy the key

### Step 2: Set Environment Variable

```bash
export GROQ_API_KEY="gsk_..."
```

### Step 3: Run Demo

```bash
python demo/company/demo_multi_csv_groq.py
```

Select option **1** for Groq (default).

---

## Available Groq Models

The demo uses **llama-3.1-70b-versatile** by default (best for code generation).

Other options:
- `llama-3.1-70b-versatile` - Best overall (default)
- `llama-3.1-8b-instant` - Faster, smaller
- `mixtral-8x7b-32768` - Good for long context

---

## Comparison

| Provider | Speed | Quality | Cost | Setup |
|----------|-------|---------|------|-------|
| **Groq** | ⚡⚡⚡ Very Fast | ✅ Excellent | 💰 Free | Easy |
| OpenAI | ⚡ Moderate | ✅✅ Best | 💰💰 Paid | Easy |
| Ollama | ⚡⚡ Fast | ❌ Poor (small models) | 💰 Free | Moderate |

---

## Test It

Try the UNION query that failed with Ollama:

```
Question: What are all the unique office locations?
```

**With Ollama qwen2.5:7b:** ❌ Syntax error (UNION outside WHERE)
**With Groq llama-3.1-70b:** ✅ Should work correctly!

---

## Example Session

```bash
$ export GROQ_API_KEY="gsk_..."
$ python demo/company/demo_multi_csv_groq.py

================================================================================
Multi-CSV Demo: LLM-Generated SPARQL-GGF Queries
================================================================================

Select LLM provider:
  1. Groq (Fast, Free Tier) [RECOMMENDED]
  2. OpenAI (GPT-4)
  3. Ollama (Local)

Provider [1/2/3]: 1
✓ Using Groq (llama-3.1-70b-versatile)
  Fast inference with free tier!

================================================================================
Enter questions (or 'quit' to exit)
Example questions:
  - What are the top 5 highest paid employees?
  - Show employees in the Engineering department
  - What is the average salary in each department?
  - What are all the unique office locations?
================================================================================

Question: What are all the unique office locations?

[... generates correct SPARQL with proper UNION syntax ...]
```

---

## Groq Features

✅ **Fast**: Inference in < 1 second
✅ **Accurate**: Follows SPARQL syntax better than small models
✅ **Free**: Generous free tier
✅ **Models**: llama-3.1-70b, mixtral-8x7b, etc.

---

## If You Get Rate Limited

Groq free tier limits:
- 30 requests/minute
- 14,400 requests/day

If you hit limits:
- Wait a minute
- Or use OpenAI
- Or use Ollama locally

---

## Advanced: Use Groq in Advanced Demo

For hard queries with subqueries:

```bash
# Copy the Groq support to advanced demo
cp demo/company/demo_multi_csv_groq.py demo/company/demo_advanced_groq.py

# Edit to use schema_advanced.txt instead of schema.txt
sed -i 's/schema.txt/schema_advanced.txt/g' demo/company/demo_advanced_groq.py

# Run
python demo/company/demo_advanced_groq.py
```

---

## Troubleshooting

### "GROQ_API_KEY not set"
```bash
export GROQ_API_KEY="your-key"
# Or add to ~/.bashrc or ~/.zshrc
```

### "Invalid API key"
- Check you copied the full key (starts with `gsk_`)
- Get new key at https://console.groq.com

### "Rate limit exceeded"
- Wait 60 seconds
- Groq free tier: 30 req/min, 14,400 req/day

---

## Summary

**Use Groq for:**
- ✅ Fast testing
- ✅ Better query generation than small Ollama models
- ✅ Free development

**Use OpenAI for:**
- Production deployments
- Maximum quality

**Use Ollama for:**
- Offline/air-gapped environments
- Privacy requirements

---

**Get started now:** https://console.groq.com 🚀
