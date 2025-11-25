"""
Natural Language Explainer: Logical Plan → Human-Readable Summary

Converts logical plans and cost estimates into 2-4 sentence explanations
for user confirmation before query execution.
"""

from typing import Dict, List, Optional


class Explainer:
    """Generate natural language explanations of logical plans"""

    def explain(self, logical_plan: dict, cost_estimate: Optional[Dict] = None) -> str:
        """
        Generate natural language explanation of query plan.

        Args:
            logical_plan: Dict conforming to logical_plan.json schema
            cost_estimate: Optional cost estimate from CostEstimator

        Returns:
            str: 2-4 sentence explanation suitable for user confirmation
        """
        steps = logical_plan['steps']
        output = logical_plan['output']

        # Build step descriptions
        step_descriptions = [self._describe_step(step) for step in steps]

        # Summarize query flow
        if len(step_descriptions) == 1:
            flow = step_descriptions[0]
        elif len(step_descriptions) == 2:
            flow = f"{step_descriptions[0]}, then {step_descriptions[1]}"
        else:
            first = step_descriptions[0]
            last = step_descriptions[-1]
            middle_count = len(step_descriptions) - 2
            if middle_count == 1:
                flow = f"{first}, process the data, then {last}"
            else:
                flow = f"{first}, perform {middle_count} intermediate steps, then {last}"

        # Build output description
        output_vars = output.get('variables', ['result'])
        # Ensure we have at least one variable
        if not output_vars:
            output_vars = ['result']

        if len(output_vars) == 1:
            var_list = output_vars[0]
        elif len(output_vars) == 2:
            var_list = f"{output_vars[0]} and {output_vars[1]}"
        else:
            var_list = f"{', '.join(output_vars[:-1])}, and {output_vars[-1]}"

        distinct_clause = " (unique values)" if output.get('distinct') else ""
        limit_clause = f" (up to {output['limit']} results)" if output.get('limit') else ""

        # Build explanation
        sentences = []

        # Sentence 1: What the query does
        sentences.append(f"This query will {flow}.")

        # Sentence 2: What it returns
        sentences.append(f"It will return {var_list}{distinct_clause}{limit_clause}.")

        # Sentence 3: Cost estimate (if provided)
        if cost_estimate:
            latency = cost_estimate['latency_ms']
            latency_str = f"{latency:.0f}ms" if latency < 1000 else f"{latency/1000:.1f}s"

            cost_parts = [f"~{latency_str}"]

            if cost_estimate['tokens'] > 0:
                tokens = cost_estimate['tokens']
                cost_usd = cost_estimate['cost_usd']
                cost_parts.append(f"{tokens} tokens (${cost_usd:.4f})")

            if cost_estimate['api_calls'] > 0:
                cost_parts.append(f"{cost_estimate['api_calls']} API calls")

            # Mention parallelism if present
            parallel_info = ""
            if cost_estimate.get('parallel_groups'):
                num_parallel = len(cost_estimate['parallel_groups'])
                parallel_info = f" with {num_parallel} parallel execution group{'s' if num_parallel > 1 else ''}"

            sentences.append(f"Estimated cost: {', '.join(cost_parts)}{parallel_info}.")

        return " ".join(sentences)

    def _describe_step(self, step: dict) -> str:
        """Convert a single step to natural language"""
        operation = step['operation']
        ggf = step['ggf']
        ggf_name = ggf['name']
        args = ggf['args']

        # Operation-specific descriptions
        if operation == "read_filesystem":
            if 'READDIR' in ggf_name:
                path = args.get('path', '...')
                return f"list files in {path}"
            elif 'READFILE' in ggf_name:
                file_arg = args.get('file', args.get('path', '...'))
                if isinstance(file_arg, str) and file_arg.startswith('?'):
                    return "read file contents"
                else:
                    return f"read {file_arg}"
            elif 'CSV' in ggf_name:
                return "parse CSV data"
            elif 'RDF' in ggf_name:
                return "load RDF data"
            else:
                return "access filesystem"

        elif operation == "llm_extract":
            prompt = args.get('prompt', '')
            if 'extract' in prompt.lower():
                return "extract structured data using LLM"
            elif 'summarize' in prompt.lower():
                return "summarize content using LLM"
            elif 'classify' in prompt.lower():
                return "classify content using LLM"
            else:
                return "process text with LLM"

        elif operation == "web_search":
            query = args.get('query', '...')
            if isinstance(query, str) and not query.startswith('?'):
                return f"search web for '{query}'"
            else:
                return "search the web"

        elif operation == "vector_search":
            query = args.get('query', args.get('text', '...'))
            if isinstance(query, str) and not query.startswith('?'):
                return f"find similar documents to '{query}'"
            else:
                return "perform vector similarity search"

        elif operation == "sql_query":
            return "query SQL database"

        elif operation == "join":
            return "join data from multiple sources"

        elif operation == "filter":
            return "filter results"

        elif operation == "aggregate":
            return "aggregate results"

        elif operation == "graph_operation":
            if 'RECURSE' in ggf_name:
                return "recursively traverse graph"
            elif 'MERGE' in ggf_name:
                return "merge multiple graphs"
            elif 'CONSTRUCT' in ggf_name:
                return "construct new graph"
            else:
                return "perform graph operation"

        else:
            # Fallback: use GGF name
            return f"execute {ggf_name}"
