# Dataset Setup Scripts

This directory contains scripts for acquiring and preparing the Serial Killers dataset.

## Quick Start

```bash
cd demo/serial_killers/setup

# Step 1: Download dataset (manual or API)
python download_data.py

# Step 2: Inspect raw data
python inspect_data.py

# Step 3: Clean and normalize data
python clean_data.py

# Step 4: Validate cleaned data
python validate_data.py
```

## Scripts

### 1. download_data.py

Downloads Wikipedia Serial Killers dataset from Kaggle.

**Methods:**
- **Automatic:** Uses Kaggle API (requires `pip install kaggle` + API credentials)
- **Manual:** Provides download instructions

**Output:**
- `../data/serial_killers.csv` - Raw dataset

**Usage:**
```bash
# Try automatic download
python download_data.py

# Or follow manual instructions printed by the script
```

### 2. inspect_data.py

Generates inspection report analyzing raw data quality.

**Analysis:**
- Schema (columns, data types)
- Missing data percentages
- Value distributions
- Data quality issues

**Output:**
- `../data/inspection_report.txt` - Detailed analysis report

**Usage:**
```bash
python inspect_data.py
```

### 3. clean_data.py

Cleans and normalizes data for SPARQL consumption.

**Operations:**
- Normalize column names (lowercase, underscores)
- Handle missing values
- Parse temporal data (years → year_start, year_end, decade)
- Parse victim counts (ranges → victim_min, victim_max)
- Validate data types

**Output:**
- `../data/serial_killers_clean.csv` - Cleaned dataset (all rows)
- `../data/serial_killers_complete.csv` - Complete cases only (no critical nulls)
- `../data/cleaning_report.txt` - Cleaning summary

**Usage:**
```bash
python clean_data.py
```

### 4. validate_data.py

Validates cleaned dataset against quality criteria.

**Checks:**
- Required columns present
- Minimum row count (400+)
- Name completeness
- Derived column parsing success
- URL validity
- Overall data quality

**Exit Code:**
- `0` - Validation passed
- `1` - Validation failed

**Usage:**
```bash
# Validate default cleaned dataset
python validate_data.py

# Validate specific file
python validate_data.py ../data/serial_killers_complete.csv
```

## Dataset Schema

### Raw Columns
- `name` - Serial killer name
- `years_active` - Years active (e.g., "1972-1978", "1995")
- `victims` - Victim count (e.g., "33", "10-15", "50+")
- `methods` - Methods used
- `notes` - Additional notes
- `wikipedia_url` - Wikipedia article URL

### Derived Columns (added by cleaning)
- `year_start` (int) - Start year
- `year_end` (int) - End year
- `decade` (string) - Decade (e.g., "1970s")
- `victim_min` (int) - Minimum victim count
- `victim_max` (int) - Maximum victim count

## Dependencies

```bash
pip install pandas numpy
pip install kaggle  # Optional: for automatic download
```

## Troubleshooting

### Kaggle API Authentication

If using Kaggle API, create `~/.kaggle/kaggle.json`:

```json
{
  "username": "your_username",
  "key": "your_api_key"
}
```

Get credentials from: https://www.kaggle.com/settings

### Manual Download Issues

If download fails:
1. Download manually from: https://www.kaggle.com/datasets/dante890b/wikipedia-serial-killers-list
2. Extract ZIP file
3. Copy CSV to: `demo/serial_killers/data/serial_killers.csv`
4. Run `python inspect_data.py` to verify

### Validation Failures

Common issues:
- **Missing columns:** Check raw CSV has expected columns
- **Low row count:** Ensure complete CSV was downloaded
- **Parsing failures:** Inspect `cleaning_report.txt` for details
