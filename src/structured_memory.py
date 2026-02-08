"""
Enhanced Cognee - Structured Memory Model

Implements hierarchical observations like claude-mem with structured types and concepts.
Provides auto-categorization and rich metadata for memories.

Memory Types:
- bugfix: Fixing a bug or error
- feature: Adding new functionality
- decision: Making a design or architectural decision
- refactor: Refactoring existing code
- discovery: Discovering how something works
- general: General observations

Memory Concepts:
- how-it-works: Understanding how something works
- gotcha: Common pitfalls or edge cases
- trade-off: Trade-offs between alternatives
- pattern: Design patterns or best practices
- general: General concepts

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Memory type enumeration."""
    BUGFIX = "bugfix"
    FEATURE = "feature"
    DECISION = "decision"
    REFACTOR = "refactor"
    DISCOVERY = "discovery"
    GENERAL = "general"


class MemoryConcept(str, Enum):
    """Memory concept enumeration."""
    HOW_IT_WORKS = "how-it-works"
    GOTCHA = "gotcha"
    TRADE_OFF = "trade-off"
    PATTERN = "pattern"
    GENERAL = "general"


class AutoCategorizer:
    """
    Auto-categorization engine for memories.

    Analyzes content to detect memory type and concept.
    """

    def __init__(self):
        """Initialize auto-categorizer."""
        # Type detection patterns
        self.type_patterns = {
            MemoryType.BUGFIX: [
                r'\bfix\b', r'\bbug\b', r'\berror\b', r'\bissue\b',
                r'\bpatch\b', r'\bresolve\b', r'\bcorrect\b'
            ],
            MemoryType.FEATURE: [
                r'\badd\b', r'\bimplement\b', r'\bcreate\b',
                r'\bnew\b', r'\bfeature\b', r'\benhancement\b'
            ],
            MemoryType.DECISION: [
                r'\bdecided\b', r'\bchoice\b', r'\bchose\b',
                r'\bselected\b', r'\barchitecture\b', r'\bdesign\b'
            ],
            MemoryType.REFACTOR: [
                r'\brefactor\b', r'\bclean\b', r'\bsimplify\b',
                r'\brestructure\b', r'\breorganize\b', r'\bimprove\b'
            ],
            MemoryType.DISCOVERY: [
                r'\bdiscover\b', r'\bfound\b', r'\blearned\b',
                r'\binvestigate\b', r'\bexplore\b', r'\bfigured out\b'
            ]
        }

        # Concept detection patterns
        self.concept_patterns = {
            MemoryConcept.HOW_IT_WORKS: [
                r'\bworks\b', r'\bhow to\b', r'\bimplementation\b',
                r'\bmechanism\b', r'\bprocess\b'
            ],
            MemoryConcept.GOTCHA: [
                r'\bgotcha\b', r'\bpitfall\b', r'\bedge case\b',
                r'\bwatch out\b', r'\bbe careful\b', r'\bwarning\b'
            ],
            MemoryConcept.TRADE_OFF: [
                r'\btrade-off\b', r'\bbalance\b', r'\bbetween\b',
                r'\bversus\b', r'\bvs\b', r'\bpro\b', r'\bcon\b'
            ],
            MemoryConcept.PATTERN: [
                r'\bpattern\b', r'\bpractice\b', r'\bapproach\b',
                r'\bmethod\b', r'\bstrategy\b'
            ]
        }

    def categorize(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Auto-categorize a memory.

        Args:
            content: Memory content
            metadata: Optional metadata

        Returns:
            Categorization dict with type, concept, files, facts
        """
        content_lower = content.lower()

        # Detect memory type
        memory_type = self._detect_type(content_lower)

        # Detect memory concept
        memory_concept = self._detect_concept(content_lower)

        # Extract file paths
        files = self._extract_files(content, metadata)

        # Extract facts
        facts = self._extract_facts(content)

        return {
            "memory_type": memory_type,
            "memory_concept": memory_concept,
            "files": files,
            "facts": facts
        }

    def _detect_type(self, content_lower: str) -> MemoryType:
        """Detect memory type from content."""
        scores = {}

        for memory_type, patterns in self.type_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower))
                score += matches
            scores[memory_type] = score

        # Return type with highest score, or general
        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] > 0:
                return best_type

        return MemoryType.GENERAL

    def _detect_concept(self, content_lower: str) -> MemoryConcept:
        """Detect memory concept from content."""
        scores = {}

        for memory_concept, patterns in self.concept_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower))
                score += matches
            scores[memory_concept] = score

        # Return concept with highest score, or general
        if scores:
            best_concept = max(scores, key=scores.get)
            if scores[best_concept] > 0:
                return best_concept

        return MemoryConcept.GENERAL

    def _extract_files(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract file paths from content.

        Args:
            content: Memory content
            metadata: Optional metadata

        Returns:
            List of file paths
        """
        files = set()

        # Check metadata first
        if metadata and "files" in metadata:
            if isinstance(metadata["files"], list):
                files.update(metadata["files"])

        # Extract from content using regex patterns
        # Pattern: path/to/file.ext, ./file.ext, ../file.ext, /absolute/path
        file_patterns = [
            r'[a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+',  # File extensions
            r'`([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)`',  # Code files in backticks
            r'"([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)"',  # Files in quotes
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                # Filter to only file-like paths
                if '/' in match or '\\' in match or '.' in match:
                    files.add(match)

        return sorted(list(files))

    def _extract_facts(self, content: str) -> List[str]:
        """
        Extract facts from content.

        Args:
            content: Memory content

        Returns:
            List of facts
        """
        facts = []

        # Extract sentences (simple heuristic)
        sentences = re.split(r'[.!?]+', content)

        for sentence in sentences:
            sentence = sentence.strip()
            # Keep sentences that are meaningful
            if len(sentence) > 10 and len(sentence) < 200:
                facts.append(sentence)

        # Limit to 10 facts
        return facts[:10]


class StructuredMemoryModel:
    """
    Structured memory model manager.

    Handles hierarchical observations with types, concepts, and rich metadata.
    """

    def __init__(self, db_pool):
        """
        Initialize structured memory model.

        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool
        self.categorizer = AutoCategorizer()
        self.stats = {
            "observations_added": 0,
            "auto_categorized": 0,
            "search_by_type": 0,
            "search_by_concept": 0,
            "search_by_file": 0
        }

    async def add_observation(
        self,
        content: str,
        agent_id: str = "default",
        memory_type: Optional[MemoryType] = None,
        memory_concept: Optional[MemoryConcept] = None,
        narrative: Optional[str] = None,
        before_state: Optional[str] = None,
        after_state: Optional[str] = None,
        files: Optional[List[str]] = None,
        facts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a structured observation.

        Args:
            content: Memory content
            agent_id: Agent identifier
            memory_type: Optional memory type (auto-detected if not provided)
            memory_concept: Optional memory concept (auto-detected if not provided)
            narrative: Detailed narrative explanation
            before_state: State before the change
            after_state: State after the change
            files: List of files referenced
            facts: List of key facts
            metadata: Additional metadata

        Returns:
            Memory ID (UUID)
        """
        # Auto-categorize if types not provided
        if memory_type is None or memory_concept is None:
            categorization = self.categorizer.categorize(content, metadata)
            if memory_type is None:
                memory_type = categorization["memory_type"]
                self.stats["auto_categorized"] += 1
            if memory_concept is None:
                memory_concept = categorization["memory_concept"]

            # Use extracted values if not provided
            if files is None:
                files = categorization["files"]
            if facts is None:
                facts = categorization["facts"]

        # Default values
        memory_type = memory_type or MemoryType.GENERAL
        memory_concept = memory_concept or MemoryConcept.GENERAL
        files = files or []
        facts = facts or []
        metadata = metadata or {}

        async with self.db_pool.acquire() as conn:
            memory_id = await conn.fetchval("""
                SELECT shared_memory.add_structured_observation(
                    $1::text,
                    $2::varchar,
                    $3::memory_type,
                    $4::memory_concept,
                    $5::text,
                    $6::text,
                    $7::text,
                    $8::jsonb,
                    $9::jsonb,
                    $10::jsonb
                )
            """, content, agent_id, memory_type, memory_concept,
                 narrative, before_state, after_state,
                 json.dumps(files), json.dumps(facts),
                 json.dumps(metadata))

        self.stats["observations_added"] += 1
        logger.info(f"Added structured observation: {memory_id} (type={memory_type}, concept={memory_concept})")

        return str(memory_id)

    async def search_by_type(
        self,
        memory_type: MemoryType,
        agent_id: str = "default",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search observations by memory type.

        Args:
            memory_type: Memory type to filter by
            agent_id: Agent identifier
            limit: Maximum results

        Returns:
            List of matching observations
        """
        self.stats["search_by_type"] += 1

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM shared_memory.search_by_type($1::memory_type, $2::varchar, $3::int)
            """, memory_type, agent_id, limit)

        return [dict(row) for row in rows]

    async def search_by_concept(
        self,
        memory_concept: MemoryConcept,
        agent_id: str = "default",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search observations by memory concept.

        Args:
            memory_concept: Memory concept to filter by
            agent_id: Agent identifier
            limit: Maximum results

        Returns:
            List of matching observations
        """
        self.stats["search_by_concept"] += 1

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM shared_memory.search_by_concept($1::memory_concept, $2::varchar, $3::int)
            """, memory_concept, agent_id, limit)

        return [dict(row) for row in rows]

    async def search_by_file(
        self,
        file_path: str,
        agent_id: str = "default",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search observations by file reference.

        Args:
            file_path: File path to search for
            agent_id: Agent identifier
            limit: Maximum results

        Returns:
            List of matching observations
        """
        self.stats["search_by_file"] += 1

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM shared_memory.search_by_file($1::text, $2::varchar, $3::int)
            """, file_path, agent_id, limit)

        return [dict(row) for row in rows]

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get structured memory statistics.

        Returns:
            Statistics dict
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM shared_memory.structured_stats
            """)

        return {
            **self.stats,
            "database": {
                "total_observations": row["total_observations"],
                "bugfix_count": row["bugfix_count"],
                "feature_count": row["feature_count"],
                "decision_count": row["decision_count"],
                "refactor_count": row["refactor_count"],
                "discovery_count": row["discovery_count"],
                "general_count": row["general_count"],
                "how_it_works_count": row["how_it_works_count"],
                "gotcha_count": row["gotcha_count"],
                "trade_off_count": row["trade_off_count"],
                "pattern_count": row["pattern_count"],
                "unique_files_referenced": row["unique_files_referenced"]
            }
        }

    async def migrate_existing_data(self) -> int:
        """
        Migrate existing documents to structured format.

        Returns:
            Number of documents migrated
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT shared_memory.migrate_to_structured()")

        logger.info(f"Migrated {result} documents to structured format")
        return int(result)


async def main():
    """Test structured memory model."""
    import asyncpg

    # Mock connection pool (for testing)
    print("Structured memory model requires database connection")
    print("Use with PostgreSQL connection pool")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
