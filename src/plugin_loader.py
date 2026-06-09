"""
Plugin Loader - Phase 12 (17.1)
==================================
Provides a lightweight plugin system so third-party packages can extend
Enhanced Cognee with custom document loaders, memory processors, or search
backends without modifying the core codebase.

Plugin discovery:
    Plugins register themselves via Python package entry_points under the
    group "enhanced_cognee.loaders".  Example pyproject.toml snippet:

        [project.entry-points."enhanced_cognee.loaders"]
        csv_loader = "my_package.loaders:CsvLoader"

    Each loader must be a class that inherits from EnhancedCogneeLoader.

Built-in loaders (always available, no installation required):
    - PlainTextLoader   (handles .txt, .md, .rst)
    - JsonLoader        (handles .json, .jsonl)
    - HtmlLoader        (handles .html, .htm - requires BeautifulSoup if installed)

Usage:
    from src.plugin_loader import PluginRegistry
    reg = PluginRegistry()
    reg.discover()
    loader = reg.get_loader_for(".csv")
    content = await loader.load("/path/to/data.csv")
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)

ENTRY_POINTS_GROUP = "enhanced_cognee.loaders"


# ---------------------------------------------------------------------------
# Abstract base class for loaders
# ---------------------------------------------------------------------------

class EnhancedCogneeLoader(ABC):
    """
    Abstract base class for Enhanced Cognee document loaders.

    Subclass this and register via entry_points to add support for new
    file types or data sources.
    """

    #: List of file extensions this loader handles (e.g., [".csv", ".tsv"])
    SUPPORTED_EXTENSIONS: List[str] = []

    #: Human-readable display name
    DISPLAY_NAME: str = "Custom Loader"

    #: Short description shown in list_loaders()
    DESCRIPTION: str = ""

    @abstractmethod
    async def load(self, source: str, **kwargs: Any) -> str:
        """
        Load content from *source* (file path, URL, or connection string).
        Returns raw text content suitable for passing to cognify().

        Raises:
            ValueError  - if source format is invalid or unsupported
            IOError     - if source cannot be accessed
        """

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Return True if this loader can handle the given source."""
        ext = Path(source).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS

    def metadata(self) -> Dict[str, Any]:
        """Return loader metadata dict for list_loaders() output."""
        return {
            "name": type(self).__name__,
            "display_name": self.DISPLAY_NAME,
            "description": self.DESCRIPTION,
            "extensions": self.SUPPORTED_EXTENSIONS,
            "package": type(self).__module__.split(".")[0],
        }


# ---------------------------------------------------------------------------
# Built-in loaders
# ---------------------------------------------------------------------------

class PlainTextLoader(EnhancedCogneeLoader):
    """Load plain text files (.txt, .md, .rst)."""

    SUPPORTED_EXTENSIONS = [".txt", ".md", ".rst", ".text"]
    DISPLAY_NAME = "Plain Text Loader"
    DESCRIPTION = "Loads plain text, Markdown, and reStructuredText files."

    async def load(self, source: str, encoding: str = "utf-8", **kwargs: Any) -> str:
        path = Path(source)
        if not path.exists():
            raise IOError(f"File not found: {source}")
        return path.read_text(encoding=encoding)


class JsonLoader(EnhancedCogneeLoader):
    """Load JSON and JSON-Lines files."""

    SUPPORTED_EXTENSIONS = [".json", ".jsonl", ".ndjson"]
    DISPLAY_NAME = "JSON Loader"
    DESCRIPTION = "Loads JSON objects or JSON-Lines (one JSON object per line)."

    async def load(self, source: str, **kwargs: Any) -> str:
        import json
        path = Path(source)
        if not path.exists():
            raise IOError(f"File not found: {source}")

        raw = path.read_text(encoding="utf-8")
        # Try JSON-Lines first
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if all(ln.startswith("{") or ln.startswith("[") for ln in lines[:3]):
            parts = []
            for ln in lines:
                try:
                    obj = json.loads(ln)
                    parts.append(json.dumps(obj, ensure_ascii=True))
                except json.JSONDecodeError:
                    parts.append(ln)
            return "\n".join(parts)
        return raw


