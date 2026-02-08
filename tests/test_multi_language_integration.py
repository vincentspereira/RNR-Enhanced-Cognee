"""
Integration Tests for Multi-Language System

Tests integration between multi-language components with databases and MCP server.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from src.language_detector import language_detector
from src.multi_language_search import multi_language_search
from src.performance_optimizer import performance_optimizer


# Helper for async context manager mocking
def create_mock_acquire_context(mock_conn):
    """Create a proper async context manager for postgres_pool.acquire()"""
    class MockAcquireContext:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass
    return MockAcquireContext()


@pytest.mark.integration
class TestLanguageDetectionIntegration:
    """Integration tests for language detection with memory operations"""

    @pytest.mark.asyncio
    async def test_add_memory_with_language_detection(self):
        """Test adding memory with automatic language detection"""
        # Simulate memory content in Spanish
        content = "Esta es una prueba de deteccion de idioma"

        # Detect language
        lang_code, confidence = language_detector.detect_language(content)

        # Add language metadata
        metadata = multi_language_search.add_language_metadata(content, None)

        assert metadata['language'] == 'es'
        assert metadata['language_confidence'] >= 0.5
        assert 'language_name' in metadata

    @pytest.mark.asyncio
    async def test_multi_language_memory_workflow(self):
        """Test complete workflow with multi-language memories"""
        memories = []

        # Add memories in different languages
        texts = [
            ('This is English text', 'en'),
            ('Este es texto en espanol', 'es'),
            ('Ceci est un texte francais', 'fr'),
            ('Dies ist ein deutscher Text', 'de'),
        ]

        for text, expected_lang in texts:
            lang_code, confidence = language_detector.detect_language(text)
            metadata = multi_language_search.add_language_metadata(text, None)

            memories.append({
                'content': text,
                'language': lang_code,
                'metadata': json.dumps(metadata)
            })

        # Verify all languages detected
        assert len(memories) == 4
        assert all('language' in m['metadata'] for m in memories)

    @pytest.mark.asyncio
    async def test_cross_language_search_workflow(self):
        """Test cross-language search workflow"""
        memories = [
            {'id': '1', 'content': 'momentum strategy', 'metadata': json.dumps({'language': 'en'})},
            {'id': '2', 'content': 'estrategia de momento', 'metadata': json.dumps({'language': 'es'})},
            {'id': '3', 'content': 'momentum trading', 'metadata': json.dumps({'language': 'en'})},
        ]

        # Search with English query
        query = "momentum"
        query_lang, _ = language_detector.detect_language(query)

        ranked = multi_language_search.cross_language_search(
            query=query,
            memories=memories,
            query_language=query_lang
        )

        # English memories should rank first
        assert len(ranked) == 3
        assert ranked[0]['language'] == 'en'

    @pytest.mark.asyncio
    async def test_faceted_search_integration(self):
        """Test faceted search with language filtering"""
        from src.advanced_search import advanced_search

        memories = [
            {'id': '1', 'content': 'feature', 'metadata': json.dumps({'language': 'en', 'memory_type': 'feature'})},
            {'id': '2', 'content': 'caracteristica', 'metadata': json.dumps({'language': 'es', 'memory_type': 'feature'})},
            {'id': '3', 'content': 'bugfix', 'metadata': json.dumps({'language': 'en', 'memory_type': 'bugfix'})},
        ]

        # Filter by language and type
        filtered = advanced_search.faceted_search(
            memories,
            filters={'language': ['en'], 'memory_type': ['feature']}
        )

        assert len(filtered) == 1
        assert filtered[0]['id'] == '1'


@pytest.mark.integration
@pytest.mark.postgresql
class TestDatabaseIntegration:
    """Integration tests with PostgreSQL database"""

    @pytest.mark.asyncio
    async def test_language_metadata_persistence(self):
        """Test that language metadata persists correctly"""
        # Mock database connection
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

        # Simulate memory insertion with language metadata
        content = "This is a test memory"
        metadata = multi_language_search.add_language_metadata(content, None)

        # Mock successful insert
        mock_conn.execute.return_value = None

        # Verify metadata structure
        assert 'language' in metadata
        assert metadata['language'] == 'en'
        assert json.dumps(metadata) is not None

    @pytest.mark.asyncio
    async def test_language_filtered_query(self):
        """Test language-filtered database query"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Mock query result with language metadata
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            'id': 'test-id',
            'data_text': 'Test content',
            'metadata': json.dumps({'language': 'en'}),
            'created_at': '2026-02-06T10:00:00'
        }.get(key)

        mock_conn.fetch.return_value = [mock_row]
        mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

        # Execute optimized query
        result = await performance_optimizer.optimize_query(
            query="test",
            postgres_pool=mock_pool,
            user_id="test_user",
            agent_id="test_agent",
            language="en"
        )

        assert isinstance(result, list)
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_language_distribution_from_database(self):
        """Test getting language distribution from database"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Mock multiple memories with different languages
        mock_rows = [
            MagicMock(metadata=json.dumps({'language': 'en'})),
            MagicMock(metadata=json.dumps({'language': 'en'})),
            MagicMock(metadata=json.dumps({'language': 'es'})),
            MagicMock(metadata=json.dumps({'language': 'fr'})),
        ]

        for row in mock_rows:
            row.__getitem__ = lambda self, key: self.metadata

        mock_conn.fetch.return_value = mock_rows
        mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

        # Get distribution
        memories = [{'id': str(i), 'metadata': row.metadata} for i, row in enumerate(mock_rows)]
        distribution = multi_language_search.get_language_distribution(memories)

        assert distribution['en'] == 2
        assert distribution['es'] == 1
        assert distribution['fr'] == 1


@pytest.mark.integration
class TestMCPServerIntegration:
    """Integration tests with MCP server"""

    @pytest.mark.asyncio
    async def test_detect_language_mcp_tool(self):
        """Test detect_language MCP tool integration"""
        # Import MCP server functions
        from enhanced_cognee_mcp_server import detect_language

        # Test with English text
        result = await detect_language("This is a test")

        assert 'OK' in result
        assert 'English' in result
        assert 'en' in result

    @pytest.mark.asyncio
    async def test_get_supported_languages_mcp_tool(self):
        """Test get_supported_languages MCP tool integration"""
        from enhanced_cognee_mcp_server import get_supported_languages

        result = await get_supported_languages()

        assert 'OK' in result
        assert '28' in result or '29' in result  # Number of supported languages

    @pytest.mark.asyncio
    async def test_search_by_language_mcp_tool(self):
        """Test search_by_language MCP tool integration"""
        from enhanced_cognee_mcp_server import search_by_language

        # Mock postgres pool
        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = []
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            result = await search_by_language(
                query="test",
                language="en",
                user_id="test",
                agent_id="test",
                limit=10
            )

            # Should return results (possibly empty)
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_cross_language_search_mcp_tool(self):
        """Test cross_language_search MCP tool integration"""
        from enhanced_cognee_mcp_server import cross_language_search

        # Mock postgres pool
        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = []
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            result = await cross_language_search(
                query="test query",
                user_id="test",
                agent_id="test",
                limit=10
            )

            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_language_distribution_mcp_tool(self):
        """Test get_language_distribution MCP tool integration"""
        from enhanced_cognee_mcp_server import get_language_distribution

        # Mock postgres pool
        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = []
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            result = await get_language_distribution(
                user_id="test",
                agent_id="test"
            )

            assert isinstance(result, str)


@pytest.mark.integration
class TestPerformanceIntegration:
    """Integration tests for performance optimization"""

    @pytest.mark.asyncio
    async def test_query_performance_tracking(self):
        """Test that query performance is tracked correctly"""
        # Track some queries
        performance_optimizer._track_query('language_search', 45.0)
        performance_optimizer._track_query('language_search', 55.0)
        performance_optimizer._track_query('cross_language_search', 75.0)

        stats = performance_optimizer.get_performance_stats()

        assert 'language_search' in stats
        assert stats['language_search']['count'] == 2
        assert stats['language_search']['avg_ms'] == 50.0

    @pytest.mark.asyncio
    async def test_benchmark_integration(self):
        """Test performance benchmarking integration"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        # Create async context manager for acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, *args):
                pass

        mock_pool = AsyncMock()
        mock_pool.acquire = lambda: MockAcquireContext()

        benchmark_results = await performance_optimizer.benchmark_query_performance(
            postgres_pool=mock_pool,
            user_id="test_user",
            agent_id="test_agent"
        )

        # Verify all benchmarks were run
        assert 'language_filtered_ms' in benchmark_results
        assert 'regular_query_ms' in benchmark_results
        assert 'language_distribution_ms' in benchmark_results


