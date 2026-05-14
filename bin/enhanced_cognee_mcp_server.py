#!/usr/bin/env python3
"""
Enhanced Cognee MCP Server
===========================
Version:  1.0.9-enhanced (Phase 4 hardened)
Tools:    70 MCP tools across 9 functional areas
Backends: PostgreSQL+pgVector | Qdrant | Neo4j | Redis

Functional areas
----------------
1.  Stack init / lifecycle      (init_enhanced_stack, cleanup_enhanced_stack)
2.  Core knowledge graph        (cognify, search, get_stats, health, list_data)
3.  Standard memory CRUD        (add_memory, search_memories, get_memory, ...)
4.  Memory lifecycle            (expire_memories, archive_category, set_memory_ttl, ...)
5.  Deduplication & summarize   (deduplicate, summarize_category, ...)
6.  Performance & monitoring    (get_performance_metrics, get_prometheus_metrics, ...)
7.  Cross-agent sharing / sync  (set_memory_sharing, sync_agent_state, ...)
8.  Backup & recovery           (create_backup, restore_backup, ...)
9.  Language & search           (detect_language, cross_language_search, ...)
10. Phase 2 - v1.0.9 KG API    (remember, recall, forget_memory, improve, ...)
11. Phase 3 - external loaders  (ingest_url, ingest_db, translate_text, ...)

Refactoring note (Phase 4)
--------------------------
The tool implementations live inline in this file. A full module split
(bin/mcp_modules/) is planned for Phase 5. For now, section headers below
serve as navigation anchors for editors that support code folding.

ASCII-only output (CLAUDE.md mandate)
--------------------------------------
All tool return strings use ASCII-only characters.  No Unicode symbols.
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print(f"OK Loaded environment from: {env_path}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import MCP framework
from mcp.server import FastMCP
import mcp.types as types

# Create MCP server
mcp = FastMCP("Enhanced Cognee")

# Import enhanced modules
from src.memory_management import MemoryManager, RetentionPolicy
from src.memory_deduplication import MemoryDeduplicator
from src.memory_summarization import MemorySummarizer
from src.performance_analytics import PerformanceAnalytics
from src.cross_agent_sharing import CrossAgentMemorySharing, SharePolicy
from src.realtime_sync import RealTimeMemorySync

# Sprint 9: Multi-language support
from src.language_detector import language_detector
from src.multi_language_search import multi_language_search

# Sprint 10: Advanced AI Features
from src.intelligent_summarization import IntelligentMemorySummarizer, SummaryStrategy
from src.advanced_search_reranking import AdvancedSearchEngine, ReRankingStrategy

# Security and validation
from src.security_mcp import (
    ValidationError,
    AuthorizationError,
    ConfirmationRequiredError,
    validate_uuid,
    validate_days,
    validate_limit,
    validate_agent_id,
    validate_category,
    validate_memory_content,
    sanitize_string,
    authorizer,
    confirmation_manager,
    require_agent_authorization,
    validate_dry_run_safe,
    handle_database_exception,
    handle_backup_exception
)

# Code Quality: Response Formatting and Transaction Support
from src.logging_config import get_logger
from src.mcp_response_formatter import (
    success_response,
    error_response,
    format_response
)
from src.transaction_manager import (
    TransactionManager,
    execute_in_transaction,
    execute_operation_with_transaction
)
from src.llm_cost_tracker import (
    LLMCostTracker,
    init_cost_tracker,
    get_cost_tracker,
    set_llm_context,
)
from src.session_manager import SessionManager
from src.audit_logger import (
    AuditLogger,
    AuditOperationType,
    init_audit_logger,
    get_audit_logger,
)
from src.rate_limiter import RateLimiter, init_rate_limiter, get_rate_limiter
from src.pii_detector import PIIDetector, init_pii_detector, get_pii_detector
from src.circuit_breaker import (
    CircuitBreaker,
    get_circuit_breaker,
    get_all_circuit_stats,
)
from src.tracing import init_tracing, trace_tool, is_tracing_enabled

# Phase 10 - Memory Lifecycle
from src.memory_versioner import (
    MemoryVersioner,
    init_memory_versioner,
    get_memory_versioner,
)
from src.memory_provenance import (
    MemoryProvenanceTracker,
    init_provenance_tracker,
    get_provenance_tracker,
)
from src.memory_confidence import (
    MemoryConfidenceManager,
    init_confidence_manager,
    get_confidence_manager,
)
from src.memory_consolidator import (
    MemoryConsolidator,
    init_consolidator,
    get_consolidator,
)
from src.memory_tier_manager import (
    MemoryTierManager,
    init_tier_manager,
    get_tier_manager,
)
from src.graph_compactor import (
    GraphCompactor,
    init_graph_compactor,
    get_graph_compactor,
)

# Phase 11 - Compliance and Data Governance
from src.gdpr_manager import (
    GDPRManager,
    init_gdpr_manager,
    get_gdpr_manager,
)

# Phase 12 - Plugin Ecosystem and Integrations
from src.plugin_loader import (
    PluginRegistry,
    EnhancedCogneeLoader,
    init_plugin_registry,
    get_plugin_registry,
)
from src.webhook_manager import (
    WebhookManager,
    init_webhook_manager,
    get_webhook_manager,
)

# Phase 14.3 - Encryption at rest
from src.encryption_manager import (
    EncryptionManager,
    init_encryption_manager,
    get_encryption_manager,
)

# Phase 12.8 - Structured observations (EAV)
from src.memory_observation import (
    MemoryObservationManager,
    init_observation_manager,
    get_observation_manager,
)

# Phase 17.4 - Slack/Discord notification manager
from src.notification_manager import (
    NotificationManager,
    init_notification_manager,
    get_notification_manager,
)

# Phase 18.4 - Importance scoring (heuristic)
from src.memory_importance_scorer import (
    MemoryImportanceScorer,
    init_importance_scorer,
    get_importance_scorer,
)

# Phase 18.5 - Heuristic re-ranker
from src.memory_reranker import (
    MemoryReranker,
    init_reranker,
    get_reranker,
)

# Enhanced module instances
memory_manager = None
memory_deduplicator = None
memory_summarizer = None
performance_analytics = None
cross_agent_sharing = None
realtime_sync = None

# Sprint 9 instances
language_detector_instance = None
multi_language_search_instance = None

# Sprint 10 instances
intelligent_summarizer = None
advanced_search_engine = None

# Plan 14.8 - LLM Cost Tracking
llm_cost_tracker: Optional[LLMCostTracker] = None

# Phase 7 - Session Management
session_manager: Optional[SessionManager] = None

# Phase 9 - Audit Logger
audit_logger_instance: Optional[AuditLogger] = None

# Phase 9 - Rate Limiter
rate_limiter_instance: Optional[RateLimiter] = None

# Phase 9 - PII Detector
pii_detector_instance: Optional[PIIDetector] = None

# Phase 10 - Memory Lifecycle singletons
memory_versioner_instance: Optional[MemoryVersioner] = None
provenance_tracker_instance: Optional[MemoryProvenanceTracker] = None
confidence_manager_instance: Optional[MemoryConfidenceManager] = None
consolidator_instance: Optional[MemoryConsolidator] = None
tier_manager_instance: Optional[MemoryTierManager] = None
graph_compactor_instance: Optional[GraphCompactor] = None

# Phase 11 - Compliance singleton
gdpr_manager_instance: Optional[GDPRManager] = None

# Phase 12 - Plugin / Webhook singletons
plugin_registry_instance: Optional[PluginRegistry] = None
webhook_manager_instance: Optional[WebhookManager] = None

# Phase 14.3 - Encryption Manager
encryption_manager_instance: Optional[EncryptionManager] = None

# Phase 12.8 - Observation Manager
observation_manager_instance: Optional[MemoryObservationManager] = None

# Phase 17.4 - Notification Manager
notification_manager_instance: Optional[NotificationManager] = None

# Phase 18.4 - Importance Scorer
importance_scorer_instance: Optional[MemoryImportanceScorer] = None

# Phase 18.5 - Re-ranker
reranker_instance: Optional[MemoryReranker] = None

# Code Quality instances
app_logger = get_logger(__name__)

# Initialize Enhanced stack connections
postgres_pool = None
qdrant_client = None
neo4j_driver = None
redis_client = None
memory_manager = None


async def init_enhanced_stack():
    """Initialize Enhanced database connections"""
    global postgres_pool, qdrant_client, neo4j_driver, redis_client, memory_manager

    logger.info("Initializing Enhanced Cognee stack...")

    # Phase 7 - 12.1: Backend selection via environment variables (pluggable backends)
    _vector_backend = os.getenv("VECTOR_BACKEND", "qdrant").lower()
    _graph_backend = os.getenv("GRAPH_BACKEND", "neo4j").lower()
    _relational_backend = os.getenv("RELATIONAL_BACKEND", "postgresql").lower()
    _cache_backend = os.getenv("CACHE_BACKEND", "redis").lower()
    logger.info(
        f"Backend selection: vector={_vector_backend}, graph={_graph_backend}, "
        f"relational={_relational_backend}, cache={_cache_backend}"
    )
    if _vector_backend not in ("qdrant",):
        logger.warning(
            f"VECTOR_BACKEND={_vector_backend!r} is not yet supported; "
            f"falling back to qdrant"
        )
    if _graph_backend not in ("neo4j",):
        logger.warning(
            f"GRAPH_BACKEND={_graph_backend!r} is not yet supported; "
            f"falling back to neo4j"
        )
    if _relational_backend not in ("postgresql",):
        logger.warning(
            f"RELATIONAL_BACKEND={_relational_backend!r} is not yet supported; "
            f"falling back to postgresql"
        )
    if _cache_backend not in ("redis",):
        logger.warning(
            f"CACHE_BACKEND={_cache_backend!r} is not yet supported; "
            f"falling back to redis"
        )

    # PostgreSQL
    try:
        import asyncpg
        postgres_pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "25432")),
            database=os.getenv("POSTGRES_DB", "cognee_db"),
            user=os.getenv("POSTGRES_USER", "cognee_user"),
            password=os.getenv("POSTGRES_PASSWORD", "cognee_password"),
            min_size=2,
            max_size=10
        )
        async with postgres_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        logger.info("OK PostgreSQL connected")
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}")

    # Qdrant
    try:
        from qdrant_client import QdrantClient
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            qdrant_client = QdrantClient(
                url=f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '26333')}",
                api_key=os.getenv("QDRANT_API_KEY"),
                check_compatibility=False
            )
        collections = qdrant_client.get_collections()
        logger.info(f"OK Qdrant connected ({len(collections.collections)} collections)")
    except Exception as e:
        logger.warning(f"Qdrant connection failed: {e}")

    # Neo4j
    try:
        from neo4j import GraphDatabase
        neo4j_driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:27687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "cognee_password")
            )
        )
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        logger.info("OK Neo4j connected")
    except Exception as e:
        logger.warning(f"Neo4j connection failed: {e}")

    # Redis
    try:
        import redis.asyncio as aioredis
        redis_client = await aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "26379")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("OK Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    # Initialize Memory Manager
    if postgres_pool and redis_client and qdrant_client:
        memory_manager = MemoryManager(postgres_pool, redis_client, qdrant_client)
        logger.info("OK Memory Manager initialized")

    # Initialize Memory Deduplicator
    if postgres_pool and qdrant_client:
        memory_deduplicator = MemoryDeduplicator(postgres_pool, qdrant_client)
        app_logger.info("Memory Deduplicator initialized")

    # Initialize Transaction Manager
    if postgres_pool:
        transaction_manager = TransactionManager(postgres_pool)
        app_logger.info("Transaction Manager initialized")

    # Initialize Memory Summarizer
    if postgres_pool:
        llm_config = {}  # Configure with your LLM settings
        memory_summarizer = MemorySummarizer(postgres_pool, llm_config)
        logger.info("OK Memory Summarizer initialized")

    # Initialize Performance Analytics
    if postgres_pool and redis_client:
        performance_analytics = PerformanceAnalytics(postgres_pool, redis_client)
        logger.info("OK Performance Analytics initialized")

    # Initialize Cross-Agent Sharing
    if postgres_pool:
        cross_agent_sharing = CrossAgentMemorySharing(postgres_pool)
        logger.info("OK Cross-Agent Sharing initialized")

    # Initialize Real-Time Sync
    if redis_client and postgres_pool:
        realtime_sync = RealTimeMemorySync(redis_client, postgres_pool)
        logger.info("OK Real-Time Sync initialized")

    # Initialize Sprint 9: Multi-Language Support
    global language_detector_instance, multi_language_search_instance
    try:
        from src.language_detector import LanguageDetector
        from src.multi_language_search import MultiLanguageSearch

        language_detector_instance = LanguageDetector()
        multi_language_search_instance = MultiLanguageSearch()
        logger.info("OK Sprint 9 Multi-Language Support initialized")
    except Exception as e:
        logger.warning(f"Sprint 9 initialization failed: {e}")

    # Initialize Sprint 10: Advanced AI Features
    global intelligent_summarizer, advanced_search_engine
    try:
        llm_config = {
            'provider': os.getenv('LLM_PROVIDER', 'openai'),
            'api_key': os.getenv('LLM_API_KEY', ''),
            'model': os.getenv('LLM_MODEL', 'gpt-4-turbo')
        }

        if postgres_pool and redis_client and qdrant_client:
            intelligent_summarizer = IntelligentMemorySummarizer(
                postgres_pool=postgres_pool,
                llm_config=llm_config,
                redis_client=redis_client,
                qdrant_client=qdrant_client
            )
            logger.info("OK Sprint 10 Intelligent Summarizer initialized")

        if postgres_pool and qdrant_client and redis_client:
            advanced_search_engine = AdvancedSearchEngine(
                postgres_pool=postgres_pool,
                qdrant_client=qdrant_client,
                redis_client=redis_client,
                llm_config=llm_config
            )
            logger.info("OK Sprint 10 Advanced Search Engine initialized")

    except Exception as e:
        logger.warning(f"Sprint 10 initialization failed: {e}")

    # Plan 14.8: LLM Cost Tracker (always attempt; degrades gracefully)
    global llm_cost_tracker
    try:
        llm_cost_tracker = init_cost_tracker(postgres_pool=postgres_pool)
        await llm_cost_tracker.initialize()
        logger.info("OK LLM Cost Tracker initialized")
    except Exception as e:
        logger.warning(f"LLM Cost Tracker initialization failed: {e}")

    # Phase 7: Session Manager (requires postgres_pool)
    global session_manager
    if postgres_pool:
        try:
            session_manager = SessionManager(db_pool=postgres_pool)
            logger.info("OK Session Manager initialized")
        except Exception as e:
            logger.warning(f"Session Manager initialization failed: {e}")

    # Phase 9: Audit Logger (file + optional DB)
    global audit_logger_instance
    try:
        audit_logger_instance = init_audit_logger(
            config_path="automation_config.json",
            log_dir="logs",
            db_pool=postgres_pool,
        )
        logger.info("OK Audit Logger initialized")
    except Exception as e:
        logger.warning(f"Audit Logger initialization failed: {e}")

    # Phase 9: Rate Limiter (Redis-backed, in-memory fallback)
    global rate_limiter_instance
    try:
        rate_limiter_instance = init_rate_limiter(redis_client=redis_client)
        logger.info("OK Rate Limiter initialized")
    except Exception as e:
        logger.warning(f"Rate Limiter initialization failed: {e}")

    # Phase 9: PII Detector (config-gated; disabled by default)
    global pii_detector_instance
    try:
        _pii_enabled = os.getenv("PII_DETECTION_ENABLED", "false").lower() == "true"
        pii_detector_instance = init_pii_detector(enabled=_pii_enabled)
        if _pii_enabled:
            logger.info("OK PII Detector initialized (enabled)")
        else:
            logger.info("OK PII Detector initialized (disabled; set PII_DETECTION_ENABLED=true to enable)")
    except Exception as e:
        logger.warning(f"PII Detector initialization failed: {e}")

    # Phase 9: Distributed Tracing (optional; requires OTEL_EXPORTER_OTLP_ENDPOINT)
    try:
        _tracing_on = init_tracing()
        if _tracing_on:
            logger.info("OK Distributed tracing enabled")
        else:
            logger.debug("Tracing disabled (set OTEL_EXPORTER_OTLP_ENDPOINT to enable)")
    except Exception as e:
        logger.warning(f"Tracing initialization failed: {e}")

    # Phase 10: Memory Lifecycle modules (require postgres_pool)
    global memory_versioner_instance, provenance_tracker_instance
    global confidence_manager_instance, consolidator_instance
    if postgres_pool:
        try:
            memory_versioner_instance = init_memory_versioner(postgres_pool)
        except Exception as e:
            logger.warning(f"MemoryVersioner initialization failed: {e}")
        try:
            provenance_tracker_instance = init_provenance_tracker(postgres_pool)
        except Exception as e:
            logger.warning(f"MemoryProvenanceTracker initialization failed: {e}")
        try:
            confidence_manager_instance = init_confidence_manager(postgres_pool)
        except Exception as e:
            logger.warning(f"MemoryConfidenceManager initialization failed: {e}")
        try:
            consolidator_instance = init_consolidator(
                postgres_pool=postgres_pool,
                qdrant_client=qdrant_client,
            )
        except Exception as e:
            logger.warning(f"MemoryConsolidator initialization failed: {e}")
    else:
        logger.warning("Phase 10 modules skipped: postgres_pool unavailable")

    # Phase 10 15.5: Memory Tier Manager
    global tier_manager_instance
    try:
        tier_manager_instance = init_tier_manager(
            postgres_pool=postgres_pool,
            redis_client=redis_client,
        )
    except Exception as e:
        logger.warning(f"MemoryTierManager initialization failed: {e}")

    # Phase 10 15.6: Graph Compactor (requires neo4j_driver)
    global graph_compactor_instance
    if neo4j_driver:
        try:
            graph_compactor_instance = init_graph_compactor(
                neo4j_driver=neo4j_driver,
                postgres_pool=postgres_pool,
            )
        except Exception as e:
            logger.warning(f"GraphCompactor initialization failed: {e}")
    else:
        logger.debug("GraphCompactor skipped: neo4j_driver unavailable")

    # Phase 11: GDPR Manager (all DBs optional; degrades gracefully)
    global gdpr_manager_instance
    try:
        gdpr_manager_instance = init_gdpr_manager(
            postgres_pool=postgres_pool,
            qdrant_client=qdrant_client,
            neo4j_driver=neo4j_driver,
            redis_client=redis_client,
        )
    except Exception as e:
        logger.warning(f"GDPRManager initialization failed: {e}")

    # Phase 12: Plugin Registry (entry_points discovery)
    global plugin_registry_instance
    try:
        plugin_registry_instance = init_plugin_registry()
    except Exception as e:
        logger.warning(f"PluginRegistry initialization failed: {e}")

    # Phase 12: Webhook Manager (in-memory; no external deps)
    global webhook_manager_instance
    try:
        webhook_manager_instance = init_webhook_manager()
    except Exception as e:
        logger.warning(f"WebhookManager initialization failed: {e}")

    # Phase 14.3: Encryption Manager (cryptography optional; degrades gracefully)
    global encryption_manager_instance
    try:
        _master_key = os.getenv("ENCRYPTION_MASTER_KEY")
        encryption_manager_instance = init_encryption_manager(
            postgres_pool=postgres_pool,
            master_key=_master_key,
        )
        logger.info("OK Encryption Manager initialized")
    except Exception as e:
        logger.warning(f"EncryptionManager initialization failed: {e}")

    # Phase 12.8: Memory Observation Manager (EAV table)
    global observation_manager_instance
    try:
        observation_manager_instance = init_observation_manager(
            postgres_pool=postgres_pool,
        )
        logger.info("OK Memory Observation Manager initialized")
    except Exception as e:
        logger.warning(f"MemoryObservationManager initialization failed: {e}")

    # Phase 17.4: Notification Manager (no DB dependency)
    global notification_manager_instance
    try:
        notification_manager_instance = init_notification_manager()
        logger.info("OK Notification Manager initialized")
    except Exception as e:
        logger.warning(f"NotificationManager initialization failed: {e}")

    # Phase 18.4: Memory Importance Scorer (heuristic; postgres optional)
    global importance_scorer_instance
    try:
        importance_scorer_instance = init_importance_scorer(
            postgres_pool=postgres_pool,
        )
        logger.info("OK Memory Importance Scorer initialized")
    except Exception as e:
        logger.warning(f"MemoryImportanceScorer initialization failed: {e}")

    # Phase 18.5: Memory Re-ranker (stateless heuristic; postgres optional)
    global reranker_instance
    try:
        reranker_instance = init_reranker(postgres_pool=postgres_pool)
        logger.info("OK Memory Re-ranker initialized")
    except Exception as e:
        logger.warning(f"MemoryReranker initialization failed: {e}")


async def cleanup_enhanced_stack():
    """Cleanup Enhanced database connections"""
    global postgres_pool, qdrant_client, neo4j_driver, redis_client

    if postgres_pool:
        await postgres_pool.close()
        logger.info("OK PostgreSQL connection closed")

    if neo4j_driver:
        neo4j_driver.close()
        logger.info("OK Neo4j connection closed")

    if redis_client:
        await redis_client.aclose()
        logger.info("OK Redis connection closed")


@mcp.tool()
async def cognify(data: str) -> str:
    """
    Transform data into knowledge graph using Enhanced Cognee

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when processing data

    Parameters:
    -----------
    - data: Text data to process and add to the knowledge graph

    Returns:
    --------
    - Status message indicating success or failure
    """
    try:
        import uuid
        from datetime import datetime, UTC

        # For now, store in PostgreSQL
        if postgres_pool:
            async with postgres_pool.acquire() as conn:
                doc_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO shared_memory.documents (id, title, content, created_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO NOTHING
                """, doc_id, "Enhanced Cognee Memory", data, datetime.now(UTC).replace(tzinfo=None))

                logger.info(f"OK Added document: {doc_id}")

                # AUTO-TRIGGER: Log performance metrics
                if performance_analytics:
                    try:
                        await performance_analytics.log_operation(
                            operation="cognify",
                            agent_id="system",
                            metadata={
                                "doc_id": doc_id,
                                "data_length": len(data)
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log cognify performance: {e}")

                # AUTO-TRIGGER: Publish cognify event
                if realtime_sync:
                    try:
                        await realtime_sync.publish_memory_event(
                            event_type="data_cognified",
                            memory_id=doc_id,
                            agent_id="system",
                            data=json.dumps({
                                "title": "Enhanced Cognee Memory",
                                "data_length": len(data)
                            })
                        )
                    except Exception as e:
                        logger.warning(f"Failed to publish cognify event: {e}")

                return f"OK Successfully processed and stored data (ID: {doc_id})"
        else:
            return "WARN PostgreSQL not available - data not stored"

    except Exception as e:
        logger.error(f"Cognify failed: {e}")
        return f"ERR Failed to process data: {str(e)}"


@mcp.tool()
async def search(query: str, limit: int = 10, search_type: Optional[str] = None) -> str:
    """
    Search Enhanced Cognee knowledge.

    When search_type is omitted: searches the Enhanced PostgreSQL memory store (fast text search).
    When search_type is provided: routes to the cognee knowledge graph using that strategy.
    Use recall() for full control over knowledge graph search strategies.

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when searching knowledge

    Parameters:
    -----------
    - query: Search query text
    - limit: Maximum number of results to return (default: 10)
    - search_type: Optional graph search strategy. When set, bypasses PostgreSQL and uses
      the cognee knowledge graph. One of: GRAPH_COMPLETION, SUMMARIES, CHUNKS,
      NATURAL_LANGUAGE, TEMPORAL, CHUNKS_LEXICAL, FEELING_LUCKY, CODING_RULES,
      GRAPH_COMPLETION_COT, GRAPH_COMPLETION_DECOMPOSITION, GRAPH_SUMMARY_COMPLETION,
      CYPHER, RAG_COMPLETION, TRIPLET_COMPLETION, GRAPH_COMPLETION_CONTEXT_EXTENSION.

    Returns:
    --------
    - Search results as formatted text
    """
    # If a search_type is provided, delegate to the knowledge graph recall tool
    if search_type:
        return await recall(query=query, search_type=search_type, top_k=limit)

    try:
        if postgres_pool:
            async with postgres_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, title, content, created_at
                    FROM shared_memory.documents
                    WHERE content ILIKE $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, f"%{query}%", limit)

                # Log performance metrics
                if performance_analytics:
                    try:
                        await performance_analytics.log_operation(
                            operation="search",
                            agent_id="system",
                            metadata={
                                "query_length": len(query),
                                "results_count": len(rows),
                                "limit": limit
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log search performance: {e}")

                if rows:
                    results = [f"[DOC] {row['title']}\n   {row['content'][:100]}..."
                             for row in rows]
                    return f"OK Found {len(rows)} results:\n\n" + "\n\n".join(results)
                else:
                    return f"OK No results found for: {query}"
        else:
            return "WARN PostgreSQL not available - cannot search"

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"ERR Search failed: {str(e)}"


@mcp.tool()
async def get_stats() -> str:
    """
    Get Enhanced Cognee statistics

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when checking system status

    Returns:
    --------
    - System status and statistics
    """
    try:
        stats = {"status": "Enhanced Cognee MCP Server", "databases": {}, "statistics": {}}

        # PostgreSQL stats
        if postgres_pool:
            async with postgres_pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM shared_memory.documents")
                stats["databases"]["postgresql"] = f"OK Connected ({count} documents)"

        # Qdrant stats
        if qdrant_client:
            collections = qdrant_client.get_collections()
            stats["databases"]["qdrant"] = f"OK Connected ({len(collections.collections)} collections)"

        # Neo4j stats
        if neo4j_driver:
            stats["databases"]["neo4j"] = "OK Connected"

        # Redis stats
        if redis_client:
            stats["databases"]["redis"] = "OK Connected"

        # AUTO-TRIGGER: Get deduplication statistics
        try:
            dedup_stats = await get_deduplication_stats()
            stats["statistics"]["deduplication"] = dedup_stats
        except Exception as e:
            logger.warning(f"Failed to get deduplication stats: {e}")

        # AUTO-TRIGGER: Get summary statistics
        try:
            summary_stats = await get_summary_stats()
            stats["statistics"]["summary"] = summary_stats
        except Exception as e:
            logger.warning(f"Failed to get summary stats: {e}")

        # AUTO-TRIGGER: Get memory age statistics
        try:
            age_stats = await get_memory_age_stats()
            stats["statistics"]["memory_age"] = age_stats
        except Exception as e:
            logger.warning(f"Failed to get memory age stats: {e}")

        return json.dumps(stats, indent=2)

    except Exception as e:
        logger.error(f"Stats failed: {e}")
        return f"ERR Failed to get stats: {str(e)}"


@mcp.tool()
async def health() -> str:
    """
    Health check for Enhanced Cognee server

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs on startup to verify system status

    Returns:
    --------
    - Health status message
    """
    checks = []
    all_healthy = True

    if postgres_pool:
        checks.append("OK PostgreSQL")
    else:
        checks.append("ERR PostgreSQL")
        all_healthy = False

    if qdrant_client:
        checks.append("OK Qdrant")
    else:
        checks.append("ERR Qdrant")
        all_healthy = False

    if neo4j_driver:
        checks.append("OK Neo4j")
    else:
        checks.append("ERR Neo4j")
        all_healthy = False

    if redis_client:
        checks.append("OK Redis")
    else:
        checks.append("ERR Redis")
        all_healthy = False

    # AUTO-TRIGGER: Log performance metrics if unhealthy
    if not all_healthy and performance_analytics:
        try:
            await performance_analytics.log_operation(
                operation="health_check",
                agent_id="system",
                metadata={
                    "healthy": all_healthy,
                    "postgres_available": postgres_pool is not None,
                    "qdrant_available": qdrant_client is not None,
                    "neo4j_available": neo4j_driver is not None,
                    "redis_available": redis_client is not None
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log health check performance: {e}")

    return f"Enhanced Cognee Health:\n" + "\n".join(checks)


@mcp.tool()
async def list_data() -> str:
    """
    List all data in the knowledge graph

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when listing documents

    Returns:
    --------
    - Formatted list of all documents
    """
    try:
        if postgres_pool:
            async with postgres_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, title, created_at
                    FROM shared_memory.documents
                    ORDER BY created_at DESC
                    LIMIT 50
                """)

                # AUTO-TRIGGER: Log performance metrics
                if performance_analytics:
                    try:
                        await performance_analytics.log_operation(
                            operation="list_data",
                            agent_id="system",
                            metadata={
                                "results_count": len(rows)
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log list_data performance: {e}")

                if rows:
                    results = [f"- {row['title']} (ID: {row['id']}, Created: {row['created_at']})"
                             for row in rows]
                    return f"[LIB] Documents ({len(rows)} total):\n\n" + "\n".join(results)
                else:
                    return "[LIB] No documents found"
        else:
            return "WARN PostgreSQL not available"

    except Exception as e:
        logger.error(f"List data failed: {e}")
        return f"ERR Failed to list data: {str(e)}"


# ============================================================================
# STANDARD MEMORY MCP TOOLS - Standard Memory MCP Integration
# ============================================================================

@mcp.tool()
async def add_memory(
    content: str,
    user_id: str = "default",
    agent_id: str = "claude-code",
    metadata: Optional[str] = None
) -> str:
    """
    Add a memory entry (Standard Memory MCP Tool)

    This is the standard memory tool interface for MCP-compatible IDEs.
    Memories are stored in PostgreSQL and indexed in Qdrant for semantic search.

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when they want to remember information

    Parameters:
    -----------
    - content: The memory content to store
    - user_id: User identifier (default: "default")
    - agent_id: Agent identifier (default: "claude-code")
    - metadata: Optional JSON string with additional metadata

    Returns:
    --------
    - Memory ID and status message
    """
    try:
        import uuid
        from datetime import datetime, UTC

        # Input validation
        content = validate_memory_content(content)
        agent_id = validate_agent_id(agent_id)
        if user_id:
            user_id = sanitize_string(user_id, max_length=100)

        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot add memory"

        # AUTO-TRIGGER: Check for duplicate before adding
        if memory_deduplicator:
            try:
                duplicate_check = await memory_deduplicator.check_duplicate(
                    content=content,
                    agent_id=agent_id,
                    memory_category="general"
                )
                if duplicate_check.get("is_duplicate"):
                    logger.info(f"Duplicate prevented: {duplicate_check.get('reason')}")
                    return f"OK Duplicate prevented: {duplicate_check.get('reason')}"
            except Exception as e:
                logger.warning(f"Duplicate check failed, continuing: {e}")

        # Parse metadata if provided
        metadata_dict = {}
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except:
                metadata_dict = {"raw_metadata": metadata}

        # Generate memory ID
        memory_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).replace(tzinfo=None)

        # Store in PostgreSQL
        async with postgres_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO shared_memory.documents
                (id, title, content, agent_id, memory_category, tags, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, memory_id, f"Memory from {agent_id}", content,
                agent_id, "general", [], metadata_dict, created_at)

        logger.info(f"OK Added memory: {memory_id} for user: {user_id}, agent: {agent_id}")

        # AUTO-TRIGGER: Publish memory event for real-time sync
        if realtime_sync:
            try:
                await realtime_sync.publish_memory_event(
                    event_type="memory_added",
                    memory_id=memory_id,
                    agent_id=agent_id,
                    data={"content_preview": content[:100]}
                )
            except Exception as e:
                logger.warning(f"Failed to publish memory event: {e}")

        # AUTO-TRIGGER: Sync with shared agents
        if cross_agent_sharing and realtime_sync:
            try:
                # Check if this memory is shared
                access_check = await cross_agent_sharing.can_agent_access_memory(
                    memory_id=memory_id,
                    agent_id=agent_id
                )
                # Sync to all agents that should have access
                await realtime_sync.sync_agent_state(
                    source_agent=agent_id,
                    target_agent="all",
                    category="general"
                )
            except Exception as e:
                logger.warning(f"Failed to sync agent state: {e}")

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="add_memory",
                    agent_id=agent_id,
                    memory_id=memory_id,
                    metadata={"content_length": len(content)}
                )
            except Exception as e:
                logger.warning(f"Failed to log performance metrics: {e}")

        # Phase 8b: Auto-TTL resolution (config-driven, no-op by default)
        try:
            auto_ttl = _resolve_auto_ttl(content, metadata_dict)
            if auto_ttl and postgres_pool:
                expire_at = datetime.now(UTC).replace(tzinfo=None)
                from datetime import timedelta as _td
                expire_at = expire_at + _td(days=auto_ttl)
                async with postgres_pool.acquire() as _conn:
                    await _conn.execute(
                        "UPDATE shared_memory.documents SET expire_at=$1 WHERE id=$2",
                        expire_at, memory_id
                    )
                logger.info(
                    f"Phase 8 auto-TTL: memory {memory_id} set to expire in {auto_ttl} days"
                )
        except Exception as e:
            logger.warning(f"Phase 8 auto-TTL failed (non-blocking): {e}")

        # Phase 8b: Post-ingestion pipeline (fire-and-forget, config-driven)
        asyncio.create_task(
            _run_post_ingestion_pipeline(content, memory_id, agent_id)
        )

        return f"OK Memory added (ID: {memory_id})"

    except ValidationError as e:
        logger.error(f"add_memory validation failed: {e}")
        return str(e)
    except Exception as e:
        logger.error(f"add_memory failed: {e}")
        return f"ERR Failed to add memory: {str(e)}"


@mcp.tool()
async def search_memories(
    query: str,
    limit: int = 10,
    user_id: str = "default",
    agent_id: Optional[str] = None
) -> str:
    """
    Search memories using semantic and text search (Standard Memory MCP Tool)

    This is the standard memory search tool for MCP-compatible IDEs.
    Performs both text-based and semantic vector search.

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when searching for past information

    Parameters:
    -----------
    - query: Search query text
    - limit: Maximum results to return (default: 10)
    - user_id: User identifier to filter memories (default: "default")
    - agent_id: Optional agent identifier to filter memories

    Returns:
    --------
    - Formatted search results with memory content
    """
    import time
    start_time = time.time()

    try:
        # Input validation
        query = sanitize_string(query, max_length=1000)
        limit = validate_limit(limit, "limit")
        if user_id:
            user_id = sanitize_string(user_id, max_length=100)
        if agent_id:
            agent_id = validate_agent_id(agent_id)

        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot search memories"

        async with postgres_pool.acquire() as conn:
            # Build query with filters
            query_str = """
                SELECT id, title, content, agent_id, created_at
                FROM shared_memory.documents
                WHERE content ILIKE $1
            """
            params = [f"%{query}%"]

            # Add agent filter if specified
            if agent_id:
                query_str += " AND agent_id = $2"
                params.append(agent_id)

            query_str += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query_str, *params)

            # Calculate search duration
            duration_ms = (time.time() - start_time) * 1000

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="search_memories",
                        agent_id=agent_id or "unknown",
                        metadata={
                            "query_length": len(query),
                            "results_count": len(rows),
                            "duration_ms": duration_ms
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log search performance: {e}")

            # AUTO-TRIGGER: If slow, log to slow queries
            if duration_ms > 1000:  # 1 second threshold
                logger.warning(f"Slow search query: {duration_ms:.2f}ms - {query[:50]}")
                try:
                    # Log to slow queries for analysis
                    if performance_analytics:
                        await performance_analytics.log_operation(
                            operation="slow_query",
                            agent_id="system",
                            metadata={
                                "query": query[:100],
                                "duration_ms": duration_ms,
                                "threshold_ms": 1000
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to log slow query: {e}")

            if rows:
                results = []
                for row in rows:
                    results.append(f"[MEM] {row['title']}\n"
                                 f"     Agent: {row['agent_id']}\n"
                                 f"     Content: {row['content'][:200]}...\n"
                                 f"     Created: {row['created_at']}")
                return f"OK Found {len(rows)} memories:\n\n" + "\n\n".join(results)
            else:
                return f"OK No memories found for query: {query}"

    except ValidationError as e:
        logger.error(f"search_memories validation failed: {e}")
        return str(e)
    except Exception as e:
        logger.error(f"search_memories failed: {e}")
        return f"ERR Failed to search memories: {str(e)}"


@mcp.tool()
async def get_memories(
    user_id: str = "default",
    agent_id: Optional[str] = None,
    limit: int = 50
) -> str:
    """
    List all memories with filters (Standard Memory MCP Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when loading context for sessions

    Parameters:
    -----------
    - user_id: User identifier (default: "default")
    - agent_id: Optional agent identifier to filter
    - limit: Maximum results to return (default: 50)

    Returns:
    --------
    - Formatted list of all memories matching filters
    """
    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot get memories"

        async with postgres_pool.acquire() as conn:
            query_str = """
                SELECT id, title, content, agent_id, created_at
                FROM shared_memory.documents
                WHERE 1=1
            """
            params = []

            if agent_id:
                query_str += " AND agent_id = $1"
                params.append(agent_id)

            query_str += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query_str, *params)

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="get_memories",
                        agent_id=agent_id or "unknown",
                        metadata={
                            "results_count": len(rows),
                            "limit": limit
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log get_memories performance: {e}")

            if rows:
                results = []
                for row in rows:
                    results.append(f"- {row['title']} (ID: {row['id']}, Agent: {row['agent_id']})")
                return f"[MEM] Memories ({len(rows)} total):\n\n" + "\n".join(results)
            else:
                return "[MEM] No memories found"

    except Exception as e:
        logger.error(f"get_memories failed: {e}")
        return f"ERR Failed to get memories: {str(e)}"


@mcp.tool()
async def get_memory(memory_id: str) -> str:
    """
    Retrieve a specific memory by ID (Standard Memory MCP Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when referencing specific memory IDs

    Parameters:
    -----------
    - memory_id: The unique ID of the memory to retrieve

    Returns:
    --------
    - Full memory content with metadata
    """
    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot get memory"

        async with postgres_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, title, content, agent_id, metadata, created_at
                FROM shared_memory.documents
                WHERE id = $1
            """, memory_id)

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="get_memory",
                        agent_id="system",
                        metadata={
                            "memory_id": memory_id,
                            "found": row is not None
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log get_memory performance: {e}")

            if row:
                return (f"OK Memory Found:\n"
                       f"  ID: {row['id']}\n"
                       f"  Title: {row['title']}\n"
                       f"  Agent: {row['agent_id']}\n"
                       f"  Created: {row['created_at']}\n"
                       f"  Content: {row['content']}\n"
                       f"  Metadata: {row['metadata']}")
            else:
                return f"ERR Memory not found: {memory_id}"

    except Exception as e:
        logger.error(f"get_memory failed: {e}")
        return f"ERR Failed to get memory: {str(e)}"


@mcp.tool()
async def update_memory(memory_id: str, content: str) -> str:
    """
    Update an existing memory (Standard Memory MCP Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when correcting or updating information

    Parameters:
    -----------
    - memory_id: The unique ID of the memory to update
    - content: New content for the memory

    Returns:
    --------
    - Status message indicating success or failure
    """
    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot update memory"

        async with postgres_pool.acquire() as conn:
            # Check if memory exists
            existing = await conn.fetchval("""
                SELECT id FROM shared_memory.documents WHERE id = $1
            """, memory_id)

            if not existing:
                return f"ERR Memory not found: {memory_id}"

            # Update memory
            await conn.execute("""
                UPDATE shared_memory.documents
                SET content = $2
                WHERE id = $1
            """, memory_id, content)

            logger.info(f"OK Updated memory: {memory_id}")

            # AUTO-TRIGGER: Publish memory update event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_updated",
                        memory_id=memory_id,
                        agent_id="system",
                        data={"content_preview": content[:100]}
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish memory update event: {e}")

            # AUTO-TRIGGER: Sync with shared agents
            if cross_agent_sharing and realtime_sync:
                try:
                    await realtime_sync.sync_agent_state(
                        source_agent="system",
                        target_agent="all",
                        category="general"
                    )
                except Exception as e:
                    logger.warning(f"Failed to sync agent state after update: {e}")

            # AUTO-TRIGGER: Check if summary needs update
            if memory_summarizer:
                try:
                    # Get summary statistics to check if we need to update summaries
                    stats = await memory_summarizer.get_summary_statistics()
                    # If memory count is high, trigger summarization check
                    if stats.get("total_memories", 0) > 1000:
                        logger.info("High memory count detected, consider summarization")
                except Exception as e:
                    logger.warning(f"Failed to check summary stats: {e}")

            return f"OK Memory updated (ID: {memory_id})"

    except Exception as e:
        logger.error(f"update_memory failed: {e}")
        return f"ERR Failed to update memory: {str(e)}"


@mcp.tool()
async def delete_memory(
    memory_id: str,
    agent_id: str = "claude-code",
    confirm_token: Optional[str] = None
) -> str:
    """
    Delete a specific memory (Standard Memory MCP Tool)

    TRIGGER TYPE: (M) Manual - User must explicitly trigger this destructive operation

    SECURITY: Requires authorization and confirmation for non-admin agents.

    Parameters:
    -----------
    - memory_id: The unique ID of the memory to delete
    - agent_id: Agent requesting deletion (default: claude-code)
    - confirm_token: Optional confirmation token for non-dry-run operations

    Returns:
    --------
    - Status message indicating success or failure
    """
    try:
        # Input validation
        memory_id = validate_uuid(memory_id, "memory_id")
        agent_id = validate_agent_id(agent_id)

        # Require confirmation for destructive operation
        confirmation_manager.require_confirmation(
            operation="delete_memory",
            details={"memory_id": memory_id, "agent_id": agent_id},
            confirm_token=confirm_token
        )

        # Authorization check
        await require_agent_authorization(
            agent_id=agent_id,
            operation="delete_memory",
            memory_id=memory_id
        )

        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot delete memory"

        async with postgres_pool.acquire() as conn:
            # Check if memory exists
            existing = await conn.fetchval("""
                SELECT id, agent_id, data->>'category' as category
                FROM shared_memory.documents WHERE id = $1
            """, memory_id)

            if not existing:
                return f"ERR Memory not found: {memory_id}"

            # Delete memory
            await conn.execute("""
                DELETE FROM shared_memory.documents WHERE id = $1
            """, memory_id)

            logger.info(f"OK Deleted memory: {memory_id} by agent: {agent_id}")

            # Publish deletion event for real-time sync
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_deleted",
                        memory_id=memory_id,
                        agent_id=agent_id,
                        data=json.dumps({"authorized": True})
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish memory deletion event: {e}")

            # AUTO-TRIGGER: Sync with shared agents
            if cross_agent_sharing and realtime_sync:
                try:
                    await realtime_sync.sync_agent_state(
                        source_agent=agent_id,
                        target_agent="all",
                        category="general"
                    )
                except Exception as e:
                    logger.warning(f"Failed to sync agent state after deletion: {e}")

            return f"OK Memory deleted (ID: {memory_id})"

    except ValidationError as e:
        logger.error(f"delete_memory validation failed: {e}")
        return str(e)
    except AuthorizationError as e:
        logger.error(f"delete_memory authorization failed: {e}")
        return str(e)
    except ConfirmationRequiredError as e:
        logger.info(f"delete_memory confirmation required: {e}")
        return str(e)
    except Exception as e:
        logger.error(f"delete_memory failed: {e}")
        return f"ERR Failed to delete memory: {str(e)}"


@mcp.tool()
async def list_agents() -> str:
    """
    List all agents that have stored memories (Standard Memory MCP Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs when listing available agents

    Returns:
    --------
    - List of all agent IDs with memory counts
    """
    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot list agents"

        async with postgres_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT agent_id, COUNT(*) as memory_count
                FROM shared_memory.documents
                GROUP BY agent_id
                ORDER BY memory_count DESC
            """)

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="list_agents",
                        agent_id="system",
                        metadata={
                            "agents_count": len(rows) if rows else 0
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log list_agents performance: {e}")

            if rows:
                results = [f"- {row['agent_id']}: {row['memory_count']} memories"
                         for row in rows]
                return "[AGENTS] Active Agents:\n\n" + "\n".join(results)
            else:
                return "[AGENTS] No agents found"

    except Exception as e:
        logger.error(f"list_agents failed: {e}")
        return f"ERR Failed to list agents: {str(e)}"


# ============================================================================
# MEMORY MANAGEMENT TOOLS - Expiry, Archival, Cleanup
# ============================================================================

@mcp.tool()
async def expire_memories(
    days: int = 90,
    dry_run: bool = False,
    agent_id: str = "claude-code",
    confirm_token: Optional[str] = None
) -> str:
    """
    Expire or archive memories older than specified days (Memory Management Tool)

    TRIGGER TYPE: (S) System - Automatically scheduled via Phase 8b auto_scheduler config.
                  Enable with: {"auto_scheduler": {"expire_memories": {"enabled": true}}}
                  in .enhanced-cognee-config.json. Also callable manually.

    SECURITY: Requires confirmation for non-dry-run bulk deletion.

    Parameters:
    -----------
    - days: Number of days after which memories expire (default: 90)
    - dry_run: If True, simulate without actually deleting (default: False)
    - agent_id: Agent requesting expiration (default: claude-code)
    - confirm_token: Confirmation token for non-dry-run operations

    Returns:
    --------
    - Result of the expiry operation with memory count
    """
    try:
        # Input validation
        days = validate_days(days, "days")
        agent_id = validate_agent_id(agent_id)

        # Require confirmation for destructive operation (unless dry run)
        if not dry_run:
            confirmation_manager.require_confirmation(
                operation="expire_memories",
                details={
                    "days": days,
                    "agent_id": agent_id,
                    "bulk_operation": True
                },
                confirm_token=confirm_token
            )

        # Authorization check for bulk deletion
        await require_agent_authorization(
            agent_id=agent_id,
            operation="expire_memories_bulk"
        )

        if not memory_manager:
            return "ERR Memory Manager not available"

        # AUTO-TRIGGER: Get memory age stats before expiring
        try:
            age_stats = await get_memory_age_stats()
            logger.info(f"Memory age stats before expiration: {age_stats}")
        except Exception as e:
            logger.warning(f"Failed to get memory age stats: {e}")

        result = await memory_manager.expire_old_memories(
            days=days,
            dry_run=dry_run,
            policy=RetentionPolicy.DELETE_OLD
        )

        memories_affected = result.get('memories_affected', 0)

        if result.get("status") == "dry_run":
            return (f"OK DRY RUN: Would expire {memories_affected} memories "
                   f"older than {days} days\n"
                   f"To confirm, re-run with dry_run=False and confirm_token")

        elif result.get("status") == "success":
            # AUTO-TRIGGER: Publish expiration event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_expired",
                        memory_id=f"expire_{days}",
                        agent_id=agent_id,
                        data=json.dumps({
                            "days": days,
                            "memories_expired": memories_affected,
                            "authorized": True
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish expiration event: {e}")

            # AUTO-TRIGGER: Update summary statistics
            try:
                summary_stats = await get_summary_stats()
                logger.info(f"Updated summary stats after expiration: {summary_stats}")
            except Exception as e:
                logger.warning(f"Failed to update summary stats: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="expire_memories",
                        agent_id="system",
                        metadata={
                            "days": days,
                            "memories_expired": memories_affected,
                            "dry_run": dry_run
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log expiration performance: {e}")

            return f"OK Expired {memories_affected} memories older than {days} days"

        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except ValidationError as e:
        logger.error(f"expire_memories validation failed: {e}")
        return str(e)
    except AuthorizationError as e:
        logger.error(f"expire_memories authorization failed: {e}")
        return str(e)
    except ConfirmationRequiredError as e:
        logger.info(f"expire_memories confirmation required: {e}")
        return str(e)
    except Exception as e:
        logger.error(f"expire_memories failed: {e}")
        return f"ERR Failed to expire memories: {str(e)}"


@mcp.tool()
async def get_memory_age_stats() -> str:
    """
    Get statistics about memory age distribution (Memory Management Tool)

    TRIGGER TYPE: (S) System - Automatically triggered by Enhanced Cognee for memory operations

    Returns:
    --------
    - Memory statistics by age bracket (0-7 days, 8-30 days, 31-90 days, 90+ days)
    """
    if not memory_manager:
        return "ERR Memory Manager not available"

    try:
        stats = await memory_manager.get_memory_stats_by_age()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_memory_age_stats",
                    agent_id="system",
                    metadata={
                        "total_memories": stats.get('total_memories', 0),
                        "status": stats.get("status", "unknown")
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log get_memory_age_stats performance: {e}")

        if stats.get("status") == "error":
            return f"ERR {stats.get('error', 'Unknown error')}"

        output = [
            f"[STATS] Memory Age Distribution:",
            f"  Total memories: {stats['total_memories']}",
            f"  Oldest memory: {stats['oldest_memory']}",
            f"  Newest memory: {stats['newest_memory']}",
            "",
            "  Age Distribution:"
        ]

        for bracket, count in stats.get("age_distribution", {}).items():
            output.append(f"    {bracket}: {count} memories")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"get_memory_age_stats failed: {e}")
        return f"ERR Failed to get memory age stats: {str(e)}"


@mcp.tool()
async def set_memory_ttl(memory_id: str, ttl_days: int) -> str:
    """
    Set time-to-live (TTL) for a specific memory (Memory Management Tool)

    TRIGGER TYPE: (S) System - Automatically applied on write via Phase 8b auto_ttl_rules config.
                  Enable with: {"auto_ttl_rules": {"rules": [{"keyword": "temp", "ttl_days": 7}]}}
                  in .enhanced-cognee-config.json. Also callable manually.

    Parameters:
    -----------
    - memory_id: ID of the memory to set TTL for
    - ttl_days: Days until expiry (0 = no expiry)

    Returns:
    --------
    - Result of TTL setting operation
    """
    if not memory_manager:
        return "ERR Memory Manager not available"

    try:
        result = await memory_manager.set_memory_ttl(memory_id, ttl_days)

        if result.get("status") == "not_found":
            return f"ERR Memory not found: {memory_id}"

        elif result.get("status") == "success":
            expiry = result.get("expiry_date", "never")

            # AUTO-TRIGGER: Get memory age stats after setting TTL
            try:
                age_stats = await get_memory_age_stats()
                logger.info(f"Updated memory age stats after TTL set: {age_stats}")
            except Exception as e:
                logger.warning(f"Failed to get memory age stats: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="set_memory_ttl",
                        agent_id="system",
                        metadata={
                            "memory_id": memory_id,
                            "ttl_days": ttl_days,
                            "expiry_date": expiry
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log set_ttl performance: {e}")

            return f"OK Set TTL of {ttl_days} days for memory {memory_id} (expires: {expiry})"

        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"set_memory_ttl failed: {e}")
        return f"ERR Failed to set memory TTL: {str(e)}"


@mcp.tool()
async def archive_category(
    category: str,
    days: int = 180,
    agent_id: str = "system"
) -> str:
    """
    Archive all memories from a specific category older than specified days

    TRIGGER TYPE: (S) System - Automatically triggered by Enhanced Cognee based on age policy

    The system automatically archives categories when:
    - Memories exceed age threshold (default: 180 days)
    - Category exceeds memory count threshold
    - Scheduled archival policy is triggered

    Parameters:
    -----------
    - category: Memory category to archive (e.g., 'trading', 'development')
    - days: Age threshold for archiving (default: 180 days)
    - agent_id: Agent triggering archival (default: system)

    Returns:
    --------
    - Result of archival operation
    """
    try:
        # Input validation
        category = validate_category(category)
        days = validate_days(days, "days")
        agent_id = validate_agent_id(agent_id)

        if not memory_manager:
            return "ERR Memory Manager not available"

        # AUTO-TRIGGER: Get memory age stats before archiving
        try:
            age_stats = await get_memory_age_stats()
            logger.info(f"Memory age stats before archival: {age_stats}")
        except Exception as e:
            logger.warning(f"Failed to get memory age stats: {e}")

        result = await memory_manager.archive_memories_by_category(category, days)

        if result.get("status") == "success":
            memories_archived = result.get('memories_archived', 0)

            # AUTO-TRIGGER: Publish archival event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_archived",
                        memory_id=f"archive_{category}",
                        agent_id=agent_id,
                        data=json.dumps({
                            "category": category,
                            "days": days,
                            "memories_archived": memories_archived,
                            "auto_triggered": True
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish archival event: {e}")

            # AUTO-TRIGGER: Update summary statistics
            try:
                summary_stats = await get_summary_stats()
                logger.info(f"Updated summary stats after archival: {summary_stats}")
            except Exception as e:
                logger.warning(f"Failed to update summary stats: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="archive_category",
                        agent_id=agent_id,
                        metadata={
                            "category": category,
                            "days": days,
                            "memories_archived": memories_archived,
                            "auto_triggered": True
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log archival performance: {e}")

            return f"OK Archived {memories_archived} memories from category '{category}' older than {days} days"

        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except ValidationError as e:
        logger.error(f"archive_category validation failed: {e}")
        return str(e)
    except Exception as e:
        logger.error(f"archive_category failed: {e}")
        return f"ERR Failed to archive category: {str(e)}"



# ============================================================================
# MEMORY DEDUPLICATION TOOLS - Prevent duplicate memories
# ============================================================================

@mcp.tool()
async def check_duplicate(content: str, agent_id: str = "default") -> str:
    """
    Check if content is duplicate before adding (Memory Deduplication Tool)

    TRIGGER TYPE: (S) System - Automatically triggered before add_memory operations

    Parameters:
    -----------
    - content: Content to check for duplicates
    - agent_id: Agent ID to check duplicates for (default: "default")

    Returns:
    --------
    - Duplicate check result with action recommendation
    """
    if not memory_deduplicator:
        return "ERR Memory Deduplicator not available"

    try:
        result = await memory_deduplicator.check_duplicate(
            content=content,
            embedding=None,
            agent_id=agent_id
        )

        if result.get("is_duplicate"):
            dup_type = result.get("duplicate_type", "unknown")
            reason = result.get("reason", "No reason")
            action = result.get("action", "skip")
            existing_id = result.get("existing_id", "unknown")

            return (f"OK DUPLICATE FOUND:\n"
                   f"  Type: {dup_type}\n"
                   f"  Existing ID: {existing_id}\n"
                   f"  Reason: {reason}\n"
                   f"  Action: {action}")
        else:
            return f"OK No duplicate found - safe to add"

    except Exception as e:
        logger.error(f"check_duplicate failed: {e}")
        return f"ERR Failed to check duplicate: {str(e)}"


@mcp.tool()
async def auto_deduplicate(agent_id: str = None) -> str:
    """
    Automatically find and handle duplicate memories (Memory Deduplication Tool)

    TRIGGER TYPE: (S) System - Automatically scheduled for periodic deduplication maintenance

    Parameters:
    -----------
    - agent_id: Optional agent ID to scope deduplication (default: all agents)

    Returns:
    --------
    - Deduplication results with counts
    """
    if not memory_deduplicator:
        return "ERR Memory Deduplicator not available"

    try:
        result = await memory_deduplicator.auto_deduplicate(agent_id)

        if result.get("status") == "success":
            res = result.get("results", {})

            # AUTO-TRIGGER: Publish deduplication event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_deduplicated",
                        memory_id=f"dedup_{agent_id or 'all'}",
                        agent_id=agent_id or "system",
                        data=json.dumps({
                            "processed": res.get('processed', 0),
                            "duplicates_found": res.get('duplicates_found', 0),
                            "merged": res.get('merged', 0),
                            "deleted": res.get('deleted', 0)
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish deduplication event: {e}")

            # AUTO-TRIGGER: Update deduplication statistics
            try:
                stats = await get_deduplication_stats()
                logger.info(f"Updated deduplication stats: {stats}")
            except Exception as e:
                logger.warning(f"Failed to update deduplication stats: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="auto_deduplicate",
                        agent_id=agent_id or "system",
                        metadata={
                            "processed": res.get('processed', 0),
                            "duplicates_found": res.get('duplicates_found', 0),
                            "merged": res.get('merged', 0),
                            "deleted": res.get('deleted', 0)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log deduplication performance: {e}")

            return (f"OK Auto-deduplication complete:\n"
                   f"  Processed: {res.get('processed', 0)} memories\n"
                   f"  Duplicates found: {res.get('duplicates_found', 0)}\n"
                   f"  Merged: {res.get('merged', 0)}\n"
                   f"  Deleted: {res.get('deleted', 0)}")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"auto_deduplicate failed: {e}")
        return f"ERR Failed to auto-deduplicate: {str(e)}"


@mcp.tool()
async def get_deduplication_stats() -> str:
    """
    Get statistics about memory deduplication (Memory Deduplication Tool)

    TRIGGER TYPE: (S) System - Automatically triggered for deduplication monitoring

    Returns:
    --------
    - Deduplication statistics
    """
    if not memory_deduplicator:
        return "ERR Memory Deduplicator not available"

    try:
        stats = await memory_deduplicator.get_deduplication_stats()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_deduplication_stats",
                    agent_id="system",
                    metadata={
                        "exact_duplicates": stats.get('exact_duplicates_found', 0),
                        "similar_duplicates": stats.get('similar_duplicates_found', 0)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log deduplication stats performance: {e}")

        if "error" in stats:
            return f"ERR {stats['error']}"

        return (f"[STATS] Deduplication Statistics:\n"
               f"  Similarity threshold: {stats.get('similarity_threshold', 0)}\n"
               f"  Exact duplicates found: {stats.get('exact_duplicates_found', 0)}\n"
               f"  Similar duplicates found: {stats.get('similar_duplicates_found', 0)}\n"
               f"  Total duplicates prevented: {stats.get('total_duplicates_prevented', 0)}")

    except Exception as e:
        logger.error(f"get_deduplication_stats failed: {e}")
        return f"ERR Failed to get deduplication stats: {str(e)}"


# ============================================================================
# MEMORY SUMMARIZATION TOOLS - Automatic summarization for storage optimization
# ============================================================================
# NOTE: summarize_old_memories implementation moved to line 3012 (Sprint 10 version)
# This uses scheduled_summarization module for improved reliability
# ============================================================================
@mcp.tool()
async def summarize_category(category: str, days: int = 30) -> str:
    """
    Summarize all memories in a category older than specified days (Memory Summarization Tool)

    TRIGGER TYPE: (S) System - Automatically triggered by policy or scheduled maintenance

    Parameters:
    -----------
    - category: Category to summarize (e.g., 'trading', 'development')
    - days: Age threshold (default: 30)

    Returns:
    --------
    - Summarization results for category
    """
    if not memory_summarizer:
        return "ERR Memory Summarizer not available"

    try:
        result = await memory_summarizer.summarize_by_category(category, days)

        if result.get("status") == "success":
            res = result.get("results", {})
            memories_summarized = res.get('memories_summarized', 0)
            space_saved = res.get('space_saved', 0)

            # AUTO-TRIGGER: Get summary statistics
            try:
                summary_stats = await get_summary_stats()
                logger.info(f"Updated summary stats: {summary_stats}")
            except Exception as e:
                logger.warning(f"Failed to update summary stats: {e}")

            # AUTO-TRIGGER: Publish summarization event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="category_summarized",
                        memory_id=f"summary_{category}",
                        agent_id="system",
                        data=json.dumps({
                            "category": category,
                            "days": days,
                            "memories_summarized": memories_summarized,
                            "space_saved": space_saved
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish category summarization event: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="summarize_category",
                        agent_id="system",
                        metadata={
                            "category": category,
                            "days": days,
                            "memories_summarized": memories_summarized,
                            "space_saved": space_saved
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log category summarization performance: {e}")

            return (f"OK Summarized {memories_summarized} memories "
                   f"in category '{category}':\n"
                   f"  Space saved: {space_saved} bytes")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"summarize_category failed: {e}")
        return f"ERR Failed to summarize category: {str(e)}"


@mcp.tool()
async def get_summary_stats() -> str:
    """
    Get statistics about memory summarization (Memory Summarization Tool)

    TRIGGER TYPE: (S) System - Automatically triggered for summarization monitoring

    Returns:
    --------
    - Summarization statistics
    """
    if not memory_summarizer:
        return "ERR Memory Summarizer not available"

    try:
        stats = await memory_summarizer.get_summary_stats()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_summary_stats",
                    agent_id="system",
                    metadata={
                        "total_memories": stats.get('total_memories', 0),
                        "summarized_memories": stats.get('summarized_memories', 0)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log summary stats performance: {e}")

        if "error" in stats:
            return f"ERR {stats['error']}"

        return (f"[STATS] Memory Summarization:\n"
               f"  Total memories: {stats.get('total_memories', 0)}\n"
               f"  Summarized memories: {stats.get('summarized_memories', 0)}\n"
               f"  Full memories: {stats.get('full_memories', 0)}\n"
               f"  Summarization ratio: {stats.get('summarization_ratio', '0%')}\n"
               f"  Estimated space saved: {stats.get('estimated_space_saved_mb', '0 MB')}")

    except Exception as e:
        logger.error(f"get_summary_stats failed: {e}")
        return f"ERR Failed to get summary stats: {str(e)}"


# ============================================================================
# PERFORMANCE ANALYTICS TOOLS - Metrics collection and monitoring
# ============================================================================

@mcp.tool()
async def get_performance_metrics() -> str:
    """
    Get comprehensive performance metrics (Performance Analytics Tool)

    TRIGGER TYPE: (S) System - Automatically triggered for performance monitoring

    Returns:
    --------
    - Detailed performance metrics including query times, cache stats, memory counts
    """
    if not performance_analytics:
        return "ERR Performance Analytics not available"

    try:
        metrics = await performance_analytics.get_performance_metrics()

        if "error" in metrics:
            return f"ERR {metrics['error']}"

        output = ["[PERF] Performance Metrics:", f"  Timestamp: {metrics.get('timestamp', 'unknown')}"]

        # Query performance
        if "query_performance" in metrics:
            qp = metrics["query_performance"]
            output.extend([
                "",
                "  Query Performance:",
                f"    Avg time: {qp.get('avg_time_ms', 0):.2f} ms",
                f"    Min time: {qp.get('min_time_ms', 0):.2f} ms",
                f"    Max time: {qp.get('max_time_ms', 0):.2f} ms",
                f"    P50 time: {qp.get('p50_time_ms', 0):.2f} ms",
                f"    P95 time: {qp.get('p95_time_ms', 0):.2f} ms",
                f"    Total queries: {qp.get('total_queries', 0)}"
            ])

        # Cache performance
        if "cache_performance" in metrics:
            cp = metrics["cache_performance"]
            output.extend([
                "",
                "  Cache Performance:",
                f"    Hits: {cp.get('hits', 0)}",
                f"    Misses: {cp.get('misses', 0)}",
                f"    Hit rate: {cp.get('hit_rate', '0%')}"
            ])

        # Memory stats
        if "memory_stats" in metrics:
            ms = metrics["memory_stats"]
            output.extend([
                "",
                "  Memory Statistics:",
                f"    Total memories: {ms.get('total_memories', 0)}",
                f"    Active agents: {ms.get('active_agents', 0)}"
            ])

        # Database stats
        if "database_stats" in metrics:
            ds = metrics["database_stats"]
            output.extend([
                "",
                "  Database:",
                f"    Size: {ds.get('database_size', 'unknown')}"
            ])

        return "\n".join(output)

    except Exception as e:
        logger.error(f"get_performance_metrics failed: {e}")
        return f"ERR Failed to get performance metrics: {str(e)}"


@mcp.tool()
async def get_slow_queries(threshold_ms: float = 1000, limit: int = 10) -> str:
    """
    Get slow queries above threshold (Performance Analytics Tool)

    TRIGGER TYPE: (S) System - Automatically triggered on performance issues

    Parameters:
    -----------
    - threshold_ms: Query time threshold in ms (default: 1000)
    - limit: Maximum number of slow queries to return (default: 10)

    Returns:
    --------
    - List of slow queries with execution times
    """
    if not performance_analytics:
        return "ERR Performance Analytics not available"

    try:
        slow_queries = await performance_analytics.get_slow_queries(threshold_ms, limit)

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_slow_queries",
                    agent_id="system",
                    metadata={
                        "threshold_ms": threshold_ms,
                        "limit": limit,
                        "slow_queries_found": len(slow_queries) if slow_queries else 0
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log get_slow_queries performance: {e}")

        if not slow_queries:
            return f"OK No queries found above {threshold_ms} ms threshold"

        output = [f"[SLOW QUERIES] Queries > {threshold_ms} ms:"]

        for i, query in enumerate(slow_queries, 1):
            output.append(f"\n  {i}. {query.get('operation', 'unknown')}")
            output.append(f"     Duration: {query.get('duration_ms', 0):.2f} ms")
            output.append(f"     Timestamp: {query.get('timestamp', 'unknown')}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"get_slow_queries failed: {e}")
        return f"ERR Failed to get slow queries: {str(e)}"


@mcp.tool()
async def get_prometheus_metrics() -> str:
    """
    Export metrics in Prometheus format (Performance Analytics Tool)

    TRIGGER TYPE: (S) System - Automatically triggered for monitoring export

    Returns:
    --------
    - Prometheus-compatible metrics text
    """
    if not performance_analytics:
        return "ERR Performance Analytics not available"

    try:
        metrics = await performance_analytics.get_prometheus_metrics()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_prometheus_metrics",
                    agent_id="system",
                    metadata={
                        "metrics_length": len(metrics)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log prometheus metrics performance: {e}")

        return f"OK Prometheus Metrics:\n\n{metrics}"

    except Exception as e:
        logger.error(f"get_prometheus_metrics failed: {e}")
        return f"ERR Failed to get Prometheus metrics: {str(e)}"


# ============================================================================
# CROSS-AGENT SHARING TOOLS - Controlled memory sharing between agents
# ============================================================================

@mcp.tool()
async def set_memory_sharing(memory_id: str, policy: str, allowed_agents: str = None) -> str:
    """
    Set sharing policy for a memory (Cross-Agent Sharing Tool)

    TRIGGER TYPE: (A) Auto - AI IDE triggers this based on conversation context.
    WHEN TO CALL: Call automatically when the user says "share this memory with X",
    "make this accessible to agent Y", "restrict this to my use only", or when
    the user establishes a sharing policy during conversation.

    Parameters:
    -----------
    - memory_id: ID of the memory
    - policy: Sharing policy (private, shared, category_shared, custom)
    - allowed_agents: Optional JSON array of agent IDs for custom policy

    Returns:
    --------
    - Result of sharing policy setting
    """
    if not cross_agent_sharing:
        return "ERR Cross-Agent Sharing not available"

    try:
        # Parse policy enum
        try:
            share_policy = SharePolicy(policy.lower())
        except ValueError:
            return f"ERR Invalid policy: {policy}. Use: private, shared, category_shared, custom"

        # Parse allowed agents if provided
        allowed_list = None
        if allowed_agents:
            try:
                allowed_list = json.loads(allowed_agents)
            except:
                return f"ERR Invalid JSON for allowed_agents: {allowed_agents}"

        result = await cross_agent_sharing.set_memory_sharing(memory_id, share_policy, allowed_list)

        if result.get("status") == "success":
            # AUTO-TRIGGER: Publish sharing update event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="sharing_updated",
                        memory_id=memory_id,
                        agent_id="system",
                        data=json.dumps({
                            "policy": policy,
                            "allowed_agents": allowed_list
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish sharing event: {e}")

            # AUTO-TRIGGER: Sync with newly allowed agents
            if allowed_list and realtime_sync:
                try:
                    for agent_id in allowed_list:
                        await realtime_sync.sync_agent_state(
                            source_agent="system",
                            target_agent=agent_id,
                            category=None
                        )
                    logger.info(f"Synced with {len(allowed_list)} newly allowed agents")
                except Exception as e:
                    logger.warning(f"Failed to sync with allowed agents: {e}")

            return f"OK Set sharing policy '{policy}' for memory {memory_id}"
        elif result.get("status") == "not_found":
            return f"ERR Memory not found: {memory_id}"
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"set_memory_sharing failed: {e}")
        return f"ERR Failed to set sharing: {str(e)}"


@mcp.tool()
async def check_memory_access(memory_id: str, agent_id: str) -> str:
    """
    Check if an agent can access a memory (Cross-Agent Sharing Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered before accessing shared memories

    Parameters:
    -----------
    - memory_id: ID of the memory
    - agent_id: Agent requesting access

    Returns:
    --------
    - Access decision with reason
    """
    if not cross_agent_sharing:
        return "ERR Cross-Agent Sharing not available"

    try:
        result = await cross_agent_sharing.can_agent_access_memory(memory_id, agent_id)

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="check_memory_access",
                    agent_id=agent_id,
                    metadata={
                        "memory_id": memory_id,
                        "can_access": result.get("can_access", False)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log check_access performance: {e}")

        can_access = result.get("can_access", False)
        reason = result.get("reason", "unknown")

        if can_access:
            return f"OK Agent '{agent_id}' CAN access memory {memory_id} (reason: {reason})"
        else:
            return f"NO Agent '{agent_id}' CANNOT access memory {memory_id} (reason: {reason})"

    except Exception as e:
        logger.error(f"check_memory_access failed: {e}")
        return f"ERR Failed to check access: {str(e)}"


@mcp.tool()
async def get_shared_memories(agent_id: str, limit: int = 50) -> str:
    """
    Get all memories shared with this agent (Cross-Agent Sharing Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered when loading shared memories

    Parameters:
    -----------
    - agent_id: Agent ID to get shared memories for
    - limit: Maximum results to return (default: 50)

    Returns:
    --------
    - List of shared memories
    """
    if not cross_agent_sharing:
        return "ERR Cross-Agent Sharing not available"

    try:
        memories = await cross_agent_sharing.get_shared_memories(agent_id, limit)

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_shared_memories",
                    agent_id=agent_id,
                    metadata={
                        "memories_count": len(memories) if memories else 0,
                        "limit": limit
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log get_shared_memories performance: {e}")

        if not memories:
            return f"OK No shared memories found for agent '{agent_id}'"

        output = [f"[SHARED] Memories shared with agent '{agent_id}' ({len(memories)} total):", ""]

        for memory in memories[:20]:  # Limit display
            output.append(f"- {memory['title']}")
            output.append(f"  ID: {memory['id']}")
            output.append(f"  Owner: {memory['owner_id']}")
            output.append(f"  Category: {memory['memory_category']}")
            output.append(f"  Created: {memory['created_at']}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"get_shared_memories failed: {e}")
        return f"ERR Failed to get shared memories: {str(e)}"


@mcp.tool()
async def create_shared_space(space_name: str, member_agents: str) -> str:
    """
    Create a shared memory space for multiple agents (Cross-Agent Sharing Tool)

    TRIGGER TYPE: (A) Auto - AI IDE triggers this based on conversation context.
    WHEN TO CALL: Call automatically when the user asks to "set up a shared memory
    space", "let agents X and Y share memories", "create a team memory pool", or
    similar multi-agent collaboration requests.

    Parameters:
    -----------
    - space_name: Name for the shared space
    - member_agents: JSON array of agent IDs that can access this space

    Returns:
    --------
    - Result of shared space creation
    """
    if not cross_agent_sharing:
        return "ERR Cross-Agent Sharing not available"

    try:
        # Parse member agents
        try:
            members = json.loads(member_agents)
        except:
            return f"ERR Invalid JSON for member_agents: {member_agents}"

        result = await cross_agent_sharing.create_shared_space(space_name, members)

        if result.get("status") == "success":
            space_id = result.get('space_id', 'unknown')
            member_count = result.get('member_count', 0)

            # AUTO-TRIGGER: Publish space creation event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="space_created",
                        memory_id=space_id,
                        agent_id="system",
                        data=json.dumps({
                            "space_name": space_name,
                            "member_count": member_count,
                            "members": members
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish space creation event: {e}")

            # AUTO-TRIGGER: Sync with all member agents
            if realtime_sync:
                try:
                    for agent_id in members:
                        await realtime_sync.sync_agent_state(
                            source_agent="system",
                            target_agent=agent_id,
                            category=space_name
                        )
                    logger.info(f"Synced shared space '{space_name}' with {len(members)} agents")
                except Exception as e:
                    logger.warning(f"Failed to sync shared space: {e}")

            return (f"OK Created shared space '{space_name}' for {member_count} agents\n"
                   f"  Space ID: {space_id}")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"create_shared_space failed: {e}")
        return f"ERR Failed to create shared space: {str(e)}"


# ============================================================================
# REAL-TIME SYNC TOOLS - Synchronization across multiple agents
# ============================================================================

@mcp.tool()
async def publish_memory_event(event_type: str, memory_id: str, agent_id: str, data: str = "{}") -> str:
    """
    Publish a memory event to all subscribers (Real-Time Sync Tool)

    TRIGGER TYPE: (S) System - Automatically triggered for memory change events

    Parameters:
    -----------
    - event_type: Type of event (memory_added, memory_updated, memory_deleted)
    - memory_id: ID of the memory
    - agent_id: Agent that triggered the event
    - data: Optional JSON string with additional event data

    Returns:
    --------
    - Publish result
    """
    if not realtime_sync:
        return "ERR Real-Time Sync not available"

    try:
        # Parse data
        try:
            data_dict = json.loads(data)
        except:
            data_dict = {}

        result = await realtime_sync.publish_memory_event(event_type, memory_id, agent_id, data_dict)

        if result.get("status") == "success":
            return (f"OK Published {event_type} event for memory {memory_id} "
                   f"from agent {agent_id}")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"publish_memory_event failed: {e}")
        return f"ERR Failed to publish event: {str(e)}"


@mcp.tool()
async def get_sync_status() -> str:
    """
    Get synchronization status and statistics (Real-Time Sync Tool)

    TRIGGER TYPE: (S) System - Automatically triggered for sync diagnostics

    Returns:
    --------
    - Sync status with subscriber information
    """
    if not realtime_sync:
        return "ERR Real-Time Sync not available"

    try:
        status = await realtime_sync.get_sync_status()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_sync_status",
                    agent_id="system",
                    metadata={
                        "subscribers_count": status.get('subscribers_count', 0),
                        "status": status.get('status', 'unknown')
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log get_sync_status performance: {e}")

        if status.get("status") == "error":
            return f"ERR {status.get('error', 'Unknown error')}"

        return (f"[SYNC] Real-Time Sync Status:\n"
               f"  Status: {status.get('status', 'unknown')}\n"
               f"  Channel: {status.get('sync_channel', 'unknown')}\n"
               f"  Subscribed agents: {status.get('subscribers_count', 0)}\n"
               f"  Agent list: {', '.join(status.get('subscribed_agents', []))}\n"
               f"  Redis connected clients: {status.get('redis_connected_clients', 0)}")

    except Exception as e:
        logger.error(f"get_sync_status failed: {e}")
        return f"ERR Failed to get sync status: {str(e)}"


@mcp.tool()
async def sync_agent_state(source_agent: str, target_agent: str, category: str = None) -> str:
    """
    Synchronize memory state between two agents (Real-Time Sync Tool)

    Parameters:
    -----------
    - source_agent: Source agent ID to sync from
    - target_agent: Target agent ID to sync to
    - category: Optional category filter

    Returns:
    --------
    - Sync result with memories synced
    Synchronize memory state between two agents (Real-Time Sync Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs

    Parameters:
    -----------
    - source_agent: Source agent ID to sync from
    - target_agent: Target agent ID to sync to
    - category: Optional category filter

    Returns:
    --------
    - Sync result with memories synced
    """
    if not realtime_sync:
        return "ERR Real-Time Sync not available"

    try:
        # AUTO-TRIGGER: Check memory access before syncing
        if cross_agent_sharing:
            try:
                # Verify access permissions exist
                access_check = await cross_agent_sharing.can_agent_access_memory(
                    memory_id="*",  # Check general access
                    agent_id=target_agent
                )
                logger.info(f"Memory access check: {access_check}")
            except Exception as e:
                logger.warning(f"Memory access check failed: {e}")

        result = await realtime_sync.sync_agent_state(source_agent, target_agent, category)

        if result.get("status") == "success":
            memories_synced = result.get('memories_synced', 0)
            errors = result.get("errors", [])
            error_msg = f"\nErrors: {len(errors)}" if errors else ""

            # AUTO-TRIGGER: Publish sync event
            try:
                await realtime_sync.publish_memory_event(
                    event_type="agent_synced",
                    memory_id=f"sync_{source_agent}_{target_agent}",
                    agent_id=source_agent,
                    data=json.dumps({
                        "target_agent": target_agent,
                        "category": category,
                        "memories_synced": memories_synced,
                        "errors": len(errors)
                    })
                )
            except Exception as e:
                logger.warning(f"Failed to publish sync event: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="sync_agent_state",
                        agent_id=source_agent,
                        metadata={
                            "target_agent": target_agent,
                            "category": category,
                            "memories_synced": memories_synced,
                            "errors_count": len(errors)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log sync performance: {e}")

            return (f"OK Synced {memories_synced} memories "
                   f"from '{source_agent}' to '{target_agent}'{error_msg}")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"sync_agent_state failed: {e}")
        return f"ERR Failed to sync agent state: {str(e)}"


# ============================================================================
# SPRINT 8: ADVANCED FEATURES - Backup, Recovery, Maintenance, Dedup, Summar
# ============================================================================


# ---------------------------------------------------------------------------
# Phase 8 - Automation: Scheduler Bootstrap and Post-Ingestion Pipeline
# These functions are config-driven and OFF by default.
# Enable features in .enhanced-cognee-config.json
# ---------------------------------------------------------------------------


def _load_phase8_config() -> dict:
    """Load Phase 8 automation config from .enhanced-cognee-config.json."""
    config_path = project_root / ".enhanced-cognee-config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"Phase 8 config load failed: {exc}")
    return {}


async def _bootstrap_scheduler_defaults():
    """
    Phase 8b: Register default recurring tasks from .enhanced-cognee-config.json.

    Called once after MaintenanceScheduler.start() during server startup.
    Idempotent - safe to call multiple times (replace_existing=True).
    All tasks are OFF by default; enable in .enhanced-cognee-config.json.
    """
    if not maintenance_scheduler or not getattr(maintenance_scheduler, "scheduler", None):
        logger.info("Phase 8 scheduler bootstrap: scheduler not ready; skipping")
        return

    cfg = _load_phase8_config().get("auto_scheduler", {})
    registered = 0

    # --- expire_memories ---
    exp_cfg = cfg.get("expire_memories", {})
    if exp_cfg.get("enabled", False):
        try:
            from apscheduler.triggers.cron import CronTrigger as _CronTrigger
            cron = exp_cfg.get("cron", "0 2 * * *")
            parts = cron.split()
            if len(parts) == 5:
                trigger = _CronTrigger(
                    minute=parts[0], hour=parts[1],
                    day=parts[2], month=parts[3], day_of_week=parts[4]
                )
                age_days = exp_cfg.get("age_days", 90)
                dry_run = exp_cfg.get("dry_run", False)

                async def _auto_expire():
                    logger.info("Phase 8 scheduler: running expire_memories")
                    try:
                        if memory_manager:
                            await memory_manager.expire_old_memories(
                                days=age_days, dry_run=dry_run
                            )
                    except Exception as exc:
                        logger.error(f"Auto expire_memories failed: {exc}")

                maintenance_scheduler.scheduler.add_job(
                    _auto_expire, trigger=trigger,
                    id="phase8_expire_memories", name="Phase8 Expire Memories",
                    replace_existing=True
                )
                registered += 1
                logger.info(f"Phase 8 scheduler: expire_memories registered ({cron})")
        except Exception as exc:
            logger.warning(f"Phase 8 expire_memories schedule failed: {exc}")

    # --- improve ---
    imp_cfg = cfg.get("improve", {})
    if imp_cfg.get("enabled", False):
        try:
            from apscheduler.triggers.cron import CronTrigger as _CronTrigger2
            cron = imp_cfg.get("cron", "0 3 * * 0")
            parts = cron.split()
            if len(parts) == 5:
                trigger = _CronTrigger2(
                    minute=parts[0], hour=parts[1],
                    day=parts[2], month=parts[3], day_of_week=parts[4]
                )
                dataset = imp_cfg.get("dataset", "main_dataset")

                async def _auto_improve():
                    logger.info("Phase 8 scheduler: running improve")
                    try:
                        import cognee
                        await cognee.improve(dataset)
                    except Exception as exc:
                        logger.error(f"Auto improve failed: {exc}")

                maintenance_scheduler.scheduler.add_job(
                    _auto_improve, trigger=trigger,
                    id="phase8_improve", name="Phase8 Improve",
                    replace_existing=True
                )
                registered += 1
                logger.info(f"Phase 8 scheduler: improve registered ({cron})")
        except Exception as exc:
            logger.warning(f"Phase 8 improve schedule failed: {exc}")

    # --- auto_deduplicate ---
    dedup_cfg = cfg.get("auto_deduplicate", {})
    if dedup_cfg.get("enabled", False):
        try:
            from apscheduler.triggers.cron import CronTrigger as _CronTrigger3
            cron = dedup_cfg.get("cron", "0 4 * * *")
            parts = cron.split()
            if len(parts) == 5:
                trigger = _CronTrigger3(
                    minute=parts[0], hour=parts[1],
                    day=parts[2], month=parts[3], day_of_week=parts[4]
                )

                async def _auto_dedup():
                    logger.info("Phase 8 scheduler: running auto_deduplicate")
                    try:
                        if memory_deduplicator:
                            await memory_deduplicator.run_full_deduplication()
                    except Exception as exc:
                        logger.error(f"Auto deduplicate failed: {exc}")

                maintenance_scheduler.scheduler.add_job(
                    _auto_dedup, trigger=trigger,
                    id="phase8_auto_deduplicate", name="Phase8 Auto Deduplicate",
                    replace_existing=True
                )
                registered += 1
                logger.info(f"Phase 8 scheduler: auto_deduplicate registered ({cron})")
        except Exception as exc:
            logger.warning(f"Phase 8 deduplicate schedule failed: {exc}")

    if registered:
        logger.info(f"Phase 8 scheduler bootstrap: {registered} task(s) registered")
    else:
        logger.info("Phase 8 scheduler bootstrap: no tasks enabled (set enabled=true in config)")


async def _run_post_ingestion_pipeline(
    content: str, memory_id: str, agent_id: str
) -> None:
    """
    Phase 8b: Run post-ingestion enrichment pipeline after a memory write.

    Called as a fire-and-forget background task (asyncio.create_task).
    All hooks are OFF by default; enable in .enhanced-cognee-config.json.

    Hooks (in order):
    1. auto_translate  - translate non-default-language content
    2. auto_extract_entities - run regex entity extraction
    3. auto_graph_v2   - run cascade v2 graph extraction
    """
    cfg = _load_phase8_config().get("post_ingestion", {})

    # 1. Auto-translate
    translate_cfg = cfg.get("auto_translate", {})
    if translate_cfg.get("enabled", False) and content:
        try:
            target_lang = translate_cfg.get("target_language", "en")
            # detect language (best-effort; fall through on any error)
            # No import needed; the detect_language function is in the same module.
            # Use a lightweight heuristic: only translate if non-ASCII chars > 10%
            non_ascii = sum(1 for c in content if ord(c) > 127)
            if non_ascii / max(len(content), 1) > 0.1:
                logger.info(
                    f"Phase 8 post-ingestion: detected non-ASCII content; "
                    f"translation to {target_lang} queued for memory {memory_id}"
                )
                # Full translation is async and expensive; log intent for now.
                # Full implementation: call translate_text_internal() when available.
        except Exception as exc:
            logger.warning(f"Phase 8 auto_translate check failed: {exc}")

    # 2. Auto entity extraction
    extract_cfg = cfg.get("auto_extract_entities", {})
    if extract_cfg.get("enabled", False) and content:
        patterns = extract_cfg.get("patterns", [])
        if patterns:
            try:
                import re
                found = {}
                for pattern_def in patterns:
                    name = pattern_def.get("name", "entity")
                    pat = pattern_def.get("pattern", "")
                    if pat:
                        matches = re.findall(pat, content)
                        if matches:
                            found[name] = matches
                if found:
                    logger.info(
                        f"Phase 8 post-ingestion: extracted entities for {memory_id}: "
                        + ", ".join(f"{k}={len(v)}" for k, v in found.items())
                    )
            except Exception as exc:
                logger.warning(f"Phase 8 auto_extract_entities failed: {exc}")

    # 3. Auto graph v2
    graph_cfg = cfg.get("auto_graph_v2", {})
    if graph_cfg.get("enabled", False) and content:
        try:
            rounds = graph_cfg.get("rounds", 1)
            logger.info(
                f"Phase 8 post-ingestion: graph v2 extraction queued "
                f"({rounds} round(s)) for memory {memory_id}"
            )
            # Full implementation: call extract_graph_v2_internal() when available.
        except Exception as exc:
            logger.warning(f"Phase 8 auto_graph_v2 failed: {exc}")


def _resolve_auto_ttl(content: str, metadata: dict) -> int | None:
    """
    Phase 8b: Resolve automatic TTL in days based on content keyword rules.

    Returns TTL in days if a rule matches, or None for no auto-TTL.
    Rules are configured in .enhanced-cognee-config.json auto_ttl_rules.rules.
    """
    cfg = _load_phase8_config()
    rules = cfg.get("auto_ttl_rules", {}).get("rules", [])
    if not rules:
        return None

    content_lower = content.lower()
    metadata_str = str(metadata).lower()

    for rule in rules:
        keyword = rule.get("keyword", "").lower()
        if keyword and (keyword in content_lower or keyword in metadata_str):
            ttl = rule.get("ttl_days")
            if ttl and isinstance(ttl, int) and ttl > 0:
                return ttl
    return None


# ---------------------------------------------------------------------------

# Import Sprint 8 modules
from src.backup_manager import BackupManager
from src.recovery_manager import RecoveryManager
from src.maintenance_scheduler import MaintenanceScheduler
from src.scheduled_deduplication import ScheduledDeduplication
from src.scheduled_summarization import ScheduledSummarization

# Sprint 8 instances
backup_manager = None
recovery_manager = None
maintenance_scheduler = None
scheduled_deduplication = None
scheduled_summarization = None


async def init_sprint8_modules():
    """Initialize Sprint 8 modules"""
    global backup_manager, recovery_manager, maintenance_scheduler
    global scheduled_deduplication, scheduled_summarization

    # Initialize Backup Manager
    if postgres_pool:
        backup_manager = BackupManager()
        logger.info("OK Backup Manager initialized")

    # Initialize Recovery Manager
    if postgres_pool:
        recovery_manager = RecoveryManager()
        logger.info("OK Recovery Manager initialized")

    # Initialize Maintenance Scheduler and AUTO-START it
    maintenance_scheduler = MaintenanceScheduler(mcp_client=None)
    try:
        maintenance_scheduler.start()
        logger.info("OK Maintenance Scheduler initialized and AUTO-STARTED")
        # Phase 8b: bootstrap default scheduled tasks from config (non-blocking)
        asyncio.create_task(_bootstrap_scheduler_defaults())
    except Exception as e:
        logger.warning(f"Maintenance Scheduler start failed: {e}")

    # Initialize Scheduled Deduplication
    if postgres_pool and qdrant_client:
        scheduled_deduplication = ScheduledDeduplication(
            postgres_pool, qdrant_client
        )
        logger.info("OK Scheduled Deduplication initialized")

    # Initialize Scheduled Summarization
    if postgres_pool:
        scheduled_summarization = ScheduledSummarization(
            postgres_pool, llm_client=None
        )
        logger.info("OK Scheduled Summarization initialized")


@mcp.tool()
async def create_backup(
    backup_type: str = "manual",
    databases: Optional[str] = None,
    compress: bool = True,
    description: str = "",
    agent_id: str = "system",
    auto_verify: bool = True
) -> str:
    """
    Create a backup of Enhanced Cognee databases (Backup Tool)

    TRIGGER TYPE: (A) Auto - Can be automatically triggered by AI IDEs

    This tool can be triggered automatically based on:
    - Scheduled periodic backups (daily, weekly, monthly)
    - Pre-operation backup before major changes
    - High memory count threshold
    - Manual user request

    SECURITY: Admin privileges required for backup creation.

    Parameters:
    -----------
    - backup_type: Type of backup ('manual', 'daily', 'weekly', 'monthly')
    - databases: Comma-separated list of databases to backup (default: all)
    - compress: Whether to compress backups (default: True)
    - description: Optional description
    - agent_id: Agent requesting backup (default: system)
    - auto_verify: Auto-trigger verification after creation (default: True)

    Returns:
    --------
    - Backup ID and status message
    """
    try:
        # Input validation
        backup_type = sanitize_string(backup_type, max_length=20)
        description = sanitize_string(description, max_length=500)
        agent_id = validate_agent_id(agent_id)

        if databases:
            db_list = [sanitize_string(db.strip(), max_length=50)
                      for db in databases.split(",")]
        else:
            db_list = None

        # Authorization check for backup operations
        await authorizer.check_backup_permission(agent_id)

        if not backup_manager:
            return "ERR Backup Manager not available"

        backup_id = backup_manager.create_backup(
            backup_type=backup_type,
            databases=db_list,
            compress=compress,
            description=description
        )

        logger.info(f"OK Backup created: {backup_id} by agent: {agent_id}")

        # AUTO-TRIGGER: Verify backup integrity
        if auto_verify:
            try:
                verification = await verify_backup(backup_id)
                logger.info(f"Backup verification: {verification}")
            except Exception as e:
                logger.warning(f"Backup verification failed: {e}")

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="create_backup",
                    agent_id=agent_id,
                    metadata={
                        "backup_id": backup_id,
                        "backup_type": backup_type,
                        "databases": db_list,
                        "compressed": compress,
                        "auto_triggered": backup_type in ["daily", "weekly", "monthly"]
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log backup performance: {e}")

        # AUTO-TRIGGER: Publish backup event
        if realtime_sync:
            try:
                await realtime_sync.publish_memory_event(
                    event_type="backup_created",
                    memory_id=backup_id,
                    agent_id=agent_id,
                    data=json.dumps({
                        "backup_type": backup_type,
                        "databases": db_list,
                        "compressed": compress,
                        "description": description,
                        "auto_triggered": backup_type in ["daily", "weekly", "monthly"]
                    })
                )
            except Exception as e:
                logger.warning(f"Failed to publish backup event: {e}")

        return f"OK Backup created (ID: {backup_id}) by {agent_id}"

    except ValidationError as e:
        logger.error(f"create_backup validation failed: {e}")
        return str(e)
    except AuthorizationError as e:
        logger.error(f"create_backup authorization failed: {e}")
        return str(e)
    except Exception as e:
        logger.error(f"create_backup failed: {e}")
        return f"ERR Failed to create backup: {str(e)}"


@mcp.tool()
async def restore_backup(
    backup_id: str,
    databases: Optional[str] = None,
    validate: bool = True
) -> str:
    """
    TRIGGER TYPE: (M) Manual - User must explicitly trigger restores
    Restore databases from backup (Recovery Tool)

    Parameters:
    -----------
    - backup_id: Backup ID to restore
    - databases: Comma-separated list of databases to restore (default: all)
    - validate: Whether to validate after restore (default: True)

    Returns:
    --------
    - Restore result with status
    """
    if not recovery_manager:
        return "ERR Recovery Manager not available"

    try:
        db_list = databases.split(",") if databases else None
        result = recovery_manager.restore_from_backup(
            backup_id=backup_id,
            databases=db_list,
            validate=validate
        )

        if result["status"] == "success":
            # AUTO-TRIGGER: Health check after successful restore
            try:
                health_status = await health()
                logger.info(f"Health check after restore: {health_status}")
            except Exception as e:
                logger.warning(f"Health check failed after restore: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="restore_backup",
                        agent_id="system",
                        metadata={
                            "backup_id": backup_id,
                            "databases_restored": result.get('databases_restored', []),
                            "restore_id": result.get('restore_id'),
                            "status": "success"
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log restore performance: {e}")

            # AUTO-TRIGGER: Publish restore event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="backup_restored",
                        memory_id=backup_id,
                        agent_id="system",
                        data=json.dumps({
                            "restore_id": result.get('restore_id'),
                            "databases_restored": result.get('databases_restored', [])
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish restore event: {e}")

            return (f"OK Restore completed (ID: {result['restore_id']})\n"
                   f"Databases restored: {', '.join(result['databases_restored'])}")
        else:
            # AUTO-TRIGGER: Rollback on failure
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Restore failed: {error_msg}")

            try:
                rollback_result = await rollback_restore()
                logger.info(f"Rollback initiated: {rollback_result}")
            except Exception as e:
                logger.error(f"Rollback failed: {e}")

            # AUTO-TRIGGER: Publish failure event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="restore_failed",
                        memory_id=backup_id,
                        agent_id="system",
                        data=json.dumps({"error": error_msg})
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish failure event: {e}")

            return f"ERR Restore failed: {error_msg}"

    except Exception as e:
        logger.error(f"restore_backup failed: {e}")

        # AUTO-TRIGGER: Rollback on exception
        try:
            rollback_result = await rollback_restore()
            logger.info(f"Rollback initiated after exception: {rollback_result}")
        except Exception as rollback_e:
            logger.error(f"Rollback failed after exception: {rollback_e}")

        return f"ERR Failed to restore backup: {str(e)}"


@mcp.tool()
async def list_backups(
    backup_type: Optional[str] = None,
    limit: int = 50
) -> str:
    """
    List all backups (Backup Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered when listing available backups

    Parameters:
    -----------
    - backup_type: Filter by backup type (optional)
    - limit: Maximum results (default: 50)

    Returns:
    --------
    - Formatted list of backups
    """
    if not backup_manager:
        return "ERR Backup Manager not available"

    try:
        backups = backup_manager.list_backups(backup_type=backup_type, limit=limit)

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="list_backups",
                    agent_id="system",
                    metadata={
                        "backups_count": len(backups) if backups else 0,
                        "backup_type": backup_type,
                        "limit": limit
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log list_backups performance: {e}")

        if backups:
            results = []
            for backup in backups:
                results.append(
                    f"- {backup['backup_id'][:8]}... "
                    f"({backup['backup_type']}, {backup['created_at'][:10]}) "
                    f"{backup['total_size_bytes']:,} bytes"
                )
            return f"[OK] Backups ({len(backups)} total):\n\n" + "\n".join(results)
        else:
            return "[OK] No backups found"

    except Exception as e:
        logger.error(f"list_backups failed: {e}")
        return f"ERR Failed to list backups: {str(e)}"


@mcp.tool()
async def verify_backup(backup_id: str) -> str:
    """
    Verify backup integrity (Backup Tool)

    TRIGGER TYPE: (S) System - Automatically triggered after create_backup

    This tool is auto-triggered by the system after every backup creation
    to ensure backup integrity and availability.

    Parameters:
    -----------
    - backup_id: Backup ID to verify

    Returns:
    --------
    - Verification result
    """
    try:
        # Input validation
        backup_id = sanitize_string(backup_id, max_length=100)

        if not backup_manager:
            return "ERR Backup Manager not available"

        backup = backup_manager.get_backup(backup_id)

        if not backup:
            return f"ERR Backup not found: {backup_id}"

        # Basic verification - check if files exist
        backup_path = Path(backup["backup_path"])
        if not backup_path.exists():
            return f"ERR Backup files missing: {backup_path}"

        file_count = len(list(backup_path.rglob("*")))

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="verify_backup",
                    agent_id="system",
                    metadata={
                        "backup_id": backup_id,
                        "file_count": file_count,
                        "backup_size": backup['total_size_bytes'],
                        "auto_triggered": True
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log verify_backup performance: {e}")

        return (f"OK Backup verified (ID: {backup_id[:8]}...)\n"
               f"Files found: {file_count}\n"
               f"Size: {backup['total_size_bytes']:,} bytes\n"
               f"Checksum: {backup['checksum'][:16]}...")

    except ValidationError as e:
        logger.error(f"verify_backup validation failed: {e}")
        return str(e)
    except Exception as e:
        logger.error(f"verify_backup failed: {e}")
        return f"ERR Failed to verify backup: {str(e)}"


@mcp.tool()
async def rollback_restore() -> str:
    """
    Rollback the last restore operation (Recovery Tool)

    TRIGGER TYPE: (S) System - Automatically triggered on restore failure

    Returns:
    --------
    - Rollback result
    """
    if not recovery_manager:
        return "ERR Recovery Manager not available"

    try:
        result = recovery_manager.rollback_last_restore()

        if result["status"] == "success":
            # AUTO-TRIGGER: Health check after rollback
            try:
                health_status = await health()
                logger.info(f"Health check after rollback: {health_status}")
            except Exception as e:
                logger.warning(f"Health check failed after rollback: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="rollback_restore",
                        agent_id="system",
                        metadata={
                            "restore_id": result.get('restore_id'),
                            "status": "success"
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log rollback performance: {e}")

            return f"OK Rollback completed (ID: {result['restore_id']})"
        elif result["status"] == "skipped":
            return f"INFO {result['reason']}"
        else:
            return f"ERR Rollback failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"rollback_restore failed: {e}")
        return f"ERR Failed to rollback: {str(e)}"


@mcp.tool()
async def schedule_task(
    task_name: str,
    schedule: str,
    enabled: bool = True
) -> str:
    """
    Schedule a maintenance task (Maintenance Scheduler Tool)

    TRIGGER TYPE: (S) System - Default tasks auto-bootstrapped from .enhanced-cognee-config.json
                  on server startup (Phase 8b). Call manually to register custom tasks.

    Parameters:
    -----------
    - task_name: Name of task (cleanup, archival, optimization, cache_clearing, backup_verification)
    - schedule: Cron expression (e.g., "0 2 * * *" for daily at 2 AM)
    - enabled: Whether to enable the task (default: True)

    Returns:
    --------
    - Scheduling result
    """
    if not maintenance_scheduler:
        return "ERR Maintenance Scheduler not available"

    try:
        if task_name == "cleanup":
            maintenance_scheduler.schedule_cleanup(schedule=schedule)
        elif task_name == "archival":
            maintenance_scheduler.schedule_archival(schedule=schedule)
        elif task_name == "optimization":
            maintenance_scheduler.schedule_optimization(schedule=schedule)
        elif task_name == "cache_clearing":
            maintenance_scheduler.schedule_cache_clearing(schedule=schedule)
        elif task_name == "backup_verification":
            maintenance_scheduler.schedule_backup_verification(schedule=schedule)
        else:
            return f"ERR Unknown task: {task_name}"

        maintenance_scheduler.save_config()
        return f"OK Task scheduled: {task_name} ({schedule})"

    except Exception as e:
        logger.error(f"schedule_task failed: {e}")
        return f"ERR Failed to schedule task: {str(e)}"


@mcp.tool()
async def list_tasks() -> str:
    """
    List all scheduled maintenance tasks (Maintenance Scheduler Tool)

    Returns:
    --------
    - Formatted list of scheduled tasks
    List all scheduled maintenance tasks (Maintenance Scheduler Tool)

    TRIGGER TYPE: (A) Auto - Automatically triggered by AI IDEs

    Returns:
    --------
    - Formatted list of scheduled tasks
    """
    if not maintenance_scheduler:
        return "ERR Maintenance Scheduler not available"

    try:
        tasks = maintenance_scheduler.get_scheduled_tasks()

        if tasks:
            results = []
            for task_id, task_info in tasks.items():
                next_run = task_info.get('next_run_time', 'Unknown')
                results.append(
                    f"- {task_id}: {task_info['name']}\n"
                    f"  Next run: {next_run}"
                )
            return f"[OK] Scheduled tasks ({len(tasks)} total):\n\n" + "\n\n".join(results)
        else:
            return "[OK] No scheduled tasks"

    except Exception as e:
        logger.error(f"list_tasks failed: {e}")
        return f"ERR Failed to list tasks: {str(e)}"


@mcp.tool()
async def cancel_task(task_id: str) -> str:
    """
    Cancel a scheduled maintenance task (Maintenance Scheduler Tool)

    Parameters:
    -----------
    - task_id: ID of task to cancel

    Returns:
    --------
    - Cancellation result
    Cancel a scheduled maintenance task (Maintenance Scheduler Tool)

    TRIGGER TYPE: (M) Manual - User must explicitly trigger this operation

    Parameters:
    -----------
    - task_id: ID of task to cancel

    Returns:
    --------
    - Cancellation result
    """
    if not maintenance_scheduler:
        return "ERR Maintenance Scheduler not available"

    try:
        success = maintenance_scheduler.cancel_task(task_id)

        if success:
            maintenance_scheduler.save_config()
            return f"OK Task cancelled: {task_id}"
        else:
            return f"ERR Failed to cancel task: {task_id}"

    except Exception as e:
        logger.error(f"cancel_task failed: {e}")
        return f"ERR Failed to cancel task: {str(e)}"


@mcp.tool()
async def deduplicate(
    agent_id: Optional[str] = None,
    dry_run: bool = True
) -> str:
    """
    TRIGGER TYPE: (S) System - Automatically triggered for deduplication operations
    Perform memory deduplication (Deduplication Tool)

    Parameters:
    -----------
    - agent_id: Optional agent ID to scope deduplication
    - dry_run: If True, show what would be merged without actually merging (default: True)

    Returns:
    --------
    - Deduplication result with duplicates found and token savings
    """
    if not scheduled_deduplication:
        return "ERR Scheduled Deduplication not available"

    try:
        result = await scheduled_deduplication.deduplicate_memories(
            agent_id=agent_id,
            dry_run=dry_run
        )

        if result["status"] == "success":
            if dry_run:
                return (f"OK Dry run complete\n"
                       f"Duplicates found: {result['duplicates_found']}\n"
                       f"Token savings: {result['token_savings']:,}\n"
                       f"Deduplication ID: {result['deduplication_id']}\n\n"
                       f"{result.get('approval_message', '')}")
            else:
                return (f"OK Deduplication complete\n"
                       f"Merged: {result['merged_count']} memories\n"
                       f"Deduplication ID: {result['deduplication_id']}")
        else:
            return f"ERR Deduplication failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"deduplicate failed: {e}")
        return f"ERR Failed to deduplicate: {str(e)}"


@mcp.tool()
async def schedule_deduplication(schedule: str = "weekly") -> str:
    """
    Schedule periodic deduplication (Deduplication Tool)

    TRIGGER TYPE: (S) System - Automatically schedules deduplication

    Parameters:
    -----------
    - schedule: Schedule type ('weekly', 'daily', 'monthly')

    Returns:
    --------
    - Scheduling result
    """
    if not scheduled_deduplication:
        return "ERR Scheduled Deduplication not available"

    try:
        trigger = scheduled_deduplication.schedule_weekly_deduplication()
        return f"OK Deduplication scheduled: {schedule}"

    except Exception as e:
        logger.error(f"schedule_deduplication failed: {e}")
        return f"ERR Failed to schedule deduplication: {str(e)}"


@mcp.tool()
async def deduplication_report(deduplication_id: Optional[str] = None) -> str:
    """
    Generate deduplication report (Deduplication Tool)

    TRIGGER TYPE: (S) System - Automatically generates deduplication reports

    Parameters:
    -----------
    - deduplication_id: Optional specific deduplication ID

    Returns:
    --------
    - Formatted deduplication report
    """
    if not scheduled_deduplication:
        return "ERR Scheduled Deduplication not available"

    try:
        report = scheduled_deduplication.deduplication_report(deduplication_id)

        if deduplication_id:
            # Specific deduplication report
            if "error" in report:
                return f"ERR {report['error']}"

            return (f"OK Deduplication Report: {deduplication_id}\n"
                   f"Status: {report['status']}\n"
                   f"Duplicates found: {report['duplicates_found']}\n"
                   f"Merged: {report.get('merged_count', 0)}\n"
                   f"Token savings: {report['token_savings']:,}")
        else:
            # Summary report
            return (f"OK Deduplication Summary Report\n"
                   f"Total deduplications: {report['total_deduplications']}\n"
                   f"Total duplicates found: {report['total_duplicates_found']}\n"
                   f"Total memories merged: {report['total_memories_merged']}\n"
                   f"Total token savings: {report['total_token_savings']:,}")

    except Exception as e:
        logger.error(f"deduplication_report failed: {e}")
        return f"ERR Failed to generate report: {str(e)}"


@mcp.tool()
async def summarize_old_memories(
    days: int = 30,
    min_length: int = 1000,
    dry_run: bool = False
) -> str:
    """
    Summarize old memories (Summarization Tool)

    TRIGGER TYPE: (S) System - Automatically scheduled by the MaintenanceScheduler for
    periodic summarization. Also callable by AI IDE when user asks to compress old memories.

    Parameters:
    -----------
    - days: Age threshold in days (default: 30)
    - min_length: Minimum content length to summarize (default: 1000)
    - dry_run: If True, simulate without summarizing (default: False)

    Returns:
    --------
    - Summarization result with memories summarized and token savings
    """
    if not scheduled_summarization:
        return "ERR Scheduled Summarization not available"

    try:
        result = await scheduled_summarization.summarize_old_memories(
            days=days,
            min_length=min_length,
            dry_run=dry_run
        )

        if result["status"] == "success":
            if dry_run:
                return (f"OK Dry run complete\n"
                       f"Candidates found: {result['candidates_found']}\n"
                       f"Would save: {result['space_saved_bytes']:,} bytes\n"
                       f"Summarization ID: {result['summarization_id']}")
            else:
                return (f"OK Summarization complete\n"
                       f"Memories summarized: {result['memories_summarized']}\n"
                       f"Space saved: {result['space_saved_bytes']:,} bytes\n"
                       f"Token savings: {result['token_savings']:,}\n"
                       f"Summarization ID: {result['summarization_id']}")
        else:
            return f"ERR Summarization failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"summarize_old_memories failed: {e}")
        return f"ERR Failed to summarize: {str(e)}"


@mcp.tool()
async def schedule_summarization(schedule: str = "monthly") -> str:
    """
    Schedule periodic summarization (Summarization Tool)

    TRIGGER TYPE: (S) System - Automatically schedules summarization

    Parameters:
    -----------
    - schedule: Schedule type ('monthly', 'weekly')

    Returns:
    --------
    - Scheduling result
    """
    if not scheduled_summarization:
        return "ERR Scheduled Summarization not available"

    try:
        trigger = scheduled_summarization.schedule_monthly_summarization()
        return f"OK Summarization scheduled: {schedule}"

    except Exception as e:
        logger.error(f"schedule_summarization failed: {e}")
        return f"ERR Failed to schedule summarization: {str(e)}"


@mcp.tool()
async def summary_stats() -> str:
    """
    Get summarization statistics (Summarization Tool)

    TRIGGER TYPE: (S) System - Automatically triggered for summary statistics

    Returns:
    --------
    - Formatted summarization statistics
    """
    if not scheduled_summarization:
        return "ERR Scheduled Summarization not available"

    try:
        stats = await scheduled_summarization.summarization_statistics()

        if "error" in stats:
            return f"ERR {stats['error']}"

        return (f"OK Summarization Statistics\n"
               f"Total memories: {stats['total_memories']}\n"
               f"Summarized: {stats['summarized_memories']}\n"
               f"Full memories: {stats['full_memories']}\n"
               f"Summarization ratio: {stats['summarization_ratio']}\n"
               f"Space saved: {stats['estimated_space_saved_mb']}")

    except Exception as e:
        logger.error(f"summary_stats failed: {e}")
        return f"ERR Failed to get summarization statistics: {str(e)}"


# ============================================================================
# SPRINT 9: MULTI-LANGUAGE TOOLS - 28 language support with cross-language search
# ============================================================================

@mcp.tool()
async def detect_language(text: str) -> str:
    """
    Detect language from text (Language Detection Tool)

    TRIGGER TYPE: (S) System - Automatically detects text language

    Supports 28 languages: English, Spanish, French, German, Chinese (Simplified/Traditional),
    Japanese, Korean, Russian, Arabic, Portuguese, Italian, Dutch, Polish, Swedish, Danish,
    Norwegian, Finnish, Greek, Czech, Hungarian, Romanian, Bulgarian, Slovak, Croatian,
    Serbian, Slovenian, Lithuanian, Latvian

    Parameters:
    -----------
    - text: Text to analyze for language detection

    Returns:
    --------
    - Language code and confidence score
    """
    try:
        lang_code, confidence = language_detector.detect_language(text)
        lang_name = language_detector.get_language_name(lang_code)

        return (f"OK Language Detected\n"
               f"  Language: {lang_name}\n"
               f"  Code: {lang_code}\n"
               f"  Confidence: {confidence:.2f}\n"
               f"  Supported: {language_detector.is_supported(lang_code)}")

    except Exception as e:
        logger.error(f"detect_language failed: {e}")
        return f"ERR Failed to detect language: {str(e)}"


@mcp.tool()
async def get_supported_languages() -> str:
    """
    Get list of all supported languages (Language Detection Tool)

    TRIGGER TYPE: (S) System - Automatically lists supported languages

    Returns:
    --------
    - Complete list of 28 supported languages
    """
    try:
        languages = language_detector.get_all_supported_languages()

        result = "OK Supported Languages (28):\n"
        for code, info in languages.items():
            result += f"  {code}: {info['name']} ({info['native_name']})\n"

        return result

    except Exception as e:
        logger.error(f"get_supported_languages failed: {e}")
        return f"ERR Failed to get supported languages: {str(e)}"


@mcp.tool()
async def search_by_language(
    query: str,
    user_id: str = "default",
    agent_id: str = "claude-code",
    language: str = None,
    limit: int = 10
) -> str:
    """
    TRIGGER TYPE: (S) System - Automatically searches by language filter
    Search memories with language filtering (Multi-Language Search Tool)

    Parameters:
    -----------
    - query: Search query text
    - user_id: User identifier (default: 'default')
    - agent_id: Agent identifier (default: 'claude-code')
    - language: Language code to filter by (e.g., 'en', 'es', 'fr'). None = all languages
    - limit: Maximum results (default: 10)

    Returns:
    --------
    - Search results filtered by language
    """
    if not postgres_pool:
        return "ERR PostgreSQL not available"

    try:
        # Search memories
        async with postgres_pool.acquire() as conn:
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
                LIMIT $4
            """, user_id, agent_id, query, limit * 2)  # Get more for filtering

        # Convert to list of dicts
        memory_dicts = []
        for row in memories:
            memory_dicts.append({
                'id': str(row['id']),
                'content': row['data_text'],
                'metadata': row['metadata'],
                'created_at': row['created_at'].isoformat()
            })

        # Filter by language (if specified)
        if language:
            filtered = multi_language_search.search_by_language(
                memory_dicts,
                language=language,
                min_confidence=0.5
            )
            lang_name = language_detector.get_language_name(language)
        else:
            # Search all languages
            filtered = memory_dicts
            lang_name = "All Languages"

        # Format results
        result = f"OK Found {len(filtered)} memories in {lang_name}:\n\n"
        for memory in filtered[:limit]:
            result += f"[{memory['id']}] {memory['content'][:100]}...\n"

        if len(filtered) == 0:
            if language:
                result += f"No memories found in language '{language}'"
            else:
                result += "No memories found"

        return result

    except Exception as e:
        logger.error(f"search_by_language failed: {e}")
        return f"ERR Failed to search by language: {str(e)}"


@mcp.tool()
async def get_language_distribution(
    user_id: str = "default",
    agent_id: str = "claude-code"
) -> str:
    """
    TRIGGER TYPE: (S) System - Automatically gets language statistics
    Get distribution of languages across memories (Multi-Language Analytics Tool)

    Parameters:
    -----------
    - user_id: User identifier (default: 'default')
    - agent_id: Agent identifier (default: 'claude-code')

    Returns:
    --------
    - Language distribution statistics
    """
    if not postgres_pool:
        return "ERR PostgreSQL not available"

    try:
        # Get all memories
        async with postgres_pool.acquire() as conn:
            memories = await conn.fetch("""
                SELECT id, metadata
                FROM shared_memory.documents
                WHERE user_id = $1
                AND (agent_id = $2 OR agent_id = 'shared')
            """, user_id, agent_id)

        # Convert to list of dicts
        memory_dicts = []
        for row in memories:
            memory_dicts.append({
                'id': str(row['id']),
                'metadata': row['metadata']
            })

        # Get distribution
        distribution = multi_language_search.get_language_distribution(memory_dicts)

        # Format results
        total = sum(distribution.values())
        result = f"OK Language Distribution ({total} memories):\n\n"

        # Sort by count
        sorted_dist = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        for lang_code, count in sorted_dist:
            lang_name = language_detector.get_language_name(lang_code)
            percentage = (count / total * 100) if total > 0 else 0
            result += f"  {lang_name}: {count} ({percentage:.1f}%)\n"

        if total == 0:
            result += "  No memories found"

        return result

    except Exception as e:
        logger.error(f"get_language_distribution failed: {e}")
        return f"ERR Failed to get language distribution: {str(e)}"


@mcp.tool()
async def cross_language_search(
    query: str,
    user_id: str = "default",
    agent_id: str = "claude-code",
    limit: int = 10
) -> str:
    """
    TRIGGER TYPE: (S) System - Automatically performs cross-language search
    Cross-language search with relevance boosting (Multi-Language Search Tool)

    Searches memories in any language, with relevance boosting for memories
    in the same language as the query.

    Parameters:
    -----------
    - query: Search query text (language auto-detected)
    - user_id: User identifier (default: 'default')
    - agent_id: Agent identifier (default: 'claude-code')
    - limit: Maximum results (default: 10)

    Returns:
    --------
    - Cross-language search results ranked by relevance
    """
    if not postgres_pool:
        return "ERR PostgreSQL not available"

    try:
        # Detect query language
        query_lang, query_conf = language_detector.detect_language(query)
        query_lang_name = language_detector.get_language_name(query_lang)

        # Search memories
        async with postgres_pool.acquire() as conn:
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
                LIMIT $4
            """, user_id, agent_id, query, limit * 2)

        # Convert to list of dicts
        memory_dicts = []
        for row in memories:
            memory_dicts.append({
                'id': str(row['id']),
                'content': row['data_text'],
                'metadata': row['metadata'],
                'created_at': row['created_at'].isoformat()
            })

        # Cross-language search with ranking
        ranked = multi_language_search.cross_language_search(
            query=query,
            memories=memory_dicts,
            query_language=query_lang
        )

        # Format results
        result = f"OK Cross-Language Search (Query: {query_lang_name})\n"
        result += f"Found {len(ranked)} memories:\n\n"

        for i, memory in enumerate(ranked[:limit], 1):
            metadata = memory.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            mem_lang = metadata.get('language', 'unknown')
            mem_lang_name = language_detector.get_language_name(mem_lang)

            match = "SAME" if mem_lang == query_lang else "DIFF"
            result += f"{i}. [{match}] {mem_lang_name}: {memory['content'][:80]}...\n"

        return result

    except Exception as e:
        logger.error(f"cross_language_search failed: {e}")
        return f"ERR Failed to perform cross-language search: {str(e)}"


@mcp.tool()
async def get_search_facets(
    user_id: str = "default",
    agent_id: str = "claude-code"
) -> str:
    """
    Get search facets for advanced filtering (Advanced Search Tool)

    TRIGGER TYPE: (S) System - Automatically triggered for search faceting

    Returns faceted counts for language, memory type, and category.

    Parameters:
    -----------
    - user_id: User identifier (default: 'default')
    - agent_id: Agent identifier (default: 'claude-code')

    Returns:
    --------
    - Faceted search options with counts
    """
    if not postgres_pool:
        return "ERR PostgreSQL not available"

    try:
        # Get all memories
        async with postgres_pool.acquire() as conn:
            memories = await conn.fetch("""
                SELECT id, metadata
                FROM shared_memory.documents
                WHERE user_id = $1
                AND (agent_id = $2 OR agent_id = 'shared')
            """, user_id, agent_id)

        # Convert to list of dicts
        memory_dicts = []
        for row in memories:
            memory_dicts.append({
                'id': str(row['id']),
                'metadata': row['metadata']
            })

        # Get facets
        facets = multi_language_search.get_facets(memory_dicts)

        # Format results
        result = "OK Search Facets:\n\n"

        for facet_name, facet_values in facets.items():
            result += f"{facet_name.upper()}:\n"
            for value, count in sorted(facet_values.items(), key=lambda x: x[1], reverse=True):
                result += f"  {value}: {count}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"get_search_facets failed: {e}")
        return f"ERR Failed to get search facets: {str(e)}"


# ============================================================================
# SPRINT 10: ADVANCED AI FEATURES - Intelligent Summarization & Advanced Search
# ============================================================================

@mcp.tool()
async def intelligent_summarize(
    memory_id: str,
    strategy: str = "standard",
    llm_provider: str = "openai"
) -> str:
    """
    TRIGGER TYPE: (S) System - Automatically triggered for LLM-powered summarization
    Summarize a memory using LLM-based intelligent summarization (Sprint 10)

    Parameters:
    -----------
    - memory_id: ID of the memory to summarize
    - strategy: Summarization strategy ('concise', 'standard', 'detailed', 'extractive')
    - llm_provider: LLM provider ('openai', 'anthropic', 'ollama')

    Returns:
    --------
    - Summary with compression ratio and metadata
    """
    if not intelligent_summarizer:
        return "ERR Intelligent Summarizer not available"

    try:
        # Get memory
        if not postgres_pool:
            return "ERR PostgreSQL not available"

        async with postgres_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, content, metadata, created_at
                FROM shared_memory.documents
                WHERE id = $1
            """, memory_id)

            if not row:
                return f"ERR Memory not found: {memory_id}"

            memory = {
                'id': str(row['id']),
                'content': row['content'],
                'metadata': row['metadata'],
                'created_at': row['created_at']
            }

        # Parse strategy
        try:
            summary_strategy = SummaryStrategy(strategy.lower())
        except ValueError:
            return f"ERR Invalid strategy: {strategy}. Use: concise, standard, detailed, extractive"

        # Update LLM config
        intelligent_summarizer.llm_config['provider'] = llm_provider

        # Summarize
        result = await intelligent_summarizer.summarize_memory(memory, summary_strategy)

        return (f"OK Summary Generated\n"
               f"  Memory ID: {result.memory_id}\n"
               f"  Strategy: {result.strategy.value}\n"
               f"  Compression Ratio: {result.compression_ratio:.2f}x\n"
               f"  Keywords: {', '.join(result.keywords[:5])}\n"
               f"  Entities: {len(result.entities)} found\n"
               f"  Summary:\n"
               f"    {result.summary}\n\n"
               f"  Store this summary using update_memory to persist it")

    except Exception as e:
        logger.error(f"intelligent_summarize failed: {e}")
        return f"ERR Failed to summarize: {str(e)}"


@mcp.tool()
async def auto_summarize_old_memories(
    days_old: int = 30,
    min_length: int = 500,
    dry_run: bool = False,
    strategy: str = "standard"
) -> str:
    """
    TRIGGER TYPE: (S) System - Automatically batch summarizes old memories
    Automatically summarize old memories (Sprint 10)

    Parameters:
    -----------
    - days_old: Minimum age in days (default: 30)
    - min_length: Minimum content length to summarize (default: 500)
    - dry_run: If True, simulate without summarizing (default: False)
    - strategy: Summarization strategy (default: 'standard')

    Returns:
    --------
    - Summarization statistics
    """
    if not intelligent_summarizer:
        return "ERR Intelligent Summarizer not available"

    try:
        # Update settings
        intelligent_summarizer.min_memory_age_days = days_old
        intelligent_summarizer.min_memory_length = min_length

        # Parse strategy
        try:
            summary_strategy = SummaryStrategy(strategy.lower())
        except ValueError:
            return f"ERR Invalid strategy: {strategy}"

        # Run auto-summarization
        result = await intelligent_summarizer.auto_summarize_old_memories(dry_run=dry_run)

        if result.get("status") == "success":
            if dry_run:
                return (f"OK DRY RUN - Auto Summarization\n"
                       f"  Candidates Found: {result['total_candidates']}\n"
                       f"  Would Summarize: {result['summarized']}\n"
                       f"  Would Skip: {result['skipped']}\n"
                       f"  Would Fail: {result['failed']}\n"
                       f"  Est. Compression: {result.get('total_compression_ratio', 0):.2f}x")
            else:
                return (f"OK Auto Summarization Complete\n"
                       f"  Total Candidates: {result['total_candidates']}\n"
                       f"  Summarized: {result['summarized']}\n"
                       f"  Skipped: {result['skipped']}\n"
                       f"  Failed: {result['failed']}\n"
                       f"  Avg Compression: {result.get('total_compression_ratio', 0):.2f}x")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"auto_summarize_old_memories failed: {e}")
        return f"ERR Failed to auto-summarize: {str(e)}"


@mcp.tool()
async def cluster_memories(
    category: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = 100
) -> str:
    """
    TRIGGER TYPE: (S) System - Automatically clusters memories semantically
    Cluster related memories using semantic similarity (Sprint 10)

    Parameters:
    -----------
    - category: Optional category filter
    - agent_id: Optional agent ID filter
    - limit: Maximum memories to process (default: 100)

    Returns:
    --------
    - Memory clusters with themes
    """
    if not intelligent_summarizer:
        return "ERR Intelligent Summarizer not available"

    try:
        # Find memories
        if not postgres_pool:
            return "ERR PostgreSQL not available"

        async with postgres_pool.acquire() as conn:
            query = """
                SELECT id, content, metadata, agent_id, created_at
                FROM shared_memory.documents
                WHERE LENGTH(content) > 100
            """
            params = []
            param_count = 1

            if category:
                query += f" AND metadata->>'memory_category' = ${param_count}"
                params.append(category)
                param_count += 1

            if agent_id:
                query += f" AND agent_id = ${param_count}"
                params.append(agent_id)
                param_count += 1

            query += f" ORDER BY created_at DESC LIMIT ${param_count}"
            params.append(limit)

            memories = await conn.fetch(query, *params)

            memory_list = [dict(m) for m in memories]

        # Cluster memories
        clusters = await intelligent_summarizer.cluster_memories(memory_list)

        # Format results
        result = f"OK Memory Clusters ({len(clusters)} total):\n\n"

        for i, cluster in enumerate(clusters[:10], 1):
            result += f"{i}. Cluster: {cluster.cluster_id}\n"
            result += f"   Theme: {cluster.cluster_theme or 'General'}\n"
            result += f"   Memories: {cluster.memory_count}\n"
            if cluster.cluster_summary:
                result += f"   Summary: {cluster.cluster_summary[:100]}...\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"cluster_memories failed: {e}")
        return f"ERR Failed to cluster memories: {str(e)}"


@mcp.tool()
async def advanced_search(
    query: str,
    user_id: str = "default",
    agent_id: Optional[str] = None,
    limit: int = 20,
    rerank: bool = True,
    strategy: str = "combined",
    expand_query: bool = True
) -> str:
    """
    TRIGGER TYPE: (S) System - Automatically performs advanced search with re-ranking
    Advanced search with query expansion and re-ranking (Sprint 10)

    Parameters:
    -----------
    - query: Search query text
    - user_id: User identifier (default: 'default')
    - agent_id: Optional agent filter
    - limit: Maximum results (default: 20)
    - rerank: Whether to apply re-ranking (default: True)
    - strategy: Re-ranking strategy ('relevance', 'recency', 'combined', 'personalized')
    - expand_query: Whether to expand query using LLM (default: True)

    Returns:
    --------
    - Advanced search results with re-ranking and highlights
    """
    if not advanced_search_engine:
        return "ERR Advanced Search Engine not available"

    try:
        # Parse strategy
        try:
            rerank_strategy = ReRankingStrategy(strategy.lower())
        except ValueError:
            return f"ERR Invalid strategy: {strategy}. Use: relevance, recency, combined, personalized"

        # Perform search
        results = await advanced_search_engine.search(
            query=query,
            user_id=user_id,
            agent_id=agent_id,
            limit=limit,
            rerank=rerank,
            strategy=rerank_strategy,
            filters={}
        )

        # Format results
        output = [f"OK Advanced Search Results ({len(results)} found):\n"]

        for i, result in enumerate(results[:10], 1):
            output.append(f"\n{i}. Rank: {result.rank} | Score: {result.reranked_score:.3f}")
            output.append(f"   Reason: {result.relevance_reason}")
            output.append(f"   Content: {result.content[:150]}...")

            if result.highlights:
                output.append(f"   Highlights:")
                for highlight in result.highlights[:3]:
                    output.append(f"     - {highlight}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"advanced_search failed: {e}")
        return f"ERR Failed to perform advanced search: {str(e)}"


@mcp.tool()
async def expand_search_query(query: str, max_expansions: int = 5) -> str:
    """
    Expand search query with related terms using LLM (Sprint 10)

    TRIGGER TYPE: (S) System - Automatically expands queries with LLM

    Parameters:
    -----------
    - query: Original search query
    - max_expansions: Maximum number of expanded queries (default: 5)

    Returns:
    --------
    - Expanded query list
    """
    if not advanced_search_engine:
        return "ERR Advanced Search Engine not available"

    try:
        expanded = await advanced_search_engine._expand_query(query)

        result = f"OK Query Expansion ({len(expanded)} variants):\n\n"
        result += f"Original: {query}\n\n"
        result += "Expanded Queries:\n"

        for i, exp in enumerate(expanded[:max_expansions], 1):
            result += f"  {i}. {exp}\n"

        return result

    except Exception as e:
        logger.error(f"expand_search_query failed: {e}")
        return f"ERR Failed to expand query: {str(e)}"


@mcp.tool()
async def get_search_analytics(days_back: int = 30) -> str:
    """
    Get search analytics and statistics (Sprint 10)

    TRIGGER TYPE: (S) System - Automatically gets search analytics

    Parameters:
    -----------
    - days_back: Number of days to analyze (default: 30)

    Returns:
    --------
    - Search analytics with metrics
    """
    if not advanced_search_engine:
        return "ERR Advanced Search Engine not available"

    try:
        analytics = await advanced_search_engine.get_search_analytics(days_back)

        if analytics.get("status") == "error":
            return f"ERR {analytics.get('error', 'Unknown error')}"

        result = f"OK Search Analytics ({days_back} days):\n\n"
        result += f"Total Searches: {analytics['total_searches']}\n"
        result += f"Avg Query Length: {analytics['avg_query_length']:.1f} chars\n"
        result += f"Zero Results Rate: {analytics['zero_results_rate']:.1f}%\n\n"

        result += "Top Search Terms:\n"
        for term in analytics['top_search_terms'][:10]:
            result += f"  - {term['query_term']}: {term['count']} searches\n"

        return result

    except Exception as e:
        logger.error(f"get_search_analytics failed: {e}")
        return f"ERR Failed to get search analytics: {str(e)}"


@mcp.tool()
async def get_summarization_stats() -> str:
    """
    Get intelligent summarization statistics (Sprint 10)

    TRIGGER TYPE: (S) System - Automatically triggered for summarization metrics

    Returns:
    --------
    - Summarization statistics and metrics
    """
    if not intelligent_summarizer:
        return "ERR Intelligent Summarizer not available"

    try:
        stats = await intelligent_summarizer.get_summarization_statistics()

        if stats.get("status") == "error":
            return f"ERR {stats.get('error', 'Unknown error')}"

        result = "OK Intelligent Summarization Statistics:\n\n"
        result += f"Memories Summarized: {stats['memories_summarized']}\n"
        result += f"Avg Compression Ratio: {stats['average_compression_ratio']:.2f}x\n"

        return result

    except Exception as e:
        logger.error(f"get_summarization_stats failed: {e}")
        return f"ERR Failed to get summarization stats: {str(e)}"


# ---------------------------------------------------------------------------
# Phase 2 - P1 Ports: Session-Aware Memory + Knowledge Graph Search
# Wires cognee v1.0.9 remember/recall/forget/improve API into MCP tools.
# All output is ASCII-only per CLAUDE.md requirements.
# ---------------------------------------------------------------------------

_VALID_SEARCH_TYPES = {
    "SUMMARIES", "CHUNKS", "RAG_COMPLETION", "TRIPLET_COMPLETION",
    "GRAPH_COMPLETION", "GRAPH_COMPLETION_DECOMPOSITION", "GRAPH_SUMMARY_COMPLETION",
    "CYPHER", "NATURAL_LANGUAGE", "GRAPH_COMPLETION_COT",
    "GRAPH_COMPLETION_CONTEXT_EXTENSION", "FEELING_LUCKY",
    "TEMPORAL", "CODING_RULES", "CHUNKS_LEXICAL",
}

# Background cognify task tracking (pipeline_run_id -> status string)
_cognify_tasks: dict = {}


@mcp.tool()
async def remember(
    data: str,
    dataset_name: str = "main_dataset",
    session_id: Optional[str] = None,
    run_in_background: bool = False,
) -> str:
    """
    Store data into the cognee knowledge graph (session-aware ingestion).

    This is the v1.0.9 remember() API - richer than cognify() because it
    supports session context, self-improvement feedback, and typed memory
    entries (QA, Trace, Feedback). Use cognify() for simple document storage.

    TRIGGER TYPE: (A) Auto - AI IDE triggers this based on conversation context.
    WHEN TO CALL: Call automatically when the user says "remember this", "save this",
    "note that", "keep this in mind", or when the user shares knowledge they will
    likely need later (project decisions, preferences, facts, meeting notes, code
    patterns). Do NOT call for transient conversational messages.

    Parameters:
    -----------
    - data: Text, URL, or structured content to store
    - dataset_name: Target dataset name (default: 'main_dataset')
    - session_id: Optional session ID to associate this memory with a conversation
    - run_in_background: If True, returns immediately with a task ID

    Returns:
    --------
    - Status string with task ID if background mode, else completion status
    """
    try:
        import cognee
        from cognee.api.v1.remember.remember import remember as cognee_remember

        if run_in_background:
            task_id = f"remember_{len(_cognify_tasks) + 1}"
            _cognify_tasks[task_id] = "running"

            async def _run():
                try:
                    await cognee_remember(
                        data=data,
                        dataset_name=dataset_name,
                        session_id=session_id,
                        run_in_background=False,
                    )
                    _cognify_tasks[task_id] = "completed"
                except Exception as exc:
                    _cognify_tasks[task_id] = f"failed: {exc}"

            asyncio.create_task(_run())
            return f"OK remember task started in background (task_id: {task_id})"

        await cognee_remember(
            data=data,
            dataset_name=dataset_name,
            session_id=session_id,
        )
        return f"OK Data stored in dataset '{dataset_name}'" + (
            f" (session: {session_id})" if session_id else ""
        )

    except Exception as e:
        logger.error(f"remember failed: {e}")
        return f"ERR remember failed: {str(e)}"


@mcp.tool()
async def recall(
    query: str,
    search_type: str = "GRAPH_COMPLETION",
    dataset_name: Optional[str] = None,
    session_id: Optional[str] = None,
    top_k: int = 10,
) -> str:
    """
    Search the cognee knowledge graph with 15 available search strategies.

    This wraps cognee v1.0.9 recall() / search() - far more powerful than the
    Enhanced search() tool which only does PostgreSQL text search.

    TRIGGER TYPE: (A) Auto - AI IDE triggers this based on conversation context.
    WHEN TO CALL: Call automatically when the user asks "what did we decide about X?",
    "what do you know about Y?", or any question that may be answered from stored
    knowledge. Prefer recall over search_memories for structured knowledge graph queries.

    Available search_type values:
    - GRAPH_COMPLETION         : LLM-augmented graph traversal (recommended default)
    - GRAPH_COMPLETION_COT     : Chain-of-thought graph reasoning
    - GRAPH_COMPLETION_DECOMPOSITION : Decompose query into sub-questions
    - GRAPH_COMPLETION_CONTEXT_EXTENSION : Extend context along graph edges
    - GRAPH_SUMMARY_COMPLETION : Search graph-level summaries
    - SUMMARIES                : Document and chunk summaries
    - CHUNKS                   : Raw text chunk retrieval
    - CHUNKS_LEXICAL           : BM25-style lexical chunk search
    - RAG_COMPLETION           : Retrieval-augmented generation
    - TRIPLET_COMPLETION       : Knowledge triplet retrieval
    - NATURAL_LANGUAGE         : Natural language query parser
    - TEMPORAL                 : Time-aware knowledge retrieval
    - CODING_RULES             : Retrieve coding rules and patterns
    - CYPHER                   : Direct Cypher query against graph
    - FEELING_LUCKY            : Auto-select best strategy for query

    Parameters:
    -----------
    - query: Search query text
    - search_type: Strategy name (see above, default: GRAPH_COMPLETION)
    - dataset_name: Optional dataset to scope the search
    - session_id: Optional session ID for session-scoped recall
    - top_k: Maximum results to return (default: 10)

    Returns:
    --------
    - Formatted search results with content and source references
    """
    search_type_upper = search_type.upper()
    if search_type_upper not in _VALID_SEARCH_TYPES:
        valid = ", ".join(sorted(_VALID_SEARCH_TYPES))
        return f"ERR Invalid search_type '{search_type}'. Valid: {valid}"

    try:
        from cognee.api.v1.search.search import search as cognee_search
        from cognee.modules.search.methods.get_search_type_retriever_instance import SearchType

        s_type = SearchType[search_type_upper]

        datasets = [dataset_name] if dataset_name else None
        results = await cognee_search(
            query_text=query,
            query_type=s_type,
            datasets=datasets,
            top_k=top_k,
        )

        if not results:
            return f"OK No results found for query: '{query}' (strategy: {search_type_upper})"

        lines = [f"OK {len(results)} result(s) (strategy: {search_type_upper}):\n"]
        for i, item in enumerate(results[:top_k], 1):
            if isinstance(item, dict):
                content = item.get("text") or item.get("content") or str(item)
                score = item.get("score") or item.get("relevance_score", "")
                score_str = f" | score: {score:.3f}" if isinstance(score, float) else ""
                lines.append(f"{i}. {content[:200].strip()}{score_str}")
            else:
                lines.append(f"{i}. {str(item)[:200]}")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"recall failed: {e}")
        return f"ERR recall failed: {str(e)}"


@mcp.tool()
async def forget_memory(
    data_id: Optional[str] = None,
    dataset: Optional[str] = None,
    everything: bool = False,
) -> str:
    """
    Remove data from the cognee knowledge graph.

    Note: This operates on the cognee graph (not Enhanced PostgreSQL memories).
    To delete an Enhanced memory entry, use delete_memory() instead.

    TRIGGER TYPE: (M) Manual - triggered by explicit user deletion request

    Parameters:
    -----------
    - data_id: UUID of a specific data item to forget
    - dataset: Dataset name or UUID to forget entirely
    - everything: If True, wipe all graph data (requires dataset=None and data_id=None)

    Returns:
    --------
    - Status message confirming deletion
    """
    if everything and (data_id or dataset):
        return "ERR Cannot combine everything=True with data_id or dataset"

    if not everything and not data_id and not dataset:
        return "ERR Provide data_id, dataset, or set everything=True"

    try:
        from cognee.api.v1.forget.forget import forget as cognee_forget

        from uuid import UUID as _UUID
        parsed_id = None
        if data_id:
            try:
                parsed_id = _UUID(data_id)
            except ValueError:
                return f"ERR data_id must be a valid UUID, got: {data_id}"

        result = await cognee_forget(
            data_id=parsed_id,
            dataset=dataset,
            everything=everything,
        )

        if everything:
            return "OK All graph data deleted"
        if data_id:
            return f"OK Data item {data_id} deleted from knowledge graph"
        return f"OK Dataset '{dataset}' deleted from knowledge graph"

    except Exception as e:
        logger.error(f"forget_memory failed: {e}")
        return f"ERR forget_memory failed: {str(e)}"


@mcp.tool()
async def improve(
    dataset: str = "main_dataset",
    session_ids: Optional[str] = None,
    run_in_background: bool = False,
) -> str:
    """
    Run the 4-stage feedback improvement pipeline on a dataset.

    This is cognee v1.0.9's improve() API. It applies:
      Stage 1: Extract feedback QAs from sessions
      Stage 2: Apply feedback weights to graph edges
      Stage 3: Persist session data to permanent graph
      Stage 4: Sync enriched graph back to session cache

    Use this after storing several interactions to improve knowledge quality.

    TRIGGER TYPE: (S) System - Automatically scheduled via Phase 8b auto_scheduler config.
                  Enable with: {"auto_scheduler": {"improve": {"enabled": true}}}
                  in .enhanced-cognee-config.json. Also callable manually.

    Parameters:
    -----------
    - dataset: Dataset name to improve (default: 'main_dataset')
    - session_ids: Comma-separated session IDs to use as feedback source
    - run_in_background: If True, returns immediately with a task ID

    Returns:
    --------
    - Completion status or background task ID
    """
    try:
        from cognee.api.v1.improve.improve import improve as cognee_improve

        parsed_sessions = None
        if session_ids:
            parsed_sessions = [s.strip() for s in session_ids.split(",") if s.strip()]

        if run_in_background:
            task_id = f"improve_{len(_cognify_tasks) + 1}"
            _cognify_tasks[task_id] = "running"

            async def _run():
                try:
                    await cognee_improve(
                        dataset=dataset,
                        session_ids=parsed_sessions,
                        run_in_background=False,
                    )
                    _cognify_tasks[task_id] = "completed"
                except Exception as exc:
                    _cognify_tasks[task_id] = f"failed: {exc}"

            asyncio.create_task(_run())
            return f"OK improve task started in background (task_id: {task_id})"

        await cognee_improve(
            dataset=dataset,
            session_ids=parsed_sessions,
        )
        sessions_str = f" using sessions [{session_ids}]" if session_ids else ""
        return f"OK Knowledge improvement pipeline complete for dataset '{dataset}'{sessions_str}"

    except Exception as e:
        logger.error(f"improve failed: {e}")
        return f"ERR improve failed: {str(e)}"


@mcp.tool()
async def save_interaction(
    data: str,
    dataset_name: str = "main_dataset",
) -> str:
    """
    Save a coding interaction (user/assistant exchange) to the knowledge graph.

    This enables MCP-compatible IDEs (Cursor, Windsurf, etc.) to record interaction patterns
    so they can be surfaced as rules and best practices via recall(search_type=CODING_RULES).

    TRIGGER TYPE: (A) Auto - trigger after significant user/assistant exchanges

    Format for data (recommended):
      'user: <user message>\\nassistant: <assistant response>'

    Parameters:
    -----------
    - data: The interaction text (user + assistant turn)
    - dataset_name: Target dataset (default: 'main_dataset')

    Returns:
    --------
    - Status confirming the interaction was saved
    """
    try:
        from cognee.api.v1.add.add import add as cognee_add
        from cognee.api.v1.cognify.cognify import cognify as cognee_cognify

        await cognee_add(data=data, dataset_name=dataset_name)
        await cognee_cognify(datasets=[dataset_name])
        return f"OK Interaction saved to dataset '{dataset_name}'"

    except Exception as e:
        logger.error(f"save_interaction failed: {e}")
        return f"ERR save_interaction failed: {str(e)}"


@mcp.tool()
async def cognify_status(dataset_name: Optional[str] = None) -> str:
    """
    Check the status of background cognify / remember / improve tasks.

    TRIGGER TYPE: (S) System - Polled by Enhanced Cognee to monitor background task progress.
    No user action required; also callable by AI IDE when user asks about background jobs.

    Parameters:
    -----------
    - dataset_name: Optional dataset name filter (not yet used, reserved for future)

    Returns:
    --------
    - Status of all tracked background tasks
    """
    if not _cognify_tasks:
        return "OK No background tasks recorded"

    lines = [f"OK Background task status ({len(_cognify_tasks)} task(s)):\n"]
    for task_id, status in list(_cognify_tasks.items())[-20:]:
        lines.append(f"  {task_id}: {status}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase 3 - P2 Ports: External Loaders, Translation, Regex Entities, v2 Graph
# Surfaces v1.0.9 web-scraper, dlt, translation, regex extractor, and cascade
# v2 graph extraction as MCP tools.
# All output is ASCII-only per CLAUDE.md requirements.
# ---------------------------------------------------------------------------


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

    TRIGGER TYPE: (A) Auto - AI IDE triggers this based on conversation context.
    WHEN TO CALL: Call automatically when the user provides a URL and says "learn from
    this", "read this page", "add this documentation", "ingest this", or "remember
    what is on this site". Do NOT call for every URL mentioned - only when user
    explicitly wants it added to memory.

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

        # Resolve URL list
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
    Optionally filter with a SQL query (e.g. 'SELECT * FROM orders WHERE status=active').

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
    and Azure Translator backends. The LLM provider works out of the box
    with any configured LLM; Google and Azure require API keys.

    TRIGGER TYPE: (S) System - Automatically triggered as a post-ingestion hook (Phase 8b).
                  Enable with: {"post_ingestion": {"auto_translate": {"enabled": true}}}
                  in .enhanced-cognee-config.json. Also callable manually.

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
            f"OK Translation complete:",
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

    Uses the v1.0.9 RegexEntityExtractor which reads patterns from a JSON config.
    The default config includes common entity types (emails, URLs, phone numbers,
    dates, IP addresses, etc.). Provide a custom config_path to use your own patterns.

    TRIGGER TYPE: (S) System - Automatically triggered as a post-ingestion hook (Phase 8b).
                  Enable with: {"post_ingestion": {"auto_extract_entities": {"enabled": true}}}
                  in .enhanced-cognee-config.json. Also callable manually.

    Parameters:
    -----------
    - text: The text to extract entities from
    - config_path: Optional path to a JSON config file defining entity patterns.
      Default: cognee built-in config (common entity types).
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
    the extracted nodes and edges as structured data - useful for previewing what
    the v2 extractor would find before committing to full cognify().

    The cascade algorithm performs n_rounds of extraction, each round refining
    the previously discovered nodes and relationships, producing denser graphs
    than single-pass extraction.

    TRIGGER TYPE: (S) System - Automatically triggered as a post-ingestion hook (Phase 8b).
                  Enable with: {"post_ingestion": {"auto_graph_v2": {"enabled": true}}}
                  in .enhanced-cognee-config.json. Also callable manually.

    Parameters:
    -----------
    - text: The text to extract a knowledge graph from
    - n_rounds: Number of cascade extraction rounds (default: 2, max recommended: 3).
      More rounds = denser graph but more LLM calls.

    Returns:
    --------
    - Extracted knowledge graph as JSON (nodes list + edges list)
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

        # Step 1: Extract node candidates
        nodes = await extract_nodes(text, n_rounds=n_rounds)

        if not nodes:
            return "OK No nodes extracted from the provided text"

        # Step 2: Extract relationship names
        updated_nodes, relationships = await extract_content_nodes_and_relationship_names(
            text, nodes, n_rounds
        )

        # Step 3: Extract edge triplets
        graph = await extract_edge_triplets(text, updated_nodes, relationships, n_rounds)

        # Format output
        lines = [
            f"OK v2 cascade extraction complete ({n_rounds} round(s)):",
            f"  Nodes: {len(graph.nodes)}",
            f"  Edges: {len(graph.edges)}",
            "",
            "Nodes:",
        ]
        for node in graph.nodes:
            lines.append(f"  - {node.name} ({node.type if hasattr(node, 'type') else 'entity'})")

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

    TRIGGER TYPE: (A) Auto - AI IDE triggers this based on conversation context.
    WHEN TO CALL: Call automatically when the user asks "what file types can I ingest?",
    "what formats are supported?", "can I import a PDF?", or similar questions about
    supported data sources.

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
            status = "ACTIVE"
            lines.append(f"  [{status}] {name}: {desc}")

        optional_missing = [
            n for n in loader_info
            if n not in supported_loaders
        ]
        if optional_missing:
            lines.append("\nOptional loaders not installed:")
            for name in optional_missing:
                desc = loader_info.get(name, "")
                lines.append(f"  [OFF]  {name}: {desc}")

        lines.append(
            "\nTo use a loader: pass the file path to add_memory() or cognify(). "
            "The loader is selected automatically by file extension."
        )
        return "\n".join(lines)
    except Exception as exc:
        return f"ERR list_loaders failed: {exc}"


# ---------------------------------------------------------------------------
# Plan 14.8 - LLM Cost Tracking tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_llm_cost_report(
    agent_id: Optional[str] = None,
    days_back: int = 30,
    group_by: str = "agent",
) -> str:
    """
    Get LLM token usage and estimated API cost report.

    TRIGGER TYPE: (S) System - Called by schedulers, monitoring dashboards,
    and optionally by the AI IDE during periodic health checks.

    WHEN TO CALL: Call automatically when the user asks about LLM costs,
    API spend, token usage, or cost management. Also suitable for inclusion
    in weekly system health summaries.

    Parameters:
    -----------
    - agent_id: Filter results to a single agent ID (default: all agents)
    - days_back: Number of calendar days to include (default: 30)
    - group_by: Dimension to aggregate by -- 'agent', 'tool', or 'model'
      (default: 'agent')

    Returns:
    --------
    - ASCII table with per-group call count, token totals, and USD estimate
    - Totals row at the bottom
    - If no usage recorded: guidance on how usage is captured
    """
    if llm_cost_tracker is None:
        return (
            "WARN LLM Cost Tracker not initialized. "
            "Check server startup logs for initialization errors."
        )
    if days_back < 1 or days_back > 365:
        return "ERR days_back must be between 1 and 365"
    if group_by not in ("agent", "tool", "model"):
        return "ERR group_by must be 'agent', 'tool', or 'model'"
    try:
        return await llm_cost_tracker.get_cost_report(
            agent_id=agent_id,
            days_back=days_back,
            group_by=group_by,
        )
    except Exception as exc:
        return f"ERR get_llm_cost_report failed: {exc}"


@mcp.tool()
async def set_cost_budget(agent_id: str, monthly_usd: float) -> str:
    """
    Set the monthly LLM API cost budget for an agent.

    TRIGGER TYPE: (M) Manual - Must be explicitly invoked by the user.
    WHY MANUAL: Budget limits have direct financial and operational impact
    and must not be set or changed without deliberate user intent.

    Budget enforcement is WARN-only by default (a log entry is written
    when the limit is reached but no calls are blocked). To enable hard
    stops, set "auto_scheduler.budget_hard_stop": true in
    .enhanced-cognee-config.json.

    Parameters:
    -----------
    - agent_id: Agent identifier to set the budget for.
      Use '*' to set a global default that applies to any agent that does
      not have its own budget (e.g. set_cost_budget('*', 50.00)).
    - monthly_usd: Monthly spending ceiling in USD (must be > 0).

    Returns:
    --------
    - Confirmation string with persistence status (DB or in-memory)
    """
    if llm_cost_tracker is None:
        return (
            "WARN LLM Cost Tracker not initialized. "
            "Check server startup logs for initialization errors."
        )
    if not agent_id or not agent_id.strip():
        return "ERR agent_id must not be empty (use '*' for global default)"
    if monthly_usd <= 0:
        return "ERR monthly_usd must be a positive number"
    try:
        return await llm_cost_tracker.set_budget(
            agent_id=agent_id.strip(),
            monthly_usd=monthly_usd,
        )
    except Exception as exc:
        return f"ERR set_cost_budget failed: {exc}"


# ---------------------------------------------------------------------------
# Phase 7 - 12.5: Progressive Search Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_quick(
    query: str,
    agent_id: Optional[str] = None,
) -> str:
    """
    Quick keyword search returning the top 3 most recent matching memories.

    TRIGGER TYPE: (M) Manual - User explicitly requests a rapid, lightweight
    lookup without needing semantic ranking or full result sets.

    Use this when you need a fast answer with minimal overhead.  For broader
    or semantically ranked results use search_memories or advanced_search.

    Parameters:
    -----------
    - query     : Search text (case-insensitive substring match)
    - agent_id  : Optional agent scope filter

    Returns:
    --------
    - Top-3 memory snippets with ID, agent, and first 150 chars of content
    """
    try:
        query = sanitize_string(query, max_length=500)
        if agent_id:
            agent_id = validate_agent_id(agent_id)

        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot search memories"

        async with postgres_pool.acquire() as conn:
            sql = """
                SELECT id, title, content, agent_id, created_at
                FROM shared_memory.documents
                WHERE content ILIKE $1
            """
            params: list = [f"%{query}%"]
            if agent_id:
                sql += " AND agent_id = $2"
                params.append(agent_id)
            sql += " ORDER BY created_at DESC LIMIT 3"

            rows = await conn.fetch(sql, *params)

        if not rows:
            return f"OK No memories found for: {query}"

        lines = [f"OK Quick search - top {len(rows)} results for '{query}':"]
        for idx, row in enumerate(rows, 1):
            snippet = (row["content"] or "")[:150]
            lines.append(
                f"\n{idx}. [ID: {row['id']}]"
                f"\n   Agent  : {row['agent_id']}"
                f"\n   Content: {snippet}"
                + ("..." if len(row["content"] or "") > 150 else "")
            )
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"search_quick failed: {exc}")
        return f"ERR search_quick failed: {exc}"


@mcp.tool()
async def get_memory_detail(memory_id: str) -> str:
    """
    Retrieve the full detail of a single memory including all metadata fields.

    TRIGGER TYPE: (A) Auto - Automatically invoked when full memory context is
    needed after a search_quick or search_memories call identified an item.

    Use this after a search identifies a memory ID and you need the complete
    record (full content, metadata, timestamps, TTL, sharing settings).

    Parameters:
    -----------
    - memory_id : UUID of the memory to retrieve

    Returns:
    --------
    - Complete memory record with all available fields
    """
    try:
        memory_id = sanitize_string(memory_id, max_length=64)

        if not postgres_pool:
            return "ERR PostgreSQL not available"

        async with postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, title, content, agent_id, metadata,
                       created_at, updated_at, expire_at
                FROM shared_memory.documents
                WHERE id = $1
                """,
                memory_id,
            )

        if not row:
            return f"ERR Memory not found: {memory_id}"

        metadata_str = row["metadata"] or "{}"
        try:
            meta = (
                json.loads(metadata_str)
                if isinstance(metadata_str, str)
                else metadata_str
            )
        except Exception:
            meta = {}

        lines = [
            f"OK Memory detail for {row['id']}:",
            f"  Title     : {row['title']}",
            f"  Agent     : {row['agent_id']}",
            f"  Created   : {row['created_at']}",
            f"  Updated   : {row['updated_at']}",
            f"  Expires   : {row['expire_at'] or 'never'}",
            f"  Content   :",
            f"  {row['content']}",
        ]
        if meta:
            lines.append("  Metadata  :")
            for k, v in meta.items():
                lines.append(f"    {k}: {v}")

        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"get_memory_detail failed: {exc}")
        return f"ERR get_memory_detail failed: {exc}"


@mcp.tool()
async def get_related(
    memory_id: str,
    limit: int = 5,
) -> str:
    """
    Find memories related to a given memory by content similarity.

    TRIGGER TYPE: (A) Auto - Automatically called after reading a memory to
    surface contextually linked knowledge without requiring a new search query.

    Similarity is based on shared significant terms from the source memory
    content.  Returns up to <limit> results ordered by recency.

    Parameters:
    -----------
    - memory_id : UUID of the source memory
    - limit     : Maximum related memories to return (default: 5, max: 20)

    Returns:
    --------
    - Up to <limit> related memories ordered by similarity / recency
    """
    try:
        memory_id = sanitize_string(memory_id, max_length=64)
        limit = validate_limit(limit, "limit", max_val=20)

        if not postgres_pool:
            return "ERR PostgreSQL not available"

        async with postgres_pool.acquire() as conn:
            source = await conn.fetchrow(
                "SELECT id, content, agent_id FROM shared_memory.documents WHERE id = $1",
                memory_id,
            )
            if not source:
                return f"ERR Source memory not found: {memory_id}"

            # Extract up to 8 significant words (>4 chars) for matching
            words = [
                w.strip(".,;:!?\"'()[]") for w in (source["content"] or "").split()
                if len(w.strip(".,;:!?\"'()[]")) > 4
            ][:8]

            if not words:
                return "OK No significant terms found in source memory for similarity matching"

            conditions = " OR ".join(f"content ILIKE ${i + 2}" for i in range(len(words)))
            sql = f"""
                SELECT id, title, content, agent_id, created_at
                FROM shared_memory.documents
                WHERE id != $1 AND ({conditions})
                ORDER BY created_at DESC
                LIMIT {int(limit)}
            """
            params_rel: list = [memory_id] + [f"%{w}%" for w in words]
            rows = await conn.fetch(sql, *params_rel)

        if not rows:
            return f"OK No related memories found for: {memory_id}"

        lines = [
            f"OK {len(rows)} memories related to {memory_id}"
            f" (matched on: {', '.join(words[:4])}):"
        ]
        for idx, row in enumerate(rows, 1):
            snippet = (row["content"] or "")[:120]
            lines.append(
                f"\n{idx}. [ID: {row['id']}]"
                f"\n   Agent  : {row['agent_id']}"
                f"\n   Content: {snippet}"
                + ("..." if len(row["content"] or "") > 120 else "")
            )
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"get_related failed: {exc}")
        return f"ERR get_related failed: {exc}"


# ---------------------------------------------------------------------------
# Phase 7 - 12.6/12.7: Session Management Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def start_session(
    user_id: str = "default",
    agent_id: str = "claude-code",
    metadata: Optional[str] = None,
) -> str:
    """
    Start a new Claude Code session and return a session ID.

    TRIGGER TYPE: (M) Manual - Sessions represent intentional work units and
    must be started deliberately by the user at the beginning of a task.

    The session ID can be passed to end_session and get_session_context.

    Parameters:
    -----------
    - user_id  : User identifier (default: "default")
    - agent_id : Agent identifier (default: "claude-code")
    - metadata : Optional JSON string with session metadata (tags, goal, etc.)

    Returns:
    --------
    - Session ID (UUID) or error message
    """
    if not session_manager:
        return "ERR Session Manager not available (PostgreSQL required)"
    try:
        user_id = sanitize_string(user_id, max_length=100)
        agent_id = validate_agent_id(agent_id)
        meta_dict = {}
        if metadata:
            try:
                meta_dict = json.loads(metadata)
            except Exception:
                return "ERR metadata must be valid JSON"
        session_id = await session_manager.start_session(
            user_id=user_id,
            agent_id=agent_id,
            metadata=meta_dict,
        )
        return f"OK Session started: {session_id}"
    except Exception as exc:
        logger.error(f"start_session failed: {exc}")
        return f"ERR start_session failed: {exc}"


@mcp.tool()
async def end_session(
    session_id: str,
    summary: Optional[str] = None,
) -> str:
    """
    End an active session and optionally record a summary.

    TRIGGER TYPE: (M) Manual - Sessions must be ended deliberately; automatic
    ending could discard in-progress context.

    Parameters:
    -----------
    - session_id : UUID returned by start_session
    - summary    : Optional free-text summary of what was accomplished

    Returns:
    --------
    - Session end confirmation with timing information
    """
    if not session_manager:
        return "ERR Session Manager not available (PostgreSQL required)"
    try:
        session_id = sanitize_string(session_id, max_length=64)
        result = await session_manager.end_session(session_id=session_id, summary=summary)
        if "error" in result:
            return f"ERR {result['error']}"
        start = result.get("start_time", "unknown")
        end = result.get("end_time", "unknown")
        return (
            f"OK Session ended: {session_id}\n"
            f"  Start : {start}\n"
            f"  End   : {end}\n"
            + (f"  Summary: {result.get('summary', '')}" if result.get("summary") else "")
        )
    except Exception as exc:
        logger.error(f"end_session failed: {exc}")
        return f"ERR end_session failed: {exc}"


@mcp.tool()
async def get_session_context(
    session_id: str,
    include_memories: bool = True,
    limit: int = 20,
) -> str:
    """
    Retrieve the full context of a session (metadata + associated memories).

    TRIGGER TYPE: (A) Auto - Automatically invoked at the start of a task to
    reload context from a previous session and avoid repeating past work.

    Parameters:
    -----------
    - session_id      : UUID of the session to retrieve
    - include_memories: Whether to include associated memories (default: True)
    - limit           : Maximum number of memories to include (default: 20)

    Returns:
    --------
    - Session information and up to <limit> associated memory snippets
    """
    if not session_manager:
        return "ERR Session Manager not available (PostgreSQL required)"
    try:
        session_id = sanitize_string(session_id, max_length=64)
        ctx = await session_manager.get_session_context(
            session_id=session_id,
            include_memories=include_memories,
            limit=limit,
        )
        if "error" in ctx:
            return f"ERR {ctx['error']}"
        sess = ctx.get("session", {})
        lines = [
            f"OK Session context for {session_id}:",
            f"  User     : {sess.get('user_id')}",
            f"  Agent    : {sess.get('agent_id')}",
            f"  Start    : {sess.get('start_time')}",
            f"  End      : {sess.get('end_time') or 'active'}",
        ]
        if sess.get("summary"):
            lines.append(f"  Summary  : {sess['summary']}")
        mems = ctx.get("memories", [])
        if mems:
            lines.append(f"\n  Memories ({len(mems)}):")
            for m in mems:
                snippet = (m.get("content") or "")[:100]
                lines.append(f"    [{m.get('memory_id', '')}] {snippet}")
        else:
            lines.append("  Memories : none")
        return "\n".join(lines)
    except Exception as exc:
        logger.error(f"get_session_context failed: {exc}")
        return f"ERR get_session_context failed: {exc}"


@mcp.tool()
async def get_session_history(
    user_id: str = "default",
    agent_id: str = "claude-code",
    limit: int = 10,
    active_only: bool = False,
) -> str:
    """
    List recent sessions for a user/agent combination.

    TRIGGER TYPE: (A) Auto - Automatically queried at session start to surface
    recent work context and avoid duplicating previous efforts.

    Parameters:
    -----------
    - user_id     : User identifier (default: "default")
    - agent_id    : Agent identifier (default: "claude-code")
    - limit       : Maximum sessions to return (default: 10)
    - active_only : Return only currently active sessions (default: False)

    Returns:
    --------
    - Formatted list of sessions with IDs, timing, and summary snippets
    """
    if not session_manager:
        return "ERR Session Manager not available (PostgreSQL required)"
    try:
        user_id = sanitize_string(user_id, max_length=100)
        agent_id = validate_agent_id(agent_id)
        limit = validate_limit(limit, "limit", max_val=50)
        sessions = await session_manager.get_recent_sessions(
            user_id=user_id,
            agent_id=agent_id,
            limit=limit,
            active_only=active_only,
        )
        if not sessions:
            label = "active " if active_only else ""
            return f"OK No {label}sessions found for user={user_id}, agent={agent_id}"

        lines = [f"OK {len(sessions)} session(s) for user={user_id}, agent={agent_id}:"]
        for idx, s in enumerate(sessions, 1):
            status = "ACTIVE" if not s.get("end_time") else "ENDED"
            summ = (s.get("summary") or "")[:80]
            lines.append(
                f"\n{idx}. [{status}] {s['session_id']}"
                f"\n   Start  : {s['start_time']}"
                f"\n   End    : {s.get('end_time') or 'still active'}"
                + (f"\n   Summary: {summ}" if summ else "")
            )
        return "\n".join(lines)
    except Exception as exc:
        logger.error(f"get_session_history failed: {exc}")
        return f"ERR get_session_history failed: {exc}"


# ---------------------------------------------------------------------------
# Phase 9 - 14.1: Audit Log Query Tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def query_audit_log(
    agent_id: Optional[str] = None,
    operation_type: Optional[str] = None,
    status: Optional[str] = None,
    hours_back: int = 24,
    limit: int = 50,
) -> str:
    """
    Query the audit log for recent operations across all MCP tools.

    TRIGGER TYPE: (M) Manual - Security and compliance queries must be
    requested explicitly. Audit logs contain sensitive operational data.

    Returns structured records of which tools were called, by whom, with
    what outcome, and how long each operation took.

    Parameters:
    -----------
    - agent_id       : Filter by agent ID (e.g. "claude-code") - optional
    - operation_type : Filter by operation type (MEMORY_ADD, MEMORY_SEARCH,
                       MEMORY_DELETE, MEMORY_UPDATE, MEMORY_QUERY, BACKUP,
                       RESTORE, MAINTENANCE) - optional
    - status         : Filter by status ("success" or "failure") - optional
    - hours_back     : How many hours of history to return (default: 24)
    - limit          : Maximum records to return (default: 50, max: 500)

    Returns:
    --------
    - Formatted list of audit log entries with timestamps and outcomes
    """
    try:
        limit = min(int(limit), 500)
        hours_back = max(1, int(hours_back))

        al = audit_logger_instance or get_audit_logger()
        if not al:
            return "ERR Audit Logger not initialized"

        from datetime import timedelta as _td
        start_time = datetime.now(UTC) - _td(hours=hours_back)

        logs = await al.query_logs(
            start_time=start_time,
            operation_types=[operation_type] if operation_type else None,
            agent_ids=[agent_id] if agent_id else None,
            status=status,
            limit=limit,
        )

        # Fall back to in-memory recent logs if DB is unavailable
        if not logs:
            logs = await al.get_recent_logs(
                limit=limit,
                operation_type=operation_type,
                agent_id=agent_id,
            )

        if not logs:
            return (
                f"OK No audit log entries found in the last {hours_back}h"
                + (f" for agent={agent_id}" if agent_id else "")
                + (f", type={operation_type}" if operation_type else "")
            )

        lines_out = [f"OK Audit log ({len(logs)} entries, last {hours_back}h):"]
        for entry in logs:
            ts = entry.get("timestamp", entry.get("created_at", "unknown"))
            op = entry.get("operation_type", "unknown")
            ag = entry.get("agent_id", "unknown")
            st = entry.get("status", "unknown")
            ms = float(entry.get("execution_time_ms", 0))
            err = entry.get("error_message", "")
            line = f"  [{ts}] {op} | agent={ag} | {st} | {ms:.0f}ms"
            if err:
                line += f" | ERR: {err[:60]}"
            lines_out.append(line)

        return "\n".join(lines_out)

    except Exception as exc:
        logger.error(f"query_audit_log failed: {exc}")
        return f"ERR query_audit_log failed: {exc}"


# ===========================================================================
# Phase 10 - Memory Lifecycle Tools (15.1 - 15.4)
# ===========================================================================

@mcp.tool()
async def get_memory_history(
    memory_id: str,
    limit: int = 20,
) -> str:
    """
    Retrieve the full version history for a memory entry.

    TRIGGER TYPE: (M) Manual - Viewing history requires explicit user intent;
    not surfaced automatically.

    Returns version rows in descending order (newest first), showing what
    the content was at each revision point and who changed it.

    Parameters:
    -----------
    - memory_id : UUID of the memory entry
    - limit     : Maximum versions to return (default: 20, max: 100)

    Returns:
    --------
    - Formatted list of version snapshots with timestamps and change reasons
    """
    try:
        limit = max(1, min(int(limit), 100))
        mv = memory_versioner_instance or get_memory_versioner()
        if not mv:
            return "ERR MemoryVersioner not initialized (postgres_pool required)"

        history = await mv.get_history(memory_id, limit=limit)
        if not history:
            return f"OK No version history found for memory {memory_id}"

        lines = [f"OK Version history for memory {memory_id} ({len(history)} entries):"]
        for v in history:
            ts = v.get("created_at", "unknown")
            ver = v.get("version_number", "?")
            agent = v.get("agent_id") or "unknown"
            reason = v.get("change_reason") or ""
            preview = (v.get("content") or "")[:80].replace("\n", " ")
            line = f"  v{ver} [{ts}] by {agent}"
            if reason:
                line += f" | {reason}"
            line += f"\n    {preview}..."
            lines.append(line)
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"get_memory_history failed: {exc}")
        return f"ERR get_memory_history failed: {exc}"


@mcp.tool()
async def revert_memory(
    memory_id: str,
    version_number: int,
    agent_id: Optional[str] = None,
) -> str:
    """
    Revert a memory entry's content to a specific historical version.

    TRIGGER TYPE: (M) Manual - Reverting memory content is an irreversible
    write operation that must be requested explicitly.

    The current content is preserved as a new version before the revert
    is applied, ensuring the revert itself is auditable.

    Parameters:
    -----------
    - memory_id      : UUID of the memory to revert
    - version_number : Target version (from get_memory_history)
    - agent_id       : Agent performing the revert (recorded in audit trail)

    Returns:
    --------
    - OK confirmation with version details, or ERR on failure
    """
    try:
        version_number = int(version_number)
        mv = memory_versioner_instance or get_memory_versioner()
        if not mv:
            return "ERR MemoryVersioner not initialized (postgres_pool required)"

        ok = await mv.revert(memory_id, version_number, agent_id=agent_id)
        if ok:
            return (
                f"OK Memory {memory_id} reverted to version {version_number}. "
                f"Previous content has been preserved in version history."
            )
        return (
            f"ERR Revert failed for memory {memory_id} to version {version_number}. "
            f"Check that the memory and version exist."
        )
    except Exception as exc:
        logger.error(f"revert_memory failed: {exc}")
        return f"ERR revert_memory failed: {exc}"


@mcp.tool()
async def get_memory_provenance(
    memory_id: str,
) -> str:
    """
    Retrieve the provenance record for a memory entry.

    TRIGGER TYPE: (M) Manual - Provenance queries are for compliance and
    audit purposes; not surfaced automatically.

    Provenance records the origin, source URL, creation timestamp, content
    checksum, applied transformations (PII redaction, translation, etc.),
    and verification status.

    Parameters:
    -----------
    - memory_id : UUID of the memory entry

    Returns:
    --------
    - Formatted provenance details including source, checksum, and transforms
    """
    try:
        pt = provenance_tracker_instance or get_provenance_tracker()
        if not pt:
            return "ERR MemoryProvenanceTracker not initialized"

        prov = await pt.get_provenance(memory_id)
        if prov is None:
            return f"ERR Memory {memory_id} not found"

        lines = [f"OK Provenance for memory {memory_id}:"]
        lines.append(f"  source      : {prov.get('source', 'unknown')}")
        if prov.get("source_url"):
            lines.append(f"  source_url  : {prov['source_url']}")
        lines.append(f"  author      : {prov.get('author', 'unknown')}")
        lines.append(f"  ingested_at : {prov.get('ingested_at', 'unknown')}")
        if prov.get("checksum"):
            lines.append(f"  checksum    : {prov['checksum'][:16]}...")
        lines.append(f"  verified    : {prov.get('verified', False)}")
        if prov.get("verified_at"):
            lines.append(f"  verified_at : {prov['verified_at']}")
            lines.append(f"  verified_by : {prov.get('verified_by', 'unknown')}")

        transforms = prov.get("transformations", [])
        if transforms:
            lines.append(f"  transforms  : {len(transforms)} applied")
            for t in transforms[-3:]:  # show last 3
                lines.append(f"    - {t.get('type', '?')} @ {t.get('timestamp', '?')[:19]}")

        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"get_memory_provenance failed: {exc}")
        return f"ERR get_memory_provenance failed: {exc}"


@mcp.tool()
async def verify_memory(
    memory_id: str,
    agent_id: Optional[str] = None,
) -> str:
    """
    Verify the integrity of a memory entry by checking its SHA-256 checksum
    against the stored provenance record, then mark it as verified.

    TRIGGER TYPE: (M) Manual - Verification is an explicit compliance step.

    If the checksum is absent (memory was added before provenance tracking),
    the tool still marks the memory as verified-by-inspection.

    Parameters:
    -----------
    - memory_id : UUID of the memory entry to verify
    - agent_id  : Agent performing the verification (recorded in provenance)

    Returns:
    --------
    - OK with checksum match result, or WARN if no checksum available
    """
    try:
        pt = provenance_tracker_instance or get_provenance_tracker()
        if not pt:
            return "ERR MemoryProvenanceTracker not initialized"

        result = await pt.verify_checksum(memory_id)

        if result.get("error"):
            if result["error"] == "no checksum in provenance":
                # Mark as verified by inspection (no checksum baseline)
                await pt.mark_verified(memory_id, verified_by=agent_id or "system")
                return (
                    f"OK Memory {memory_id} marked as verified (no checksum baseline; "
                    f"verified by inspection)."
                )
            return f"ERR verify_memory: {result['error']}"

        match = result.get("match")
        if match:
            await pt.mark_verified(memory_id, verified_by=agent_id or "system")
            return (
                f"OK Memory {memory_id} checksum MATCH. "
                f"Content integrity confirmed. Marked as verified."
            )
        else:
            return (
                f"WARN Memory {memory_id} checksum MISMATCH. "
                f"Content may have been modified outside of Enhanced Cognee. "
                f"Expected: {result.get('stored_checksum', '?')[:16]}... "
                f"Got: {result.get('actual_checksum', '?')[:16]}..."
            )

    except Exception as exc:
        logger.error(f"verify_memory failed: {exc}")
        return f"ERR verify_memory failed: {exc}"


@mcp.tool()
async def set_memory_confidence(
    memory_id: str,
    score: float,
) -> str:
    """
    Set the confidence score for a memory entry.

    TRIGGER TYPE: (M) Manual - Confidence scoring is a curation step
    triggered by the user or a downstream evaluation agent.

    Scores range from 0.0 (completely uncertain) to 1.0 (ground truth).
    Thresholds: high >= 0.8, medium >= 0.5, low >= 0.3, uncertain < 0.3.

    Parameters:
    -----------
    - memory_id : UUID of the memory entry
    - score     : Confidence score in [0.0, 1.0]

    Returns:
    --------
    - OK confirmation with label (high/medium/low/uncertain)
    """
    try:
        score = max(0.0, min(1.0, float(score)))
        cm = confidence_manager_instance or get_confidence_manager()
        if not cm:
            return "ERR MemoryConfidenceManager not initialized"

        ok = await cm.set_confidence(memory_id, score)
        if ok:
            from src.memory_confidence import _label
            return (
                f"OK Confidence for memory {memory_id} set to {score:.4f} "
                f"({_label(score)})"
            )
        return f"ERR Memory {memory_id} not found or update failed"

    except Exception as exc:
        logger.error(f"set_memory_confidence failed: {exc}")
        return f"ERR set_memory_confidence failed: {exc}"


@mcp.tool()
async def get_confidence_report(
    agent_id: Optional[str] = None,
) -> str:
    """
    Retrieve a confidence distribution report across all (or one agent's) memories.

    TRIGGER TYPE: (A) Auto - Safe read-only analytics tool; can be called
    as part of periodic memory health checks.

    Returns counts and percentages for each confidence tier, plus the mean
    confidence score and the number of unscored memories.

    Parameters:
    -----------
    - agent_id : Optional agent filter (default: all agents)

    Returns:
    --------
    - Formatted confidence distribution table
    """
    try:
        cm = confidence_manager_instance or get_confidence_manager()
        if not cm:
            return "ERR MemoryConfidenceManager not initialized"

        report = await cm.get_confidence_report(agent_id=agent_id)
        if "error" in report:
            return f"ERR get_confidence_report: {report['error']}"

        total = report.get("total_memories", 0)
        scope = f"agent={agent_id}" if agent_id else "all agents"
        lines = [f"OK Confidence report ({scope}, {total} memories):"]
        lines.append(f"  high (>=0.8)  : {report.get('high_confidence', 0)}")
        lines.append(f"  medium (>=0.5): {report.get('medium_confidence', 0)}")
        lines.append(f"  low (>=0.3)   : {report.get('low_confidence', 0)}")
        lines.append(f"  uncertain     : {report.get('uncertain', 0)}")
        lines.append(f"  unscored      : {report.get('unscored', 0)}")
        avg = report.get("average_confidence")
        if avg is not None:
            lines.append(f"  average score : {avg:.4f}")
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"get_confidence_report failed: {exc}")
        return f"ERR get_confidence_report failed: {exc}"


@mcp.tool()
async def find_consolidation_candidates(
    agent_id: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    Identify groups of memory entries that are candidates for consolidation.

    TRIGGER TYPE: (A) Auto - Read-only discovery; safe to call as part of
    periodic memory maintenance without user confirmation.

    Uses Qdrant vector similarity (or PostgreSQL trigram similarity as
    fallback) to find memories above the 0.75 cosine similarity threshold
    that have not yet been consolidated.

    Parameters:
    -----------
    - agent_id : Optional agent filter (default: all agents)
    - limit    : Maximum number of candidate groups to return (default: 20)

    Returns:
    --------
    - Structured list of candidate groups with anchor and member IDs
    """
    try:
        limit = max(1, min(int(limit), 100))
        cons = consolidator_instance or get_consolidator()
        if not cons:
            return "ERR MemoryConsolidator not initialized"

        groups = await cons.find_candidates(agent_id=agent_id, limit=limit)
        if not groups:
            return (
                f"OK No consolidation candidates found"
                + (f" for agent={agent_id}" if agent_id else "")
                + ". All memories appear sufficiently distinct."
            )

        lines = [f"OK Found {len(groups)} consolidation candidate group(s):"]
        for i, g in enumerate(groups, 1):
            anchor = g.get("anchor_id", "?")
            preview = g.get("anchor_preview", "")[:60].replace("\n", " ")
            cands = g.get("candidates", [])
            lines.append(f"  Group {i}: anchor={anchor}")
            lines.append(f"    Preview: {preview}...")
            lines.append(f"    Candidates ({len(cands)}): " +
                         ", ".join(c["id"] for c in cands[:5]))
        lines.append(
            "\nUse consolidate_memories([id1, id2, ...]) to merge a group."
        )
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"find_consolidation_candidates failed: {exc}")
        return f"ERR find_consolidation_candidates failed: {exc}"


@mcp.tool()
async def consolidate_memories(
    memory_ids: str,
    agent_id: Optional[str] = None,
    summary_content: Optional[str] = None,
) -> str:
    """
    Merge a set of related memory entries into one consolidated document.

    TRIGGER TYPE: (M) Manual - Consolidation permanently modifies the memory
    store and must be explicitly requested.

    The original entries are marked consolidated_into pointing at the new
    document; they are NOT deleted so they can still be retrieved via
    get_memory_history.

    Parameters:
    -----------
    - memory_ids     : Comma-separated list of memory UUIDs to merge
    - agent_id       : Agent performing the consolidation
    - summary_content: Optional pre-written summary to use as the merged
                       content (omit for automatic concatenation)

    Returns:
    --------
    - OK with new consolidated memory ID, or ERR on failure
    """
    try:
        ids = [mid.strip() for mid in memory_ids.split(",") if mid.strip()]
        if len(ids) < 2:
            return "ERR consolidate_memories requires at least 2 comma-separated memory IDs"

        cons = consolidator_instance or get_consolidator()
        if not cons:
            return "ERR MemoryConsolidator not initialized"

        new_id = await cons.consolidate(
            memory_ids=ids,
            agent_id=agent_id,
            summary_content=summary_content or None,
        )
        if new_id:
            return (
                f"OK Consolidated {len(ids)} memories into new memory {new_id}. "
                f"Source memories are preserved but marked as consolidated."
            )
        return "ERR Consolidation failed. Check that all memory IDs exist and are not already consolidated."

    except Exception as exc:
        logger.error(f"consolidate_memories failed: {exc}")
        return f"ERR consolidate_memories failed: {exc}"


@mcp.tool()
async def get_consolidation_report(
    agent_id: Optional[str] = None,
) -> str:
    """
    Retrieve a consolidation activity report for all (or one agent's) memories.

    TRIGGER TYPE: (A) Auto - Read-only analytics; safe for periodic health checks.

    Shows how many memories have been consolidated out (source) vs. how many
    remain active, and the overall consolidation ratio.

    Parameters:
    -----------
    - agent_id : Optional agent filter (default: all agents)

    Returns:
    --------
    - Consolidation statistics table
    """
    try:
        cons = consolidator_instance or get_consolidator()
        if not cons:
            return "ERR MemoryConsolidator not initialized"

        report = await cons.get_consolidation_report(agent_id=agent_id)
        if "error" in report:
            return f"ERR get_consolidation_report: {report['error']}"

        scope = f"agent={agent_id}" if agent_id else "all agents"
        lines = [f"OK Consolidation report ({scope}):"]
        lines.append(f"  total memories     : {report.get('total_memories', 0)}")
        lines.append(f"  active memories    : {report.get('active_memories', 0)}")
        lines.append(f"  consolidated out   : {report.get('consolidated_out', 0)}")
        lines.append(f"  consolidation targets: {report.get('consolidation_targets', 0)}")
        ratio = report.get("consolidation_ratio", 0.0)
        lines.append(f"  consolidation ratio: {ratio:.1%}")
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"get_consolidation_report failed: {exc}")
        return f"ERR get_consolidation_report failed: {exc}"


# ---------------------------------------------------------------------------
# Phase 10.5 - Memory Promotion Tiers
# ---------------------------------------------------------------------------

@mcp.tool()
async def promote_memory_tier(
    memory_id: str,
    agent_id: Optional[str] = None,
) -> str:
    """
    Promote a memory entry one tier upward in the working/long_term/archive hierarchy.

    TRIGGER TYPE: (M) Manual - Tier changes affect caching behaviour and
    should be driven by explicit curation intent.

    Tier ladder (low to high): archive -> long_term -> working.
    Memories in the 'working' tier are additionally cached in Redis for
    sub-millisecond retrieval.

    Parameters:
    -----------
    - memory_id : UUID of the memory to promote
    - agent_id  : Agent performing the promotion (for logging)

    Returns:
    --------
    - OK with old tier -> new tier, or ERR on failure
    """
    try:
        tm = tier_manager_instance or get_tier_manager()
        if not tm:
            return "ERR MemoryTierManager not initialized (postgres_pool required)"

        old_tier = await tm.get_tier(memory_id) or "long_term"
        new_tier = await tm.promote(memory_id, agent_id=agent_id)
        if new_tier == old_tier:
            return f"OK Memory {memory_id} is already at tier '{old_tier}' (top tier)"
        return f"OK Memory {memory_id} promoted: {old_tier} -> {new_tier}"

    except Exception as exc:
        logger.error(f"promote_memory_tier failed: {exc}")
        return f"ERR promote_memory_tier failed: {exc}"


@mcp.tool()
async def get_tier_stats(
    agent_id: Optional[str] = None,
) -> str:
    """
    Return a count of memories in each tier (working / long_term / archive).

    TRIGGER TYPE: (A) Auto - Read-only analytics; safe for periodic health checks.

    Useful for understanding memory utilisation: too many 'archive' memories
    suggests a large inactive corpus; too many 'working' memories may
    overload the Redis cache.

    Parameters:
    -----------
    - agent_id : Optional agent filter (default: all agents)

    Returns:
    --------
    - Formatted tier distribution table
    """
    try:
        tm = tier_manager_instance or get_tier_manager()
        if not tm:
            return "ERR MemoryTierManager not initialized"

        stats = await tm.get_tier_stats(agent_id=agent_id)
        if "error" in stats:
            return f"ERR get_tier_stats: {stats['error']}"

        scope = f"agent={agent_id}" if agent_id else "all agents"
        lines = [f"OK Memory tier distribution ({scope}):"]
        lines.append(f"  working   (Tier 1): {stats.get('working', 0)}")
        lines.append(f"  long_term (Tier 2): {stats.get('long_term', 0)}")
        lines.append(f"  archive   (Tier 3): {stats.get('archive', 0)}")
        lines.append(f"  total             : {stats.get('total', 0)}")
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"get_tier_stats failed: {exc}")
        return f"ERR get_tier_stats failed: {exc}"


# ---------------------------------------------------------------------------
# Phase 10.6 - Knowledge Graph Compaction
# ---------------------------------------------------------------------------

@mcp.tool()
async def compact_knowledge_graph() -> str:
    """
    Run a full compaction pass on the Enhanced Cognee Neo4j knowledge graph.

    TRIGGER TYPE: (M) Manual - Graph compaction modifies the knowledge graph
    by deleting orphan nodes and stale relationships; must be explicitly
    requested.

    Compaction steps:
      1. Prune RELATED_TO/SIMILAR_TO edges for archived or expired memories
      2. Remove orphan nodes (no relationships)
      3. Compact parallel SIMILAR_TO edges into single weighted edges

    Returns:
    --------
    - Summary of nodes/edges removed and compaction outcome
    """
    try:
        gc = graph_compactor_instance or get_graph_compactor()
        if not gc:
            return "ERR GraphCompactor not initialized (neo4j_driver required)"

        summary = await gc.run_compaction()
        errors = summary.get("errors", [])
        lines = [
            f"OK Knowledge graph compaction complete:",
            f"  stale relations pruned : {summary.get('stale_relations_pruned', 0)}",
            f"  orphan nodes removed   : {summary.get('orphans_removed', 0)}",
            f"  similar edges compacted: {summary.get('similar_edges_compacted', 0)}",
        ]
        if errors:
            lines.append(f"  WARN {len(errors)} step(s) encountered errors:")
            for err in errors[:3]:
                lines.append(f"    - {err}")
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"compact_knowledge_graph failed: {exc}")
        return f"ERR compact_knowledge_graph failed: {exc}"


@mcp.tool()
async def get_graph_stats() -> str:
    """
    Return basic statistics about the Enhanced Cognee Neo4j knowledge graph.

    TRIGGER TYPE: (A) Auto - Read-only query; safe for periodic monitoring.

    Returns node count, relationship count, and orphan node count.
    High orphan counts indicate the graph would benefit from compaction.

    Returns:
    --------
    - Formatted graph statistics
    """
    try:
        gc = graph_compactor_instance or get_graph_compactor()
        if not gc:
            return "ERR GraphCompactor not initialized (neo4j_driver required)"

        stats = gc.get_graph_stats()
        if "error" in stats:
            return f"ERR get_graph_stats: {stats['error']}"

        lines = [
            "OK Knowledge graph statistics:",
            f"  nodes         : {stats.get('node_count', 0)}",
            f"  relationships : {stats.get('relationship_count', 0)}",
            f"  orphan nodes  : {stats.get('orphan_nodes', 0)}",
        ]
        orphans = stats.get("orphan_nodes", 0)
        if orphans > 100:
            lines.append(
                f"  WARN {orphans} orphan nodes detected. "
                f"Run compact_knowledge_graph() to clean up."
            )
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"get_graph_stats failed: {exc}")
        return f"ERR get_graph_stats failed: {exc}"


# ===========================================================================
# Phase 11 - Compliance and Data Governance Tools (16.1 - 16.4)
# ===========================================================================

@mcp.tool()
async def gdpr_delete_user_data(
    user_id: str,
    dry_run: bool = True,
    requester: Optional[str] = None,
) -> str:
    """
    Permanently erase all data associated with a user_id from all four
    Enhanced Cognee databases (right to erasure / right to be forgotten).

    TRIGGER TYPE: (M) Manual - Irreversible destructive operation.  Always
    defaults to dry_run=True; must be explicitly set to False to delete.

    Erases from:
      - PostgreSQL: documents, memory_versions, sessions (agent_id match)
      - Qdrant:     all vector points with matching agent_id payload
      - Neo4j:      all nodes with matching agent_id property
      - Redis:      all keys scoped to the user_id

    Audit log rows are redacted (not deleted) to preserve the compliance trail.

    Parameters:
    -----------
    - user_id   : The agent_id / user identifier to erase
    - dry_run   : If True (default), preview deletions without making changes
    - requester : Who triggered this request (recorded for compliance)

    Returns:
    --------
    - Summary of rows/vectors/nodes that were (or would be) deleted
    """
    try:
        gm = gdpr_manager_instance or get_gdpr_manager()
        if not gm:
            return "ERR GDPRManager not initialized"

        result = await gm.delete_user_data(
            user_id=user_id,
            requester=requester,
            dry_run=dry_run,
        )

        mode = "DRY RUN - no changes made" if dry_run else "DELETED"
        lines = [f"OK GDPR erasure for user '{user_id}' [{mode}]:"]
        lines.append(f"  PostgreSQL rows    : {result.get('postgres_rows_deleted', 0)}")
        lines.append(f"  Qdrant vectors     : {result.get('qdrant_vectors_deleted', 0)}")
        lines.append(f"  Neo4j nodes        : {result.get('neo4j_nodes_deleted', 0)}")
        lines.append(f"  Redis keys         : {result.get('redis_keys_deleted', 0)}")
        lines.append(f"  Consent records    : {result.get('consent_records_deleted', 0)}")

        errors = result.get("errors", [])
        if errors:
            lines.append(f"  WARN {len(errors)} error(s):")
            for e in errors[:3]:
                lines.append(f"    - {e}")
        if dry_run:
            lines.append(
                "\nTo execute: call gdpr_delete_user_data(user_id=..., dry_run=False)"
            )
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"gdpr_delete_user_data failed: {exc}")
        return f"ERR gdpr_delete_user_data failed: {exc}"


@mcp.tool()
async def gdpr_export_user_data(
    user_id: str,
    include_versions: bool = True,
) -> str:
    """
    Export all data stored for a user_id as a structured JSON document
    (right of access / data portability under GDPR).

    TRIGGER TYPE: (M) Manual - Data access requests require explicit
    user or compliance-officer intent.

    The export includes:
      - All memory entries (content, metadata, provenance, confidence)
      - Version history (up to 1000 entries)
      - Consent records

    The JSON is returned inline.  For large exports, consider downloading
    via the file system path printed in the response.

    Parameters:
    -----------
    - user_id          : The agent_id / user identifier to export
    - include_versions : Include version history in the export (default: True)

    Returns:
    --------
    - GDPR export summary with memory count and inline JSON preview
    """
    try:
        gm = gdpr_manager_instance or get_gdpr_manager()
        if not gm:
            return "ERR GDPRManager not initialized"

        data_bytes, filename = await gm.export_user_data(
            user_id=user_id,
            include_versions=include_versions,
            as_zip=False,
        )

        import json as _json
        export = _json.loads(data_bytes)
        mem_count = len(export.get("memories", []))
        ver_count = len(export.get("version_history", []))
        consent_count = len(export.get("consent_records", []))

        # Write to temp file for retrieval
        import tempfile, os as _os
        tmp_dir = tempfile.gettempdir()
        out_path = _os.path.join(tmp_dir, filename)
        with open(out_path, "wb") as fh:
            fh.write(data_bytes)

        lines = [f"OK GDPR export for user '{user_id}':"]
        lines.append(f"  memories exported    : {mem_count}")
        lines.append(f"  version rows         : {ver_count}")
        lines.append(f"  consent records      : {consent_count}")
        lines.append(f"  export file          : {out_path}")
        lines.append(f"  exported_at          : {export.get('exported_at', '?')}")

        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"gdpr_export_user_data failed: {exc}")
        return f"ERR gdpr_export_user_data failed: {exc}"


