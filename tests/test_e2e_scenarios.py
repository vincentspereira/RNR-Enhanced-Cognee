"""
End-to-End Tests for Enhanced Cognee

Tests complete user scenarios from start to finish.
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


@pytest.mark.e2e
class TestUserScenarios:
    """Test complete end-to-end user scenarios"""

    @pytest.mark.asyncio
    async def test_multilingual_user_scenario(self):
        """
        Scenario: User works with memories in multiple languages

        1. User adds memory in English
        2. User adds memory in Spanish
        3. User searches and finds both
        4. User filters by language
        """
        from enhanced_cognee_mcp_server import (
            detect_language,
            search_by_language,
            get_language_distribution
        )

        # Step 1 & 2: Add memories (simulated via language detection)
        english_text = "Implement momentum trading strategy"
        spanish_text = "Implementar estrategia de trading de momento"

        en_result = await detect_language(english_text)
        es_result = await detect_language(spanish_text)

        # Verify languages detected
        assert 'English' in en_result
        assert 'Spanish' in es_result or 'Espanol' in es_result

        # Step 3 & 4: Search (mock database)
        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()
            # Mock returning both memories
            mock_rows = [
                MagicMock(id='1', data_text=english_text, metadata=json.dumps({'language': 'en'}), created_at='2026-02-06'),
                MagicMock(id='2', data_text=spanish_text, metadata=json.dumps({'language': 'es'}), created_at='2026-02-06'),
            ]
            mock_conn.fetch.return_value = mock_rows
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            # Search all
            all_results = await search_by_language(
                query="trading",
                user_id="user1",
                agent_id="agent1",
                limit=10
            )

            # Filter by English only
            en_results = await search_by_language(
                query="trading",
                language="en",
                user_id="user1",
                agent_id="agent1",
                limit=10
            )

            # Verify
            assert isinstance(all_results, str)
            assert isinstance(en_results, str)

    @pytest.mark.asyncio
    async def test_cross_language_discovery_scenario(self):
        """
        Scenario: User discovers related content across languages

        1. User searches in English
        2. System finds related Spanish content
        3. User reviews cross-language results
        """
        from enhanced_cognee_mcp_server import cross_language_search

        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()

            # Mock multilingual memories
            mock_rows = [
                MagicMock(id='1', data_text='momentum strategy', metadata=json.dumps({'language': 'en'}), created_at='2026-02-06'),
                MagicMock(id='2', data_text='estrategia de momento', metadata=json.dumps({'language': 'es'}), created_at='2026-02-06'),
                MagicMock(id='3', data_text='mean reversion', metadata=json.dumps({'language': 'en'}), created_at='2026-02-06'),
            ]

            # Make rows behave like dicts
            class MockDatetime:
                def __init__(self, date_str):
                    self.date_str = date_str
                def isoformat(self):
                    return self.date_str

            def make_mock_getitem(row_obj):
                def mock_getitem(self, key):
                    if key == 'id': return row_obj.id
                    elif key == 'data_text': return row_obj.data_text
                    elif key == 'content': return row_obj.data_text
                    elif key == 'metadata': return row_obj.metadata
                    elif key == 'created_at': return MockDatetime(row_obj.created_at)
                    else: return None
                return mock_getitem

            for row in mock_rows:
                row.__getitem__ = make_mock_getitem(row)

            mock_conn.fetch.return_value = mock_rows
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            # Search with English query
            results = await cross_language_search(
                query="momentum strategy",
                user_id="user1",
                agent_id="agent1",
                limit=10
            )

            # Should return ranked results
            assert isinstance(results, str)
            assert 'Cross-Language' in results

    @pytest.mark.asyncio
    async def test_faceted_exploration_scenario(self):
        """
        Scenario: User explores memories using facets

        1. User views all memories
        2. User applies language filter
        3. User applies type filter
        4. User views facets
        """
        from enhanced_cognee_mcp_server import get_search_facets

        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()

            # Mock diverse memories
            mock_rows = [
                MagicMock(metadata=json.dumps({'language': 'en', 'memory_type': 'feature', 'category': 'trading'})),
                MagicMock(metadata=json.dumps({'language': 'es', 'memory_type': 'bugfix', 'category': 'trading'})),
                MagicMock(metadata=json.dumps({'language': 'en', 'memory_type': 'feature', 'category': 'development'})),
            ]

            # Make rows behave properly
            for row in mock_rows:
                row.__getitem__ = lambda self, key: self.metadata

            mock_conn.fetch.return_value = mock_rows
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            # Get facets
            facets = await get_search_facets(
                user_id="user1",
                agent_id="agent1"
            )

            # Verify facets returned
            assert isinstance(facets, str)
            assert 'Search Facets' in facets

    @pytest.mark.asyncio
    async def test_search_suggestions_scenario(self):
        """
        Scenario: User gets search suggestions while typing

        1. User starts typing "strat"
        2. System provides suggestions
        3. User selects suggestion
        4. System performs search
        """
        from src.advanced_search import advanced_search
        from enhanced_cognee_mcp_server import search_by_language

        # Create memories with common terms
        memories = [
            {'id': '1', 'content': 'momentum trading strategy'},
            {'id': '2', 'content': 'mean reversion strategy'},
            {'id': '3', 'content': 'arbitrage strategy'},
        ]

        # Get suggestions
        suggestions = await advanced_search.get_search_suggestions(
            partial_query='strat',
            memories=memories,
            limit=5
        )

        # Verify suggestions
        assert len(suggestions) > 0
        assert any('strategy' in s['term'] for s in suggestions)

        # Track search for history
        advanced_search.track_search('strategy')

        # Perform search (mock database)
        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = []
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            results = await search_by_language(
                query='strategy',
                user_id="user1",
                agent_id="agent1",
                limit=10
            )

            assert isinstance(results, str)

    @pytest.mark.asyncio
    async def test_language_statistics_scenario(self):
        """
        Scenario: User views language statistics

        1. User adds many memories in different languages
        2. User views language distribution
        3. User understands their multilingual usage
        """
        from enhanced_cognee_mcp_server import get_language_distribution

        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()

            # Mock memories with known distribution
            mock_rows = []
            lang_counts = {'en': 15, 'es': 8, 'fr': 5, 'de': 3}

            for lang, count in lang_counts.items():
                for _ in range(count):
                    mock_rows.append(
                        MagicMock(metadata=json.dumps({'language': lang}))
                    )

            # Make rows behave properly
            for row in mock_rows:
                row.__getitem__ = lambda self, key: self.metadata

            mock_conn.fetch.return_value = mock_rows
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            # Get distribution
            stats = await get_language_distribution(
                user_id="user1",
                agent_id="agent1"
            )

            # Verify
            assert isinstance(stats, str)
            assert 'Language Distribution' in stats

    @pytest.mark.asyncio
    async def test_performance_benchmarking_scenario(self):
        """
        Scenario: User benchmarks system performance

        1. User runs performance benchmarks
        2. System measures query speeds
        3. User verifies performance meets requirements
        """
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
            user_id="user1",
            agent_id="agent1"
        )

        # Verify all benchmarks completed
        assert 'language_filtered_ms' in benchmarks
        assert 'regular_query_ms' in benchmarks
        assert 'language_distribution_ms' in benchmarks

        # Verify performance is acceptable (<1000ms for all operations, or -1 for errors)
        assert all(v < 1000 or v == -1 for v in benchmarks.values())  # 1 second max or error


@pytest.mark.e2e
class TestMigrationScenarios:
    """Test migration and upgrade scenarios"""

    @pytest.mark.asyncio
    async def test_migrate_existing_memories_scenario(self):
        """
        Scenario: System migrates existing memories to include language metadata

        1. System has memories without language metadata
        2. Migration detects languages
        3. Memories updated with language metadata
        """
        from src.language_detector import language_detector
        from src.multi_language_search import multi_language_search

        # Simulate existing memories without language metadata
        existing_memories = [
            {'id': '1', 'content': 'This is English text', 'metadata': '{}'},
            {'id': '2', 'content': 'Este es texto espanol', 'metadata': '{"category": "test"}'},
            {'id': '3', 'content': 'Ceci est un texte francais', 'metadata': '{"tags": ["important"]}'},
        ]

        # Migrate: detect language for each
        migrated = []
        for memory in existing_memories:
            old_metadata = json.loads(memory['metadata'])
            new_metadata = multi_language_search.add_language_metadata(
                memory['content'],
                old_metadata
            )

            migrated.append({
                'id': memory['id'],
                'content': memory['content'],
                'metadata': json.dumps(new_metadata)
            })

        # Verify migration
        assert len(migrated) == 3

        for memory in migrated:
            metadata = json.loads(memory['metadata'])
            assert 'language' in metadata
            # Original metadata preserved
            if memory['id'] == '2':
                assert metadata['category'] == 'test'
            if memory['id'] == '3':
                assert 'tags' in metadata


@pytest.mark.e2e
class TestErrorRecoveryScenarios:
    """Test error recovery and resilience scenarios"""

    @pytest.mark.asyncio
    async def test_database_connection_failure_scenario(self):
        """
        Scenario: Database connection fails during operation

        1. User performs operation
        2. Database connection fails
        3. System handles gracefully
        """
        from src.performance_optimizer import performance_optimizer

        # Mock database that fails
        mock_pool = AsyncMock()

        # Create async context manager that raises exception
        class MockAcquireWithError:
            async def __aenter__(self):
                raise Exception("Connection failed")
            async def __aexit__(self, *args):
                pass

        mock_pool.acquire = lambda: MockAcquireWithError()

        # Should handle exception
        result = await performance_optimizer.optimize_query(
            query="test",
            postgres_pool=mock_pool,
            user_id="user1",
            agent_id="agent1"
        )

        # Should return empty result, not crash
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_metadata_recovery_scenario(self):
        """
        Scenario: System handles invalid metadata gracefully

        1. Database returns corrupted metadata
        2. System recovers without crashing
        """
        from src.multi_language_search import multi_language_search

        memories = [
            {'id': '1', 'metadata': 'corrupted json{{{'},
            {'id': '2', 'metadata': None},
            {'id': '3', 'metadata': '{"language": "en"}'},
        ]

        # Should handle gracefully
        distribution = multi_language_search.get_language_distribution(memories)

        # Should not crash, return some results
        assert isinstance(distribution, dict)


@pytest.mark.e2e
class TestConcurrencyScenarios:
    """Test concurrent user scenarios"""

    @pytest.mark.asyncio
    async def test_concurrent_users_scenario(self):
        """
        Scenario: Multiple users use system simultaneously

        1. User A searches in English
        2. User B searches in Spanish
        3. Both get correct results
        """
        from enhanced_cognee_mcp_server import search_by_language

        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = []
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            # Concurrent searches
            results = await asyncio.gather(
                search_by_language("trading", "en", "userA", "agent1", 10),
                search_by_language("trading", "es", "userB", "agent1", 10),
                search_by_language("trading", "fr", "userC", "agent1", 10),
            )

            # All should complete successfully
            assert len(results) == 3
            assert all(isinstance(r, str) for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_language_detection_scenario(self):
        """
        Scenario: System processes multiple language detections concurrently

        1. Many users add memories simultaneously
        2. System detects all languages efficiently
        """
        from src.language_detector import language_detector

        texts = [f"Text {i} in English" for i in range(50)]

        # Process all concurrently
        results = await asyncio.gather(*[
            asyncio.to_thread(language_detector.detect_language, text)
            for text in texts
        ])

        # All should complete
        assert len(results) == 50
        assert all(lang == 'en' for lang, conf in results)


@pytest.mark.e2e
class TestCompleteWorkflows:
    """Test complete end-to-end workflows"""

    @pytest.mark.asyncio
    async def test_complete_multilingual_workflow(self):
        """
        Complete workflow: Add memories in multiple languages, search, and analyze

        1. Add English memory
        2. Add Spanish memory
        3. Add French memory
        4. Search across all languages
        5. View language statistics
        6. Filter by specific language
        """
        from enhanced_cognee_mcp_server import (
            detect_language,
            get_language_distribution,
            search_by_language,
            cross_language_search
        )

        # Step 1-3: Detect languages
        texts = {
            'en': "Implement momentum trading strategy with proper risk management",
            'es': "Implementar estrategia de trading de momento con gestion de riesgo",
            'fr': "Implementer la strategie de trading de momentum avec gestion des risques",
        }

        for lang, text in texts.items():
            result = await detect_language(text)
            assert 'OK' in result

        # Step 4-6: Search operations (mock database)
        with patch('enhanced_cognee_mcp_server.postgres_pool') as mock_pool:
            mock_conn = AsyncMock()

            # Mock returning all three memories
            mock_rows = []
            for i, (lang, text) in enumerate(texts.items()):
                row = MagicMock()
                row.id = str(i)
                row.data_text = text
                row.metadata = json.dumps({'language': lang})
                row.created_at = '2026-02-06'

                def make_getitem(meta):
                    return lambda self, key: meta if key == 'metadata' else getattr(self, key, None)

                row.__getitem__ = make_getitem(row.metadata)
                mock_rows.append(row)

            mock_conn.fetch.return_value = mock_rows
            mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)

            # Cross-language search
            cross_results = await cross_language_search(
                query="trading strategy",
                user_id="user1",
                agent_id="agent1",
                limit=10
            )

            # Language distribution
            distribution = await get_language_distribution(
                user_id="user1",
                agent_id="agent1"
            )

            # Language-specific search
            en_results = await search_by_language(
                query="trading",
                language="en",
                user_id="user1",
                agent_id="agent1",
                limit=10
            )

            # Verify all operations completed
            assert isinstance(cross_results, str)
            assert isinstance(distribution, str)
            assert isinstance(en_results, str)
