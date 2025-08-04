#!/usr/bin/env python3
"""
Virtual Environment Setup Script for RTSP Camera Streaming Application
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import List, Tuple, Optional

def get_venv_path() -> Path:
    """Get the virtual environment path"""
    return Path("venv")

def get_activation_script() -> str:
    """Get the activation script path based on OS"""
    venv_path = get_venv_path()
    if platform.system() == "Windows":
        return str(venv_path / "Scripts" / "activate.bat")
    else:
        return str(venv_path / "bin" / "activate")

def get_python_executable() -> str:
    """Get the Python executable path in virtual environment"""
    venv_path = get_venv_path()
    if platform.system() == "Windows":
        return str(venv_path / "Scripts" / "python.exe")
    else:
        return str(venv_path / "bin" / "python")

def get_pip_executable() -> str:
    """Get the pip executable path in virtual environment"""
    venv_path = get_venv_path()
    if platform.system() == "Windows":
        return str(venv_path / "Scripts" / "pip.exe")
    else:
        return str(venv_path / "bin" / "pip")

def check_python_version() -> bool:
    """Check if Python version is 3.7 or higher"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        print(f"   Current version: {sys.version}")
        return False

    # Warning for very new Python versions
    if sys.version_info >= (3, 13):
        print(f"⚠️  You're using Python {sys.version_info.major}.{sys.version_info.minor}")
        print("   This is a very new version. If you encounter package compatibility issues,")
        print("   consider using Python 3.11 or 3.12 for better package support.")
        print()

    return True

def venv_exists() -> bool:
    """Check if virtual environment already exists"""
    return get_venv_path().exists()

def create_venv() -> bool:
    """Create virtual environment"""
    try:
        print("🔨 Creating virtual environment...")
        result = subprocess.run([
            sys.executable, "-m", "venv", "venv"
        ], check=True, capture_output=True, text=True)
        print("✅ Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr}")
        return False

def install_dependencies() -> bool:
    """Install project dependencies in virtual environment"""
    try:
        pip_executable = get_pip_executable()

        print("📦 Installing dependencies...")

        # Upgrade pip and setuptools first
        print("   Upgrading pip and setuptools...")
        subprocess.run([
            pip_executable, "install", "--upgrade", "pip", "setuptools", "wheel"
        ], check=True, capture_output=True)

        # Install project dependencies
        print("   Installing project dependencies...")
        result = subprocess.run([
            pip_executable, "install", "-r", "requirements.txt"
        ], check=True, capture_output=True, text=True)

        print("✅ Dependencies installed successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr}")

        # Provide helpful suggestions for common issues
        if "setuptools.build_meta" in str(e.stderr) or "numpy" in str(e.stderr):
            print("\n💡 Troubleshooting suggestions:")
            print("   1. Try using Python 3.11 or 3.12 instead of a newer version")
            print("   2. Make sure you have the latest pip: pip install --upgrade pip")
            print("   3. For macOS with Apple Silicon, try: pip install --upgrade setuptools")
            print("   4. If OpenCV fails, try: pip install opencv-python-headless instead")

        return False

def install_dev_dependencies() -> bool:
    """Install development dependencies (mypy for type checking)"""
    try:
        pip_executable = get_pip_executable()

        print("🛠️  Installing development dependencies...")
        result = subprocess.run([
            pip_executable, "install", "mypy>=1.7.0,<2.0.0"
        ], check=True, capture_output=True, text=True)

        print("✅ Development dependencies installed successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install development dependencies: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr}")
        print("   Note: You can still use the application without development dependencies")
        return False

def show_activation_instructions() -> None:
    """Show instructions for activating the virtual environment"""
    activation_script = get_activation_script()
    system = platform.system()

    print("\n🚀 Virtual environment setup complete!")
    print("=" * 50)
    print("To activate the virtual environment:")
    print()

    if system == "Windows":
        print(f"   {activation_script}")
        print("   # or")
        print("   venv\\Scripts\\activate.bat")
    else:
        print(f"   source {activation_script}")
        print("   # or")
        print("   source venv/bin/activate")

    print("\nTo deactivate:")
    print("   deactivate")

    print("\nTo run the application:")
    print("   python app.py")
    print("   # or")
    print("   python run.py")

    print("\nTo run type checking:")
    print("   python check_types.py")
    print("=" * 50)

def main() -> None:
    """Main setup function"""
    print("🎥 RTSP Camera Streaming - Virtual Environment Setup")
    print("=" * 55)

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    print(f"✅ Python {sys.version.split()[0]} detected")

    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        print("   Make sure you're running this script from the project root directory")
        sys.exit(1)

    # Create virtual environment if it doesn't exist
    if venv_exists():
        print("⚠️  Virtual environment already exists")
        response = input("   Recreate it? (y/N): ").lower().strip()
        if response == 'y':
            print("🗑️  Removing existing virtual environment...")
            import shutil
            shutil.rmtree(get_venv_path())
        else:
            print("   Using existing virtual environment")

    if not venv_exists():
        if not create_venv():
            sys.exit(1)

    # Install dependencies
    if not install_dependencies():
        print("\n⚠️  Dependency installation failed.")
        print("   You can try installing dependencies manually:")
        print("   1. Activate the virtual environment")
        print("   2. Run: pip install --upgrade pip setuptools wheel")
        print("   3. Run: pip install -r requirements.txt")

        response = input("\nContinue with setup anyway? (y/N): ").lower().strip()
        if response != 'y':
            sys.exit(1)

    # Ask about development dependencies
    print()
    install_dev = input("📋 Install development dependencies (mypy for type checking)? (Y/n): ").lower().strip()
    if install_dev != 'n':
        install_dev_dependencies()

    # Show activation instructions
    show_activation_instructions()

if __name__ == '__main__':
    main()