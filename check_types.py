#!/usr/bin/env python3
"""
Type checking script for RTSP Camera Streaming Application
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

def check_mypy_installed() -> bool:
    """Check if mypy is installed"""
    try:
        subprocess.run(['mypy', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_type_check() -> int:
    """Run type checking on all Python files"""
    if not check_mypy_installed():
        print("❌ mypy is not installed.")
        print("Install it with: pip install mypy==1.7.1")
        return 1

    # Files to check
    files_to_check: List[str] = [
        'app.py',
        'config.py',
        'run.py',
        'check_types.py'
    ]

    print("🔍 Running type checking with mypy...")
    print("=" * 50)

    # Run mypy on each file
    all_passed: bool = True
    for file_path in files_to_check:
        if not Path(file_path).exists():
            print(f"⚠️  Skipping {file_path} (file not found)")
            continue

        print(f"Checking {file_path}...")
        try:
            result = subprocess.run(
                ['mypy', file_path],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                print(f"✅ {file_path} - No type errors found")
            else:
                print(f"❌ {file_path} - Type errors found:")
                print(result.stdout)
                if result.stderr:
                    print("Errors:", result.stderr)
                all_passed = False

        except Exception as e:
            print(f"❌ Error checking {file_path}: {e}")
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("🎉 All type checks passed!")
        return 0
    else:
        print("💥 Some type checks failed. Please fix the errors above.")
        return 1

def main() -> None:
    """Main function"""
    print("🎯 RTSP Camera Streaming - Type Checker")
    print("=" * 50)

    exit_code: int = run_type_check()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()