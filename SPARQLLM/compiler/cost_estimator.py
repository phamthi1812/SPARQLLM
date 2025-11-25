"""
Cost Estimator: Predict Query Execution Cost

Estimates latency, token consumption, and monetary cost from logical plans.
Uses GGF catalog metadata and dependency analysis to predict execution time.
"""

from typing import Dict, List, Optional, Set

from SPARQLLM.catalog import find_ggfs_by_alias


class CostEstimator:
    """Estimate query execution cost from logical plan"""

    def __init__(self):
        """Initialize with GGF catalog"""
        pass  # Catalog loaded on-demand via find_ggfs_by_alias

    def estimate(self, logical_plan: dict) -> Dict:
        """
        Estimate cost for a logical plan.

        Args:
            logical_plan: Dict conforming to logical_plan.json schema

        Returns:
            Dict with:
                - latency_ms: Estimated P50 latency in milliseconds
                - tokens: Total token consumption (LLM calls only)
                - api_calls: Number of external API calls
                - parallel_groups: List of step sets that can run in parallel
                - cost_category: "low", "medium", or "high"
        """
        steps = logical_plan['steps']

        # Build dependency graph
        deps = self._build_dependency_graph(steps)

        # Identify parallel execution opportunities
        parallel_groups = self.identify_parallel_groups(logical_plan)

        # Calculate costs
        total_tokens = 0
        api_calls = 0
        step_costs = {}

        for step in steps:
            ggf_name = step['ggf']['name']
            metadata = self._get_ggf_metadata(ggf_name)

            step_id = step['id']
            latency = metadata.get('latency_ms', 100)
            step_costs[step_id] = latency

            # Count tokens
            if metadata.get('tokens'):
                total_tokens += metadata['tokens']

            # Count API calls (LLM, web, MCP)
            data_sources = metadata.get('data_sources', [])
            if any(src in ['llm', 'web', 'mcp', 'sql', 'vector'] for src in data_sources):
                api_calls += 1

        # Calculate total latency considering parallelism
        total_latency = self._calculate_latency_with_parallelism(
            step_costs, parallel_groups
        )

        # Estimate monetary cost (Groq pricing: ~$0.10 per 1M tokens)
        cost_usd = (total_tokens / 1_000_000) * 0.10

        # Categorize cost
        cost_category = self._categorize_cost(total_latency, total_tokens, api_calls)

        return {
            'latency_ms': total_latency,
            'tokens': total_tokens,
            'api_calls': api_calls,
            'cost_usd': cost_usd,
            'parallel_groups': [list(g) for g in parallel_groups],
            'cost_category': cost_category
        }

    def _build_dependency_graph(self, steps: List[dict]) -> Dict[str, Set[str]]:
        """Build dependency graph from steps"""
        graph = {}
        for step in steps:
            step_id = step['id']
            deps = set(step.get('depends_on', []))
            graph[step_id] = deps
        return graph

    def identify_parallel_groups(self, logical_plan: dict) -> List[Set[str]]:
        """
        Identify sets of steps that can execute in parallel.

        Returns:
            List of sets, where each set contains step IDs that can run concurrently
        """
        steps = logical_plan['steps']
        deps = self._build_dependency_graph(steps)

        # Group steps by dependency level (topological layers)
        levels = []
        processed = set()

        while len(processed) < len(deps):
            # Find steps whose dependencies are all satisfied
            current_level = set()
            for step_id, dependencies in deps.items():
                if step_id not in processed and dependencies.issubset(processed):
                    current_level.add(step_id)

            if not current_level:
                # No progress - circular dependency (should be caught by compiler)
                break

            levels.append(current_level)
            processed.update(current_level)

        # Filter out single-step levels (no parallelism opportunity)
        parallel_groups = [level for level in levels if len(level) > 1]

        return parallel_groups

    def _calculate_latency_with_parallelism(
        self,
        step_costs: Dict[str, float],
        parallel_groups: List[Set[str]]
    ) -> float:
        """
        Calculate total latency accounting for parallel execution.

        For parallel groups, use max latency instead of sum.
        """
        # Identify which steps are in parallel groups
        parallel_steps = set()
        for group in parallel_groups:
            parallel_steps.update(group)

        # Calculate cost
        total_latency = 0.0

        # Add cost of non-parallel steps
        for step_id, latency in step_costs.items():
            if step_id not in parallel_steps:
                total_latency += latency

        # Add cost of parallel groups (max within each group)
        for group in parallel_groups:
            group_latencies = [step_costs[step_id] for step_id in group]
            total_latency += max(group_latencies)

        return total_latency

    def _get_ggf_metadata(self, ggf_name: str) -> Dict:
        """Get metadata for GGF from catalog"""
        metadata = find_ggfs_by_alias(ggf_name)
        if metadata is None:
            # Fallback defaults if GGF not in catalog
            return {
                'latency_ms': 100,
                'tokens': 0,
                'data_sources': ['filesystem']
            }

        # Convert catalog format to metadata dict
        result = {
            'latency_ms': metadata.get('latency_ms', 100),
            'data_sources': []
        }

        if metadata.get('tokens'):
            result['tokens'] = metadata['tokens']

        return result

    def _categorize_cost(self, latency_ms: float, tokens: int, api_calls: int) -> str:
        """
        Categorize query cost as low/medium/high.

        Criteria:
            - Low: <500ms, <100 tokens, ≤1 API call
            - High: >5000ms OR >2000 tokens OR >5 API calls
            - Medium: everything else
        """
        if latency_ms < 500 and tokens < 100 and api_calls <= 1:
            return "low"
        elif latency_ms > 5000 or tokens > 2000 or api_calls > 5:
            return "high"
        else:
            return "medium"