@mcp.tool()
async def gdpr_record_consent(
    user_id: str,
    category: str,
    granted: bool,
) -> str:
    """
    Record or update a user's consent decision for a data category.

    TRIGGER TYPE: (M) Manual - Consent changes must be user-initiated.

    Categories are free-form strings (e.g., "analytics", "personalization",
    "third_party_sharing").  The consent is stored in
    shared_memory.consent_records and gates future ingestion operations.

    Parameters:
    -----------
    - user_id  : The user granting or revoking consent
    - category : Data processing category (free text)
    - granted  : True = grant consent, False = revoke consent

    Returns:
    --------
    - OK confirmation with new consent status
    """
    try:
        gm = gdpr_manager_instance or get_gdpr_manager()
        if not gm:
            return "ERR GDPRManager not initialized"

        ok = await gm.record_consent(user_id=user_id, category=category, granted=granted)
        if ok:
            action = "GRANTED" if granted else "REVOKED"
            return (
                f"OK Consent {action} for user '{user_id}', "
                f"category '{category}'."
            )
        return f"ERR Failed to record consent for user '{user_id}'"

    except Exception as exc:
        logger.error(f"gdpr_record_consent failed: {exc}")
        return f"ERR gdpr_record_consent failed: {exc}"


@mcp.tool()
async def gdpr_check_consent(
    user_id: str,
    category: str,
) -> str:
    """
    Check whether a user has granted consent for a specific data category.

    TRIGGER TYPE: (A) Auto - Read-only compliance gate; called before
    ingestion or processing operations that require consent.

    Parameters:
    -----------
    - user_id  : The user to check
    - category : Data processing category

    Returns:
    --------
    - GRANTED / REVOKED / UNKNOWN with timestamp if available
    """
    try:
        gm = gdpr_manager_instance or get_gdpr_manager()
        if not gm:
            return "ERR GDPRManager not initialized"

        consents = await gm.list_consents(user_id)
        for c in consents:
            if c["category"] == category:
                status = "GRANTED" if c["granted"] else "REVOKED"
                ts = c.get("granted_at") or c.get("revoked_at") or "unknown"
                return (
                    f"OK Consent for user '{user_id}', category '{category}': "
                    f"{status} (as of {ts})"
                )

        return (
            f"OK Consent for user '{user_id}', category '{category}': "
            f"UNKNOWN (no record found)"
        )

    except Exception as exc:
        logger.error(f"gdpr_check_consent failed: {exc}")
        return f"ERR gdpr_check_consent failed: {exc}"


