"""Dependency check: installs anything missing, then says whether the API key is visible (never prints it)."""
import importlib, os, subprocess, sys


def ensure(mod, pkg=None):
    pkg = pkg or mod
    try:
        importlib.import_module(mod); return True
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg]); return True
        except subprocess.CalledProcessError:
            return False


required = [("anthropic", "anthropic"), ("pypdf", "pypdf"), ("docx", "python-docx"),
            ("pytest", "pytest"), ("requests", "requests"), ("bs4", "beautifulsoup4"),
            ("ddgs", "ddgs")]
missing = [pkg for mod, pkg in required if not ensure(mod, pkg)]
print("MISSING:", missing if missing else "none")
print("ANTHROPIC_API_KEY:", "found" if os.environ.get("ANTHROPIC_API_KEY") else "NOT FOUND")
sys.exit(1 if missing else 0)
