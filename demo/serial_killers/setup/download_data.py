#!/usr/bin/env python3
"""
Dataset Acquisition Script for Serial Killers Demo

Downloads Wikipedia Serial Killers dataset from Kaggle.
Supports manual download instructions or Kaggle API.
"""

import os
import sys
from pathlib import Path
import hashlib


def get_data_dir():
    """Get absolute path to data directory"""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def check_kaggle_cli():
    """Check if Kaggle CLI is installed"""
    try:
        import kaggle
        return True
    except ImportError:
        return False


def verify_file(filepath):
    """Verify downloaded file exists and has reasonable size"""
    if not filepath.exists():
        return False, "File not found"

    size = filepath.stat().st_size
    if size < 50000:  # Less than 50KB seems too small
        return False, f"File too small: {size} bytes (expected > 50KB)"

    return True, f"File verified: {size:,} bytes"


def download_with_kaggle_api(data_dir):
    """Download dataset using Kaggle API"""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        print("🔄 Initializing Kaggle API...")
        api = KaggleApi()
        api.authenticate()

        print("📥 Downloading dataset: dante890b/wikipedia-serial-killers-list")
        dataset_name = "dante890b/wikipedia-serial-killers-list"

        # Download to temp directory
        temp_dir = data_dir / "temp"
        temp_dir.mkdir(exist_ok=True)

        api.dataset_download_files(dataset_name, path=str(temp_dir), unzip=True)

        # Find the CSV file
        csv_files = list(temp_dir.glob("*.csv"))
        if not csv_files:
            return False, "No CSV file found in downloaded archive"

        # Move to data directory
        source_file = csv_files[0]
        target_file = data_dir / "serial_killers.csv"
        source_file.rename(target_file)

        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir)

        return True, str(target_file)

    except Exception as e:
        return False, f"Kaggle API error: {str(e)}"


def print_manual_instructions(data_dir):
    """Print manual download instructions"""
    target_path = data_dir / "serial_killers.csv"

    print("\n" + "="*70)
    print("📋 MANUAL DOWNLOAD INSTRUCTIONS")
    print("="*70)
    print()
    print("1. Sign up for a free Kaggle account (if you don't have one):")
    print("   👉 https://www.kaggle.com")
    print()
    print("2. Go to the dataset page:")
    print("   👉 https://www.kaggle.com/datasets/dante890b/wikipedia-serial-killers-list")
    print()
    print("3. Click 'Download' button (top right)")
    print()
    print("4. Extract the downloaded ZIP file")
    print()
    print("5. Copy the CSV file to this location:")
    print(f"   👉 {target_path}")
    print()
    print("="*70)
    print()
    print("After downloading, run this script again to verify the file.")
    print()


def main():
    """Main download workflow"""
    print("🎯 Serial Killers Dataset Acquisition")
    print("Dataset: Wikipedia Serial Killers List (Kaggle)")
    print()

    data_dir = get_data_dir()
    target_file = data_dir / "serial_killers.csv"

    # Check if file already exists
    if target_file.exists():
        success, message = verify_file(target_file)
        if success:
            print(f"✅ Dataset already exists: {target_file}")
            print(f"   {message}")
            return 0
        else:
            print(f"⚠️  Existing file has issues: {message}")
            print("   Will attempt to re-download...")

    # Try Kaggle API first
    if check_kaggle_cli():
        print("✅ Kaggle CLI detected. Attempting automatic download...")
        success, result = download_with_kaggle_api(data_dir)

        if success:
            print(f"✅ Dataset downloaded successfully!")
            print(f"   Location: {result}")

            # Verify
            verify_success, verify_msg = verify_file(Path(result))
            print(f"   {verify_msg}")
            return 0
        else:
            print(f"❌ Automatic download failed: {result}")
            print("   Falling back to manual instructions...")
    else:
        print("ℹ️  Kaggle CLI not installed (optional)")
        print("   Install with: pip install kaggle")
        print()

    # Manual instructions
    print_manual_instructions(data_dir)

    # Check if user manually downloaded
    if target_file.exists():
        success, message = verify_file(target_file)
        if success:
            print(f"✅ File verified successfully!")
            print(f"   {message}")
            return 0

    print("⏳ Waiting for manual download...")
    print(f"   Run this script again after placing CSV at: {target_file}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
