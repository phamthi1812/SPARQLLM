#!/usr/bin/env python3
"""
Data Validation Script for Serial Killers Dataset

Automated validation checks for cleaned dataset.
"""

import sys
from pathlib import Path
import pandas as pd


def get_data_path():
    """Get path to cleaned dataset"""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    return data_dir / "serial_killers_clean.csv"


def validate_schema(df):
    """Validate required columns exist"""
    errors = []
    warnings = []

    # Required columns
    required_cols = ['name']
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"Missing REQUIRED column: '{col}'")

    # Expected columns (not critical but should be there)
    expected_cols = ['years_active', 'victims', 'wikipedia_url', 'notes']
    for col in expected_cols:
        if col not in df.columns:
            warnings.append(f"Missing expected column: '{col}'")

    # Derived columns (should exist after cleaning)
    derived_cols = ['year_start', 'year_end', 'decade', 'victim_min', 'victim_max']
    for col in derived_cols:
        if col not in df.columns:
            warnings.append(f"Missing derived column: '{col}'")

    return errors, warnings


def validate_row_count(df):
    """Validate minimum row count"""
    errors = []
    warnings = []

    min_rows = 400
    if len(df) < min_rows:
        errors.append(f"Expected at least {min_rows} rows, found {len(df)}")
    elif len(df) < 450:
        warnings.append(f"Row count is low: {len(df)} (expected 500+)")

    return errors, warnings


def validate_names(df):
    """Validate name column"""
    errors = []
    warnings = []

    if 'name' not in df.columns:
        return errors, warnings

    # Check for null names
    null_names = df['name'].isnull().sum()
    if null_names > 0:
        errors.append(f"Found {null_names} rows with null names")

    # Check for empty names
    empty_names = (df['name'].str.strip() == '').sum()
    if empty_names > 0:
        errors.append(f"Found {empty_names} rows with empty names")

    # Check for duplicates
    duplicates = df['name'].duplicated().sum()
    if duplicates > 10:
        warnings.append(f"Found {duplicates} duplicate names (may be legitimate)")

    return errors, warnings


def validate_derived_columns(df):
    """Validate derived columns were computed correctly"""
    errors = []
    warnings = []

    # Check decade parsing success rate
    if 'decade' in df.columns and 'years_active' in df.columns:
        years_present = df['years_active'].notna().sum()
        decades_parsed = df['decade'].notna().sum()

        if years_present > 0:
            success_rate = decades_parsed / years_present
            if success_rate < 0.80:  # Less than 80% success
                errors.append(f"Decade parsing failed for {years_present - decades_parsed} rows ({success_rate:.1%} success rate)")
            elif success_rate < 0.90:
                warnings.append(f"Decade parsing below 90%: {success_rate:.1%} success rate")

    # Check victim count parsing
    if 'victim_min' in df.columns and 'victims' in df.columns:
        victims_present = df['victims'].notna().sum()
        victims_parsed = df['victim_min'].notna().sum()

        if victims_present > 0:
            success_rate = victims_parsed / victims_present
            if success_rate < 0.80:
                errors.append(f"Victim count parsing failed for {victims_present - victims_parsed} rows ({success_rate:.1%} success rate)")
            elif success_rate < 0.90:
                warnings.append(f"Victim count parsing below 90%: {success_rate:.1%} success rate")

    return errors, warnings


def validate_urls(df):
    """Validate Wikipedia URLs"""
    errors = []
    warnings = []

    if 'wikipedia_url' not in df.columns:
        return errors, warnings

    # Check for valid URLs
    non_null_urls = df['wikipedia_url'].notna().sum()
    if non_null_urls > 0:
        invalid_urls = ~df['wikipedia_url'].str.startswith('http', na=True)
        invalid_count = invalid_urls.sum()

        if invalid_count > non_null_urls * 0.1:  # More than 10% invalid
            errors.append(f"Found {invalid_count} invalid URLs ({invalid_count/non_null_urls:.1%})")
        elif invalid_count > 0:
            warnings.append(f"Found {invalid_count} invalid URLs")

    return errors, warnings


def validate_data_quality(df):
    """General data quality checks"""
    errors = []
    warnings = []

    # Check total missing data
    total_cells = df.shape[0] * df.shape[1]
    missing_cells = df.isnull().sum().sum()
    missing_pct = (missing_cells / total_cells) * 100

    if missing_pct > 50:
        errors.append(f"Excessive missing data: {missing_pct:.1f}% of all cells")
    elif missing_pct > 30:
        warnings.append(f"High missing data: {missing_pct:.1f}% of all cells")

    # Check for completely empty rows
    empty_rows = (df.isnull().sum(axis=1) == len(df.columns)).sum()
    if empty_rows > 0:
        errors.append(f"Found {empty_rows} completely empty rows")

    return errors, warnings


def run_all_validations(df):
    """Run all validation checks"""
    all_errors = []
    all_warnings = []

    # Run each validation
    validations = [
        ("Schema", validate_schema),
        ("Row Count", validate_row_count),
        ("Names", validate_names),
        ("Derived Columns", validate_derived_columns),
        ("URLs", validate_urls),
        ("Data Quality", validate_data_quality),
    ]

    for name, validator in validations:
        errors, warnings = validator(df)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    return all_errors, all_warnings


def print_validation_results(df, errors, warnings):
    """Print formatted validation results"""
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print()

    # Dataset info
    print("📊 Dataset Overview:")
    print(f"   Rows:    {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    print(f"   Missing: {df.isnull().sum().sum()} cells")
    print()

    # Errors
    if errors:
        print("❌ ERRORS FOUND:")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
        print()
    else:
        print("✅ No errors found")
        print()

    # Warnings
    if warnings:
        print("⚠️  WARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
        print()
    else:
        print("✅ No warnings")
        print()

    # Overall result
    print("=" * 80)
    if errors:
        print("❌ VALIDATION FAILED")
        print(f"   {len(errors)} error(s), {len(warnings)} warning(s)")
    elif warnings:
        print("⚠️  VALIDATION PASSED WITH WARNINGS")
        print(f"   {len(warnings)} warning(s)")
    else:
        print("✅ VALIDATION PASSED")
        print("   All checks successful!")
    print("=" * 80)


def main():
    """Main validation workflow"""
    print("✓ Serial Killers Dataset Validation")
    print()

    # Get dataset path (allow command-line override)
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = get_data_path()

    if not csv_path.exists():
        print(f"❌ Dataset not found: {csv_path}")
        print(f"   Run clean_data.py first to generate cleaned dataset.")
        return 1

    print(f"📂 Loading dataset: {csv_path}")

    try:
        # Load dataset
        df = pd.read_csv(csv_path)
        print(f"✅ Loaded {len(df)} rows")
        print()

        # Run validations
        print("🔍 Running validation checks...")
        errors, warnings = run_all_validations(df)
        print()

        # Print results
        print_validation_results(df, errors, warnings)

        # Exit code
        if errors:
            return 1
        else:
            return 0

    except Exception as e:
        print(f"❌ Error during validation: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
