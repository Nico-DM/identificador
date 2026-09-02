import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("DISABLE_DATABASE", "1")
os.environ.setdefault("ENVIRONMENT", "development")
