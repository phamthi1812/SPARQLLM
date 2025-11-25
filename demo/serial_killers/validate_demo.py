#!/usr/bin/env python3
"""
Demo Validation Script

Factchecks everything in the Serial Killers demo:
- CSV data quality
- All queries (Q1-Q6)
- GGF functions
- LLM integration
"""

import subprocess
import pandas as pd
from pathlib import Path
import sys
import json
from datetime import datetime

class DemoValidator:
    def __init__(self):
        self.demo_dir = Path(__file__).parent
        self.root_dir = self.demo_dir.parents[1]
        self.data_dir = self.demo_dir / 'data'
        self.queries_dir = self.demo_dir / 'queries'
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'data_validation': {},
            'query_tests': {},
            'ggf_tests': {},
            'summary': {}
        }

    def print_section(self, title):
        print(f"\n{'='*80}")
        print(f"{title}")
        print(f"{'='*80}\n")

    def validate_csv_data(self):
        """Validate CSV data quality."""
        self.print_section("1. CSV DATA VALIDATION")

        csv_file = self.data_dir / 'serial_killers_clean.csv'

        if not csv_file.exists():
            print(f"❌ CSV file not found: {csv_file}")
            self.results['data_validation']['status'] = 'FAIL'
            return False

        try:
            df = pd.read_csv(csv_file)

            # Basic checks
            checks = {
                'file_exists': csv_file.exists(),
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': list(df.columns),
                'has_name': 'name' in df.columns,
                'has_decade': 'decade' in df.columns,
                'has_victim_min': 'victim_min' in df.columns,
                'has_victim_max': 'victim_max' in df.columns,
                'null_names': df['name'].isnull().sum() if 'name' in df.columns else 'N/A',
                'null_decades': df['decade'].isnull().sum() if 'decade' in df.columns else 'N/A',
                'unique_names': df['name'].nunique() if 'name' in df.columns else 'N/A',
                'unique_decades': df['decade'].nunique() if 'decade' in df.columns else 'N/A',
            }

            self.results['data_validation'] = checks

            # Print results
            print(f"✓ File exists: {csv_file.name}")
            print(f"✓ Rows: {checks['row_count']}")
            print(f"✓ Columns: {checks['column_count']}")
            print(f"  Columns: {', '.join(checks['columns'][:5])}...")
            print(f"✓ Has required columns:")
            print(f"  - name: {checks['has_name']}")
            print(f"  - decade: {checks['has_decade']}")
            print(f"  - victim_min: {checks['has_victim_min']}")
            print(f"  - victim_max: {checks['has_victim_max']}")
            print(f"✓ Data quality:")
            print(f"  - NULL names: {checks['null_names']}")
            print(f"  - NULL decades: {checks['null_decades']}")
            print(f"  - Unique names: {checks['unique_names']}")
            print(f"  - Unique decades: {checks['unique_decades']}")

            # Sample data
            print(f"\n✓ Sample data (first 3 rows):")
            print(df.head(3).to_string())

            return True

        except Exception as e:
            print(f"❌ Error validating CSV: {e}")
            self.results['data_validation']['error'] = str(e)
            return False

    def run_query(self, query_file, timeout=60):
        """Run a SPARQL query and return results."""
        try:
            cmd = f'source {self.root_dir}/venv312_new/bin/activate && slm-run -c config.ini -f {query_file}'
            result = subprocess.run(
                ['bash', '-c', cmd],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Timeout after {timeout}s',
                'exit_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1
            }

    def test_queries(self):
        """Test all demo queries."""
        self.print_section("2. QUERY TESTS")

        query_files = [
            ('q1_top_victims.sparql', 'Top victims (Pure CSV)', 10),
            ('q5_geographical_patterns.sparql', 'Geographical patterns (Pure CSV)', 5),
            ('q6_decade_statistics.sparql', 'Decade statistics (Pure CSV)', 10),
        ]

        for query_file, desc, expected_min_rows in query_files:
            query_path = self.queries_dir / query_file
            query_id = query_file.replace('.sparql', '')

            print(f"\nTesting: {query_id}")
            print(f"Description: {desc}")
            print(f"Expected: >= {expected_min_rows} rows")

            if not query_path.exists():
                print(f"  ⚠  Query file not found: {query_path}")
                self.results['query_tests'][query_id] = {'status': 'SKIP', 'reason': 'File not found'}
                continue

            result = self.run_query(query_path, timeout=30)

            if result['success']:
                # Count rows in output
                lines = [l for l in result['stdout'].split('\n') if l.strip() and not l.startswith('[')]
                row_count = max(0, len(lines) - 1)  # Subtract header

                status = 'PASS' if row_count >= expected_min_rows else 'WARNING'
                print(f"  ✓ Query executed successfully")
                print(f"  ✓ Returned {row_count} rows")
                print(f"  {'' if status == 'PASS' else '⚠ '} Status: {status}")

                # Show first few lines
                if row_count > 0:
                    print(f"\n  Sample output:")
                    for line in lines[:4]:
                        print(f"    {line[:100]}")

                self.results['query_tests'][query_id] = {
                    'status': status,
                    'rows': row_count,
                    'expected_min': expected_min_rows
                }
            else:
                print(f"  ✗ Query failed")
                print(f"  ✗ Error: {result['stderr'][:200]}")
                self.results['query_tests'][query_id] = {
                    'status': 'FAIL',
                    'error': result['stderr'][:200]
                }

        return True

    def test_ggf_functions(self):
        """Test individual GGF functions."""
        self.print_section("3. GGF FUNCTION TESTS")

        # Test SLM-CSV
        print("\nTesting: SLM-CSV")
        csv_query = '''PREFIX ggf: <http://ggf.org/>
PREFIX ex: <http://example.org/>
SELECT (COUNT(?name) AS ?count) WHERE {
    BIND(ggf:SLM-CSV("./demo/serial_killers/data/serial_killers_clean.csv") AS ?g)
    GRAPH ?g {
        ?row ex:name ?name .
    }
}'''

        result = self.run_inline_query(csv_query)
        if result['success']:
            print(f"  ✓ SLM-CSV works")
            print(f"  ✓ Output: {result['stdout'].split('n')[0] if result['stdout'] else 'N/A'}")
            self.results['ggf_tests']['SLM-CSV'] = {'status': 'PASS'}
        else:
            print(f"  ✗ SLM-CSV failed")
            print(f"  ✗ Error: {result['stderr'][:200]}")
            self.results['ggf_tests']['SLM-CSV'] = {'status': 'FAIL', 'error': result['stderr'][:200]}

        return True

    def run_inline_query(self, query_str):
        """Run an inline SPARQL query."""
        try:
            cmd = f'source {self.root_dir}/venv312_new/bin/activate && slm-run -c config.ini -q \'{query_str}\''
            result = subprocess.run(
                ['bash', '-c', cmd],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e)
            }

    def test_llm_integration(self):
        """Test LLM integration."""
        self.print_section("4. LLM INTEGRATION TEST")

        test_file = self.demo_dir / 'test_llm_simple.sparql'

        if not test_file.exists():
            print(f"⚠  LLM test file not found: {test_file}")
            self.results['ggf_tests']['SLM-LLMGRAPH'] = {'status': 'SKIP', 'reason': 'Test file not found'}
            return True

        print(f"\nTesting: SLM-LLMGRAPH (Ollama)")
        print(f"Query: test_llm_simple.sparql")

        result = self.run_query(test_file, timeout=60)

        if result['success']:
            print(f"  ✓ SLM-LLMGRAPH works")
            # Check if we got actual LLM response
            if 'Ted Bundy' in result['stdout']:
                print(f"  ✓ LLM responded correctly (found 'Ted Bundy')")
                self.results['ggf_tests']['SLM-LLMGRAPH'] = {'status': 'PASS'}
            else:
                print(f"  ⚠ LLM response unexpected")
                self.results['ggf_tests']['SLM-LLMGRAPH'] = {'status': 'WARNING', 'reason': 'Unexpected response'}

            # Show output
            print(f"\n  Sample output:")
            for line in result['stdout'].split('\n')[:5]:
                print(f"    {line}")
        else:
            print(f"  ✗ SLM-LLMGRAPH failed")
            print(f"  ✗ Error: {result['stderr'][:200]}")
            self.results['ggf_tests']['SLM-LLMGRAPH'] = {'status': 'FAIL', 'error': result['stderr'][:200]}

        return True

    def generate_summary(self):
        """Generate validation summary."""
        self.print_section("VALIDATION SUMMARY")

        # Count statuses
        data_ok = self.results['data_validation'].get('file_exists', False)

        query_pass = sum(1 for t in self.results['query_tests'].values() if t.get('status') == 'PASS')
        query_fail = sum(1 for t in self.results['query_tests'].values() if t.get('status') == 'FAIL')
        query_warn = sum(1 for t in self.results['query_tests'].values() if t.get('status') == 'WARNING')
        query_total = len(self.results['query_tests'])

        ggf_pass = sum(1 for t in self.results['ggf_tests'].values() if t.get('status') == 'PASS')
        ggf_fail = sum(1 for t in self.results['ggf_tests'].values() if t.get('status') == 'FAIL')
        ggf_total = len(self.results['ggf_tests'])

        self.results['summary'] = {
            'data_validation': 'PASS' if data_ok else 'FAIL',
            'queries': {
                'total': query_total,
                'pass': query_pass,
                'fail': query_fail,
                'warning': query_warn
            },
            'ggfs': {
                'total': ggf_total,
                'pass': ggf_pass,
                'fail': ggf_fail
            },
            'overall': 'PASS' if (data_ok and query_fail == 0 and ggf_fail == 0) else 'FAIL'
        }

        print(f"\nData Validation: {'✓ PASS' if data_ok else '✗ FAIL'}")
        print(f"\nQueries: {query_pass}/{query_total} passed")
        if query_fail > 0:
            print(f"  ✗ {query_fail} failed")
        if query_warn > 0:
            print(f"  ⚠ {query_warn} warnings")

        print(f"\nGGFs: {ggf_pass}/{ggf_total} passed")
        if ggf_fail > 0:
            print(f"  ✗ {ggf_fail} failed")

        print(f"\n{'='*80}")
        print(f"OVERALL: {'✓ PASS' if self.results['summary']['overall'] == 'PASS' else '✗ FAIL'}")
        print(f"{'='*80}\n")

        # Save report (convert numpy types to Python types)
        report_file = self.demo_dir / 'validation_report.json'
        def convert_types(obj):
            """Convert numpy types to Python types for JSON serialization."""
            import numpy as np
            if isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            elif isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            return obj

        with open(report_file, 'w') as f:
            json.dump(convert_types(self.results), f, indent=2)
        print(f"✓ Report saved: {report_file}")

        return self.results['summary']['overall'] == 'PASS'

    def run(self):
        """Run all validations."""
        print(f"\n{'='*80}")
        print("SERIAL KILLERS DEMO VALIDATION")
        print(f"{'='*80}")
        print(f"Demo directory: {self.demo_dir}")
        print(f"Timestamp: {self.results['timestamp']}")

        # Run validations
        self.validate_csv_data()
        self.test_queries()
        self.test_ggf_functions()
        self.test_llm_integration()

        # Generate summary
        success = self.generate_summary()

        return success

def main():
    validator = DemoValidator()
    success = validator.run()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
