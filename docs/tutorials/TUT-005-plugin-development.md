# Tutorial 05: Writing a Custom Loader Plugin

**Audience:** Plugin developers
**Time required:** 30 minutes
**Prerequisites:** Python packaging knowledge; RNR Enhanced Cognee installed in a
  virtual environment; see RB-005 for the operational steps

---

## Overview

RNR Enhanced Cognee discovers document loaders via Python's entry_points mechanism.
You write a class, register it in your package's pyproject.toml, and Enhanced
Cognee picks it up automatically at startup -- no changes to the RNR Enhanced Cognee
source are needed.

This tutorial builds a YAML loader step by step.

---

## Step 1: Understand the Base Class

All loaders must subclass EnhancedCogneeLoader from src.plugin_loader:

    from src.plugin_loader import EnhancedCogneeLoader
    from typing import Any

    class EnhancedCogneeLoader:         # abstract base (for reference)
        SUPPORTED_EXTENSIONS: list      # e.g. [".yaml", ".yml"]
        DISPLAY_NAME: str               # shown in list_loader_plugins
        DESCRIPTION: str                # shown in list_loader_plugins

        async def load(self, source: str, **kwargs: Any) -> str:
            ...  # must return plain text content

        @classmethod
        def can_handle(cls, source: str) -> bool:
            ...  # auto-implemented from SUPPORTED_EXTENSIONS

The load() method receives a file path (or URL for future loaders) and must return
a string. That string is passed directly to cognify() for knowledge graph ingestion.

---

## Step 2: Write the YAML Loader

Create a file my_cognee_plugins/loaders/yaml_loader.py:

    """
    YAML Loader for RNR Enhanced Cognee.
    Converts YAML documents to readable key=value text for cognify ingestion.
    """

    from src.plugin_loader import EnhancedCogneeLoader
    from pathlib import Path
    from typing import Any


    class YamlLoader(EnhancedCogneeLoader):
        """Load YAML configuration and data files."""

        SUPPORTED_EXTENSIONS = [".yaml", ".yml"]
        DISPLAY_NAME = "YAML Loader"
        DESCRIPTION = "Loads YAML files, flattening nested keys into readable text."

        async def load(self, source: str, **kwargs: Any) -> str:
            path = Path(source)
            if not path.exists():
                raise IOError(f"File not found: {source}")

            try:
                import yaml
            except ImportError:
                raise ImportError(
                    "PyYAML is required for YamlLoader. Run: pip install pyyaml"
                )

            with path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh)

            if data is None:
                return ""

            return self._flatten(data)

        def _flatten(self, obj, prefix=""):
            lines = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    lines.extend(self._flatten(value, full_key))
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    full_key = f"{prefix}[{i}]"
                    lines.extend(self._flatten(item, full_key))
            else:
                lines.append(f"{prefix} = {obj}")
            return lines

Key design points:
- The load() method is async. Even if the work is synchronous, the signature
  must include async so the PluginRegistry can await it consistently.
- Import optional dependencies inside load() so the loader can be registered
  without requiring the dependency to be installed. The ImportError will only
  surface when load() is actually called.
- Raise IOError for access problems and ImportError or ValueError for structural
  issues. Do not swallow exceptions silently.

---

## Step 3: Add the Package Structure

Create a minimal package:

    my_cognee_plugins/
      __init__.py
      loaders/
        __init__.py
        yaml_loader.py
    pyproject.toml

pyproject.toml:

    [project]
    name = "my-cognee-plugins"
    version = "0.1.0"
    requires-python = ">=3.10"
    dependencies = ["pyyaml>=6.0"]

    [project.entry-points."enhanced_cognee.loaders"]
    yaml_loader = "my_cognee_plugins.loaders.yaml_loader:YamlLoader"

    [build-system]
    requires = ["setuptools>=68"]
    build-backend = "setuptools.backends.legacy:build"

The entry_points group must be exactly "enhanced_cognee.loaders". The key
(yaml_loader) is an arbitrary label used in log output. The value is the import
path to the class.

---

## Step 4: Install and Verify

    pip install -e .
    RNR-Enhanced-Cognee start

    Tool: list_loader_plugins

Expected:

    [OK] 4 loader(s) registered
    - PlainTextLoader  (.txt, .md, .rst, .text)  [RNR-Enhanced-Cognee built-in]
    - JsonLoader       (.json, .jsonl, .ndjson)   [RNR-Enhanced-Cognee built-in]
    - HtmlLoader       (.html, .htm)              [RNR-Enhanced-Cognee built-in]
    - YamlLoader       (.yaml, .yml)              [my-cognee-plugins]

---

## Step 5: Test with a Real File

Create a test YAML file:

    # config.yaml
    database:
      host: localhost
      port: 25432
    features:
      versioning: true
      gdpr: true

Call the loader:

    Tool: load_document_with_plugin
    Parameters:
      source: "/path/to/config.yaml"

Expected response:

    [OK] Loaded 5 lines from config.yaml using YamlLoader
    database.host = localhost
    database.port = 25432
    features.versioning = True
    features.gdpr = True

You can now pass this content directly to cognify() to index it in the knowledge
graph.

---

## Common Mistakes

**Missing async on load()**
The PluginRegistry expects an awaitable. A synchronous load() raises TypeError
at call time.

**Catching all exceptions in load()**
If load() catches and suppresses an IOError, the caller cannot distinguish a
missing file from an empty file. Let access errors propagate.

**Hardcoding file paths in SUPPORTED_EXTENSIONS**
SUPPORTED_EXTENSIONS must contain lowercase extension strings starting with a dot:
[".yaml", ".yml"] not ["yaml", "yml"] or [".YAML"].

---

## What to Read Next

- RB-005: Adding a Custom Loader -- operational steps for deployment
- ADR-005: Graceful Degradation -- how the registry handles a loader that fails
  to instantiate at startup