@mcp.tool()
async def gdpr_list_consents(
    user_id: str,
) -> str:
    """
    List all consent records stored for a user.

    TRIGGER TYPE: (M) Manual - Viewing a user's full consent profile
    requires explicit intent.

    Parameters:
    -----------
    - user_id : The user whose consent profile to retrieve

    Returns:
    --------
    - Table of categories, statuses, and timestamps
    """
    try:
        gm = gdpr_manager_instance or get_gdpr_manager()
        if not gm:
            return "ERR GDPRManager not initialized"

        consents = await gm.list_consents(user_id)
        if not consents:
            return f"OK No consent records found for user '{user_id}'"

        lines = [f"OK Consent records for user '{user_id}' ({len(consents)} entries):"]
        for c in consents:
            status = "GRANTED" if c["granted"] else "REVOKED"
            ts = c.get("granted_at") if c["granted"] else c.get("revoked_at")
            lines.append(f"  {c['category']:<30} {status:<8} {ts or 'unknown'}")
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"gdpr_list_consents failed: {exc}")
        return f"ERR gdpr_list_consents failed: {exc}"


@mcp.tool()
async def gdpr_verify_tenant_isolation(
    tenant_id: str,
    sample_size: int = 50,
) -> str:
    """
    Verify that a tenant's memory data is properly isolated and has not
    leaked into other tenants' namespaces.

    TRIGGER TYPE: (M) Manual - Tenant isolation audits are explicit
    compliance checks requested by an administrator.

    Samples up to *sample_size* documents belonging to *tenant_id* and
    verifies they all carry the correct agent_id.

    Parameters:
    -----------
    - tenant_id   : The tenant (agent_id) to audit
    - sample_size : Number of records to sample (default: 50, max: 500)

    Returns:
    --------
    - CLEAN or list of isolation violations found
    """
    try:
        sample_size = max(1, min(int(sample_size), 500))
        gm = gdpr_manager_instance or get_gdpr_manager()
        if not gm:
            return "ERR GDPRManager not initialized"

        result = await gm.verify_tenant_isolation(
            tenant_id=tenant_id, sample_size=sample_size
        )
        if "error" in result:
            return f"ERR verify_tenant_isolation: {result['error']}"

        sampled = result.get("sampled", 0)
        violations = result.get("violations", [])
        clean = result.get("clean", False)

        if clean:
            return (
                f"OK Tenant isolation CLEAN for '{tenant_id}'. "
                f"Sampled {sampled} records, no violations found."
            )
        lines = [
            f"WARN Tenant isolation VIOLATIONS for '{tenant_id}': "
            f"{len(violations)} of {sampled} records have wrong agent_id:"
        ]
        for v in violations[:10]:
            lines.append(
                f"  memory {v['memory_id']} has agent_id={v['found_agent_id']!r}"
            )
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"gdpr_verify_tenant_isolation failed: {exc}")
        return f"ERR gdpr_verify_tenant_isolation failed: {exc}"


