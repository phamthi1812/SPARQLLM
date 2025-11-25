#!/usr/bin/env python3
"""
GGF Catalog Generator

Scans SPARQLLM/udf/ for Graph Generating Functions registered in config.ini.
Extracts metadata from:
- Docstrings (description)
- Type hints (signature)
- @ggf_metadata decorators (manual annotations)
- Module analysis (inferred data sources)

Outputs RDF catalog (Turtle format) to SPARQLLM/data/ggf-catalog.ttl

Usage:
    python -m SPARQLLM.tools.generate_ggf_catalog
"""

import ast
import hashlib
import importlib.util
import inspect
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from configparser import ConfigParser

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

# Namespaces
GGF = Namespace("http://ggf.org/")
SCHEMA = Namespace("https://schema.org/")

CATALOG_VERSION = "1.0.0"


class GGFCatalogGenerator:
    """Generate RDF catalog from GGF codebase"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: Path to config.ini (default: auto-detect from project root)
        """
        if config_path is None:
            # Auto-detect project root
            self.base_dir = Path(__file__).parent.parent.parent
            config_path = self.base_dir / "config.ini"
        else:
            self.base_dir = config_path.parent

        self.config_path = config_path
        self.config = ConfigParser()
        self.config.read(config_path)

    def generate(self) -> Graph:
        """
        Generate complete GGF catalog.

        Returns:
            RDFLib Graph with all GGF metadata
        """
        # Extract GGF aliases from config.ini
        aliases = self._extract_aliases()
        print(f"Found {len(aliases)} GGF aliases in config.ini")

        # Build catalog graph
        g = Graph()
        g.bind("ggf", GGF)
        g.bind("schema", SCHEMA)
        g.bind("rdfs", RDFS)

        # Add catalog metadata
        catalog_uri = GGF["catalog"]
        g.add((catalog_uri, GGF.catalogVersion, Literal(CATALOG_VERSION)))
        g.add((catalog_uri, GGF.generatedAt, Literal(datetime.utcnow(), datatype=XSD.dateTime)))

        # Process each GGF
        for alias, module_path in aliases.items():
            try:
                metadata = self._extract_ggf_metadata(alias, module_path)
                self._add_ggf_to_graph(g, alias, metadata)
            except Exception as e:
                print(f"Warning: Failed to process {alias}: {e}")
                continue

        return g

    def _extract_aliases(self) -> Dict[str, str]:
        """
        Extract GGF aliases from [Associations] section of config.ini

        Returns:
            Dict mapping alias name to Python module path
        """
        aliases = {}
        if 'Associations' in self.config:
            for alias, module_path in self.config['Associations'].items():
                # Clean up alias and module path, preserve case
                alias = alias.strip().upper()  # ConfigParser lowercases, so uppercase it
                module_path = module_path.strip()
                aliases[alias] = module_path
        return aliases

    def _extract_ggf_metadata(self, alias: str, module_path: str) -> Dict:
        """
        Extract metadata for a single GGF.

        Args:
            alias: GGF alias (e.g., "SLM-READFILE")
            module_path: Python module path (e.g., "SPARQLLM.udf.readfile.readhtmlfile")

        Returns:
            Dict with extracted metadata
        """
        metadata = {
            'alias': alias,
            'module_path': module_path
        }

        # Try to load the module and extract metadata from decorator
        try:
            parts = module_path.split('.')
            module_parts = parts[:-1]
            function_name = parts[-1]

            # Construct file path
            if module_parts[0] == "SPARQLLM":
                module_parts = module_parts[1:]
            module_file_path = "/".join(module_parts) + ".py"
            full_path = self.base_dir / "SPARQLLM" / module_file_path

            if full_path.exists():
                # Try to import and check for decorator
                spec = importlib.util.spec_from_file_location(parts[-2], full_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, function_name):
                        func = getattr(module, function_name)
                        if hasattr(func, '_ggf_metadata'):
                            metadata.update(func._ggf_metadata)

                # Extract docstring
                metadata['description'] = self._extract_docstring(full_path, function_name)
            else:
                print(f"  Module file not found: {full_path}")

        except Exception as e:
            print(f"  Could not load module {module_path}: {e}")

        # Infer data sources from module path and alias
        metadata['data_sources'] = self._infer_data_sources(alias, module_path)

        # Infer network requirement
        if "requires_network" not in metadata:
            network_sources = {"llm", "web", "mcp"}
            has_network_source = any(src in network_sources for src in metadata['data_sources'])
            metadata["requires_network"] = has_network_source

        # Set default latency based on data source (if not manually specified)
        if 'latency_ms' not in metadata and metadata['data_sources']:
            # Use first data source for default
            source = metadata['data_sources'][0]
            defaults = {
                'filesystem': 50,
                'llm': 1500,
                'web': 800,
                'vector': 200,
                'sql': 300,
                'mcp': 1000,
                'graph': 100
            }
            metadata['latency_ms'] = defaults.get(source, 100)

        # Set defaults
        if 'deterministic' not in metadata:
            # Non-deterministic if LLM or web-based
            metadata['deterministic'] = not any(src in ['llm', 'web'] for src in metadata['data_sources'])

        if 'cacheable' not in metadata:
            # LLM calls typically not cacheable
            metadata['cacheable'] = 'llm' not in metadata['data_sources']

        return metadata

    def _extract_docstring(self, file_path: Path, function_name: str) -> str:
        """Extract function docstring via AST parsing"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    docstring = ast.get_docstring(node)
                    if docstring:
                        # Clean up docstring (first line only)
                        return docstring.split('\n')[0].strip()
        except Exception:
            pass

        return f"Graph Generating Function: {function_name}"

    def _infer_data_sources(self, alias: str, module_path: str) -> List[str]:
        """
        Infer data sources from module path and alias.

        Returns:
            List of data source types (filesystem, llm, web, sql, vector, mcp, graph)
        """
        text_lower = (alias + " " + module_path).lower()
        text_module = module_path.lower()
        sources = []

        # Priority order: check most specific first

        # LLM (exclusive - if it's LLM, don't check other sources)
        if any(kw in text_module for kw in ["llmgraph", "llmollama", "llm_graph", "llm_text"]):
            sources.append("llm")
            return sources  # LLM is exclusive

        # MCP alias (exclusive check for alias module)
        if "mcp.alias" in module_path:
            sources.append("mcp")
            sources.append("llm")  # MCP aliases typically wrap LLM calls
            return sources

        # MCP tools
        if "mcp" in text_module and "mcp_tool" in text_module:
            sources.append("mcp")
            return sources

        # Filesystem (common patterns)
        if any(kw in text_module for kw in ["readfile", "readdir", "abspath", "mycsv", "read_rdf"]):
            sources.append("filesystem")

        # Web scraping
        if any(kw in text_module for kw in ["bs4", "uri2text", "gettext"]):
            sources.append("web")

        # Search (vector/keyword)
        if "faiss" in text_lower:
            sources.append("vector")
        elif "whoosh" in text_lower or "search" in text_lower:
            sources.append("web")  # Whoosh typically indexes web content

        # Graph operations
        if any(kw in text_module for kw in ["recurse", "construct", "slm_graph", "slm_merge", "cypher", "bfs"]):
            sources.append("graph")

        # SQL/Database
        if any(kw in text_lower for kw in ["sql", "postgres", "mysql", "database"]):
            sources.append("sql")

        # GitHub API
        if "github" in text_lower:
            sources.append("web")

        # Fallback: if nothing matched, assume filesystem
        if not sources:
            sources.append("filesystem")

        return sources

    def _add_ggf_to_graph(self, g: Graph, alias: str, metadata: Dict):
        """Add GGF metadata to RDF graph"""
        uri = GGF[alias]

        # Core properties
        g.add((uri, RDF.type, GGF.GraphGeneratingFunction))
        g.add((uri, RDFS.label, Literal(alias)))
        g.add((uri, GGF.modulePath, Literal(metadata['module_path'])))

        # Description
        if 'description' in metadata:
            g.add((uri, GGF.description, Literal(metadata['description'])))

        # Signature (if available)
        if 'signature' in metadata:
            g.add((uri, GGF.signature, Literal(metadata['signature'])))

        # Cost metadata
        if 'latency_ms' in metadata:
            g.add((uri, GGF.costLatencyMs, Literal(metadata['latency_ms'], datatype=XSD.decimal)))
        if 'tokens' in metadata:
            g.add((uri, GGF.costTokens, Literal(metadata['tokens'], datatype=XSD.integer)))
        if 'rate_limit' in metadata:
            g.add((uri, GGF.rateLimitPerHour, Literal(metadata['rate_limit'], datatype=XSD.integer)))

        # Capability metadata
        for source in metadata.get('data_sources', []):
            g.add((uri, GGF.accessesDataSource, Literal(source)))

        g.add((uri, GGF.deterministic, Literal(metadata.get('deterministic', False), datatype=XSD.boolean)))
        g.add((uri, GGF.cacheable, Literal(metadata.get('cacheable', True), datatype=XSD.boolean)))
        g.add((uri, GGF.requiresNetwork, Literal(metadata.get('requires_network', False), datatype=XSD.boolean)))

        # Configuration requirements
        if 'env_var' in metadata:
            g.add((uri, GGF.requiresEnvVar, Literal(metadata['env_var'])))
        if 'config_key' in metadata:
            g.add((uri, GGF.requiresConfig, Literal(metadata['config_key'])))

        # Documentation
        if 'example' in metadata:
            g.add((uri, GGF.exampleUsage, Literal(metadata['example'])))

        # MCP metadata
        if 'mcp_server' in metadata:
            g.add((uri, GGF.mcpServer, Literal(metadata['mcp_server'])))
        if 'mcp_tool' in metadata:
            g.add((uri, GGF.mcpTool, Literal(metadata['mcp_tool'])))


def main():
    """Generate GGF catalog and save to file"""
    generator = GGFCatalogGenerator()
    catalog = generator.generate()

    # Write to file
    output_path = generator.base_dir / "SPARQLLM" / "data" / "ggf-catalog.ttl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    catalog.serialize(destination=str(output_path), format="turtle")

    # Compute content hash
    content = catalog.serialize(format="turtle")
    h = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Stats
    num_triples = len(catalog)
    num_ggfs = len(list(catalog.subjects(RDF.type, GGF.GraphGeneratingFunction)))

    print(f"\nCatalog generated successfully!")
    print(f"  Output: {output_path}")
    print(f"  GGFs: {num_ggfs}")
    print(f"  Triples: {num_triples}")
    print(f"  Size: {len(content)} bytes")
    print(f"  Hash: {h}")


if __name__ == "__main__":
    main()
