"""
Unit tests for src/plugin_loader.py

Covers PluginRegistry, EnhancedCogneeLoader subclasses, singleton helpers.
Filesystem access is mocked for loader tests.
ASCII-only assertions.
"""

import asyncio
import json
import pytest
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.plugin_loader import (  # noqa: E402
    PluginRegistry,
    PlainTextLoader,
    JsonLoader,
    HtmlLoader,
    EnhancedCogneeLoader,
    init_plugin_registry,
    get_plugin_registry,
    ENTRY_POINTS_GROUP,
)


# ---------------------------------------------------------------------------
# Tests: EnhancedCogneeLoader abstract interface
# ---------------------------------------------------------------------------

class TestEnhancedCogneeLoaderABC:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            EnhancedCogneeLoader()

    def test_can_handle_checks_extension(self):
        assert PlainTextLoader.can_handle("document.txt") is True
        assert PlainTextLoader.can_handle("archive.zip") is False

    def test_can_handle_case_insensitive(self):
        assert PlainTextLoader.can_handle("README.MD") is True
        assert PlainTextLoader.can_handle("data.TXT") is True

    def test_metadata_returns_dict(self):
        loader = PlainTextLoader()
        meta = loader.metadata()
        assert isinstance(meta, dict)
        assert "name" in meta
        assert "display_name" in meta
        assert "extensions" in meta
        assert "package" in meta


# ---------------------------------------------------------------------------
# Tests: PlainTextLoader
# ---------------------------------------------------------------------------

class TestPlainTextLoader:
    @pytest.mark.asyncio
    async def test_load_existing_file(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("Hello, World!")
        loader = PlainTextLoader()
        content = await loader.load(str(f))
        assert content == "Hello, World!"

    @pytest.mark.asyncio
    async def test_load_nonexistent_raises_ioerror(self):
        loader = PlainTextLoader()
        with pytest.raises(IOError):
            await loader.load("/no/such/file.txt")

    @pytest.mark.asyncio
    async def test_load_md_file(self, tmp_path):
        f = tmp_path / "README.md"
        f.write_text("# Title\nBody text.")
        loader = PlainTextLoader()
        content = await loader.load(str(f))
        assert "Title" in content

    @pytest.mark.asyncio
    async def test_load_rst_file(self, tmp_path):
        f = tmp_path / "doc.rst"
        f.write_text(".. title::\n   My Docs")
        loader = PlainTextLoader()
        content = await loader.load(str(f))
        assert "My Docs" in content

    def test_supported_extensions(self):
        assert ".txt" in PlainTextLoader.SUPPORTED_EXTENSIONS
        assert ".md" in PlainTextLoader.SUPPORTED_EXTENSIONS
        assert ".rst" in PlainTextLoader.SUPPORTED_EXTENSIONS


# ---------------------------------------------------------------------------
# Tests: JsonLoader
# ---------------------------------------------------------------------------

class TestJsonLoader:
    @pytest.mark.asyncio
    async def test_load_valid_json(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"key": "value", "num": 42}))
        loader = JsonLoader()
        content = await loader.load(str(f))
        assert "key" in content

    @pytest.mark.asyncio
    async def test_load_jsonlines(self, tmp_path):
        lines = [json.dumps({"id": i}) for i in range(3)]
        f = tmp_path / "data.jsonl"
        f.write_text("\n".join(lines))
        loader = JsonLoader()
        content = await loader.load(str(f))
        assert content  # should be non-empty

    @pytest.mark.asyncio
    async def test_load_nonexistent_raises_ioerror(self):
        loader = JsonLoader()
        with pytest.raises(IOError):
            await loader.load("/no/such/data.json")

    @pytest.mark.asyncio
    async def test_load_plain_text_json_file(self, tmp_path):
        """When content doesn't look like JSONL, returns raw content."""
        f = tmp_path / "doc.json"
        f.write_text("just plain text, not json")
        loader = JsonLoader()
        content = await loader.load(str(f))
        assert "just plain text" in content

    def test_can_handle_jsonl(self):
        assert JsonLoader.can_handle("data.jsonl") is True

    def test_can_handle_ndjson(self):
        assert JsonLoader.can_handle("data.ndjson") is True


# ---------------------------------------------------------------------------
# Tests: HtmlLoader
# ---------------------------------------------------------------------------