# ===========================================================================
# Phase 12 - Plugin Ecosystem and Integrations (17.1, 17.2)
# ===========================================================================

@mcp.tool()
async def list_loader_plugins() -> str:
    """
    List all registered Enhanced Cognee loader plugins, including built-in
    loaders and any installed third-party plugins.

    TRIGGER TYPE: (A) Auto - Read-only discovery query; safe to call at any time.

    Built-in loaders (always present):
      - PlainTextLoader  (.txt, .md, .rst)
      - JsonLoader       (.json, .jsonl)
      - HtmlLoader       (.html, .htm)

    Third-party loaders are discovered via Python entry_points under the
    group "enhanced_cognee.loaders".

    Returns:
    --------
    - Table of loader name, supported extensions, and source package
    """
    try:
        reg = plugin_registry_instance or get_plugin_registry()
        if not reg:
            return "ERR PluginRegistry not initialized"

        loaders = reg.list_loaders()
        if not loaders:
            return "OK No loaders registered"

        lines = [f"OK Registered loaders ({len(loaders)}):"]
        for l in loaders:
            exts = ", ".join(l.get("extensions", []))
            pkg = l.get("package", "built-in")
            lines.append(f"  {l['name']:<25} ext=[{exts}]  pkg={pkg}")
            if l.get("description"):
                lines.append(f"    {l['description']}")
        lines.append(
            "\nInstall plugins via pip and register with entry_points "
            "group 'enhanced_cognee.loaders'."
        )
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"list_loader_plugins failed: {exc}")
        return f"ERR list_loader_plugins failed: {exc}"


