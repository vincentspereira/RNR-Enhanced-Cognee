"""
Performance Optimization Module for Enhanced Cognee

Optimizes database queries for multi-language support with targeted performance.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Performance optimization for multi-language queries"""

    def __init__(self):
        self.query_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.performance_metrics = {}

    async def create_language_indexes(self, postgres_pool) -> bool:
        """
        Create database indexes for language filtering.

        Args:
            postgres_pool: PostgreSQL connection pool

        Returns:
            True if indexes created successfully
        """
        try:
            async with postgres_pool.acquire() as conn:
                # Create GIN index for metadata JSON queries
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_metadata_language
                    ON shared_memory.documents
                    USING GIN (metadata jsonb_path_ops);
                """)

                # Create expression index for language extraction
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_language_extract
                    ON shared_memory.documents
                    ((metadata->>'language'));
                """)

                # Create partial index for non-English memories
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_non_english
                    ON shared_memory.documents (id, created_at)
                    WHERE (metadata->>'language') IS DISTINCT FROM 'en';
                """)

                logger.info("OK Language indexes created")
                return True

        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            return False

    async def optimize_query(
        self,
        query: str,
        postgres_pool,
        user_id: str,
        agent_id: str,
        language: Optional[str] = None
    ) -> List[Dict]:
        """
        Optimized search query with language filtering.

        Args:
            query: Search query
            postgres_pool: PostgreSQL connection pool
            user_id: User ID
            agent_id: Agent ID
            language: Optional language filter

        Returns:
            List of memory dictionaries
        """
        start_time = datetime.now()

        try:
            async with postgres_pool.acquire() as conn:
                if language:
                    # Language-filtered query with index
                    memories = await conn.fetch("""
                        SELECT id, data_text, metadata, created_at
                        FROM shared_memory.documents
                        WHERE user_id = $1
                        AND (agent_id = $2 OR agent_id = 'shared')
                        AND (metadata->>'language') = $3
                        AND (
                            to_tsvector('english', coalesce(data_text, '')) @@ plainto_tsquery('english', $4)
                            OR data_text ILIKE '%' || $4 || '%'
                        )
                        ORDER BY created_at DESC
                        LIMIT 50
                    """, user_id, agent_id, language, query)
                else:
                    # Regular query
                    memories = await conn.fetch("""
                        SELECT id, data_text, metadata, created_at
                        FROM shared_memory.documents
                        WHERE user_id = $1
                        AND (agent_id = $2 OR agent_id = 'shared')
                        AND (
                            to_tsvector('english', coalesce(data_text, '')) @@ plainto_tsquery('english', $3)
                            OR data_text ILIKE '%' || $3 || '%'
                        )
                        ORDER BY created_at DESC
                        LIMIT 50
                    """, user_id, agent_id, query)

            # Track performance
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            self._track_query('search', elapsed)

            # Convert to list of dicts
            return [dict(row) for row in memories]

        except Exception as e:
            logger.error(f"Optimized query failed: {e}")
            return []

    def _track_query(self, query_type: str, elapsed_ms: float):
        """Track query performance metrics"""
        if query_type not in self.performance_metrics:
            self.performance_metrics[query_type] = {
                'count': 0,
                'total_ms': 0,
                'min_ms': float('inf'),
                'max_ms': 0
            }

        metrics = self.performance_metrics[query_type]
        metrics['count'] += 1
        metrics['total_ms'] += elapsed_ms
        metrics['min_ms'] = min(metrics['min_ms'], elapsed_ms)
        metrics['max_ms'] = max(metrics['max_ms'], elapsed_ms)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {}

        for query_type, metrics in self.performance_metrics.items():
            if metrics['count'] > 0:
                stats[query_type] = {
                    'count': metrics['count'],
                    'avg_ms': metrics['total_ms'] / metrics['count'],
                    'min_ms': metrics['min_ms'],
                    'max_ms': metrics['max_ms']
                }

        return stats

    async def benchmark_query_performance(
        self,
        postgres_pool,
        user_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Benchmark query performance.

        Args:
            postgres_pool: PostgreSQL connection pool
            user_id: User ID
            agent_id: Agent ID

        Returns:
            Performance benchmark results
        """
        results = {}

        try:
            # Test language-filtered query
            start = datetime.now()
            await self.optimize_query(
                query="test",
                postgres_pool=postgres_pool,
                user_id=user_id,
                agent_id=agent_id,
                language='en'
            )
            results['language_filtered_ms'] = (datetime.now() - start).total_seconds() * 1000
        except Exception:
            results['language_filtered_ms'] = -1

        try:
            # Test regular query
            start = datetime.now()
            await self.optimize_query(
                query="test",
                postgres_pool=postgres_pool,
                user_id=user_id,
                agent_id=agent_id
            )
            results['regular_query_ms'] = (datetime.now() - start).total_seconds() * 1000
        except Exception:
            results['regular_query_ms'] = -1

        try:
            # Test language distribution
            start = datetime.now()
            async with postgres_pool.acquire() as conn:
                await conn.fetch("""
                    SELECT metadata->>'language' as lang, COUNT(*)
                    FROM shared_memory.documents
                    WHERE user_id = $1
                    GROUP BY lang
                """, user_id)
            results['language_distribution_ms'] = (datetime.now() - start).total_seconds() * 1000
        except Exception:
            results['language_distribution_ms'] = -1

        return results

    def clear_cache(self):
        """Clear query cache"""
        self.query_cache.clear()
        logger.info("OK Query cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'cached_queries': len(self.query_cache),
            'cache_ttl_seconds': self.cache_ttl
        }

# Singleton instance
performance_optimizer = PerformanceOptimizer()
