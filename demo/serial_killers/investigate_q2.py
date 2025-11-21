#!/usr/bin/env python3
"""
Investigation script for Q2 empty results.
Runs from demo/serial_killers working directory.
"""
import sys
import os
from pathlib import Path

# Add SPARQLLM root to path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

import logging
import requests
import json
from rdflib import Graph, Namespace, URIRef

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_ollama_connection():
    """Test if Ollama is responding"""
    logger.info("=" * 80)
    logger.info("TEST: Ollama Connection")
    logger.info("=" * 80)

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            logger.info(f"✓ Ollama is running")
            logger.info(f"Available models: {models}")
            return True
        else:
            logger.error(f"✗ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Cannot connect to Ollama: {e}")
        return False

def test_ollama_generate():
    """Test Ollama with a simple JSON-LD generation request"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Ollama JSON-LD Generation")
    logger.info("=" * 80)

    prompt = '''Extract the killing methods used by this serial killer from the text. Return ONLY a JSON-LD object with this exact structure (no extra text): {  "@context": "https://schema.org/",  "@type": "Person",  "name": "Ted Bundy",  "description": "brief comma-separated list of methods (e.g., shooting, stabbing, poisoning)"}

Text: Confessed to 30 murders across multiple states. Used charm and good looks to lure victims. Known for bludgeoning and strangling victims.'''

    payload = {
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0}
    }

    logger.info(f"Sending prompt to Ollama...")
    logger.info(f"Prompt length: {len(prompt)} chars")

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            llm_response = result['response']

            logger.info(f"✓ LLM Response received")
            logger.info(f"Response length: {len(llm_response)} chars")
            logger.info(f"Raw response:\n{llm_response}")

            # Try to parse as JSON-LD
            try:
                json_data = json.loads(llm_response)
                logger.info(f"✓ Valid JSON structure")
                logger.info(f"JSON keys: {list(json_data.keys())}")

                # Try to parse as RDF
                g = Graph()
                g.parse(data=llm_response, format="json-ld")
                logger.info(f"✓ Valid JSON-LD - parsed {len(g)} triples")

                # Show triples
                logger.info("Triples:")
                for s, p, o in g:
                    logger.info(f"  {s} --{p}--> {o}")

                # Check for schema:Person
                schema = Namespace("https://schema.org/")
                persons = list(g.subjects(predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                                         object=schema.Person))
                logger.info(f"Found {len(persons)} schema:Person entities")

                # Check for description
                descs = list(g.objects(predicate=schema.description))
                logger.info(f"Found {len(descs)} schema:description values")
                for desc in descs:
                    logger.info(f"  Description: {desc}")

                return True

            except json.JSONDecodeError as e:
                logger.error(f"✗ Invalid JSON: {e}")
                return False
            except Exception as e:
                logger.error(f"✗ Cannot parse as JSON-LD: {e}")
                return False
        else:
            logger.error(f"✗ Ollama returned status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"✗ Request failed: {e}")
        return False

def test_csv_data():
    """Test that CSV has the expected data for Q2"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: CSV Data for Q2 Decades")
    logger.info("=" * 80)

    import pandas as pd

    csv_file = Path(__file__).parent / "data" / "serial_killers_clean.csv"

    if not csv_file.exists():
        logger.error(f"✗ CSV file not found: {csv_file}")
        return False

    df = pd.read_csv(csv_file)
    logger.info(f"✓ CSV loaded: {len(df)} rows")

    # Filter for Q2 decades
    q2_decades = ["1970s", "1980s", "1990s", "2000s"]
    filtered = df[df['decade'].isin(q2_decades)]

    logger.info(f"Rows matching Q2 decades: {len(filtered)}")
    logger.info(f"Decade distribution:")
    for decade in q2_decades:
        count = len(df[df['decade'] == decade])
        logger.info(f"  {decade}: {count} rows")

    # Show first few rows
    logger.info("\nFirst 3 rows for Q2 decades:")
    for idx, row in filtered.head(3).iterrows():
        logger.info(f"  {row['name']} ({row['decade']})")
        logger.info(f"    Notes: {str(row['notes'])[:100]}...")

    return len(filtered) > 0

