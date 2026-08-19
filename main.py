"""Hospital Management System – application entry point.

Run this file to start the application:

    python main.py
"""
import sys
import os

# Ensure the project root is on the Python path so that ``src`` imports work
# regardless of where the script is executed from.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.app import main

if __name__ == "__main__":
    main()