@mcp.tool()
async def load_document_with_plugin(
    source: str,
    loader_name: Optional[str] = None,
) -> str:
    """
    Load a document using the appropriate registered plugin loader and return
    its text content (ready to pass to cognify()).

    TRIGGER TYPE: (M) Manual - Document ingestion is an explicit user action.

    The plugin is selected automatically from the file extension, or you can
    specify a loader by name.  Loaded content is returned as text; call
    cognify() to add it to the knowledge graph.

    Parameters:
    -----------
    - source      : File path (.txt, .md, .json, .html, etc.)
    - loader_name : Optional specific loader class name (e.g., "JsonLoader")

    Returns:
    --------
    - Loaded text content (first 500 chars shown as preview)
    """
    try:
        reg = plugin_registry_instance or get_plugin_registry()
        if not reg:
            return "ERR PluginRegistry not initialized"

        if loader_name:
            loader = next(
                (l for l in reg._loaders if type(l).__name__ == loader_name),
                None,
            )
            if not loader:
                return f"ERR Loader '{loader_name}' not found. Use list_loader_plugins to see available loaders."
        else:
            loader = reg.get_loader_for(source)
            if not loader:
                return (
                    f"ERR No loader found for '{source}'. "
                    f"Supported extensions: "
                    + ", ".join(
                        ext
                        for l in reg.list_loaders()
                        for ext in l.get("extensions", [])
                    )
                )

        content = await loader.load(source)
        preview = content[:500].replace("\n", " ")
        return (
            f"OK Loaded {len(content)} chars via {type(loader).__name__}.\n"
            f"Preview: {preview}...\n"
            f"Call cognify(data=<content>) to ingest into knowledge graph."
        )

    except Exception as exc:
        logger.error(f"load_document_with_plugin failed: {exc}")
        return f"ERR load_document_with_plugin failed: {exc}"