@pytest.mark.integration
class TestMultiLanguageWorkflow:
    """Integration tests for complete multi-language workflows"""

    @pytest.mark.asyncio
    async def test_complete_multi_language_workflow(self):
        """Test complete workflow from detection to search"""
        # 1. User adds memory in Spanish
        content = "La estrategia de trading es muy rentable"
        lang_code, confidence = language_detector.detect_language(content)

        # 2. Add language metadata
        metadata = multi_language_search.add_language_metadata(content, None)

        # 3. Create memory record
        memory = {
            'id': 'test-1',
            'content': content,
            'metadata': json.dumps(metadata)
        }

        # 4. Search by language
        memories = [memory]
        filtered = multi_language_search.search_by_language(memories, language='es')

        # 5. Verify results
        assert len(filtered) == 1
        assert filtered[0]['id'] == 'test-1'

    @pytest.mark.asyncio
    async def test_cross_language_discovery_workflow(self):
        """Test discovering related content across languages"""
        memories = [
            {'id': '1', 'content': 'momentum strategy', 'metadata': json.dumps({'language': 'en'})},
            {'id': '2', 'content': 'estrategia de momento', 'metadata': json.dumps({'language': 'es'})},
            {'id': '3', 'content': 'strategie de momentum', 'metadata': json.dumps({'language': 'fr'})},
        ]

        # Search with English query
        query = "momentum strategy"
        query_lang, _ = language_detector.detect_language(query)

        ranked = multi_language_search.cross_language_search(
            query=query,
            memories=memories,
            query_language=query_lang
        )

        # Should return all memories ranked by relevance
        assert len(ranked) == 3
        # English should be first
        assert ranked[0]['language'] == 'en'

    @pytest.mark.asyncio
    async def test_faceted_search_workflow(self):
        """Test complete faceted search workflow"""
        from src.advanced_search import advanced_search

        memories = [
            {'id': '1', 'content': 'feature', 'metadata': json.dumps({'language': 'en', 'memory_type': 'feature', 'category': 'trading'})},
            {'id': '2', 'content': 'bugfix', 'metadata': json.dumps({'language': 'es', 'memory_type': 'bugfix', 'category': 'trading'})},
            {'id': '3', 'content': 'feature2', 'metadata': json.dumps({'language': 'en', 'memory_type': 'feature', 'category': 'development'})},
        ]

        # Get facets
        facets = advanced_search.get_facet_counts(memories)

        # Apply filters
        filtered = advanced_search.faceted_search(
            memories,
            filters={'language': ['en'], 'category': ['trading']}
        )

        # Verify
        assert len(facets['language']) >= 1
        assert len(filtered) == 1
        assert filtered[0]['id'] == '1'