class TestHtmlLoader:
    @pytest.mark.asyncio
    async def test_load_html_with_beautifulsoup(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<html><body><h1>Title</h1><p>Body text.</p></body></html>")
        loader = HtmlLoader()
        content = await loader.load(str(f))
        assert "Title" in content
        assert "Body text" in content

    @pytest.mark.asyncio
    async def test_load_html_fallback_without_bs4(self, tmp_path):
        f = tmp_path / "page.html"
        f.write_text("<html><body><p>Hello World</p></body></html>")
        loader = HtmlLoader()
        with patch.dict("sys.modules", {"bs4": None}):
            content = await loader.load(str(f))
        assert "Hello World" in content

    @pytest.mark.asyncio
    async def test_load_nonexistent_html_raises_ioerror(self):
        loader = HtmlLoader()
        with pytest.raises(IOError):
            await loader.load("/no/such/page.html")

    def test_can_handle_htm(self):
        assert HtmlLoader.can_handle("index.htm") is True

    def test_can_handle_html(self):
        assert HtmlLoader.can_handle("page.html") is True


# ---------------------------------------------------------------------------
# Tests: PluginRegistry
# ---------------------------------------------------------------------------

class TestPluginRegistry:
    def test_init_empty(self):
        reg = PluginRegistry()
        assert reg._loaders == []
        assert reg._discovered is False

    def test_discover_registers_builtins(self):
        reg = PluginRegistry()
        count = reg.discover(skip_entry_points=True)
        assert count == 3  # PlainText, Json, Html
        assert reg._discovered is True

    def test_discover_idempotent_add(self):
        """discover() always appends, even if called twice."""
        reg = PluginRegistry()
        reg.discover(skip_entry_points=True)
        reg.discover(skip_entry_points=True)
        assert len(reg._loaders) == 6  # 3+3

    def test_get_loader_for_txt(self):
        reg = PluginRegistry()
        reg.discover(skip_entry_points=True)
        loader = reg.get_loader_for("file.txt")
        assert loader is not None
        assert isinstance(loader, PlainTextLoader)

    def test_get_loader_for_json(self):
        reg = PluginRegistry()
        reg.discover(skip_entry_points=True)
        loader = reg.get_loader_for("data.json")
        assert loader is not None
        assert isinstance(loader, JsonLoader)

    def test_get_loader_for_html(self):
        reg = PluginRegistry()
        reg.discover(skip_entry_points=True)
        loader = reg.get_loader_for("page.html")
        assert loader is not None
        assert isinstance(loader, HtmlLoader)

    def test_get_loader_for_unknown_returns_none(self):
        reg = PluginRegistry()
        reg.discover(skip_entry_points=True)
        loader = reg.get_loader_for("archive.zip")
        assert loader is None

    def test_list_loaders_after_discover(self):
        reg = PluginRegistry()
        reg.discover(skip_entry_points=True)
        loaders = reg.list_loaders()
        assert len(loaders) == 3
        names = [l["name"] for l in loaders]
        assert "PlainTextLoader" in names
        assert "JsonLoader" in names
        assert "HtmlLoader" in names

    def test_register_custom_loader(self):
        reg = PluginRegistry()
        reg.discover(skip_entry_points=True)

        class _CsvLoader(EnhancedCogneeLoader):
            SUPPORTED_EXTENSIONS = [".csv"]
            DISPLAY_NAME = "CSV Loader"
            DESCRIPTION = "Loads CSV files."
            async def load(self, source, **kwargs):
                return "csv content"

        loader_instance = _CsvLoader()
        reg.register(loader_instance)
        assert reg.get_loader_for("data.csv") is loader_instance

    def test_discover_with_entry_points(self):
        """Entry points discovery runs without error even with no plugins installed."""
        reg = PluginRegistry()
        count = reg.discover(skip_entry_points=False)
        assert count >= 3  # at least the 3 builtins

    def test_discover_entry_points_failure_does_not_crash(self):
        """If entry_points discovery raises, built-ins are still registered."""
        reg = PluginRegistry()
        with patch("importlib.metadata.entry_points", side_effect=RuntimeError("metadata fail")):
            count = reg.discover(skip_entry_points=False)
        assert count >= 3

    def test_discover_invalid_plugin_class_logged(self):
        """Entry point that is not an EnhancedCogneeLoader subclass is skipped."""
        reg = PluginRegistry()

        class _NotALoader:
            pass

        fake_ep = MagicMock()
        fake_ep.name = "bad_plugin"
        fake_ep.value = "some.module:BadClass"
        fake_ep.load = MagicMock(return_value=_NotALoader)

        with patch("importlib.metadata.entry_points", return_value=[fake_ep]):
            count = reg.discover(skip_entry_points=False)
        # Built-ins still registered, bad plugin skipped
        assert count == 3

    def test_discover_plugin_load_exception_skipped(self):
        """Entry point that fails to load is skipped."""
        reg = PluginRegistry()

        fake_ep = MagicMock()
        fake_ep.name = "crash_plugin"
        fake_ep.value = "bad.module:CrashClass"
        fake_ep.load = MagicMock(side_effect=ImportError("not found"))

        with patch("importlib.metadata.entry_points", return_value=[fake_ep]):
            count = reg.discover(skip_entry_points=False)
        assert count == 3

    def test_discover_builtin_instantiation_error_skipped(self):
        """If a built-in loader cannot be instantiated, it is skipped."""
        with patch.object(PlainTextLoader, "__init__", side_effect=RuntimeError("init fail")):
            reg = PluginRegistry()
            count = reg.discover(skip_entry_points=True)
        # PlainText failed, so only Json and Html registered
        assert count == 2

    def test_list_loaders_empty_before_discover(self):
        reg = PluginRegistry()
        assert reg.list_loaders() == []


# ---------------------------------------------------------------------------
# Tests: Singleton helpers
# ---------------------------------------------------------------------------

class TestSingletonHelpers:
    def test_init_and_get_singleton(self):
        reg = init_plugin_registry(skip_entry_points=True)
        assert reg is not None
        assert get_plugin_registry() is reg

    def test_get_singleton_before_init_returns_none_or_previous(self):
        # After the test above, singleton is set - just verify it returns something
        result = get_plugin_registry()
        assert result is not None  # initialized in previous test

    def test_init_creates_fresh_registry(self):
        first = init_plugin_registry(skip_entry_points=True)
        second = init_plugin_registry(skip_entry_points=True)
        # Each init creates a new instance
        assert first is not second
        # But get returns the latest
        assert get_plugin_registry() is second


# ---------------------------------------------------------------------------
# Tests: JsonLoader JSON-Lines parse error path (lines 133-134)
# ---------------------------------------------------------------------------

class TestJsonLoaderParseError:
    @pytest.mark.asyncio
    async def test_json_lines_with_invalid_line_falls_back(self, tmp_path):
        """Line 133-134: JSONDecodeError on a line -> append raw line."""
        # All first 3 lines must start with { or [ to enter JSON-Lines mode.
        # The second line starts with { but is invalid JSON.
        f = tmp_path / "mixed.jsonl"
        f.write_text('{"key": "value"}\n{INVALID_JSON}\n{"b": 2}\n', encoding="utf-8")
        loader = JsonLoader()
        result = await loader.load(str(f))
        # The raw invalid line should appear verbatim in output
        assert "{INVALID_JSON}" in result


# ---------------------------------------------------------------------------
# Tests: HtmlLoader with BeautifulSoup (lines 154-155)
# ---------------------------------------------------------------------------

class TestHtmlLoaderWithBeautifulSoup:
    @pytest.mark.asyncio
    async def test_html_loader_uses_beautifulsoup_when_available(self, tmp_path):
        """Lines 154-155: bs4 import succeeds -> soup.get_text path."""
        f = tmp_path / "page.html"
        f.write_text("<html><body><p>Hello World</p></body></html>", encoding="utf-8")

        # Mock bs4 so the import succeeds regardless of whether it's installed
        class _FakeSoup:
            def __init__(self, raw, parser):
                self._raw = raw
            def get_text(self, separator="\n"):
                return "Hello World extracted by fake soup"

        bs4_mod = types.ModuleType("bs4")
        bs4_mod.BeautifulSoup = _FakeSoup
        loader = HtmlLoader()
        with patch.dict("sys.modules", {"bs4": bs4_mod}):
            result = await loader.load(str(f))
        assert "Hello World" in result


# ---------------------------------------------------------------------------
# Tests: discover() entry_points valid plugin path (lines 208-209)
# ---------------------------------------------------------------------------

class TestDiscoverValidPlugin:
    def test_valid_plugin_registered_via_entry_point(self):
        """Lines 208-209: ep.load() returns valid EnhancedCogneeLoader subclass."""
        class MyLoader(EnhancedCogneeLoader):
            SUPPORTED_EXTENSIONS = [".myext"]
            DISPLAY_NAME = "My Loader"

            async def load(self, source, **kwargs):
                return "content"

        ep = MagicMock()
        ep.load.return_value = MyLoader
        ep.name = "my_loader"
        ep.value = "my_package.loaders:MyLoader"

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            reg = PluginRegistry()
            count = reg.discover(skip_entry_points=False)

        # 3 built-ins + 1 plugin
        assert count == 4
        loaders = reg.list_loaders()
        names = [l["name"] for l in loaders]
        assert "MyLoader" in names

    def test_non_subclass_plugin_not_registered(self):
        """Lines 213-215: ep.load() returns non-subclass -> warning, not registered."""
        class NotALoader:
            pass

        ep = MagicMock()
        ep.load.return_value = NotALoader
        ep.name = "bad_plugin"
        ep.value = "some.module:NotALoader"

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            reg = PluginRegistry()
            count = reg.discover(skip_entry_points=False)

        assert count == 3  # only built-ins
