#!/usr/bin/env python3
"""Standalone stdlib entry point; deliberately avoids runtime/AI imports."""
import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "src/hermes_memory/library.py"
spec = importlib.util.spec_from_file_location("enhanced_cognee_owned_library", MODULE)
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)

if __name__ == "__main__":
    raise SystemExit(library.main())
