#!/usr/bin/env python3
"""
Data Inspection Script for Serial Killers Dataset

Analyzes CSV schema, data quality, and generates inspection report.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime


def get_data_path():
    """Get path to dataset CSV"""
    script_dir = Path(__file__).parent
    data_file = script_dir.parent / "data" / "serial_killers.csv"
    return data_file


def analyze_schema(df):
    """Analyze DataFrame schema"""
    report = []
    report.append("=" * 80)
    report.append("SCHEMA ANALYSIS")
    report.append("=" * 80)
    report.append(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
    report.append(f"\nColumns: {df.columns.tolist()}")
    report.append(f"\nData Types:")
    for col, dtype in df.dtypes.items():
        report.append(f"  - {col}: {dtype}")
    report.append(f"\nMemory Usage: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")
    return "\n".join(report)


def analyze_missing_data(df):
    """Analyze missing values"""
    report = []
    report.append("\n" + "=" * 80)
    report.append("MISSING DATA ANALYSIS")
    report.append("=" * 80)

    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100

    report.append(f"\nTotal Missing Values: {missing.sum()}")
    report.append(f"\nPer Column:")
    for col in df.columns:
        count = missing[col]
        pct = missing_pct[col]
        if count > 0:
            report.append(f"  ❌ {col}: {count} ({pct:.1f}%)")
        else:
            report.append(f"  ✅ {col}: 0 (0.0%)")

    return "\n".join(report)


def analyze_distributions(df):
    """Analyze value distributions"""
    report = []
    report.append("\n" + "=" * 80)
    report.append("VALUE DISTRIBUTIONS")
    report.append("=" * 80)

    for col in df.columns:
        report.append(f"\n📊 {col}")
        report.append(f"   Unique values: {df[col].nunique()}")

        # For numeric columns
        if pd.api.types.is_numeric_dtype(df[col]):
            report.append(f"   Min: {df[col].min()}")
            report.append(f"   Max: {df[col].max()}")
            report.append(f"   Mean: {df[col].mean():.2f}")
            report.append(f"   Median: {df[col].median():.2f}")

        # Show top values for categorical columns
        elif df[col].nunique() < 50:
            top_vals = df[col].value_counts().head(5)
            report.append(f"   Top values:")
            for val, count in top_vals.items():
                report.append(f"     - {val}: {count}")

    return "\n".join(report)


def analyze_data_quality(df):
    """Analyze data quality issues"""
    report = []
    report.append("\n" + "=" * 80)
    report.append("DATA QUALITY CHECKS")
    report.append("=" * 80)

    issues = []

    # Check for duplicate rows
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        issues.append(f"❌ Duplicate rows: {duplicates}")
    else:
        report.append("✅ No duplicate rows")

    # Check for empty strings
    for col in df.select_dtypes(include=['object']).columns:
        empty_strings = (df[col] == '').sum()
        if empty_strings > 0:
            issues.append(f"❌ Empty strings in '{col}': {empty_strings}")

    # Check for whitespace-only strings
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].dtype == 'object':
            whitespace = df[col].str.strip().eq('').sum()
            if whitespace > 0:
                issues.append(f"❌ Whitespace-only in '{col}': {whitespace}")

    if issues:
        report.append("\n⚠️  Issues Found:")
        report.extend([f"   {issue}" for issue in issues])
    else:
        report.append("\n✅ No data quality issues detected")

    return "\n".join(report)


def show_sample_rows(df, n=5):
    """Show sample rows"""
    report = []
    report.append("\n" + "=" * 80)
    report.append(f"SAMPLE ROWS (first {n})")
    report.append("=" * 80)
    report.append("\n" + df.head(n).to_string())
    return "\n".join(report)


def generate_inspection_report(df, output_file):
    """Generate complete inspection report"""
    report = []

    # Header
    report.append("=" * 80)
    report.append("SERIAL KILLERS DATASET - INSPECTION REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # Analysis sections
    report.append(analyze_schema(df))
    report.append(analyze_missing_data(df))
    report.append(analyze_distributions(df))
    report.append(analyze_data_quality(df))
    report.append(show_sample_rows(df))

    # Footer
    report.append("\n" + "=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)

    full_report = "\n".join(report)

    # Save to file
    output_file.write_text(full_report)

    return full_report


def main():
    """Main inspection workflow"""
    print("🔍 Serial Killers Dataset Inspection")
    print()

    # Check if dataset exists
    data_file = get_data_path()
    if not data_file.exists():
        print(f"❌ Dataset not found: {data_file}")
        print(f"   Run download_data.py first to acquire the dataset.")
        return 1

    print(f"📂 Loading dataset: {data_file}")

    try:
        # Load CSV
        df = pd.read_csv(data_file)
        print(f"✅ Loaded {len(df)} rows")
        print()

        # Generate report
        output_file = data_file.parent / "inspection_report.txt"
        report = generate_inspection_report(df, output_file)

        # Print to console
        print(report)

        # Save confirmation
        print(f"\n💾 Report saved to: {output_file}")

        return 0

    except Exception as e:
        print(f"❌ Error during inspection: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
