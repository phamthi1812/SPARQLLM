"""
Phase 4 Tests: Resource Providers

Tests for store resource listing, reading, and URI templates.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import quote
from rdflib import Graph, URIRef, Literal, Namespace

from SPARQLLM.mcp.resources.store_resource import (
    list_store_resources,
    read_store_resource,
    extract_graph_name,
    extract_graph_description,
)
from SPARQLLM.udf.SPARQLLM import store, reset_store


RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
PROV = Namespace("http://www.w3.org/ns/prov#")
SCHEMA = Namespace("http://schema.org/")


@pytest.fixture(autouse=True)
def clean_store():
    """Reset store before and after each test."""
    reset_store()
    yield
    reset_store()


@pytest.fixture
def session_id():
    """Test session ID."""
    return "sess-test1234"


@pytest.fixture
def sample_graph():
    """Create a sample named graph in the store."""
    graph_uri = URIRef("urn:uuid:test-graph-123")
    g = store.get_context(graph_uri)

    # Add some sample triples
    EX = Namespace("http://example.org/")
    g.add((EX.subject1, EX.predicate1, Literal("value1")))
    g.add((EX.subject2, EX.predicate2, Literal("value2")))

    # Add metadata to the graph itself
    g.add((graph_uri, RDFS.label, Literal("Test Graph")))
    g.add((graph_uri, RDFS.comment, Literal("A test graph for unit testing")))

    return graph_uri


class TestListStoreResources:
    """Test resource listing functionality."""

    @pytest.mark.asyncio
    async def test_list_empty_store(self, session_id):
        """Test listing resources when store is empty."""
        resources = await list_store_resources(session_id)

        assert isinstance(resources, list)
        assert len(resources) == 0

    @pytest.mark.asyncio
    async def test_list_single_graph(self, session_id, sample_graph):
        """Test listing a single named graph."""
        resources = await list_store_resources(session_id)

        assert len(resources) == 1
        resource = resources[0]

        # Verify URI format (convert AnyUrl to str for comparison)
        expected_uri = f"store://{session_id}/graphs/{quote(str(sample_graph), safe='')}"
        assert str(resource.uri) == expected_uri

        # Verify metadata
        assert resource.name == "Test Graph"
        assert resource.description == "A test graph for unit testing"
        assert resource.mimeType == "application/ld+json"

    @pytest.mark.asyncio
    async def test_list_multiple_graphs(self, session_id):
        """Test listing multiple named graphs."""
        # Create 3 graphs
        graph_uris = []
        for i in range(3):
            graph_uri = URIRef(f"urn:uuid:test-graph-{i}")
            g = store.get_context(graph_uri)
            EX = Namespace("http://example.org/")
            g.add((EX[f"s{i}"], EX[f"p{i}"], Literal(f"value{i}")))
            g.add((graph_uri, RDFS.label, Literal(f"Graph {i}")))
            graph_uris.append(graph_uri)

        resources = await list_store_resources(session_id)

        assert len(resources) == 3

        # Verify all graphs are present
        resource_names = {r.name for r in resources}
        assert resource_names == {"Graph 0", "Graph 1", "Graph 2"}

    @pytest.mark.asyncio
    async def test_skip_default_graph(self, session_id):
        """Test that default graph is skipped in listing."""
        # Add triples to default graph
        EX = Namespace("http://example.org/")
        store.add((EX.s, EX.p, Literal("default graph data")))

        # Add a named graph
        graph_uri = URIRef("urn:uuid:named-graph")
        g = store.get_context(graph_uri)
        g.add((EX.s2, EX.p2, Literal("named graph data")))
        g.add((graph_uri, RDFS.label, Literal("Named Graph")))

        resources = await list_store_resources(session_id)

        # Should only list the named graph, not default
        assert len(resources) == 1
        assert resources[0].name == "Named Graph"


class TestExtractGraphMetadata:
    """Test metadata extraction functions."""

    def test_extract_name_from_rdfs_label(self):
        """Test extracting name from RDFS label."""
        graph_uri = URIRef("urn:uuid:test")
        g = store.get_context(graph_uri)
        g.add((graph_uri, RDFS.label, Literal("My Graph Name")))

        name = extract_graph_name(g)
        assert name == "My Graph Name"

    def test_extract_name_from_schema_name(self):
        """Test extracting name from schema:name."""
        graph_uri = URIRef("urn:uuid:test")
        g = store.get_context(graph_uri)
        g.add((graph_uri, SCHEMA.name, Literal("Schema Name")))

        name = extract_graph_name(g)
        assert name == "Schema Name"

    def test_extract_name_from_uuid(self):
        """Test fallback name extraction from UUID."""
        graph_uri = URIRef("urn:uuid:1234567890ab")
        g = store.get_context(graph_uri)

        name = extract_graph_name(g)
        assert name == "Graph 1234567890ab"  # Last 12 chars

    def test_extract_name_from_path(self):
        """Test extracting name from path-based URI."""
        graph_uri = URIRef("http://example.org/graphs/my-graph")
        g = store.get_context(graph_uri)

        name = extract_graph_name(g)
        assert name == "my-graph"

    def test_extract_description_from_prov_time(self):
        """Test extracting description from PROV-O timestamp."""
        graph_uri = URIRef("urn:uuid:test")
        g = store.get_context(graph_uri)
        timestamp = Literal("2025-11-20T14:30:00Z")
        g.add((graph_uri, PROV.generatedAtTime, timestamp))

        desc = extract_graph_description(g)
        assert desc == f"Generated at {timestamp}"

    def test_extract_description_from_prov_activity(self):
        """Test extracting description from PROV-O activity."""
        graph_uri = URIRef("urn:uuid:test")
        g = store.get_context(graph_uri)
        activity = URIRef("http://example.org/ggf/SLM-CSV")
        g.add((graph_uri, PROV.wasGeneratedBy, activity))

        desc = extract_graph_description(g)
        assert desc == "Generated by SLM-CSV"

    def test_extract_description_from_comment(self):
        """Test extracting description from RDFS comment."""
        graph_uri = URIRef("urn:uuid:test")
        g = store.get_context(graph_uri)
        g.add((graph_uri, RDFS.comment, Literal("This is a comment")))

        desc = extract_graph_description(g)
        assert desc == "This is a comment"

    def test_extract_description_triple_count(self):
        """Test fallback description with triple count."""
        graph_uri = URIRef("urn:uuid:test")
        g = store.get_context(graph_uri)
        EX = Namespace("http://example.org/")
        g.add((EX.s1, EX.p1, Literal("v1")))
        g.add((EX.s2, EX.p2, Literal("v2")))
        g.add((EX.s3, EX.p3, Literal("v3")))

        desc = extract_graph_description(g)
        assert desc == "Named graph with 3 triples"


class TestReadStoreResource:
    """Test resource reading functionality."""

    @pytest.mark.asyncio
    async def test_read_existing_resource(self, session_id, sample_graph):
        """Test reading an existing graph resource."""
        encoded_graph_id = quote(str(sample_graph), safe='')
        uri = f"store://{session_id}/graphs/{encoded_graph_id}"

        content = await read_store_resource(uri, session_id)

        # Verify it's valid JSON-LD
        assert isinstance(content, str)
        assert len(content) > 0

        # Should contain graph data
        import json
        data = json.loads(content)
        assert isinstance(data, (dict, list))

    @pytest.mark.asyncio
    async def test_read_nonexistent_resource(self, session_id):
        """Test reading a non-existent graph."""
        fake_graph_id = quote("urn:uuid:does-not-exist", safe='')
        uri = f"store://{session_id}/graphs/{fake_graph_id}"

        with pytest.raises(ValueError, match="Graph not found or empty"):
            await read_store_resource(uri, session_id)

    @pytest.mark.asyncio
    async def test_read_invalid_uri_format(self, session_id):
        """Test reading with invalid URI format."""
        invalid_uri = "invalid://not-a-valid-uri"

        with pytest.raises(ValueError, match="Invalid resource URI"):
            await read_store_resource(invalid_uri, session_id)

    @pytest.mark.asyncio
    async def test_read_wrong_session_id(self, session_id, sample_graph):
        """Test reading with wrong session ID."""
        encoded_graph_id = quote(str(sample_graph), safe='')
        wrong_session = "sess-wrong1234"
        uri = f"store://{wrong_session}/graphs/{encoded_graph_id}"

        with pytest.raises(ValueError, match="Invalid resource URI"):
            await read_store_resource(uri, session_id)

    @pytest.mark.asyncio
    async def test_read_resource_with_special_chars(self, session_id):
        """Test reading resource with special characters in URI."""
        # Create graph with special chars in URI
        graph_uri = URIRef("http://example.org/graphs/my-graph#special")
        g = store.get_context(graph_uri)
        EX = Namespace("http://example.org/")
        g.add((EX.subject, EX.predicate, Literal("value")))

        encoded_graph_id = quote(str(graph_uri), safe='')
        uri = f"store://{session_id}/graphs/{encoded_graph_id}"

        content = await read_store_resource(uri, session_id)

        # Should successfully decode and read
        assert isinstance(content, str)
        assert len(content) > 0


class TestResourceIntegration:
    """Integration tests with MCP server."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, session_id):
        """Test complete workflow: create graphs → list → read."""
        # Step 1: Create multiple graphs with different content
        graph_uris = []
        EX = Namespace("http://example.org/")

        for i in range(2):
            graph_uri = URIRef(f"urn:uuid:workflow-graph-{i}")
            g = store.get_context(graph_uri)
            g.add((EX[f"entity{i}"], EX.name, Literal(f"Entity {i}")))
            g.add((graph_uri, RDFS.label, Literal(f"Workflow Graph {i}")))
            graph_uris.append(graph_uri)

        # Step 2: List resources
        resources = await list_store_resources(session_id)
        assert len(resources) == 2

        # Step 3: Read each resource
        for resource in resources:
            content = await read_store_resource(resource.uri, session_id)

            # Verify content is valid JSON-LD
            import json
            data = json.loads(content)
            assert isinstance(data, (dict, list))

        # Cleanup
        reset_store()

        # Step 4: Verify empty after reset
        resources_after = await list_store_resources(session_id)
        assert len(resources_after) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