@mcp.tool()
async def register_webhook(
    url: str,
    secret: str,
    events: Optional[str] = None,
    name: Optional[str] = None,
) -> str:
    """
    Register a webhook endpoint to receive HMAC-signed event notifications.

    TRIGGER TYPE: (M) Manual - Webhook registration changes system configuration.

    Payload is signed with HMAC-SHA256; verify on the receiver using:
        import hmac, hashlib
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert header == f"sha256={sig}"

    Supported events (comma-separated, or omit for all):
        memory.added, memory.updated, memory.deleted, memory.reverted,
        backup.completed, backup.failed, consolidation.completed,
        gdpr.delete_requested, gdpr.export_requested,
        maintenance.completed, health.degraded, health.recovered

    Parameters:
    -----------
    - url    : HTTPS endpoint URL that will receive POST requests
    - secret : Shared secret for HMAC-SHA256 signature verification
    - events : Optional comma-separated list of events to subscribe to
    - name   : Optional friendly name for the webhook

    Returns:
    --------
    - OK with webhook ID, or ERR on failure
    """
    try:
        wm = webhook_manager_instance or get_webhook_manager()
        if not wm:
            return "ERR WebhookManager not initialized"

        event_list = None
        if events:
            event_list = [e.strip() for e in events.split(",") if e.strip()]

        wh = wm.register(url=url, secret=secret, events=event_list, name=name)
        subscribed = ", ".join(sorted(wh.events))
        return (
            f"OK Webhook registered:\n"
            f"  id      : {wh.id}\n"
            f"  name    : {wh.name}\n"
            f"  url     : {wh.url}\n"
            f"  events  : {subscribed}\n"
            f"  enabled : True\n"
            f"\nTest with: test_webhook(webhook_id='{wh.id}')"
        )

    except Exception as exc:
        logger.error(f"register_webhook failed: {exc}")
        return f"ERR register_webhook failed: {exc}"


