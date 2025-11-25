"""
GGF Catalog Query API

Provides functions to query the GGF catalog programmatically.
Used by LLM query planner to discover available Graph Generating Functions.
"""

from pathlib import Path
from typing import Dict, List, Optional

from rdflib import Graph, Namespace

# Namespaces
GGF = Namespace("http://ggf.org/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

# Global catalog cache
_CATALOG = None


def load_catalog() -> Graph:
    """
    Load GGF catalog from disk (cached).

    Returns:
        RDFLib Graph with GGF metadata

    Raises:
        FileNotFoundError: If catalog file doesn't exist
    """
    global _CATALOG
    if _CATALOG is None:
        catalog_path = Path(__file__).parent.parent / "data" / "ggf-catalog.ttl"
        if not catalog_path.exists():
            raise FileNotFoundError(
                f"GGF catalog not found at {catalog_path}. "
                "Run: python -m SPARQLLM.tools.generate_ggf_catalog"
            )

        _CATALOG = Graph()
        _CATALOG.parse(catalog_path, format="turtle")
        _CATALOG.bind("ggf", GGF)

    return _CATALOG


def find_ggfs_by_alias(alias: str) -> Optional[Dict]:
    """
    Find GGF by exact alias match.

    Args:
        alias: GGF alias (e.g., "SLM-READFILE")

    Returns:
        Dict with GGF metadata or None if not found
    """
    g = load_catalog()
    query = f"""
    PREFIX ggf: <http://ggf.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?description ?modulePath ?latency ?tokens ?deterministic ?cacheable
    WHERE {{
        ?ggf a ggf:GraphGeneratingFunction ;
             rdfs:label "{alias}" .
        OPTIONAL {{ ?ggf ggf:description ?description }}
        OPTIONAL {{ ?ggf ggf:modulePath ?modulePath }}
        OPTIONAL {{ ?ggf ggf:costLatencyMs ?latency }}
        OPTIONAL {{ ?ggf ggf:costTokens ?tokens }}
        OPTIONAL {{ ?ggf ggf:deterministic ?deterministic }}
        OPTIONAL {{ ?ggf ggf:cacheable ?cacheable }}
    }}
    """

    results = list(g.query(query))
    if not results:
        return None

    row = results[0]
    return {
        'alias': alias,
        'description': str(row.description) if row.description else None,
        'module_path': str(row.modulePath) if row.modulePath else None,
        'latency_ms': float(row.latency) if row.latency else None,
        'tokens': int(row.tokens) if row.tokens else None,
        'deterministic': bool(row.deterministic) if row.deterministic else False,
        'cacheable': bool(row.cacheable) if row.cacheable else True
    }


def find_ggfs_by_source(source: str) -> List[Dict]:
    """
    Find all GGFs accessing a specific data source.

    Args:
        source: Data source type ("filesystem", "llm", "web", "sql", "vector", "mcp", "graph")

    Returns:
        List of dicts with GGF name, signature, and cost metadata
    """
    g = load_catalog()
    query = f"""
    PREFIX ggf: <http://ggf.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?name ?description ?latency ?tokens WHERE {{
        ?ggf a ggf:GraphGeneratingFunction ;
             rdfs:label ?name ;
             ggf:accessesDataSource "{source}" .
        OPTIONAL {{ ?ggf ggf:description ?description }}
        OPTIONAL {{ ?ggf ggf:costLatencyMs ?latency }}
        OPTIONAL {{ ?ggf ggf:costTokens ?tokens }}
    }}
    ORDER BY ?name
    """

    results = []
    for row in g.query(query):
        results.append({
            'name': str(row.name),
            'description': str(row.description) if row.description else None,
            'latency_ms': float(row.latency) if row.latency else None,
            'tokens': int(row.tokens) if row.tokens else None
        })

    return results


def find_ggfs_by_cost(max_latency_ms: Optional[int] = None, max_tokens: Optional[int] = None) -> List[Dict]:
    """
    Find GGFs matching cost constraints.

    Args:
        max_latency_ms: Maximum acceptable latency in milliseconds
        max_tokens: Maximum acceptable token consumption

    Returns:
        List of dicts with GGF name and cost metadata
    """
    g = load_catalog()

    # Build dynamic query based on constraints
    filters = []
    if max_latency_ms is not None:
        filters.append(f"?latency <= {max_latency_ms}")
    if max_tokens is not None:
        filters.append(f"?tokens <= {max_tokens}")

    filter_clause = f"FILTER ({' && '.join(filters)})" if filters else ""

    query = f"""
    PREFIX ggf: <http://ggf.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?name ?latency ?tokens WHERE {{
        ?ggf a ggf:GraphGeneratingFunction ;
             rdfs:label ?name .
        OPTIONAL {{ ?ggf ggf:costLatencyMs ?latency }}
        OPTIONAL {{ ?ggf ggf:costTokens ?tokens }}
        {filter_clause}
    }}
    ORDER BY ?latency ?tokens
    """

    results = []
    for row in g.query(query):
        results.append({
            'name': str(row.name),
            'latency_ms': float(row.latency) if row.latency else None,
            'tokens': int(row.tokens) if row.tokens else None
        })

    return results


def find_ggfs_by_network(requires_network: bool) -> List[Dict]:
    """
    Find GGFs by network requirement.

    Args:
        requires_network: True for network-based GGFs, False for local-only

    Returns:
        List of dicts with GGF name and data sources
    """
    g = load_catalog()
    query = f"""
    PREFIX ggf: <http://ggf.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?name (GROUP_CONCAT(DISTINCT ?source; separator=",") AS ?sources) WHERE {{
        ?ggf a ggf:GraphGeneratingFunction ;
             rdfs:label ?name ;
             ggf:requiresNetwork "{str(requires_network).lower()}"^^<http://www.w3.org/2001/XMLSchema#boolean> .
        OPTIONAL {{ ?ggf ggf:accessesDataSource ?source }}
    }}
    GROUP BY ?name
    ORDER BY ?name
    """

    results = []
    for row in g.query(query):
        sources = str(row.sources).split(',') if row.sources else []
        results.append({
            'name': str(row.name),
            'data_sources': sources,
            'requires_network': requires_network
        })

    return results


def find_ggfs_by_env_requirements() -> Dict[str, List[str]]:
    """
    Find all GGFs grouped by required environment variables.

    Returns:
        Dict mapping env var name to list of GGF aliases
    """
    g = load_catalog()
    query = """
    PREFIX ggf: <http://ggf.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?name ?envVar WHERE {
        ?ggf a ggf:GraphGeneratingFunction ;
             rdfs:label ?name ;
             ggf:requiresEnvVar ?envVar .
    }
    ORDER BY ?envVar ?name
    """

    env_map = {}
    for row in g.query(query):
        env_var = str(row.envVar)
        ggf_name = str(row.name)

        if env_var not in env_map:
            env_map[env_var] = []
        env_map[env_var].append(ggf_name)

    return env_map


def get_catalog_summary() -> Dict:
    """
    Get high-level catalog statistics.

    Returns:
        Dict with counts by data source, avg latency, etc.
    """
    g = load_catalog()

    # Count total GGFs
    total_query = """
    PREFIX ggf: <http://ggf.org/>
    SELECT (COUNT(DISTINCT ?ggf) AS ?cnt) WHERE {
        ?ggf a ggf:GraphGeneratingFunction .
    }
    """
    total = list(g.query(total_query))[0].cnt

    # Count by data source
    source_query = """
    PREFIX ggf: <http://ggf.org/>
    SELECT ?source (COUNT(DISTINCT ?ggf) AS ?cnt) WHERE {
        ?ggf a ggf:GraphGeneratingFunction ;
             ggf:accessesDataSource ?source .
    }
    GROUP BY ?source
    ORDER BY DESC(?cnt)
    """
    sources = {}
    for row in g.query(source_query):
        sources[str(row.source)] = int(row.cnt)

    # Network vs local
    network_query = """
    PREFIX ggf: <http://ggf.org/>
    SELECT ?requiresNetwork (COUNT(DISTINCT ?ggf) AS ?cnt) WHERE {
        ?ggf a ggf:GraphGeneratingFunction ;
             ggf:requiresNetwork ?requiresNetwork .
    }
    GROUP BY ?requiresNetwork
    """
    network_counts = {}
    for row in g.query(network_query):
        network_counts[bool(row.requiresNetwork)] = int(row.cnt)

    return {
        'total_ggfs': int(total),
        'by_data_source': sources,
        'network_required': network_counts.get(True, 0),
        'local_only': network_counts.get(False, 0)
    }
