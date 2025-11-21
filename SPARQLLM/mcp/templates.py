"""SPARQL query templates for convenience tools

Templates use Python string formatting for parameter substitution.
All user inputs must be escaped before template insertion.
"""

# Template: Extract structured data from file using LLM
EXTRACT_STRUCTURED_DATA_TEMPLATE = """
PREFIX ggf: <http://example.org/>
PREFIX schema: <http://schema.org/>

SELECT ?entity ?property ?value WHERE {{
    # Step 1: Resolve file path
    BIND(ggf:SLM-FILE("{file_path}") AS ?filePath)

    # Step 2: Parse file based on extension
    BIND(ggf:SLM-READFILE(?filePath) AS ?contentGraph)

    # Step 3: Extract text
    GRAPH ?contentGraph {{
        ?doc schema:text ?text .
    }}

    # Step 4: LLM extraction with structured output
    BIND(ggf:LLM(CONCAT("{extraction_prompt}", "\\n\\nText: ", ?text)) AS ?llmGraph)

    # Step 5: Extract structured output
    GRAPH ?llmGraph {{
        ?entity ?property ?value .
    }}
}}
LIMIT {limit}
"""

# Template: Simple file extraction (no LLM, just parse)
SIMPLE_EXTRACT_TEMPLATE = """
PREFIX ggf: <http://example.org/>
PREFIX schema: <http://schema.org/>
PREFIX ex: <http://example.org/>

SELECT ?subject ?predicate ?object WHERE {{
    # Step 1: Resolve and read file
    BIND(ggf:SLM-FILE("{file_path}") AS ?filePath)
    BIND(ggf:SLM-READFILE(?filePath) AS ?contentGraph)

    # Step 2: Extract all triples
    GRAPH ?contentGraph {{
        ?subject ?predicate ?object .
    }}
}}
LIMIT {limit}
"""

# Template: CSV-specific extraction
CSV_EXTRACT_TEMPLATE = """
PREFIX ggf: <http://example.org/>
PREFIX schema: <http://schema.org/>
PREFIX ex: <http://example.org/>

SELECT * WHERE {{
    # Parse CSV file
    BIND(ggf:SLM-FILE("{file_path}") AS ?filePath)
    BIND(ggf:SLM-CSV(?filePath) AS ?csvGraph)

    # Extract data
    GRAPH ?csvGraph {{
        ?row ?property ?value .
    }}
}}
LIMIT {limit}
"""

# Template: Web scraping to knowledge graph
WEB_TO_KNOWLEDGE_TEMPLATE = """
PREFIX ggf: <http://example.org/>
PREFIX schema: <http://schema.org/>

CONSTRUCT {{
    ?entity ?property ?value .
    ?entity schema:url <{url}> .
}}
WHERE {{
    # Step 1: Fetch webpage content
    BIND(ggf:SLM-GETTEXT("{url}") AS ?webGraph)

    # Step 2: Extract text
    GRAPH ?webGraph {{
        ?page schema:text ?text .
    }}

    # Step 3: LLM entity extraction (if available)
    BIND(ggf:LLM(CONCAT("{extraction_prompt}", "\\n\\nText: ", SUBSTR(?text, 1, {text_max_chars}))) AS ?llmGraph)

    # Step 4: Extract entities
    GRAPH ?llmGraph {{
        ?entity ?property ?value .
    }}
}}
"""

# Simple web extraction without LLM
SIMPLE_WEB_TEMPLATE = """
PREFIX ggf: <http://example.org/>
PREFIX schema: <http://schema.org/>

SELECT ?text WHERE {{
    # Fetch webpage
    BIND(ggf:SLM-GETTEXT("{url}") AS ?webGraph)

    # Extract text content
    GRAPH ?webGraph {{
        ?page schema:text ?text .
    }}
}}
"""
