"""
Physical Compiler: Logical Plan → SPARQL Query

Translates JSON logical plans into executable SPARQL queries with GGF calls.
Uses topological sort to order steps based on dependencies.
"""

import json
from collections import deque
from pathlib import Path
from typing import Dict, List, Set, Tuple

from jsonschema import validate, ValidationError

from SPARQLLM.catalog import load_catalog, find_ggfs_by_alias


class CompilationError(Exception):
    """Raised when logical plan cannot be compiled to SPARQL"""
    pass


class PhysicalCompiler:
    """Compiles logical plans to SPARQL queries"""

    def __init__(self):
        """Initialize compiler with GGF catalog"""
        self.catalog = load_catalog()
        self.schema = self._load_schema()

    def _load_schema(self) -> dict:
        """Load JSON schema for logical plans"""
        schema_path = Path(__file__).parent / "schema" / "logical_plan.json"
        with open(schema_path, 'r') as f:
            return json.load(f)

    def compile(self, logical_plan: dict) -> str:
        """
        Compile logical plan to SPARQL query.

        Args:
            logical_plan: Dict conforming to logical_plan.json schema

        Returns:
            str: Valid SPARQL query

        Raises:
            CompilationError: If plan is invalid or cannot be compiled
        """
        # Validate plan against schema
        try:
            validate(instance=logical_plan, schema=self.schema)
        except ValidationError as e:
            raise CompilationError(f"Invalid logical plan: {e.message}")

        # Validate GGFs exist in catalog
        self._validate_ggfs(logical_plan)

        # Build dependency graph
        steps = logical_plan['steps']
        step_map = {step['id']: step for step in steps}
        dep_graph = self._build_dependency_graph(steps)

        # Topological sort
        sorted_step_ids = self.topological_sort(dep_graph)

        # Generate SPARQL components
        prefixes = self._generate_prefixes()
        binds = []
        graphs = []

        for step_id in sorted_step_ids:
            step = step_map[step_id]
            bind_clause, graph_clause = self._compile_step(step)
            if bind_clause:
                binds.append(bind_clause)
            if graph_clause:
                graphs.append(graph_clause)

        # Build output clause
        output = logical_plan['output']
        select_clause = self._build_select_clause(output)
        where_clauses = binds + graphs
        order_clause = self._build_order_clause(output.get('order_by', []))
        limit_clause = f"LIMIT {output['limit']}" if output.get('limit') else ''

        # Assemble query
        query = f"""{prefixes}

{select_clause} WHERE {{
{self._indent_clauses(where_clauses)}
}}
{order_clause}
{limit_clause}"""

        return query.strip()

    def _validate_ggfs(self, plan: dict):
        """Validate that all GGFs exist in catalog"""
        for step in plan['steps']:
            ggf_name = step['ggf']['name']
            ggf_info = find_ggfs_by_alias(ggf_name)
            if ggf_info is None:
                raise CompilationError(f"Unknown GGF: {ggf_name}")

    def _build_dependency_graph(self, steps: List[dict]) -> Dict[str, Set[str]]:
        """
        Build dependency graph from steps.

        Returns:
            Dict mapping step_id to set of step_ids it depends on
        """
        graph = {}
        for step in steps:
            step_id = step['id']
            deps = set(step.get('depends_on', []))
            graph[step_id] = deps
        return graph

    def topological_sort(self, dep_graph: Dict[str, Set[str]]) -> List[str]:
        """
        Topological sort using Kahn's algorithm.

        Args:
            dep_graph: Dict mapping node → set of nodes it depends ON

        Returns:
            List of step IDs in execution order

        Raises:
            CompilationError: If circular dependency detected
        """
        # Calculate in-degrees (how many dependencies each node has)
        in_degree = {node: len(deps) for node, deps in dep_graph.items()}

        # Find nodes with no dependencies (in-degree == 0)
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            # For each other node, check if this node was a dependency
            for other_node, deps in dep_graph.items():
                if node in deps:
                    in_degree[other_node] -= 1
                    if in_degree[other_node] == 0:
                        queue.append(other_node)

        if len(result) != len(dep_graph):
            raise CompilationError("Circular dependency detected in plan")

        return result

    def _compile_step(self, step: dict) -> Tuple[str, str]:
        """
        Generate BIND + GRAPH clauses for a single step.

        Returns:
            (bind_clause, graph_clause)
        """
        ggf = step['ggf']
        operation = step['operation']
        bindings = step.get('bindings', {})
        filters = step.get('filters', [])

        # Generate BIND clause (GGF invocation)
        bind_clause = self._generate_bind(step['id'], ggf)

        # Generate GRAPH clause (pattern matching)
        graph_clause = self._generate_graph(step['id'], operation, bindings, filters)

        return bind_clause, graph_clause

    def _generate_bind(self, step_id: str, ggf: dict) -> str:
        """Generate BIND clause for GGF invocation"""
        ggf_name = ggf['name']
        args = ggf['args']

        # Format arguments
        arg_strs = []
        for key, value in args.items():
            if isinstance(value, str):
                # Check if it's a SPARQL variable reference
                if value.startswith('?'):
                    arg_strs.append(value)
                else:
                    # String literal
                    arg_strs.append(f'"{value}"')
            elif isinstance(value, bool):
                arg_strs.append(str(value).lower())
            elif isinstance(value, (int, float)):
                arg_strs.append(str(value))
            else:
                # Complex object - serialize to JSON string
                arg_strs.append(f'"{json.dumps(value)}"')

        args_str = ', '.join(arg_strs)
        graph_var = f"?{step_id}Graph"

        return f"BIND(ggf:{ggf_name}({args_str}) AS {graph_var})"

    def _generate_graph(self, step_id: str, operation: str, bindings: dict, filters: List[str]) -> str:
        """Generate GRAPH clause with pattern matching"""
        graph_var = f"?{step_id}Graph"

        # Build triple patterns based on operation type and bindings
        patterns = []

        if operation == "read_filesystem":
            # Filesystem operations typically return file/directory metadata
            if bindings:
                for semantic_name, sparql_var in bindings.items():
                    if 'file' in semantic_name.lower() or 'path' in semantic_name.lower():
                        patterns.append(f"?item schema:contentUrl {sparql_var} .")
                    elif 'content' in semantic_name.lower():
                        patterns.append(f"?item schema:text {sparql_var} .")
                    else:
                        patterns.append(f"?item schema:value {sparql_var} .")
            else:
                patterns.append("?item ?p ?o .")

        elif operation == "llm_extract":
            # LLM extraction returns structured data (often JSON-LD)
            if bindings:
                for semantic_name, sparql_var in bindings.items():
                    # Try to infer property from semantic name
                    if 'name' in semantic_name.lower():
                        patterns.append(f"?entity schema:name {sparql_var} .")
                    elif 'date' in semantic_name.lower():
                        patterns.append(f"?entity schema:startDate {sparql_var} .")
                    elif 'description' in semantic_name.lower():
                        patterns.append(f"?entity schema:description {sparql_var} .")
                    else:
                        patterns.append(f"?entity schema:{semantic_name} {sparql_var} .")
            else:
                patterns.append("?entity ?p ?o .")

        elif operation in ["web_search", "vector_search"]:
            # Search operations return results with titles, URLs, snippets
            if bindings:
                for semantic_name, sparql_var in bindings.items():
                    if 'title' in semantic_name.lower():
                        patterns.append(f"?result schema:name {sparql_var} .")
                    elif 'url' in semantic_name.lower():
                        patterns.append(f"?result schema:url {sparql_var} .")
                    elif 'snippet' in semantic_name.lower() or 'description' in semantic_name.lower():
                        patterns.append(f"?result schema:description {sparql_var} .")
                    else:
                        patterns.append(f"?result schema:{semantic_name} {sparql_var} .")
            else:
                patterns.append("?result ?p ?o .")

        elif operation == "graph_operation":
            # Generic graph operations
            if bindings:
                for semantic_name, sparql_var in bindings.items():
                    patterns.append(f"?s schema:{semantic_name} {sparql_var} .")
            else:
                patterns.append("?s ?p ?o .")

        else:
            # Default pattern for unknown operations
            if bindings:
                for semantic_name, sparql_var in bindings.items():
                    patterns.append(f"?item schema:{semantic_name} {sparql_var} .")
            else:
                patterns.append("?item ?p ?o .")

        # Add filters
        filter_clauses = [f"FILTER({f})" for f in filters]

        # Combine patterns
        all_clauses = patterns + filter_clauses
        clauses_str = '\n        '.join(all_clauses)

        return f"""GRAPH {graph_var} {{
        {clauses_str}
    }}"""

    def _generate_prefixes(self) -> str:
        """Generate standard SPARQL prefixes"""
        return """PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
PREFIX schema: <https://schema.org/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"""

    def _build_select_clause(self, output: dict) -> str:
        """Build SELECT clause from output specification"""
        distinct = 'DISTINCT ' if output.get('distinct', False) else ''
        vars_str = ' '.join(f'?{v}' for v in output['variables'])
        return f"SELECT {distinct}{vars_str}"

    def _build_order_clause(self, order_specs: List[dict]) -> str:
        """Build ORDER BY clause"""
        if not order_specs:
            return ''

        order_items = []
        for spec in order_specs:
            var = spec['variable']
            direction = spec.get('order', 'ASC')
            order_items.append(f'{direction}(?{var})')

        return f"ORDER BY {' '.join(order_items)}"

    def _indent_clauses(self, clauses: List[str]) -> str:
        """Indent and join clauses for WHERE block"""
        indented = []
        for clause in clauses:
            if '\n' in clause:
                # Multi-line clause (GRAPH block)
                indented.append('    ' + clause.replace('\n', '\n    '))
            else:
                # Single-line clause (BIND)
                indented.append('    ' + clause)
        return '\n\n'.join(indented)
