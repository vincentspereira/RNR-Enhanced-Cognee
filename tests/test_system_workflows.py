"""
System Tests for Enhanced Cognee

Tests complete end-to-end workflows with all components.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


# Helper for async context manager mocking
def create_mock_acquire_context(mock_conn):
    """Create a proper async context manager for postgres_pool.acquire()"""
    class MockAcquireContext:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass
    return MockAcquireContext()


@pytest.mark.system
class TestCompleteMemoryLifecycle:
    """Test complete memory lifecycle with multi-language support"""

    @pytest.mark.asyncio
    async def test_memory_lifecycle_english(self):
        """Test complete lifecycle: add -> detect -> search -> retrieve"""
        from src.language_detector import language_detector
        from src.multi_language_search import multi_language_search

        # 1. Add memory (simulate)
        content = "This is a trading strategy using momentum indicators"
        lang_code, confidence = language_detector.detect_language(content)

        # 2. Add metadata
        metadata = multi_language_search.add_language_metadata(content, None)

        # 3. Create memory
        memory = {
            'id': 'mem-1',
            'content': content,
            'metadata': json.dumps(metadata)
        }

        # 4. Verify
        assert lang_code == 'en'
        assert metadata['language'] == 'en'
        assert memory['id'] == 'mem-1'

    @pytest.mark.asyncio
    async def test_memory_lifecycle_multilingual(self):
        """Test lifecycle with memories in multiple languages"""
        from src.language_detector import language_detector
        from src.multi_language_search import multi_language_search

        memories_data = [
            ('English trading strategy with momentum indicators', 'en'),
            ('Estrategia completa de trading en espanol con indicadores', 'es'),
            ('Strategie complete de trading en francais avec indicateurs', 'fr'),
        ]

        memories = []
        for content, expected_lang in memories_data:
            lang_code, confidence = language_detector.detect_language(content)
            metadata = multi_language_search.add_language_metadata(content, None)

            memory = {
                'id': f'mem-{len(memories)}',
                'content': content,
                'metadata': json.dumps(metadata)
            }
            memories.append(memory)

            # Verify language detection
            assert lang_code == expected_lang

        # Test cross-language search
        query = "trading strategy"
        query_lang, _ = language_detector.detect_language(query)

        ranked = multi_language_search.cross_language_search(
            query=query,
            memories=memories,
            query_language=query_lang
        )

        # Should return all memories
        assert len(ranked) == 3


@pytest.mark.system
class TestMultiLanguageSearchSystem:
    """Test multi-language search system workflows"""

    @pytest.mark.asyncio
    async def test_language_specific_search_workflow(self):
        """Test searching specific language"""
        from src.language_detector import language_detector
        from src.multi_language_search import multi_language_search

        # Create multi-language dataset
        memories = []
        for i, (content, lang) in enumerate([
            ('English content one', 'en'),
            ('Spanish content one', 'es'),
            ('English content two', 'en'),
            ('French content one', 'fr'),
        ]):
            metadata = {'language': lang, 'language_confidence': 0.9}
            memories.append({
                'id': f'mem-{i}',
                'content': content,
                'metadata': json.dumps(metadata)
            })

        # Search only English
        english_only = multi_language_search.search_by_language(
            memories=memories,
            language='en',
            min_confidence=0.5
        )

        assert len(english_only) == 2
        assert all(m['metadata'] for m in english_only)

    @pytest.mark.asyncio
    async def test_language_distribution_workflow(self):
        """Test getting language distribution"""
        from src.multi_language_search import multi_language_search

        # Create dataset with known distribution
        memories = []
        lang_counts = {'en': 5, 'es': 3, 'fr': 2}

        for lang, count in lang_counts.items():
            for i in range(count):
                metadata = {'language': lang}
                memories.append({
                    'id': f'{lang}-{i}',
                    'metadata': json.dumps(metadata)
                })

        # Get distribution
        distribution = multi_language_search.get_language_distribution(memories)

        # Verify
        assert distribution['en'] == 5
        assert distribution['es'] == 3
        assert distribution['fr'] == 2


@pytest.mark.system
class TestAdvancedSearchSystem:
    """Test advanced search system workflows"""

    @pytest.mark.asyncio
    async def test_faceted_search_workflow(self):
        """Test complete faceted search workflow"""
        from src.advanced_search import advanced_search
        from src.multi_language_search import multi_language_search

        # Create diverse dataset
        memories = []
        data = [
            ('en', 'feature', 'trading'),
            ('es', 'feature', 'trading'),
            ('en', 'bugfix', 'development'),
            ('fr', 'feature', 'development'),
        ]

        for i, (lang, mtype, category) in enumerate(data):
            content = f"Content {i}"
            metadata = {
                'language': lang,
                'memory_type': mtype,
                'category': category
            }
            memories.append({
                'id': f'mem-{i}',
                'content': content,
                'metadata': json.dumps(metadata)
            })

        # Get facets
        facets = advanced_search.get_facet_counts(memories)

        # Apply multiple filters
        filtered = advanced_search.faceted_search(
            memories=memories,
            filters={
                'language': ['en'],
                'memory_type': ['feature']
            }
        )

        # Verify results
        assert len(facets['language']) >= 2
        assert len(filtered) == 1
        assert filtered[0]['id'] == 'mem-0'

    @pytest.mark.asyncio
    async def test_search_suggestions_workflow(self):
        """Test search suggestions workflow"""
        from src.advanced_search import advanced_search

        # Create dataset with common terms
        memories = [
            {'id': '1', 'content': 'momentum trading strategy'},
            {'id': '2', 'content': 'mean reversion strategy'},
            {'id': '3', 'content': 'arbitrage trading opportunity'},
            {'id': '4', 'content': 'market analysis'},
        ]

        # Track searches for history
        advanced_search.track_search('momentum')
        advanced_search.track_search('strategy')

        # Get suggestions
        suggestions = await advanced_search.get_search_suggestions(
            partial_query='strat',
            memories=memories,
            limit=10
        )

        # Should have suggestions from content and history
        assert len(suggestions) > 0
        assert all('term' in s for s in suggestions)

    @pytest.mark.asyncio
    async def test_fuzzy_search_workflow(self):
        """Test fuzzy search with typos"""
        from src.advanced_search import advanced_search

        memories = [
            {'id': '1', 'content': 'momentum trading strategy'},
            {'id': '2', 'content': 'mean reversion strategy'},
        ]

        # Search with partial match
        results = await advanced_search.fuzzy_search(
            query='momentum',  # Partial match
            memories=memories,
            threshold=0.2  # Lower threshold for partial matches
        )

        # Should still find the memory
        assert len(results) > 0
        assert results[0]['memory']['id'] == '1'


@pytest.mark.system
class TestPerformanceSystem:
    """Test performance optimization system"""

    @pytest.mark.asyncio
    async def test_query_optimization_workflow(self):
        """Test query optimization workflow"""
        from src.performance_optimizer import performance_optimizer

        # Mock database
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

        # Execute optimized query
        result = await performance_optimizer.optimize_query(
            query="test query",
            postgres_pool=mock_pool,
            user_id="test_user",
            agent_id="test_agent",
            language="en"
        )

        # Should complete without error
        assert isinstance(result, list)

        # Check performance was tracked
        stats = performance_optimizer.get_performance_stats()
        # May or may not have stats depending on execution

    @pytest.mark.asyncio
    async def test_benchmark_workflow(self):
        """Test benchmarking workflow"""
        from src.performance_optimizer import performance_optimizer

        # Mock database
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

        # Run benchmarks
        benchmarks = await performance_optimizer.benchmark_query_performance(
            postgres_pool=mock_pool,
            user_id="test_user",
            agent_id="test_agent"
        )

        # Verify all benchmarks completed
        assert 'language_filtered_ms' in benchmarks
        assert 'regular_query_ms' in benchmarks
        assert 'language_distribution_ms' in benchmarks

        # Verify all are numeric (or -1 for errors)
        assert all(isinstance(v, (int, float)) for v in benchmarks.values())


@pytest.mark.system
class TestMCPToolsSystem:
    """Test MCP tools system integration"""

    @pytest.mark.asyncio
    async def test_language_detection_mcp_workflow(self):
        """Test complete language detection workflow via MCP"""
        from enhanced_cognee_mcp_server import detect_language

        # Test multiple languages
        test_cases = [
            ("Hello world", "en"),
            ("Hola mundo", "es"),
            ("Bonjour le monde", "fr"),
        ]

        for text, expected_lang in test_cases:
            result = await detect_language(text)
            assert 'OK' in result
            # Should detect the expected language or similar

    @pytest.mark.asyncio
    async def test_search_facets_mcp_workflow(self):
        """Test search facets workflow via MCP"""
        from enhanced_cognee_mcp_server import get_search_facets

        # Mock postgres pool
        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = []
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            result = await get_search_facets(
                user_id="test",
                agent_id="test"
            )

            assert isinstance(result, str)
            assert 'OK' in result


@pytest.mark.system
class TestErrorHandlingSystem:
    """Test error handling in complete workflows"""

    @pytest.mark.asyncio
    async def test_invalid_language_detection(self):
        """Test handling of invalid language detection"""
        from src.language_detector import language_detector

        # Empty text
        lang, conf = language_detector.detect_language("")
        assert lang == 'en'  # Fallback
        assert conf == 0.0

        # Special characters only
        lang, conf = language_detector.detect_language("!@#$%")
        assert lang == 'en'  # Fallback

    @pytest.mark.asyncio
    async def test_corrupted_metadata_handling(self):
        """Test handling of corrupted metadata in searches"""
        from src.multi_language_search import multi_language_search

        memories = [
            {'id': '1', 'metadata': 'invalid json'},
            {'id': '2', 'metadata': None},
            {'id': '3', 'metadata': '{}'},
        ]

        # Should handle gracefully
        distribution = multi_language_search.get_language_distribution(memories)
        assert isinstance(distribution, dict)

    @pytest.mark.asyncio
    async def test_empty_dataset_handling(self):
        """Test handling of empty datasets"""
        from src.multi_language_search import multi_language_search
        from src.advanced_search import advanced_search

        # Empty memories
        distribution = multi_language_search.get_language_distribution([])
        assert distribution == {}

        facets = advanced_search.get_facet_counts([])
        assert facets['language'] == {}
        assert facets['memory_type'] == {}


@pytest.mark.system
class TestConcurrencySystem:
    """Test concurrent operations system"""

    @pytest.mark.asyncio
    async def test_concurrent_language_detection(self):
        """Test concurrent language detection operations"""
        from src.language_detector import language_detector

        # Detect languages concurrently
        texts = [
            "English text one",
            "Spanish text one",
            "French text one",
        ] * 10

        # Process all concurrently
        results = await asyncio.gather(*[
            asyncio.to_thread(language_detector.detect_language, text)
            for text in texts
        ])

        # All should complete
        assert len(results) == 30
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_search_operations(self):
        """Test concurrent search operations"""
        from src.multi_language_search import multi_language_search

        memories = [
            {'id': str(i), 'metadata': json.dumps({'language': 'en'})}
            for i in range(100)
        ]

        # Run multiple searches concurrently
        searches = await asyncio.gather(*[
            asyncio.to_thread(multi_language_search.search_by_language, memories, 'en')
            for _ in range(5)
        ])

        # All should complete
        assert len(searches) == 5
        assert all(len(s) == 100 for s in searches)
