"""
Intelligent Memory Summarization for Enhanced Cognee
Uses LLMs to automatically summarize and cluster memories for efficient storage and retrieval
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SummaryStrategy(Enum):
    """Summarization strategies"""
    CONCISE = "concise"  # Brief summary (1-2 sentences)
    STANDARD = "standard"  # Medium summary (3-5 sentences)
    DETAILED = "detailed"  # Detailed summary (paragraph)
    EXTRACTIVE = "extractive"  # Extract key points as bullets


@dataclass
class MemoryCluster:
    """Represents a cluster of related memories"""
    cluster_id: str
    memories: List[Dict[str, Any]] = field(default_factory=list)
    cluster_summary: Optional[str] = None
    cluster_theme: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    memory_count: int = 0


@dataclass
class SummaryResult:
    """Result of a summarization operation"""
    memory_id: str
    original_content: str
    summary: str
    strategy: SummaryStrategy
    compression_ratio: float  # original_length / summary_length
    keywords: List[str] = field(default_factory=list)
    entities: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class IntelligentMemorySummarizer:
    """
    Intelligent Memory Summarization System

    Features:
    - LLM-based automatic summarization
    - Smart memory clustering
    - Knowledge extraction
    - Relationship mapping
    - Compression ratio tracking
    """

    def __init__(
        self,
        postgres_pool,
        llm_config: Dict[str, Any],
        redis_client=None,
        qdrant_client=None
    ):
        """
        Initialize the summarizer

        Args:
            postgres_pool: PostgreSQL connection pool
            llm_config: LLM configuration (provider, model, api_key, etc.)
            redis_client: Redis client for caching
            qdrant_client: Qdrant client for semantic search
        """
        self.postgres_pool = postgres_pool
        self.llm_config = llm_config
        self.redis_client = redis_client
        self.qdrant_client = qdrant_client

        # Summarization settings
        self.min_memory_age_days = 30  # Summarize memories older than 30 days
        self.min_memory_length = 500  # Only summarize if longer than 500 chars
        self.batch_size = 10  # Process memories in batches

        # Clustering settings
        self.clustering_threshold = 0.75  # Similarity threshold for clustering
        self.max_cluster_size = 50  # Maximum memories per cluster

    async def find_summarizable_memories(
        self,
        days_old: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find memories that should be summarized

        Args:
            days_old: Minimum age in days
            limit: Maximum number of memories to return

        Returns:
            List of memories that need summarization
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

            async with self.postgres_pool.acquire() as conn:
                memories = await conn.fetch("""
                    SELECT
                        id,
                        title,
                        content,
                        metadata,
                        agent_id,
                        created_at,
                        LENGTH(content) as content_length,
                        EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400 as age_days
                    FROM shared_memory.documents
                    WHERE created_at < $1
                    AND LENGTH(content) > $2
                    ORDER BY created_at ASC
                    LIMIT $3
                """, cutoff_date, self.min_memory_length, limit)

                return [dict(m) for m in memories]

        except Exception as e:
            logger.error(f"Error finding summarizable memories: {e}")
            return []

    async def summarize_memory(
        self,
        memory: Dict[str, Any],
        strategy: SummaryStrategy = SummaryStrategy.STANDARD
    ) -> SummaryResult:
        """
        Summarize a single memory using LLM

        Args:
            memory: Memory data to summarize
            strategy: Summarization strategy to use

        Returns:
            SummaryResult with summary and metadata
        """
        try:
            content = memory.get('content', '')
            memory_id = memory.get('id', '')

            # Check cache first
            cache_key = f"summary:{memory_id}:{strategy.value}"
            if self.redis_client:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return SummaryResult(**json.loads(cached))

            # Generate summary using LLM
            summary_data = await self._generate_llm_summary(content, strategy)

            # Calculate compression ratio
            compression_ratio = len(content) / len(summary_data['summary']) if summary_data['summary'] else 0

            result = SummaryResult(
                memory_id=memory_id,
                original_content=content,
                summary=summary_data['summary'],
                strategy=strategy,
                compression_ratio=compression_ratio,
                keywords=summary_data.get('keywords', []),
                entities=summary_data.get('entities', [])
            )

            # Cache the result
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key,
                    86400,  # 24 hours
                    json.dumps(result.__dict__, default=str)
                )

            return result

        except Exception as e:
            logger.error(f"Error summarizing memory {memory.get('id')}: {e}")
            raise

    async def _generate_llm_summary(
        self,
        content: str,
        strategy: SummaryStrategy
    ) -> Dict[str, Any]:
        """
        Generate summary using configured LLM

        Args:
            content: Content to summarize
            strategy: Summarization strategy

        Returns:
            Dictionary with summary, keywords, and entities
        """
        provider = self.llm_config.get('provider', 'openai')

        if provider == 'openai':
            return await self._summarize_with_openai(content, strategy)
        elif provider == 'anthropic':
            return await self._summarize_with_anthropic(content, strategy)
        elif provider == 'ollama':
            return await self._summarize_with_ollama(content, strategy)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def _summarize_with_openai(
        self,
        content: str,
        strategy: SummaryStrategy
    ) -> Dict[str, Any]:
        """Summarize using OpenAI API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.llm_config.get('api_key'))

            # Build prompt based on strategy
            system_prompt = self._build_summary_prompt(strategy)

            response = await client.chat.completions.create(
                model=self.llm_config.get('model', 'gpt-4-turbo'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Summarize the following:\n\n{content[:4000]}"}  # Limit content length
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return self._parse_summary_result(result)

        except ImportError:
            logger.error("OpenAI library not available")
            raise
        except Exception as e:
            logger.error(f"OpenAI summarization error: {e}")
            raise

    async def _summarize_with_anthropic(
        self,
        content: str,
        strategy: SummaryStrategy
    ) -> Dict[str, Any]:
        """Summarize using Anthropic Claude API"""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.llm_config.get('api_key'))

            system_prompt = self._build_summary_prompt(strategy)

            message = await client.messages.create(
                model=self.llm_config.get('model', 'claude-3-5-sonnet-20241022'),
                max_tokens=1000,
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Summarize the following:\n\n{content[:4000]}"}
                ]
            )

            # Parse the response
            response_text = message.content[0].text
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback if LLM didn't return JSON
                result = {"summary": response_text, "keywords": [], "entities": []}

            return self._parse_summary_result(result)

        except ImportError:
            logger.error("Anthropic library not available")
            raise
        except Exception as e:
            logger.error(f"Anthropic summarization error: {e}")
            raise

    async def _summarize_with_ollama(
        self,
        content: str,
        strategy: SummaryStrategy
    ) -> Dict[str, Any]:
        """Summarize using local Ollama model"""
        try:
            import aiohttp

            system_prompt = self._build_summary_prompt(strategy)

            prompt = f"{system_prompt}\n\nSummarize the following:\n\n{content[:4000]}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'http://localhost:11434/api/generate',
                    json={
                        "model": self.llm_config.get('model', 'llama2'),
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 500}
                    }
                ) as response:
                    result = await response.json()
                    summary_text = result.get('response', '')

                    return {
                        "summary": summary_text,
                        "keywords": [],
                        "entities": []
                    }

        except Exception as e:
            logger.error(f"Ollama summarization error: {e}")
            raise

    def _build_summary_prompt(self, strategy: SummaryStrategy) -> str:
        """Build system prompt based on strategy"""
        if strategy == SummaryStrategy.CONCISE:
            return """You are a memory summarization expert. Create a very concise summary (1-2 sentences) that captures the main point.

Return JSON format:
{
  "summary": "The concise summary",
  "keywords": ["key1", "key2"],
  "entities": [{"type": "person", "name": "Name"}]
}"""

        elif strategy == SummaryStrategy.STANDARD:
            return """You are a memory summarization expert. Create a medium-length summary (3-5 sentences) that captures the key information and context.

Return JSON format:
{
  "summary": "The summary",
  "keywords": ["key1", "key2", "key3"],
  "entities": [{"type": "person", "name": "Name"}, {"type": "date", "value": "2024-01-01"}]
}"""

        elif strategy == SummaryStrategy.DETAILED:
            return """You are a memory summarization expert. Create a detailed summary (paragraph) that captures all important information, context, and nuances.

Return JSON format:
{
  "summary": "The detailed summary",
  "keywords": ["key1", "key2", "key3"],
  "entities": [{"type": "person", "name": "Name"}]
}"""

        else:  # EXTRACTIVE
            return """You are a memory summarization expert. Extract the key points as a bulleted list.

Return JSON format:
{
  "summary": "- Point 1\n- Point 2\n- Point 3",
  "keywords": ["key1", "key2"],
  "entities": [{"type": "person", "name": "Name"}]
}"""

    def _parse_summary_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate summary result from LLM"""
        return {
            "summary": result.get("summary", ""),
            "keywords": result.get("keywords", []),
            "entities": result.get("entities", [])
        }

    async def cluster_memories(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[MemoryCluster]:
        """
        Cluster related memories using semantic similarity

        Args:
            memories: List of memories to cluster

        Returns:
            List of memory clusters
        """
        try:
            if not self.qdrant_client:
                logger.warning("Qdrant not available, using simple clustering")
                return self._simple_cluster(memories)

            # Use Qdrant for semantic clustering
            clusters = []
            assigned_ids = set()

            for memory in memories:
                if memory['id'] in assigned_ids:
                    continue

                # Find similar memories using semantic search
                similar_memories = await self._find_similar_memories(
                    memory,
                    [m for m in memories if m['id'] != memory['id']]
                )

                # Create cluster
                cluster = MemoryCluster(
                    cluster_id=f"cluster_{len(clusters)}",
                    memories=[memory] + similar_memories,
                    memory_count=len(similar_memories) + 1
                )

                # Generate cluster theme
                cluster.cluster_theme = await self._infer_cluster_theme(cluster)

                clusters.append(cluster)

                # Mark as assigned
                assigned_ids.add(memory['id'])
                for sm in similar_memories:
                    assigned_ids.add(sm['id'])

                if len(assigned_ids) >= len(memories):
                    break

            return clusters

        except Exception as e:
            logger.error(f"Error clustering memories: {e}")
            return self._simple_cluster(memories)

    async def _find_similar_memories(
        self,
        target_memory: Dict[str, Any],
        candidate_memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find memories semantically similar to target"""
        try:
            # Search Qdrant for similar memories
            search_result = self.qdrant_client.search(
                collection_name="cognee_general_memory",
                query_vector=self._get_embedding(target_memory.get('content', '')),
                limit=10,
                score_threshold=self.clustering_threshold
            )

            similar_ids = [hit.id for hit in search_result]
            return [m for m in candidate_memories if m['id'] in similar_ids]

        except Exception as e:
            logger.error(f"Error finding similar memories: {e}")
            return []

    async def _infer_cluster_theme(self, cluster: MemoryCluster) -> str:
        """Infer the theme/topic of a memory cluster"""
        try:
            # Combine all content from cluster
            combined_content = " ".join([
                m.get('content', '') for m in cluster.memories[:5]
            ])

            # Use LLM to infer theme
            theme = await self._generate_cluster_theme(combined_content)
            return theme

        except Exception as e:
            logger.error(f"Error inferring cluster theme: {e}")
            return "General"

    async def _generate_cluster_theme(self, content: str) -> str:
        """Generate cluster theme using LLM"""
        try:
            provider = self.llm_config.get('provider', 'openai')

            if provider == 'anthropic':
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=self.llm_config.get('api_key'))

                message = await client.messages.create(
                    model=self.llm_config.get('model', 'claude-3-5-haiku-20241022'),
                    max_tokens=50,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": f"What is the main theme/topic of these memories in 2-3 words?\n\n{content[:1000]}"}
                    ]
                )

                return message.content[0].text.strip()

            else:
                # Fallback to simple keyword extraction
                words = content.lower().split()
                # Get most common meaningful words
                from collections import Counter
                word_counts = Counter(words)
                # Filter out common words
                common_words = {word for word, count in word_counts.most_common(5)
                               if len(word) > 4}
                return ", ".join(list(common_words)[:3])

        except Exception as e:
            logger.error(f"Error generating cluster theme: {e}")
            return "General"

    def _simple_cluster(self, memories: List[Dict[str, Any]]) -> List[MemoryCluster]:
        """Simple clustering based on metadata (fallback)"""
        clusters = {}

        for memory in memories:
            metadata = memory.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            category = metadata.get('memory_category', 'general')
            agent_id = memory.get('agent_id', 'unknown')

            cluster_key = f"{category}_{agent_id}"

            if cluster_key not in clusters:
                clusters[cluster_key] = MemoryCluster(
                    cluster_id=cluster_key,
                    cluster_theme=category
                )

            clusters[cluster_key].memories.append(memory)
            clusters[cluster_key].memory_count += 1

        return list(clusters.values())

    async def auto_summarize_old_memories(
        self,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically summarize old memories that meet criteria

        Args:
            dry_run: If True, don't actually update, just report

        Returns:
            Statistics about summarization results
        """
        try:
            # Find candidates
            candidates = await self.find_summarizable_memories(
                days_old=self.min_memory_age_days,
                limit=100
            )

            logger.info(f"Found {len(candidates)} memories for summarization")

            results = {
                "status": "success",
                "total_candidates": len(candidates),
                "summarized": 0,
                "skipped": 0,
                "failed": 0,
                "total_compression_ratio": 0.0,
                "clusters_created": 0
            }

            for memory in candidates:
                try:
                    # Summarize
                    summary_result = await self.summarize_memory(memory)

                    if not dry_run:
                        # Store summary
                        await self._store_summary(summary_result)

                    results["summarized"] += 1
                    results["total_compression_ratio"] += summary_result.compression_ratio

                except Exception as e:
                    logger.error(f"Failed to summarize memory {memory.get('id')}: {e}")
                    results["failed"] += 1

            # Calculate average compression ratio
            if results["summarized"] > 0:
                results["avg_compression_ratio"] = (
                    results["total_compression_ratio"] / results["summarized"]
                )

            return results

        except Exception as e:
            logger.error(f"Error in auto-summarization: {e}")
            return {"status": "error", "error": str(e)}

    async def _store_summary(self, summary_result: SummaryResult) -> None:
        """Store summary in database"""
        try:
            async with self.postgres_pool.acquire() as conn:
                # Store summary as a separate record or update metadata
                await conn.execute("""
                    UPDATE shared_memory.documents
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        'summary',
                        $1
                    )
                    WHERE id = $2
                """, json.dumps({
                    "summary": summary_result.summary,
                    "keywords": summary_result.keywords,
                    "compression_ratio": summary_result.compression_ratio,
                    "summarized_at": summary_result.created_at.isoformat()
                }), summary_result.memory_id)

                logger.info(f"Stored summary for memory {summary_result.memory_id}")

        except Exception as e:
            logger.error(f"Error storing summary: {e}")
            raise

    def _get_embedding(self, text: str) -> List[float]:
        """Get text embedding for semantic search"""
        # This would typically use an embedding model
        # For now, return a placeholder
        import random
        return [random.random() for _ in range(1536)]

    async def get_summarization_statistics(self) -> Dict[str, Any]:
        """Get statistics about memory summarization"""
        try:
            async with self.postgres_pool.acquire() as conn:
                # Count memories with summaries
                with_summary = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM shared_memory.documents
                    WHERE metadata->>'summary' IS NOT NULL
                """)

                # Get average compression ratio
                avg_compression = await conn.fetchval("""
                    SELECT AVG((metadata->>'compression_ratio')::float)
                    FROM shared_memory.documents
                    WHERE metadata->>'compression_ratio' IS NOT NULL
                """)

                return {
                    "status": "success",
                    "memories_summarized": with_summary,
                    "average_compression_ratio": float(avg_compression) if avg_compression else 0.0
                }

        except Exception as e:
            logger.error(f"Error getting summarization stats: {e}")
            return {"status": "error", "error": str(e)}