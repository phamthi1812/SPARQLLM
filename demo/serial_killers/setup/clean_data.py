#!/usr/bin/env python3
"""
Data Cleaning Script for Serial Killers Dataset

Normalizes data for SPARQL consumption, adds derived columns.
"""

import sys
import re
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime


def get_data_path():
    """Get path to dataset CSV"""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    return data_dir / "serial_killers.csv", data_dir


def normalize_column_names(df):
    """Standardize column names to lowercase with underscores"""
    df.columns = df.columns.str.lower().str.replace(' ', '_').str.replace('-', '_')
    return df


def handle_missing_values(df):
    """Replace empty strings with NaN"""
    # Replace empty strings with NaN
    df = df.replace(r'^\s*$', np.nan, regex=True)
    df = df.replace('', np.nan)
    return df


def parse_years_active(years_str):
    """
    Parse years_active field into start and end years.

    Examples:
    - "1972-1978" → (1972, 1978)
    - "1995" → (1995, 1995)
    - "1995-present" → (1995, 2025)
    - "Unknown" → (None, None)
    """
    if pd.isna(years_str):
        return None, None

    years_str = str(years_str).strip()

    # Handle "present" or "now"
    current_year = datetime.now().year
    years_str = years_str.replace('present', str(current_year))
    years_str = years_str.replace('now', str(current_year))

    # Extract all 4-digit years
    year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', years_str)

    if len(year_matches) >= 2:
        return int(year_matches[0]), int(year_matches[-1])
    elif len(year_matches) == 1:
        year = int(year_matches[0])
        return year, year
    else:
        return None, None


def parse_victim_count(victims_str):
    """
    Parse victim count into min and max values.

    Examples:
    - "33" → (33, 33)
    - "10-15" → (10, 15)
    - "50+" → (50, None)
    - "Unknown" → (None, None)
    """
    if pd.isna(victims_str):
        return None, None

    victims_str = str(victims_str).strip()

    # Handle "+" notation (e.g., "50+")
    if '+' in victims_str:
        num_match = re.search(r'(\d+)', victims_str)
        if num_match:
            return int(num_match.group(1)), None
        return None, None

    # Extract all numbers
    numbers = re.findall(r'\d+', victims_str)

    if len(numbers) >= 2:
        # Range format (e.g., "10-15")
        return int(numbers[0]), int(numbers[-1])
    elif len(numbers) == 1:
        # Single number
        num = int(numbers[0])
        return num, num
    else:
        return None, None


