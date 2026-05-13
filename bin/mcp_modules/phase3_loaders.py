"""
bin/mcp_modules/phase3_loaders.py
===================================
Phase 3 MCP Tools: External Loaders, Translation, Regex Entities, v2 Graph

Tools in this module (6):
  - ingest_url              : Scrape URLs into knowledge graph
  - ingest_db               : Ingest relational DB via dlt pipeline
  - translate_text          : Translate text (LLM/Google/Azure backends)
  - regex_extract_entities  : Extract named entities via regex patterns
  - extract_graph_v2        : Cascade v2 knowledge graph extraction
  - list_loaders            : List available file format loaders

Source in monolith: bin/enhanced_cognee_mcp_server.py lines 4381-4744

NOTE: This module is the CANONICAL reference for Phase 3 tools.
      The monolith still defines these tools inline (to avoid double-registration).
      Future migration: remove inline definitions from monolith and call register(mcp) here.

ASCII-ONLY output constraint: no Unicode symbols per CLAUDE.md.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register(mcp: "FastMCP") -> None:
    """Register all Phase 3 tools with the given FastMCP instance."""

    @mcp.tool()
    async def ingest_url(
        url: str,
        dataset_name: str = "web",
        tavily_api_key: Optional[str] = None,
        schedule: Optional[str] = None,
    ) -> str:
        """
        Scrape one or more URLs and store their content in the knowledge graph.

        Uses the v1.0.9 web_scraper_task which supports both BeautifulSoup
        (free, no API key) and Tavily (higher quality, requires API key).

        TRIGGER TYPE: (M) Manual - triggered when user wants to ingest web content

        Parameters:
        -----------
        - url: Single URL or comma-separated list of URLs to scrape
        - dataset_name: Target dataset name (default: 'web')
        - tavily_api_key: Optional Tavily API key for premium extraction.
          Falls back to TAVILY_API_KEY env var, then BeautifulSoup.
        - schedule: Optional cron expression for recurring scrapes (e.g. '0 6 * * *').
          If omitted, scrapes immediately.

        Returns:
        --------
        - Scrape status with page count or schedule confirmation
        """
        try:
            from cognee.tasks.web_scraper.web_scraper_task import (
                web_scraper_task,
                cron_web_scraper_task,
            )

            urls = [u.strip() for u in url.split(",") if u.strip()]
            if not urls:
                return "ERR No valid URLs provided"

            api_key = tavily_api_key or os.environ.get("TAVILY_API_KEY", "")

            if schedule:
                await cron_web_scraper_task(
                    url=urls,
                    schedule=schedule,
                    tavily_api_key=api_key or None,
                    job_name=f"mcp_{dataset_name}",
                )
                return (
                    f"OK Web scrape scheduled (cron: '{schedule}') "
                    f"for {len(urls)} URL(s) in dataset '{dataset_name}'"
                )

            await web_scraper_task(
                url=urls,
                tavily_api_key=api_key or None,
                job_name=f"mcp_{dataset_name}",
            )
            return (
                f"OK Scraped {len(urls)} URL(s) and stored in knowledge graph "
                f"(dataset: '{dataset_name}')"
            )

        except ImportError as exc:
            return (
                f"ERR Web scraping requires optional dependencies: {exc}\n"
                "Install with: pip install cognee[scraping]"
            )
        except Exception as exc:
            return f"ERR ingest_url failed: {exc}"

    @mcp.tool()
    async def ingest_db(
        connection_string: str,
        dataset_name: str = "db",
        query: Optional[str] = None,
    ) -> str:
        """
        Ingest tables from a relational database into the knowledge graph via dlt.

        Supports PostgreSQL, MySQL, SQLite, MSSQL, Oracle connection strings.
        Optionally filter with a SQL query.

        TRIGGER TYPE: (M) Manual - triggered when user wants to ingest database content

        Parameters:
        -----------
        - connection_string: Database URI (e.g. 'postgresql://user:pass@host/db',
          'sqlite:///path/to/db.sqlite')
        - dataset_name: Target dataset name for grouping ingested rows (default: 'db')
        - query: Optional SQL query to filter a specific table/rows.
          Format: 'SELECT ... FROM <table> WHERE ...' or just a table name.

        Returns:
        --------
        - Ingestion status with row count
        """
        try:
            from cognee.tasks.ingestion.create_dlt_source import (
                create_dlt_source_from_connection_string,
                is_connection_string,
            )
            from cognee.tasks.ingestion.ingest_dlt_source import ingest_dlt_source

            if not is_connection_string(connection_string):
                return (
                    f"ERR '{connection_string[:40]}...' does not look like a valid connection string.\n"
                    "Expected format: postgresql://user:pass@host/db or sqlite:///path.db"
                )

            dlt_source = create_dlt_source_from_connection_string(
                connection_string=connection_string,
                query=query,
            )
            await ingest_dlt_source(dlt_source=dlt_source, dataset_name=dataset_name)
            return (
                f"OK Database ingestion complete for dataset '{dataset_name}' "
                f"(source: {connection_string[:30]}...)"
            )

        except ImportError as exc:
            return (
                f"ERR Database ingestion requires dlt: {exc}\n"
                "Install with: pip install cognee[dlt]"
            )
        except Exception as exc:
            return f"ERR ingest_db failed: {exc}"

    @mcp.tool()
    async def translate_text(
        text: str,
        target_language: str = "en",
        provider: str = "llm",
        source_language: Optional[str] = None,
    ) -> str:
        """
        Translate a text string to the target language.

        Uses the v1.0.9 translation task which supports LLM, Google Translate,
        and Azure Translator backends.

        TRIGGER TYPE: (M) Manual - triggered when user needs text translated

        Parameters:
        -----------
        - text: The text to translate
        - target_language: ISO 639-1 language code (e.g. 'en', 'es', 'fr', 'de', 'zh-cn').
          Default: 'en' (English)
        - provider: Translation backend - 'llm' (default), 'google', or 'azure'
        - source_language: Optional source language code. Auto-detected if not provided.

        Returns:
        --------
        - Translated text with source/target language info
        """
        try:
            from cognee.tasks.translation.translate_content import translate_text as _translate

            result = await _translate(
                text=text,
                target_language=target_language,
                translation_provider=provider,
                source_language=source_language,
            )
            lines = [
                "OK Translation complete:",
                f"  Source language: {result.source_language}",
                f"  Target language: {result.target_language}",
                f"  Provider: {result.provider}",
                f"  Translated text:\n{result.translated_text}",
            ]
            return "\n".join(lines)
        except Exception as exc:
            return f"ERR translate_text failed: {exc}"

    @mcp.tool()
    async def regex_extract_entities(
        text: str,
        config_path: Optional[str] = None,
    ) -> str:
        """
        Extract named entities from text using configurable regular expression patterns.

        Uses the v1.0.9 RegexEntityExtractor. The default config includes common
        entity types (emails, URLs, phone numbers, dates, IP addresses, etc.).

        TRIGGER TYPE: (M) Manual - triggered when user wants to extract entities from text

        Parameters:
        -----------
        - text: The text to extract entities from
        - config_path: Optional path to a JSON config file defining entity patterns.
          Config format: list of objects with fields:
            entity_name, entity_description, regex, description_template

        Returns:
        --------
        - List of extracted entities with their types and descriptions
        """
        try:
            from cognee.tasks.entity_completion.entity_extractors.regex_entity_extractor import (
                RegexEntityExtractor,
            )

            extractor = RegexEntityExtractor(config_path=config_path)
            entities = await extractor.extract_entities(text)

            if not entities:
                return "OK No entities found in the provided text"

            lines = [f"OK Extracted {len(entities)} entities:\n"]
            for i, entity in enumerate(entities, 1):
                entity_type = entity.is_a.name if hasattr(entity.is_a, "name") else str(entity.is_a)
                lines.append(f"  {i}. [{entity_type}] {entity.name}")
                if entity.description:
                    lines.append(f"     {entity.description}")
            return "\n".join(lines)
        except Exception as exc:
            return f"ERR regex_extract_entities failed: {exc}"

    @mcp.tool()
    async def extract_graph_v2(
        text: str,
        n_rounds: int = 2,
    ) -> str:
        """
        Extract a knowledge graph from text using v1.0.9 cascade extraction (v2 pipeline).

        Unlike cognify() which runs the full ingestion + chunking + storage pipeline,
        this tool runs cascade graph extraction directly on the provided text and returns
        the extracted nodes and edges as structured data.

        The cascade algorithm performs n_rounds of extraction, each round refining
        the previously discovered nodes and relationships.

        TRIGGER TYPE: (M) Manual - triggered when user wants to inspect v2 graph extraction

        Parameters:
        -----------
        - text: The text to extract a knowledge graph from
        - n_rounds: Number of cascade extraction rounds (default: 2, max: 5).
          More rounds = denser graph but more LLM calls.

        Returns:
        --------
        - Extracted knowledge graph as formatted text (nodes list + edges list)
        """
        try:
            from cognee.tasks.graph.cascade_extract.utils.extract_nodes import extract_nodes
            from cognee.tasks.graph.cascade_extract.utils.extract_content_nodes_and_relationship_names import (
                extract_content_nodes_and_relationship_names,
            )
            from cognee.tasks.graph.cascade_extract.utils.extract_edge_triplets import (
                extract_edge_triplets,
            )

            n_rounds = max(1, min(n_rounds, 5))

            nodes = await extract_nodes(text, n_rounds=n_rounds)
            if not nodes:
                return "OK No nodes extracted from the provided text"

            updated_nodes, relationships = await extract_content_nodes_and_relationship_names(
                text, nodes, n_rounds
            )
            graph = await extract_edge_triplets(text, updated_nodes, relationships, n_rounds)

            lines = [
                f"OK v2 cascade extraction complete ({n_rounds} round(s)):",
                f"  Nodes: {len(graph.nodes)}",
                f"  Edges: {len(graph.edges)}",
                "",
                "Nodes:",
            ]
            for node in graph.nodes:
                lines.append(f"  - {node.name} ({getattr(node, 'type', 'entity')})")
            lines.append("\nEdges:")
            for edge in graph.edges:
                src = getattr(edge, "source_node_id", "?")
                tgt = getattr(edge, "target_node_id", "?")
                rel = getattr(edge, "relationship_name", "related_to")
                lines.append(f"  - {src} --[{rel}]--> {tgt}")
            return "\n".join(lines)

        except Exception as exc:
            return f"ERR extract_graph_v2 failed: {exc}"

    @mcp.tool()
    async def list_loaders() -> str:
        """
        List all available file format loaders supported by the Enhanced Cognee stack.

        Shows which loaders are currently installed and active. Optional loaders
        (unstructured, docling, beautifulsoup, advanced PDF) are only shown if their
        dependencies are installed.

        TRIGGER TYPE: (M) Manual - triggered when user wants to know supported file formats

        Returns:
        --------
        - List of available loaders with their supported file types
        """
        try:
            from cognee.infrastructure.loaders.supported_loaders import supported_loaders

            loader_info = {
                "PyPdfLoader": "PDF files (.pdf) - pure Python, no extra deps",
                "TextLoader": "Plain text files (.txt, .md, .rst, .log)",
                "ImageLoader": "Image files (.png, .jpg, .jpeg, .gif, .bmp, .webp)",
                "AudioLoader": "Audio files (.mp3, .wav, .ogg, .flac, .m4a)",
                "CsvLoader": "CSV and TSV tabular data (.csv, .tsv)",
                "UnstructuredLoader": "Office/rich docs (.docx, .xlsx, .pptx, .epub, .odt) - requires unstructured",
                "AdvancedPdfLoader": "PDF with layout (.pdf) - requires pdfplumber",
                "BeautifulSoupLoader": "HTML web pages (.html) - requires beautifulsoup4",
                "DoclingLoader": "PDF/Office via Docling AI (.pdf, .docx) - requires docling",
            }

            lines = [f"OK Available loaders ({len(supported_loaders)} active):\n"]
            for name in supported_loaders:
                desc = loader_info.get(name, "Custom loader")
                lines.append(f"  [ACTIVE] {name}: {desc}")

            optional_missing = [n for n in loader_info if n not in supported_loaders]
            if optional_missing:
                lines.append("\nOptional loaders not installed:")
                for name in optional_missing:
                    lines.append(f"  [OFF]    {name}: {loader_info[name]}")

            lines.append(
                "\nTo use a loader: pass the file path to add_memory() or cognify(). "
                "The loader is selected automatically by file extension."
            )
            return "\n".join(lines)

        except Exception as exc:
            return f"ERR list_loaders failed: {exc}"