def test_sparql_query():
    """Test the actual SPARQL query"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: SPARQL Query Execution")
    logger.info("=" * 80)

    from SPARQLLM.config import ConfigSingleton
    from SPARQLLM.udf.SPARQLLM import store, reset_store

    # Reset store
    reset_store()

    # Initialize config
    config_file = root_dir / "config.ini"
    config = ConfigSingleton(config_file=str(config_file))

    logger.info(f"Config loaded from: {config_file}")
    logger.info(f"Ollama URL: {config.config['Requests']['SLM-OLLAMA-URL']}")
    logger.info(f"Ollama Model: {config.config['Requests']['SLM-OLLAMA-MODEL']}")

    # Simplified query - just test 1970s with LIMIT 1
    query = """
    PREFIX ggf: <http://ggf.org/>
    PREFIX ex: <http://example.org/>
    PREFIX schema: <https://schema.org/>

    SELECT ?decade ?name ?methods
    WHERE {
        # Load CSV data
        BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)

        GRAPH ?csvGraph {
            ?row ex:name ?name .
            ?row ex:decade ?decade .
            ?row ex:notes ?notes .
        }

        # Filter for 1970s only
        FILTER(?decade = "1970s")

        # Use LLM to extract methods from notes
        BIND(CONCAT(
            "Extract the killing methods used by this serial killer from the text. ",
            "Return ONLY a JSON-LD object with this exact structure (no extra text): ",
            "{",
            "  \\"@context\\": \\"https://schema.org/\\",",
            "  \\"@type\\": \\"Person\\",",
            "  \\"name\\": \\"", STR(?name), "\\",",
            "  \\"description\\": \\"brief comma-separated list of methods (e.g., shooting, stabbing, poisoning)\\"",
            "}",
            "\\n\\nText: ", SUBSTR(?notes, 1, 300)
        ) AS ?prompt)

        BIND(ggf:SLM-LLMGRAPH(?prompt) AS ?llmGraph)

        GRAPH ?llmGraph {
            ?person a schema:Person ;
                    schema:description ?methods .
        }
    }
    LIMIT 1
    """

    logger.info("Executing SPARQL query...")
    logger.info(f"Query targets 1970s decade with LIMIT 1")

    try:
        results = list(store.query(query))
        logger.info(f"✓ Query executed successfully")
        logger.info(f"Results: {len(results)} rows")

        if len(results) > 0:
            for i, row in enumerate(results):
                logger.info(f"Row {i+1}:")
                logger.info(f"  Decade: {row.decade}")
                logger.info(f"  Name: {row.name}")
                logger.info(f"  Methods: {row.methods}")
            return True
        else:
            logger.warning("✗ Query returned 0 results")

            # Debug: check if CSV loaded
            logger.info("\nDebugging: Checking CSV graph...")
            csv_check = """
            PREFIX ggf: <http://ggf.org/>
            PREFIX ex: <http://example.org/>
            SELECT (COUNT(*) as ?count)
            WHERE {
                BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?csvGraph)
                GRAPH ?csvGraph {
                    ?row ex:name ?name .
                    ?row ex:decade ?decade .
                    FILTER(?decade = "1970s")
                }
            }
            """
            csv_results = list(store.query(csv_check))
            logger.info(f"CSV rows for 1970s: {csv_results[0].count if csv_results else 0}")

            return False

    except Exception as e:
        logger.error(f"✗ Query execution failed: {e}", exc_info=True)
        return False

def main():
    """Run all investigation tests"""
    print("\n" + "=" * 80)
    print("Q2 INVESTIGATION - Empty Results Diagnosis")
    print("=" * 80)
    print(f"Working directory: {os.getcwd()}")
    print(f"Script location: {Path(__file__).parent}")
    print()

    results = {}

    # Run tests
    results['ollama_connection'] = test_ollama_connection()
    results['ollama_generate'] = test_ollama_generate()
    results['csv_data'] = test_csv_data()
    results['sparql_query'] = test_sparql_query()

    # Summary
    print("\n" + "=" * 80)
    print("INVESTIGATION SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} {test_name}")

    all_passed = all(results.values())
    print()
    if all_passed:
        print("✓ All tests passed - Q2 should work")
        return 0
    else:
        failed = [name for name, passed in results.items() if not passed]
        print(f"✗ {len(failed)} test(s) failed: {', '.join(failed)}")
        print("\nNext steps:")
        if not results['ollama_connection']:
            print("  1. Start Ollama server: ollama serve")
        if not results['ollama_generate']:
            print("  2. Check Ollama model: ollama pull qwen2.5:3b")
        if not results['csv_data']:
            print("  3. Run data cleanup: python demo/serial_killers/setup/clean_data.py")
        if not results['sparql_query']:
            print("  4. Check SPARQL query pattern and LLM response format")
        return 1

if __name__ == "__main__":
    sys.exit(main())