class HtmlLoader(EnhancedCogneeLoader):
    """Load HTML files, stripping tags (uses BeautifulSoup if available)."""

    SUPPORTED_EXTENSIONS = [".html", ".htm"]
    DISPLAY_NAME = "HTML Loader"
    DESCRIPTION = "Loads HTML files, extracting visible text content."

    async def load(self, source: str, **kwargs: Any) -> str:
        path = Path(source)
        if not path.exists():
            raise IOError(f"File not found: {source}")

        raw = path.read_text(encoding="utf-8")
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, "html.parser")
            return str(soup.get_text(separator="\n"))
        except ImportError:
            # Fallback: crude tag stripping
            import re
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text)
            return text.strip()


# ---------------------------------------------------------------------------
# Plugin Registry
# ---------------------------------------------------------------------------

_BUILTIN_LOADERS: List[Type[EnhancedCogneeLoader]] = [
    PlainTextLoader,
    JsonLoader,
    HtmlLoader,
]


class PluginRegistry:
    """
    Discover and manage Enhanced Cognee loader plugins.

    Call discover() once at startup; then use get_loader_for() to retrieve
    an appropriate loader instance for a given file or URL.
    """

    def __init__(self) -> None:
        self._loaders: List[EnhancedCogneeLoader] = []
        self._discovered = False

    def discover(self, skip_entry_points: bool = False) -> int:
        """
        Register all built-in loaders and discover installed plugins.

        Returns total number of loader classes registered.
        """
        # Register built-ins
        for cls in _BUILTIN_LOADERS:
            try:
                self._loaders.append(cls())
            except Exception as exc:
                logger.warning("Failed to instantiate built-in %s: %s", cls.__name__, exc)

        # Discover entry-point plugins
        if not skip_entry_points:
            try:
                eps = importlib.metadata.entry_points(group=ENTRY_POINTS_GROUP)
                for ep in eps:
                    try:
                        cls = ep.load()
                        if isinstance(cls, type) and issubclass(cls, EnhancedCogneeLoader):
                            self._loaders.append(cls())
                            logger.info(
                                "Loaded plugin: %s from %s", ep.name, ep.value
                            )
                        else:
                            logger.warning(
                                "Plugin %s is not an EnhancedCogneeLoader subclass", ep.name
                            )
                    except Exception as exc:
                        logger.error("Failed to load plugin %s: %s", ep.name, exc)
            except Exception as exc:
                logger.warning("entry_points discovery failed: %s", exc)

        self._discovered = True
        logger.info(
            "PluginRegistry: %d loader(s) registered", len(self._loaders)
        )
        return len(self._loaders)

    def get_loader_for(self, source: str) -> Optional[EnhancedCogneeLoader]:
        """
        Return the first registered loader that can handle *source*,
        or None if no loader matches.
        """
        for loader in self._loaders:
            if loader.can_handle(source):
                return loader
        return None

    def list_loaders(self) -> List[Dict[str, Any]]:
        """Return metadata for all registered loaders."""
        return [l.metadata() for l in self._loaders]

    def register(self, loader: EnhancedCogneeLoader) -> None:
        """Manually register a loader instance (for testing/extensions)."""
        self._loaders.append(loader)
        logger.debug("Manually registered loader: %s", type(loader).__name__)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_plugin_registry: Optional[PluginRegistry] = None


def init_plugin_registry(skip_entry_points: bool = False) -> PluginRegistry:
    """Initialise and return the module-level PluginRegistry singleton."""
    global _plugin_registry
    _plugin_registry = PluginRegistry()
    _plugin_registry.discover(skip_entry_points=skip_entry_points)
    return _plugin_registry


def get_plugin_registry() -> Optional[PluginRegistry]:
    return _plugin_registry
