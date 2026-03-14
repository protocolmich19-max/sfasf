import os
import sys


def pytest_configure(config):
    # Ensure project root is on sys.path so `db` and `handlers` are importable
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)