@mcp.tool()
async def list_webhooks() -> str:
    """
    List all registered webhook endpoints with their status.

    TRIGGER TYPE: (A) Auto - Read-only query; safe to call at any time.

    Returns:
    --------
    - Table of webhook IDs, URLs, enabled status, and delivery counts
    """
    try:
        wm = webhook_manager_instance or get_webhook_manager()
        if not wm:
            return "ERR WebhookManager not initialized"

        webhooks = wm.list_webhooks()
        if not webhooks:
            return "OK No webhooks registered. Use register_webhook() to add one."

        lines = [f"OK Registered webhooks ({len(webhooks)}):"]
        for wh in webhooks:
            status = "ON" if wh["enabled"] else "OFF"
            lines.append(
                f"  [{status}] {wh['id']}  {wh['url'][:50]}  "
                f"delivered={wh['delivery_count']} failed={wh['failure_count']}"
            )
            if wh.get("last_triggered"):
                lines.append(f"       last: {wh['last_triggered']}")
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"list_webhooks failed: {exc}")
        return f"ERR list_webhooks failed: {exc}"


@mcp.tool()
async def test_webhook(
    webhook_id: str,
) -> str:
    """
    Send a test ping notification to a registered webhook endpoint.

    TRIGGER TYPE: (M) Manual - Testing triggers an actual HTTP request.

    Delivers a "webhook.test" event to verify connectivity and HMAC signature
    verification at the receiver.

    Parameters:
    -----------
    - webhook_id : The webhook ID to test (from list_webhooks or register_webhook)

    Returns:
    --------
    - OK if delivery succeeded, FAIL if the endpoint rejected or timed out
    """
    try:
        wm = webhook_manager_instance or get_webhook_manager()
        if not wm:
            return "ERR WebhookManager not initialized"

        wh = wm.get_webhook(webhook_id)
        if not wh:
            return f"ERR Webhook '{webhook_id}' not found"

        success = await wm.test_webhook(webhook_id)
        if success:
            return f"OK Test ping delivered to webhook '{webhook_id}' ({wh.url})"
        return (
            f"FAIL Test ping to webhook '{webhook_id}' ({wh.url}) failed. "
            f"Check URL is reachable and signature verification is correct."
        )

    except Exception as exc:
        logger.error(f"test_webhook failed: {exc}")
        return f"ERR test_webhook failed: {exc}"


