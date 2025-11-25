#!/usr/bin/env python3
"""
Ground Truth Query Runner and Validator

Runs all ground truth queries and saves results for accuracy evaluation.
"""

import subprocess
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

class GroundTruthRunner:
    def __init__(self, config_path='config.ini'):
        self.gt_dir = Path(__file__).parent / 'ground_truth'
        self.results_dir = self.gt_dir / 'results'
        self.results_dir.mkdir(exist_ok=True)

        # Get absolute paths
        self.sparqllm_root = self.gt_dir.parents[2]  # SPARQLLM root directory
        self.config_path = self.sparqllm_root / config_path
        self.venv_path = self.sparqllm_root / 'venv312_new'

        # Expected results for validation
        self.expected_results = {
            'gt_01': {'min_rows': 10, 'max_rows': 10, 'columns': ['name', 'country', 'victim_min', 'victim_max']},
            'gt_02': {'min_rows': 5, 'max_rows': 20, 'columns': ['decade', 'count']},
            'gt_03': {'min_rows': 10, 'max_rows': 15, 'columns': ['country', 'count']},
            'gt_04': {'min_rows': 1, 'max_rows': 50, 'columns': ['name', 'decade', 'country']},
            'gt_05': {'min_rows': 1, 'max_rows': 20, 'columns': ['name', 'country', 'victim_min']},
        }

    def run_query(self, query_file: Path) -> dict:
        """
        Run a single SPARQL query and return results.

        Returns:
            dict with keys: success, stdout, stderr, exit_code, time_ms
        """
        query_id = query_file.stem
        print(f"\n{'='*80}")
        print(f"Running: {query_id}")
        print(f"File: {query_file.name}")
        print(f"{'='*80}")

        start = datetime.now()

        try:
            cmd = f'source {self.venv_path}/bin/activate && slm-run -c {self.config_path} -f {query_file}'
            result = subprocess.run(
                ['bash', '-c', cmd],
                cwd=self.sparqllm_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            end = datetime.now()
            time_ms = int((end - start).total_seconds() * 1000)

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.returncode,
                'time_ms': time_ms,
                'query_id': query_id
            }

        except subprocess.TimeoutExpired:
            end = datetime.now()
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Query timeout (60s)',
                'exit_code': -1,
                'time_ms': 60000,
                'query_id': query_id
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'time_ms': 0,
                'query_id': query_id
            }

    def parse_dataframe_output(self, stdout: str) -> pd.DataFrame:
        """
        Parse pandas DataFrame from stdout.

        Returns empty DataFrame if parsing fails.
        """
        try:
            # Find the DataFrame table in output
            lines = stdout.split('\n')

            # Look for pandas table (starts with column headers or index)
            table_start = -1
            for i, line in enumerate(lines):
                if any(col in line for col in ['name', 'decade', 'country', 'count', 'victim']):
                    table_start = i
                    break

            if table_start == -1:
                return pd.DataFrame()

            # Find table end (empty line or end of output)
            table_end = len(lines)
            for i in range(table_start + 1, len(lines)):
                if lines[i].strip() == '' or lines[i].startswith('['):
                    table_end = i
                    break

            table_text = '\n'.join(lines[table_start:table_end])

            # Try to parse as CSV-like format
            from io import StringIO
            df = pd.read_csv(StringIO(table_text), sep=r'\s{2,}', engine='python')
            return df

        except Exception as e:
            print(f"  ⚠ DataFrame parsing failed: {e}")
            return pd.DataFrame()

    def validate_result(self, query_id: str, df: pd.DataFrame) -> dict:
        """
        Validate query result against expected criteria.

        Returns:
            dict with keys: valid, errors, warnings
        """
        errors = []
        warnings = []

        # Get expected for this query
        expected = self.expected_results.get(query_id.split('_')[0] + '_' + query_id.split('_')[1])

        if not expected:
            warnings.append(f"No expected results defined for {query_id}")
            return {'valid': True, 'errors': errors, 'warnings': warnings}

        # Check row count
        row_count = len(df)
        if row_count == 0:
            errors.append("Query returned empty result")
        elif row_count < expected['min_rows']:
            warnings.append(f"Row count ({row_count}) below expected minimum ({expected['min_rows']})")
        elif row_count > expected['max_rows']:
            warnings.append(f"Row count ({row_count}) above expected maximum ({expected['max_rows']})")

        # Check columns
        if not df.empty:
            missing_cols = []
            for col in expected['columns']:
                if col not in df.columns:
                    missing_cols.append(col)

            if missing_cols:
                errors.append(f"Missing expected columns: {missing_cols}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def save_result(self, query_id: str, result: dict, df: pd.DataFrame, validation: dict):
        """Save query result and metadata to files."""

        # Save CSV if DataFrame not empty
        if not df.empty:
            csv_path = self.results_dir / f'{query_id}_result.csv'
            df.to_csv(csv_path, index=False)
            print(f"  ✓ Saved CSV: {csv_path.name}")

        # Save metadata
        metadata = {
            'query_id': query_id,
            'timestamp': datetime.now().isoformat(),
            'success': result['success'],
            'exit_code': result['exit_code'],
            'time_ms': result['time_ms'],
            'row_count': len(df),
            'columns': list(df.columns) if not df.empty else [],
            'validation': validation,
            'stderr': result['stderr'] if result['stderr'] else None
        }

        json_path = self.results_dir / f'{query_id}_metadata.json'
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"  ✓ Saved metadata: {json_path.name}")

    def run_all(self):
        """Run all ground truth queries and generate report."""

        print(f"\n{'='*80}")
        print("GROUND TRUTH QUERY RUNNER")
        print(f"{'='*80}")
        print(f"GT Directory: {self.gt_dir}")
        print(f"Results Directory: {self.results_dir}")

        # Find all .sparql files
        query_files = sorted(self.gt_dir.glob('gt_*.sparql'))

        if not query_files:
            print("\n❌ No ground truth queries found!")
            return False

        print(f"\nFound {len(query_files)} ground truth queries")

        results_summary = []

        for query_file in query_files:
            # Run query
            result = self.run_query(query_file)

            # Parse DataFrame
            df = self.parse_dataframe_output(result['stdout']) if result['success'] else pd.DataFrame()

            # Validate
            validation = self.validate_result(result['query_id'], df)

            # Print immediate feedback
            if result['success']:
                print(f"  ✓ Query executed successfully ({result['time_ms']}ms)")
                print(f"  ✓ Returned {len(df)} rows")

                if validation['valid']:
                    print(f"  ✓ Validation passed")
                else:
                    print(f"  ⚠ Validation issues:")
                    for error in validation['errors']:
                        print(f"    - ERROR: {error}")
                    for warning in validation['warnings']:
                        print(f"    - WARNING: {warning}")
            else:
                print(f"  ✗ Query failed (exit code: {result['exit_code']})")
                if result['stderr']:
                    print(f"  ✗ Error: {result['stderr'][:200]}")

            # Save result
            self.save_result(result['query_id'], result, df, validation)

            # Track summary
            results_summary.append({
                'query_id': result['query_id'],
                'success': result['success'],
                'time_ms': result['time_ms'],
                'rows': len(df),
                'valid': validation['valid']
            })

        # Generate summary report
        self.generate_report(results_summary)

        # Return overall success
        all_passed = all(r['success'] and r['valid'] for r in results_summary)
        return all_passed

    def generate_report(self, results_summary: list):
        """Generate summary report."""

        print(f"\n{'='*80}")
        print("GROUND TRUTH RESULTS SUMMARY")
        print(f"{'='*80}")

        total = len(results_summary)
        passed = sum(1 for r in results_summary if r['success'] and r['valid'])
        failed = total - passed

        print(f"\nTotal Queries: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")

        print(f"\n{'Query':<30} {'Status':<10} {'Time':<10} {'Rows':<10}")
        print(f"{'-'*30} {'-'*10} {'-'*10} {'-'*10}")

        for r in results_summary:
            status = '✓ PASS' if (r['success'] and r['valid']) else '✗ FAIL'
            time_str = f"{r['time_ms']}ms" if r['success'] else 'N/A'
            rows_str = str(r['rows']) if r['success'] else '0'

            print(f"{r['query_id']:<30} {status:<10} {time_str:<10} {rows_str:<10}")

        # Save JSON report
        report_path = self.results_dir / 'summary_report.json'
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total': total,
                'passed': passed,
                'failed': failed,
                'results': results_summary
            }, f, indent=2)

        print(f"\n✓ Summary report saved: {report_path}")
        print(f"{'='*80}\n")

def main():
    runner = GroundTruthRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
