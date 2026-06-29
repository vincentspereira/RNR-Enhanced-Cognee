# Runbook RB-005: Adding a Custom Document Loader Plugin

**Applies to:** RNR Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Plugin developers

---

## Overview

RNR Enhanced Cognee discovers document loaders via Python package entry_points under the
group "enhanced_cognee.loaders". Three built-in loaders handle .txt/.md/.rst,
.json/.jsonl, and .html/.htm files. This runbook adds a custom loader for a new
file type without modifying the RNR Enhanced Cognee source.

The example below adds a CSV loader for a package named my_cognee_plugins.

---

## Step 1: Create the Loader Class

Create a Python file in your package, for example
my_cognee_plugins/loaders/csv_loader.py:

    from src.plugin_loader import EnhancedCogneeLoader
    import csv
    import io
    from pathlib import Path
    from typing import Any


    class CsvLoader(EnhancedCogneeLoader):
        """Load CSV files as line-separated key=value text."""

        SUPPORTED_EXTENSIONS = [".csv", ".tsv"]
        DISPLAY_NAME = "CSV Loader"
        DESCRIPTION = "Loads CSV and TSV files, returning each row as text."

        async def load(self, source: str, **kwargs: Any) -> str:
            path = Path(source)
            if not path.exists():
                raise IOError(f"File not found: {source}")

            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
            lines = []
            with path.open(encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh, delimiter=delimiter)
                for row in reader:
                    lines.append(
                        " | ".join(f"{k}={v}" for k, v in row.items())
                    )
            return "\n".join(lines)

Rules that every loader must satisfy:

- Inherit from EnhancedCogneeLoader (imported from src.plugin_loader).
- Implement async def load(self, source: str, **kwargs) -> str.
- Set SUPPORTED_EXTENSIONS to a list of lowercase extension strings (including
  the leading dot).
- Set DISPLAY_NAME and DESCRIPTION for the list_loader_plugins MCP tool output.
- Raise IOError if the file cannot be accessed.
- Raise ValueError if the source format is structurally invalid.

---

## Step 2: Add Entry Point Registration

In your package's pyproject.toml, add:

    [project.entry-points."enhanced_cognee.loaders"]
    csv_loader = "my_cognee_plugins.loaders.csv_loader:CsvLoader"

The key (csv_loader) is an arbitrary name used for logging. The value is the
fully qualified class path in the format "module.path:ClassName".

If your package uses setup.cfg instead of pyproject.toml:

    [options.entry_points]
    enhanced_cognee.loaders =
        csv_loader = my_cognee_plugins.loaders.csv_loader:CsvLoader

---

## Step 3: Install the Package

From the directory containing your plugin's pyproject.toml:

    pip install -e .

The -e flag installs in editable mode so changes to the loader class take effect
without reinstalling.

---

## Step 4: Restart the MCP Server

Entry points are read at server startup. Restart the MCP server to pick up the
newly registered loader:

    RNR-Enhanced-Cognee start

---

## Step 5: Verify Registration

    Tool: list_loader_plugins

Expected output includes your loader:

    [OK] 4 loader(s) registered
    - PlainTextLoader  (.txt, .md, .rst, .text)
    - JsonLoader       (.json, .jsonl, .ndjson)
    - HtmlLoader       (.html, .htm)
    - CsvLoader        (.csv, .tsv)     [my_cognee_plugins]

---

## Step 6: Test the Loader

    Tool: load_document_with_plugin
    Parameters:
      source: "/path/to/data.csv"

Expected output:

    [OK] Loaded 143 lines from data.csv using CsvLoader
    name=Alice | age=32 | department=Engineering
    name=Bob   | age=27 | department=Marketing
    ...

If the loader is not found, confirm that pip install -e . completed without errors
and that the entry_points group name is exactly "enhanced_cognee.loaders" (case
sensitive).

---

## Troubleshooting

**Loader not listed after restart**
Run pip show my-cognee-plugins and check that the package is installed in the same
Python environment as the MCP server.

**IOError on valid file path**
Ensure the path uses forward slashes or raw strings on Windows. The loader receives
the path exactly as passed by the MCP caller.

**TypeError: Can't instantiate abstract class**
The load() method is not implemented, or the method signature does not match
async def load(self, source: str, **kwargs) -> str. Check for typos or missing
async keyword.
