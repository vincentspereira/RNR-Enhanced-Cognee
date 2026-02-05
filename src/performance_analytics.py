"""
Performance Analytics Module for Enhanced Cognee
Collects and exposes performance metrics for monitoring
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    query_times_ms: List[float]
    cache_hits: int
    cache_misses: int
    memory_operations: int
    error_count: int
    total_memories: int
    active_agents: int


class PerformanceAnalytics:
    """Collects and manages performance metrics"""

    def __init__(self, postgres_pool, redis_client):
        self.postgres_pool = postgres_pool
        self.redis_client = redis_client

        # Metrics storage
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)

        # Performance tracking
        self.query_times = []
        self.max_query_times = 1000

    async def record_query_time(self, operation: str, duration_ms: float):
        """Record a query execution time"""
        self.query_times.append({
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Keep only recent queries
        if len(self.query_times) > self.max_query_times:
            self.query_times = self.query_times[-self.max_query_times:]

        # Update Prometheus-style metrics (store in Redis)
        try:
            metric_key = f"metrics:query_time:{operation}"
            await self.redis_client.incrbyfloat(metric_key, duration_ms)
        except:
            pass

    async def record_cache_hit(self, cache_type: str = "default"):
        """Record a cache hit"""
        self.counters[f"cache_hit:{cache_type}"] += 1

    async def record_cache_miss(self, cache_type: str = "default"):
        """Record a cache miss"""
        self.counters[f"cache_miss:{cache_type}"] += 1

    async def record_error(self, error_type: str, operation: str = ""):
        """Record an error"""
        self.counters[f"error:{error_type}"] += 1
        logger.error(f"Error recorded: {error_type} in {operation}")

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            metrics = {}

            # Query performance
            if self.query_times:
                durations = [q["duration_ms"] for q in self.query_times]
                metrics["query_performance"] = {
                    "avg_time_ms": sum(durations) / len(durations),
                    "min_time_ms": min(durations),
                    "max_time_ms": max(durations),
                    "p50_time_ms": sorted(durations)[len(durations)//2],
                    "p95_time_ms": sorted(durations)[int(len(durations)*0.95)] if len(durations) > 20 else max(durations),
                    "total_queries": len(durations)
                }

            # Cache performance
            cache_hits = sum(v for k, v in self.counters.items() if "cache_hit" in k)
            cache_misses = sum(v for k, v in self.counters.items() if "cache_miss" in k)
            total_cache_ops = cache_hits + cache_misses

            metrics["cache_performance"] = {
                "hits": cache_hits,
                "misses": cache_misses,
                "total": total_cache_ops,
                "hit_rate": f"{(cache_hits/total_cache_ops*100):.1f}%" if total_cache_ops > 0 else "0%"
            }

            # Database stats
            if self.postgres_pool:
                async with self.postgres_pool.acquire() as conn:
                    # Memory count
                    total_memories = await conn.fetchval("SELECT COUNT(*) FROM shared_memory.documents")
                    metrics["memory_stats"] = {"total_memories": total_memories}

                    # Active agents
                    agents = await conn.fetch("""
                        SELECT agent_id, COUNT(*) as count
                        FROM shared_memory.documents
                        GROUP BY agent_id
                    """)
                    metrics["memory_stats"]["active_agents"] = len(agents)

                    # Storage stats
                    db_size = await conn.fetchval("""
                        SELECT pg_size_pretty(pg_database_size(current_database()))
                    """)
                    metrics["database_stats"] = {"database_size": db_size}

            # System health
            metrics["timestamp"] = datetime.now(timezone.utc).isoformat()
            metrics["uptime"] = "unknown"  # Would need to track start time

            return metrics

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}

    async def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus text format

        Returns:
            Prometheus-compatible metrics text
        """
        try:
            metrics_lines = []

            # Query times
            if self.query_times:
                durations = [q["duration_ms"] for q in self.query_times]
                avg_time = sum(durations) / len(durations)

                metrics_lines.append(f"# HELP enhanced_cognee_query_time_seconds Query execution time in seconds")
                metrics_lines.append(f"# TYPE enhanced_cognee_query_time_seconds gauge")
                metrics_lines.append(f"enhanced_cognee_query_time_seconds {avg_time/1000:.4f} {int(time.time())}")

            # Cache stats
            cache_hits = sum(v for k, v in self.counters.items() if "cache_hit" in k)
            cache_misses = sum(v for k, v in self.counters.items() if "cache_miss" in k)

            metrics_lines.append(f"# HELP enhanced_cognee_cache_hits Total cache hits")
            metrics_lines.append(f"# TYPE enhanced_cognee_cache_hits counter")
            metrics_lines.append(f"enhanced_cognee_cache_hits {cache_hits}")

            metrics_lines.append(f"# HELP enhanced_cognee_cache_misses Total cache misses")
            metrics_lines.append(f"# TYPE enhanced_cognee_cache_misses counter")
            metrics_lines.append(f"enhanced_cognee_cache_misses {cache_misses}")

            # Memory count
            if self.postgres_pool:
                async with self.postgres_pool.acquire() as conn:
                    count = await conn.fetchval("SELECT COUNT(*) FROM shared_memory.documents")
                    metrics_lines.append(f"# HELP enhanced_cognee_total_memories Total number of memories stored")
                    metrics_lines.append(f"# TYPE enhanced_cognee_total_memories gauge")
                    metrics_lines.append(f"enhanced_cognee_total_memories {count} {int(time.time())}")

            return "\n".join(metrics_lines)

        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics: {e}")
            return f"# Error generating metrics: {e}"

    async def get_slow_queries(self, threshold_ms: float = 1000, limit: int = 10) -> List[Dict]:
        """Get slow queries above threshold"""
        try:
            slow_queries = [
                q for q in self.query_times
                if q["duration_ms"] > threshold_ms
            ]

            # Sort by duration (slowest first)
            slow_queries.sort(key=lambda x: x["duration_ms"], reverse=True)

            return slow_queries[:limit]

        except Exception as e:
            logger.error(f"Failed to get slow queries: {e}")
            return []

    async def reset_metrics(self):
        """Reset all metrics"""
        self.query_times = []
        self.counters = defaultdict(int)
        logger.info("Performance metrics reset")