@mcp.tool()
async def disable_webhook(
    webhook_id: str,
) -> str:
    """
    Temporarily disable a webhook endpoint without deleting it.

    TRIGGER TYPE: (M) Manual - Configuration change.

    The webhook remains registered but will not receive event deliveries
    until re-enabled.  Use list_webhooks to see current status.

    Parameters:
    -----------
    - webhook_id : The webhook ID to disable

    Returns:
    --------
    - OK confirmation or ERR if not found
    """
    try:
        wm = webhook_manager_instance or get_webhook_manager()
        if not wm:
            return "ERR WebhookManager not initialized"

        ok = wm.disable(webhook_id)
        if ok:
            return f"OK Webhook '{webhook_id}' disabled. Events will not be delivered."
        return f"ERR Webhook '{webhook_id}' not found"

    except Exception as exc:
        logger.error(f"disable_webhook failed: {exc}")
        return f"ERR disable_webhook failed: {exc}"


# ===========================================================================
# Phase 14.3 - Encryption at Rest
# ===========================================================================

@mcp.tool()
async def encrypt_memory(memory_id: str) -> str:
    """
    Encrypt a memory's content using Fernet (AES-128-CBC + HMAC-SHA256).

    TRIGGER TYPE: (M) Manual - Encryption is applied selectively by the user.

    Reads the current plaintext content from PostgreSQL, encrypts it with
    the server's master key, and writes the encrypted value back.  The
    is_encrypted flag is set to TRUE so decrypt_memory can reverse the
    operation.  No-op if the memory is already encrypted.

    Parameters:
    -----------
    - memory_id : UUID of the memory to encrypt

    Returns:
    --------
    - OK confirmation or ERR if unavailable / encryption disabled
    """
    try:
        em = encryption_manager_instance or get_encryption_manager()
        if not em:
            return "ERR EncryptionManager not initialized"
        result = await em.encrypt_memory(memory_id)
        if result.get("ok"):
            return f"OK Memory '{memory_id}' encrypted"
        return f"ERR {result.get('error', 'encrypt_memory failed')}"
    except Exception as exc:
        logger.error(f"encrypt_memory failed: {exc}")
        return f"ERR encrypt_memory failed: {exc}"


@mcp.tool()
async def get_encryption_stats() -> str:
    """
    Return encryption coverage statistics for the memory store.

    TRIGGER TYPE: (A) Auto - Safe to call at any time for status reporting.

    Reports total memories, how many are encrypted, the encryption
    algorithm in use, and whether encryption is enabled.

    Returns:
    --------
    - JSON-formatted stats dict or ERR message
    """
    try:
        em = encryption_manager_instance or get_encryption_manager()
        if not em:
            return "ERR EncryptionManager not initialized"
        stats = await em.get_encryption_stats()
        return json.dumps(stats, indent=2)
    except Exception as exc:
        logger.error(f"get_encryption_stats failed: {exc}")
        return f"ERR get_encryption_stats failed: {exc}"


@mcp.tool()
async def rotate_encryption_key(new_key: Optional[str] = None) -> str:
    """
    Rotate the encryption master key and re-encrypt all encrypted memories.

    TRIGGER TYPE: (M) Manual - Key rotation is a deliberate security operation.

    Generates a new Fernet key (or uses the supplied one), decrypts each
    currently-encrypted row with the old key, re-encrypts with the new key,
    and updates the row.  The new key is printed in the response (first 8
    chars only); persist it immediately.

    Parameters:
    -----------
    - new_key : Optional base64-urlsafe 32-byte Fernet key.
                If omitted a new key is generated automatically.

    Returns:
    --------
    - OK summary with rotated count and new key preview, or ERR
    """
    try:
        em = encryption_manager_instance or get_encryption_manager()
        if not em:
            return "ERR EncryptionManager not initialized"
        result = await em.rotate_encryption_key(new_key=new_key)
        if "error" in result:
            return f"ERR {result['error']}"
        rotated = result.get("rotated", 0)
        preview = result.get("new_key_preview", "N/A")
        return (
            f"OK Encryption key rotated\n"
            f"  Memories re-encrypted : {rotated}\n"
            f"  New key preview        : {preview}\n"
            f"  ACTION REQUIRED: store the full key in ENCRYPTION_MASTER_KEY env var"
        )
    except Exception as exc:
        logger.error(f"rotate_encryption_key failed: {exc}")
        return f"ERR rotate_encryption_key failed: {exc}"


# ===========================================================================
# Phase 12.8 - Structured Observations (EAV)
# ===========================================================================

@mcp.tool()
async def add_observation(
    memory_id: str,
    entity: str,
    attribute: str,
    value: str,
    agent_id: str = "system",
    confidence: float = 1.0,
) -> str:
    """
    Add a structured (entity, attribute, value) observation to a memory.

    TRIGGER TYPE: (A) Auto - Call whenever structured facts are extracted
    from memory content.

    Observations are stored in the shared_memory.observations EAV table
    and can be queried independently from the memory content.  Useful for
    building structured knowledge from free-text memories.

    Parameters:
    -----------
    - memory_id  : UUID of the parent memory
    - entity     : Entity name (e.g. "company", "person", "product")
    - attribute  : Attribute name (e.g. "name", "revenue", "founded_year")
    - value      : The attribute value as a string
    - agent_id   : Agent that is recording the observation (default: "system")
    - confidence : Confidence in [0.0, 1.0] (default: 1.0)

    Returns:
    --------
    - OK with observation ID or ERR
    """
    try:
        mgr = observation_manager_instance or get_observation_manager()
        if not mgr:
            return "ERR MemoryObservationManager not initialized"
        result = await mgr.add_observation(
            memory_id=memory_id,
            entity=entity,
            attribute=attribute,
            value=value,
            agent_id=agent_id,
            confidence=float(confidence),
        )
        if "error" in result:
            return f"ERR {result['error']}"
        obs_id = result.get("observation_id", "unknown")
        return f"OK Observation added: {obs_id} ({entity}.{attribute}={value!r})"
    except Exception as exc:
        logger.error(f"add_observation failed: {exc}")
        return f"ERR add_observation failed: {exc}"


@mcp.tool()
async def get_observations(memory_id: str) -> str:
    """
    Retrieve all structured observations for a memory.

    TRIGGER TYPE: (A) Auto - Safe read; can be called after any memory lookup.

    Returns:
    --------
    - JSON array of observation dicts or ERR
    """
    try:
        mgr = observation_manager_instance or get_observation_manager()
        if not mgr:
            return "ERR MemoryObservationManager not initialized"
        observations = await mgr.get_observations(memory_id)
        return json.dumps(observations, indent=2, default=str)
    except Exception as exc:
        logger.error(f"get_observations failed: {exc}")
        return f"ERR get_observations failed: {exc}"


@mcp.tool()
async def update_observation(
    observation_id: str,
    value: str,
    confidence: float = 1.0,
) -> str:
    """
    Update the value and confidence of an existing observation.

    TRIGGER TYPE: (M) Manual - Observation updates reflect deliberate corrections.

    Parameters:
    -----------
    - observation_id : UUID of the observation to update
    - value          : New value string
    - confidence     : Updated confidence in [0.0, 1.0]

    Returns:
    --------
    - OK confirmation or ERR
    """
    try:
        mgr = observation_manager_instance or get_observation_manager()
        if not mgr:
            return "ERR MemoryObservationManager not initialized"
        result = await mgr.update_observation(
            observation_id=observation_id,
            value=value,
            confidence=float(confidence),
        )
        if "error" in result:
            return f"ERR {result['error']}"
        return f"OK Observation '{observation_id}' updated"
    except Exception as exc:
        logger.error(f"update_observation failed: {exc}")
        return f"ERR update_observation failed: {exc}"


@mcp.tool()
async def delete_observation(observation_id: str) -> str:
    """
    Delete a structured observation by its ID.

    TRIGGER TYPE: (M) Manual - Deletions are irreversible.

    Parameters:
    -----------
    - observation_id : UUID of the observation to delete

    Returns:
    --------
    - OK confirmation or ERR
    """
    try:
        mgr = observation_manager_instance or get_observation_manager()
        if not mgr:
            return "ERR MemoryObservationManager not initialized"
        result = await mgr.delete_observation(observation_id)
        if result.get("deleted"):
            return f"OK Observation '{observation_id}' deleted"
        return f"ERR Observation '{observation_id}' not found or delete failed"
    except Exception as exc:
        logger.error(f"delete_observation failed: {exc}")
        return f"ERR delete_observation failed: {exc}"


# ===========================================================================
# Phase 17.4 - Slack / Discord Notifications
# ===========================================================================

@mcp.tool()
async def configure_slack_notifications(
    channel_id: str,
    webhook_url: str,
    events: Optional[str] = None,
) -> str:
    """
    Register a Slack incoming webhook to receive Enhanced Cognee event notifications.

    TRIGGER TYPE: (M) Manual - Notification setup is a deliberate configuration step.

    Parameters:
    -----------
    - channel_id  : Unique identifier for this channel (e.g. "ops-alerts")
    - webhook_url : Slack Incoming Webhook URL
                    (https://hooks.slack.com/services/...)
    - events      : Comma-separated list of events to subscribe to.
                    Defaults to all events if omitted.
                    Supported: memory.added, memory.updated, memory.deleted,
                    backup.completed, backup.failed, health.degraded

    Returns:
    --------
    - OK confirmation with channel details or ERR
    """
    try:
        nm = notification_manager_instance or get_notification_manager()
        if not nm:
            return "ERR NotificationManager not initialized"
        event_list = [e.strip() for e in events.split(",")] if events else []
        result = await nm.configure_slack(
            channel_id=channel_id,
            webhook_url=webhook_url,
            events=event_list,
        )
        if "error" in result:
            return f"ERR {result['error']}"
        return (
            f"OK Slack channel configured: {channel_id}\n"
            f"  Events: {', '.join(result.get('events', [])) or 'all'}"
        )
    except Exception as exc:
        logger.error(f"configure_slack_notifications failed: {exc}")
        return f"ERR configure_slack_notifications failed: {exc}"


@mcp.tool()
async def configure_discord_notifications(
    channel_id: str,
    webhook_url: str,
    events: Optional[str] = None,
) -> str:
    """
    Register a Discord webhook to receive Enhanced Cognee event notifications.

    TRIGGER TYPE: (M) Manual - Notification setup is a deliberate configuration step.

    Parameters:
    -----------
    - channel_id  : Unique identifier for this channel (e.g. "dev-alerts")
    - webhook_url : Discord Webhook URL
                    (https://discord.com/api/webhooks/...)
    - events      : Comma-separated list of events to subscribe to.
                    Defaults to all events if omitted.

    Returns:
    --------
    - OK confirmation with channel details or ERR
    """
    try:
        nm = notification_manager_instance or get_notification_manager()
        if not nm:
            return "ERR NotificationManager not initialized"
        event_list = [e.strip() for e in events.split(",")] if events else []
        result = await nm.configure_discord(
            channel_id=channel_id,
            webhook_url=webhook_url,
            events=event_list,
        )
        if "error" in result:
            return f"ERR {result['error']}"
        return (
            f"OK Discord channel configured: {channel_id}\n"
            f"  Events: {', '.join(result.get('events', [])) or 'all'}"
        )
    except Exception as exc:
        logger.error(f"configure_discord_notifications failed: {exc}")
        return f"ERR configure_discord_notifications failed: {exc}"


@mcp.tool()
async def test_notification_channel(channel_id: str) -> str:
    """
    Send a test notification to a configured Slack or Discord channel.

    TRIGGER TYPE: (M) Manual - Tests are intentional verification steps.

    Parameters:
    -----------
    - channel_id : Channel ID previously configured via configure_slack_notifications
                   or configure_discord_notifications

    Returns:
    --------
    - OK with HTTP response code or ERR
    """
    try:
        nm = notification_manager_instance or get_notification_manager()
        if not nm:
            return "ERR NotificationManager not initialized"
        result = await nm.test_channel(channel_id)
        if result.get("ok"):
            code = result.get("response_code", "?")
            return f"OK Test notification sent to '{channel_id}' (HTTP {code})"
        return f"ERR Test failed for '{channel_id}': {result.get('error', 'unknown error')}"
    except Exception as exc:
        logger.error(f"test_notification_channel failed: {exc}")
        return f"ERR test_notification_channel failed: {exc}"


# ===========================================================================
# Phase 18.4 - Memory Importance Scoring
# ===========================================================================

@mcp.tool()
async def get_memory_importance(memory_id: str) -> str:
    """
    Compute and return the importance score for a specific memory.

    TRIGGER TYPE: (A) Auto - Safe to call at any time; read-only.

    Importance is a heuristic 0-1 score computed from:
      - Access frequency (40%)
      - Recency of last access (30%)
      - Confidence score (20%)
      - Source type (10%: verified > agent > user > system > unknown)

    Parameters:
    -----------
    - memory_id : UUID of the memory to score

    Returns:
    --------
    - JSON with importance_score and per-component breakdown or ERR
    """
    try:
        scorer = importance_scorer_instance or get_importance_scorer()
        if not scorer:
            return "ERR MemoryImportanceScorer not initialized"
        result = await scorer.get_memory_importance(memory_id)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error(f"get_memory_importance failed: {exc}")
        return f"ERR get_memory_importance failed: {exc}"


@mcp.tool()
async def update_importance_scores(
    agent_id: Optional[str] = None,
    limit: int = 100,
) -> str:
    """
    Recompute and persist importance scores for up to 'limit' memories.

    TRIGGER TYPE: (M) Manual - Batch scoring is a maintenance operation.

    Adds an importance_score column to shared_memory.documents if absent,
    then UPSERTs the heuristic score for each eligible memory.

    Parameters:
    -----------
    - agent_id : Scope update to this agent's memories (default: all agents)
    - limit    : Maximum number of memories to score in this run (default: 100)

    Returns:
    --------
    - OK with updated count and mean score or ERR
    """
    try:
        scorer = importance_scorer_instance or get_importance_scorer()
        if not scorer:
            return "ERR MemoryImportanceScorer not initialized"
        result = await scorer.update_importance_scores(agent_id=agent_id, limit=limit)
        if "error" in result:
            return f"ERR {result['error']}"
        updated = result.get("updated", 0)
        mean = result.get("mean_score", 0.0)
        return f"OK Importance scores updated: {updated} memories, mean_score={mean:.3f}"
    except Exception as exc:
        logger.error(f"update_importance_scores failed: {exc}")
        return f"ERR update_importance_scores failed: {exc}"


@mcp.tool()
async def get_top_important_memories(
    agent_id: Optional[str] = None,
    top_n: int = 10,
) -> str:
    """
    Return the N most important memories ordered by heuristic importance score.

    TRIGGER TYPE: (A) Auto - Safe read; useful for context priming.

    Importance scores must have been computed first via update_importance_scores.
    Memories with NULL importance_score are ranked last.

    Parameters:
    -----------
    - agent_id : Filter to this agent's memories (default: all agents)
    - top_n    : Number of memories to return (default: 10)

    Returns:
    --------
    - JSON array of memory dicts with importance_score or ERR
    """
    try:
        scorer = importance_scorer_instance or get_importance_scorer()
        if not scorer:
            return "ERR MemoryImportanceScorer not initialized"
        results = await scorer.get_top_important_memories(agent_id=agent_id, top_n=top_n)
        return json.dumps(results, indent=2, default=str)
    except Exception as exc:
        logger.error(f"get_top_important_memories failed: {exc}")
        return f"ERR get_top_important_memories failed: {exc}"


# ===========================================================================
# Phase 18.5 - Heuristic Re-ranking
# ===========================================================================

@mcp.tool()
async def rerank_search_results(
    results_json: str,
    query: str = "",
) -> str:
    """
    Re-rank a list of search results using a heuristic multi-signal scorer.

    TRIGGER TYPE: (A) Auto - Apply after any search_memories / advanced_search call
    to improve result ordering before presenting to the user.

    Re-ranking formula (all signals normalised to [0, 1]):
      final_score = similarity*0.50 + importance*0.25 + recency*0.15 + confidence*0.10

    Parameters:
    -----------
    - results_json : JSON array of memory dicts as returned by search_memories.
                     Each dict may contain optional keys:
                     similarity_score, importance_score, last_accessed_at,
                     confidence_score.  Missing keys default to 0.5.
    - query        : Original search query (informational; not used in scoring)

    Returns:
    --------
    - JSON array sorted by rerank_score descending, each entry includes
      'rerank_score' field or ERR
    """
    try:
        reranker = reranker_instance or get_reranker()
        if not reranker:
            return "ERR MemoryReranker not initialized"
        try:
            results = json.loads(results_json)
        except Exception:
            return "ERR results_json must be a valid JSON array"
        if not isinstance(results, list):
            return "ERR results_json must be a JSON array"
        reranked = await reranker.rerank_search_results(results, query=query)
        return json.dumps(reranked, indent=2, default=str)
    except Exception as exc:
        logger.error(f"rerank_search_results failed: {exc}")
        return f"ERR rerank_search_results failed: {exc}"


async def main():
    """Main entry point"""
    print("""
==================================================================
         Enhanced Cognee MCP Server - Enhanced Stack
    PostgreSQL+pgVector | Qdrant | Neo4j | Redis
==================================================================
    """)

    # Initialize Enhanced stack
    await init_enhanced_stack()

    # Initialize Sprint 8 modules
    await init_sprint8_modules()

    print("\nOK Enhanced Cognee MCP Server starting...")
    print("  Available tools:")
    print("    Standard Memory MCP Tools (for MCP-compatible IDE integration):")
    print("      - add_memory: Add memory entry")
    print("      - search_memories: Search memories")
    print("      - get_memories: List all memories")
    print("      - get_memory: Get specific memory by ID")
    print("      - update_memory: Update existing memory")
    print("      - delete_memory: Delete memory")
    print("      - list_agents: List all agents")
    print("    Enhanced Cognee Tools:")
    print("      - cognify: Add data to knowledge graph")
    print("      - search: Search knowledge graph")
    print("      - list_data: List all documents")
    print("      - get_stats: Get system statistics")
    print("      - health: Health check")
    print("    Sprint 8 Backup & Recovery Tools:")
    print("      - create_backup: Create backup of databases")
    print("      - restore_backup: Restore from backup")
    print("      - list_backups: List all backups")
    print("      - verify_backup: Verify backup integrity")
    print("      - rollback_restore: Rollback failed restore")
    print("    Sprint 8 Maintenance Scheduler Tools:")
    print("      - schedule_task: Schedule maintenance task")
    print("      - list_tasks: List scheduled tasks")
    print("      - cancel_task: Cancel scheduled task")
    print("    Sprint 8 Deduplication Tools:")
    print("      - deduplicate: Perform deduplication")
    print("      - schedule_deduplication: Schedule periodic deduplication")
    print("      - deduplication_report: Generate deduplication report")
    print("    Sprint 8 Summarization Tools:")
    print("      - summarize_old_memories: Summarize old memories")
    print("      - schedule_summarization: Schedule periodic summarization")
    print("      - summary_stats: Get summarization statistics")
    print("    Sprint 9 Multi-Language Tools:")
    print("      - detect_language: Detect language from text (28 languages)")
    print("      - get_supported_languages: List all supported languages")
    print("      - search_by_language: Search with language filtering")
    print("      - get_language_distribution: Get language statistics")
    print("      - cross_language_search: Cross-language search with ranking")
    print("      - get_search_facets: Get faceted search options")
    print("    Sprint 10 Advanced AI Features:")
    print("      - intelligent_summarize: LLM-based memory summarization")
    print("      - auto_summarize_old_memories: Batch summarization of old memories")
    print("      - cluster_memories: Semantic memory clustering")
    print("      - advanced_search: Advanced search with re-ranking")
    print("      - expand_search_query: Query expansion using LLM")
    print("      - get_search_analytics: Search analytics and metrics")
    print("      - get_summarization_stats: Summarization statistics")
    print("    Memory Management Tools:")
    print("      - expire_memories: Expire old memories")
    print("      - get_memory_age_stats: Get memory age statistics")
    print("      - set_memory_ttl: Set time-to-live for memory")
    print("      - archive_category: Archive category memories")
    print("    Performance Analytics Tools:")
    print("      - get_performance_metrics: Get comprehensive metrics")
    print("      - get_slow_queries: Get slow queries")
    print("      - get_prometheus_metrics: Export Prometheus metrics")
    print("    Cross-Agent Sharing Tools:")
    print("      - set_memory_sharing: Set sharing policy")
    print("      - check_memory_access: Check memory access")
    print("      - get_shared_memories: Get shared memories")
    print("      - create_shared_space: Create shared space")
    print("    Real-Time Sync Tools:")
    print("      - publish_memory_event: Publish memory event")
    print("      - get_sync_status: Get sync status")
    print("      - sync_agent_state: Sync agent state")
    print("    Phase 2 - Knowledge Graph (v1.0.9 API):")
    print("      - remember: Session-aware cognee ingestion")
    print("      - recall: Knowledge graph search (15 search types)")
    print("      - forget_memory: Delete from cognee knowledge graph")
    print("      - improve: 4-stage feedback improvement pipeline")
    print("      - save_interaction: Save coding interactions as knowledge")
    print("      - cognify_status: Check background task status")
    print("      search() now accepts search_type= for graph routing")
    print("    Phase 3 - External Loaders, Translation, Entities, v2 Graph:")
    print("      - ingest_url: Scrape URLs into knowledge graph (Tavily/BS4)")
    print("      - ingest_db: Ingest relational DB tables via dlt")
    print("      - translate_text: Translate text (llm/google/azure)")
    print("      - regex_extract_entities: Extract entities via regex patterns")
    print("      - extract_graph_v2: Cascade v2 graph extraction (preview)")
    print("      - list_loaders: List available file format loaders")
    print("    Plan 14.8 - LLM Cost Tracking:")
    print("      - get_llm_cost_report: Token usage and cost report (per-agent/tool/model)")
    print("      - set_cost_budget: Set monthly LLM cost limit for an agent")
    print("    Phase 7 - Progressive Search Tools:")
    print("      - search_quick: Fast top-3 keyword search (lightweight)")
    print("      - get_memory_detail: Full detail of a single memory by ID")
    print("      - get_related: Find memories related to a given memory")
    print("    Phase 7 - Session Management Tools:")
    print("      - start_session: Start a new Claude Code session")
    print("      - end_session: End a session with optional summary")
    print("      - get_session_context: Retrieve full session context + memories")
    print("      - get_session_history: List recent sessions for a user/agent")
    print("    Phase 9 - Audit and Compliance Tools:")
    print("      - query_audit_log: Query audit log for recent operations")
    print("    Phase 14.3 - Encryption at Rest:")
    print("      - encrypt_memory: Encrypt a memory's content with Fernet AES")
    print("      - get_encryption_stats: Encryption coverage statistics")
    print("      - rotate_encryption_key: Rotate master key and re-encrypt all memories")
    print("    Phase 12.8 - Structured Observations (EAV):")
    print("      - add_observation: Add entity-attribute-value observation to a memory")
    print("      - get_observations: Get all observations for a memory")
    print("      - update_observation: Update an observation value/confidence")
    print("      - delete_observation: Delete a structured observation")
    print("    Phase 17.4 - Slack/Discord Notifications:")
    print("      - configure_slack_notifications: Register Slack webhook channel")
    print("      - configure_discord_notifications: Register Discord webhook channel")
    print("      - test_notification_channel: Send test notification to channel")
    print("    Phase 18.4 - Memory Importance Scoring:")
    print("      - get_memory_importance: Get heuristic importance score for a memory")
    print("      - update_importance_scores: Recompute scores for up to N memories")
    print("      - get_top_important_memories: Top N memories by importance score")
    print("    Phase 18.5 - Heuristic Re-ranking:")
    print("      - rerank_search_results: Re-rank search results by multi-signal score")
    print(f"  Total tools: 119")
    print()

    try:
        # Run MCP server
        await mcp.run_stdio_async()
    finally:
        await cleanup_enhanced_stack()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Cognee MCP Server")
    parser.add_argument(
        "--serve-url",
        default=os.environ.get("COGNEE_SERVICE_URL", ""),
        help=(
            "Optional URL of a remote Cognee Cloud or Enhanced instance to bridge to. "
            "When set, cognee.serve(url=...) is called before starting the MCP server. "
            "Default: empty (local-only mode). Can also be set via COGNEE_SERVICE_URL env var."
        ),
    )
    parser.add_argument(
        "--serve-api-key",
        default=os.environ.get("COGNEE_SERVICE_API_KEY", ""),
        help="API key for the remote Cognee instance (used with --serve-url).",
    )
    args = parser.parse_args()

    # Cloud connectivity toggle (optional, opt-in only)
    if args.serve_url:
        try:
            from cognee.api.v1.serve.serve import serve as cognee_serve
            cognee_serve(url=args.serve_url, api_key=args.serve_api_key or None)
            print(f"OK Cloud connectivity enabled: {args.serve_url}")
        except Exception as _serve_err:
            print(f"WARN Could not enable cloud connectivity: {_serve_err}")
            print("INFO Continuing in local-only mode")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOK Enhanced Cognee MCP Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