def get_decade(year):
    """Get decade string from year (e.g., 1972 → "1970s")"""
    if pd.isna(year):
        return None
    try:
        decade_start = (int(year) // 10) * 10
        return f"{decade_start}s"
    except:
        return None


def add_derived_columns(df):
    """Add derived columns for temporal and victim analysis"""

    # Add decade based on start_year (if it exists directly)
    if 'start_year' in df.columns:
        df['decade'] = df['start_year'].apply(get_decade)
    # Otherwise parse from years_active field
    elif 'years_active' in df.columns:
        years_parsed = df['years_active'].apply(parse_years_active)
        df['year_start'] = years_parsed.apply(lambda x: x[0] if x else None)
        df['year_end'] = years_parsed.apply(lambda x: x[1] if x else None)
        df['decade'] = df['year_start'].apply(get_decade)

    # Use proven_victims as victim_min, possible_victims as victim_max (if they exist)
    if 'proven_victims' in df.columns and 'possible_victims' in df.columns:
        df['victim_min'] = df['proven_victims']
        df['victim_max'] = df['possible_victims']
    # Otherwise parse from victims field
    elif 'victims' in df.columns:
        victims_parsed = df['victims'].apply(parse_victim_count)
        df['victim_min'] = victims_parsed.apply(lambda x: x[0] if x else None)
        df['victim_max'] = victims_parsed.apply(lambda x: x[1] if x else None)

    return df


def validate_data_types(df):
    """Ensure columns have correct data types"""

    # Convert numeric columns
    numeric_cols = ['start_year', 'end_year', 'year_start', 'year_end',
                    'proven_victims', 'possible_victims', 'victim_min', 'victim_max']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Ensure string columns
    string_cols = ['name', 'country', 'years_active', 'methods', 'notes', 'wikipedia_url', 'decade']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('nan', np.nan)

    return df


def generate_cleaning_report(original_df, cleaned_df, output_path):
    """Generate report summarizing cleaning operations"""
    report = []

    report.append("=" * 80)
    report.append("DATA CLEANING REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # Row counts
    report.append("ROW COUNTS:")
    report.append(f"  Original: {len(original_df)}")
    report.append(f"  Cleaned:  {len(cleaned_df)}")
    report.append(f"  Removed:  {len(original_df) - len(cleaned_df)}")
    report.append("")

    # Column changes
    report.append("COLUMNS:")
    report.append(f"  Original: {list(original_df.columns)}")
    report.append(f"  Cleaned:  {list(cleaned_df.columns)}")
    report.append("")

    # Derived columns
    derived_cols = ['year_start', 'year_end', 'decade', 'victim_min', 'victim_max']
    existing_derived = [col for col in derived_cols if col in cleaned_df.columns]
    if existing_derived:
        report.append("DERIVED COLUMNS ADDED:")
        for col in existing_derived:
            non_null = cleaned_df[col].notna().sum()
            pct = (non_null / len(cleaned_df)) * 100
            report.append(f"  - {col}: {non_null}/{len(cleaned_df)} ({pct:.1f}%) computed")
        report.append("")

    # Missing data before/after
    report.append("MISSING DATA:")
    report.append(f"  Original: {original_df.isnull().sum().sum()} cells")
    report.append(f"  Cleaned:  {cleaned_df.isnull().sum().sum()} cells")
    report.append("")

    # Data quality metrics
    if 'year_start' in cleaned_df.columns:
        valid_years = cleaned_df['year_start'].notna().sum()
        report.append(f"TEMPORAL PARSING:")
        report.append(f"  Valid year ranges: {valid_years}/{len(cleaned_df)} ({valid_years/len(cleaned_df)*100:.1f}%)")
        if valid_years > 0:
            report.append(f"  Year range: {int(cleaned_df['year_start'].min())} - {int(cleaned_df['year_end'].max())}")
        report.append("")

    if 'victim_min' in cleaned_df.columns:
        valid_victims = cleaned_df['victim_min'].notna().sum()
        report.append(f"VICTIM COUNT PARSING:")
        report.append(f"  Valid counts: {valid_victims}/{len(cleaned_df)} ({valid_victims/len(cleaned_df)*100:.1f}%)")
        if valid_victims > 0:
            report.append(f"  Total victims (min): {int(cleaned_df['victim_min'].sum())}")
            report.append(f"  Average victims: {cleaned_df['victim_min'].mean():.1f}")
        report.append("")

    report.append("=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)

    full_report = "\n".join(report)
    output_path.write_text(full_report)

    return full_report


def main():
    """Main cleaning workflow"""
    print("🧹 Serial Killers Dataset Cleaning")
    print()

    # Get paths
    input_file, data_dir = get_data_path()
    if not input_file.exists():
        print(f"❌ Dataset not found: {input_file}")
        print(f"   Run download_data.py first to acquire the dataset.")
        return 1

    print(f"📂 Loading dataset: {input_file}")

    try:
        # Load original data
        df_original = pd.read_csv(input_file)
        print(f"✅ Loaded {len(df_original)} rows")
        print()

        # Create copy for cleaning
        df = df_original.copy()

        # Cleaning pipeline
        print("🔧 Applying cleaning operations...")
        df = normalize_column_names(df)
        print("  ✓ Column names normalized")

        df = handle_missing_values(df)
        print("  ✓ Missing values handled")

        df = add_derived_columns(df)
        print("  ✓ Derived columns added")

        df = validate_data_types(df)
        print("  ✓ Data types validated")
        print()

        # Save cleaned version (all rows)
        output_clean = data_dir / "serial_killers_clean.csv"
        df.to_csv(output_clean, index=False)
        print(f"💾 Cleaned dataset saved: {output_clean}")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        print()

        # Save complete cases (no critical nulls)
        critical_cols = ['name', 'victim_min']
        df_complete = df.dropna(subset=[col for col in critical_cols if col in df.columns])
        output_complete = data_dir / "serial_killers_complete.csv"
        df_complete.to_csv(output_complete, index=False)
        print(f"💾 Complete cases saved: {output_complete}")
        print(f"   Rows: {len(df_complete)}")
        print()

        # Generate report
        report_file = data_dir / "cleaning_report.txt"
        report = generate_cleaning_report(df_original, df, report_file)
        print(report)
        print()
        print(f"📊 Cleaning report saved: {report_file}")

        return 0

    except Exception as e:
        print(f"❌ Error during cleaning: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
