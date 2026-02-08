"""
Unit Tests for Advanced Search Module

Tests advanced search functionality with 100% coverage.
"""

import pytest
from datetime import datetime
from src.advanced_search import (
    advanced_search,
    AdvancedSearch
)


@pytest.mark.unit
class TestAdvancedSearch:
    """Test suite for AdvancedSearch class"""

    def test_initialization(self):
        """Test AdvancedSearch initialization"""
        search = AdvancedSearch()
        assert search.search_history == []
        assert isinstance(search.popular_terms, object)

    def test_faceted_search_single_filter(self):
        """Test faceted search with single filter"""
        memories = [
            {'id': '1', 'metadata': '{"language": "en"}'},
            {'id': '2', 'metadata': '{"language": "es"}'},
            {'id': '3', 'metadata': '{"language": "en"}'},
        ]

        filtered = advanced_search.faceted_search(
            memories,
            filters={'language': ['en']}
        )

        assert len(filtered) == 2
        assert filtered[0]['id'] == '1'
        assert filtered[1]['id'] == '3'

    def test_faceted_search_multiple_filters(self):
        """Test faceted search with multiple filters"""
        memories = [
            {'id': '1', 'metadata': '{"language": "en", "memory_type": "feature"}'},
            {'id': '2', 'metadata': '{"language": "es", "memory_type": "bugfix"}'},
            {'id': '3', 'metadata': '{"language": "en", "memory_type": "feature"}'},
        ]

        filtered = advanced_search.faceted_search(
            memories,
            filters={'language': ['en'], 'memory_type': ['feature']}
        )

        assert len(filtered) == 2

    def test_faceted_search_no_filters(self):
        """Test faceted search with no filters"""
        memories = [
            {'id': '1', 'metadata': '{"language": "en"}'},
            {'id': '2', 'metadata': '{"language": "es"}'},
        ]

        filtered = advanced_search.faceted_search(memories, filters={})
        assert len(filtered) == 2

    def test_faceted_search_empty_memories(self):
        """Test faceted search with empty memories"""
        filtered = advanced_search.faceted_search([], filters={'language': ['en']})
        assert len(filtered) == 0

    def test_faceted_search_date_range(self):
        """Test faceted search with date range filter"""
        memories = [
            {'id': '1', 'created_at': '2026-01-01T10:00:00', 'metadata': '{}'},
            {'id': '2', 'created_at': '2026-02-01T10:00:00', 'metadata': '{}'},
            {'id': '3', 'created_at': '2026-03-01T10:00:00', 'metadata': '{}'},
        ]

        filtered = advanced_search.faceted_search(
            memories,
            filters={'date_range': ('2026-01-15', '2026-02-15')}
        )

        assert len(filtered) == 1
        assert filtered[0]['id'] == '2'

    async def test_get_search_suggestions(self):
        """Test getting search suggestions"""
        memories = [
            {'id': '1', 'content': 'momentum trading strategy'},
            {'id': '2', 'content': 'mean reversion strategy'},
            {'id': '3', 'content': 'arbitrage trading'},
        ]

        suggestions = await advanced_search.get_search_suggestions(
            partial_query='strat',
            memories=memories,
            limit=10
        )

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all('term' in s for s in suggestions)
        assert all('count' in s for s in suggestions)

    async def test_get_search_suggestions_empty_query(self):
        """Test suggestions with empty query"""
        memories = [
            {'id': '1', 'content': 'test content'},
        ]

        suggestions = await advanced_search.get_search_suggestions(
            partial_query='',
            memories=memories,
            limit=10
        )

        assert isinstance(suggestions, list)

    async def test_get_search_suggestions_limit(self):
        """Test suggestions with limit"""
        memories = [
            {'id': str(i), 'content': f'test {i} content'}
            for i in range(100)
        ]

        suggestions = await advanced_search.get_search_suggestions(
            partial_query='test',
            memories=memories,
            limit=5
        )

        assert len(suggestions) <= 5

    async def test_fuzzy_search(self):
        """Test fuzzy search functionality"""
        memories = [
            {'id': '1', 'content': 'momentum trading strategy'},
            {'id': '2', 'content': 'different content'},
        ]

        results = await advanced_search.fuzzy_search(
            query='momentum strateg',
            memories=memories,
            threshold=0.2  # Lower threshold for partial matches
        )

        assert isinstance(results, list)
        assert len(results) >= 1
        assert all('memory' in r for r in results)
        assert all('similarity' in r for r in results)

    async def test_fuzzy_search_threshold(self):
        """Test fuzzy search with different thresholds"""
        memories = [
            {'id': '1', 'content': 'test content here'},
            {'id': '2', 'content': 'completely different'},
        ]

        # Low threshold - more results
        results_low = await advanced_search.fuzzy_search(
            query='test',
            memories=memories,
            threshold=0.1
        )

        # High threshold - fewer results
        results_high = await advanced_search.fuzzy_search(
            query='test',
            memories=memories,
            threshold=0.9
        )

        assert len(results_low) >= len(results_high)

    async def test_fuzzy_search_empty_memories(self):
        """Test fuzzy search with empty memories"""
        results = await advanced_search.fuzzy_search(
            query='test',
            memories=[],
            threshold=0.5
        )

        assert results == []

    def test_get_facet_counts(self):
        """Test getting facet counts"""
        memories = [
            {'id': '1', 'metadata': '{"language": "en", "memory_type": "feature", "category": "trading"}'},
            {'id': '2', 'metadata': '{"language": "es", "memory_type": "bugfix", "category": "trading"}'},
            {'id': '3', 'metadata': '{"language": "en", "memory_type": "feature", "category": "dev"}'},
        ]

        facets = advanced_search.get_facet_counts(memories)

        assert 'language' in facets
        assert 'memory_type' in facets
        assert 'category' in facets
        assert 'date_range' in facets

        assert facets['language']['en'] == 2
        assert facets['language']['es'] == 1
        assert facets['memory_type']['feature'] == 2
        assert facets['category']['trading'] == 2

    def test_get_facet_counts_empty(self):
        """Test getting facet counts from empty memories"""
        facets = advanced_search.get_facet_counts([])

        assert facets['language'] == {}
        assert facets['memory_type'] == {}
        assert facets['category'] == {}
        assert facets['date_range'] == {}

    def test_track_search(self):
        """Test tracking search queries"""
        advanced_search.track_search('test query')

        assert len(advanced_search.search_history) == 1
        assert advanced_search.search_history[0]['query'] == 'test query'
        assert 'timestamp' in advanced_search.search_history[0]
        assert advanced_search.popular_terms['test query'] == 1

    def test_track_multiple_searches(self):
        """Test tracking multiple searches"""
        # Clear history from previous tests
        advanced_search.search_history.clear()
        advanced_search.popular_terms.clear()

        advanced_search.track_search('query1')
        advanced_search.track_search('query2')
        advanced_search.track_search('query1')  # Duplicate

        assert len(advanced_search.search_history) == 3
        assert advanced_search.popular_terms['query1'] == 2
        assert advanced_search.popular_terms['query2'] == 1

    def test_get_search_history(self):
        """Test getting search history"""
        advanced_search.track_search('query1')
        advanced_search.track_search('query2')
        advanced_search.track_search('query3')

        history = advanced_search.get_search_history(limit=2)

        assert len(history) == 2
        assert history[0]['query'] == 'query2'
        assert history[1]['query'] == 'query3'

    def test_get_search_history_default_limit(self):
        """Test getting search history with default limit"""
        for i in range(20):
            advanced_search.track_search(f'query{i}')

        history = advanced_search.get_search_history()
        assert len(history) == 10  # Default limit

    def test_clear_search_history(self):
        """Test clearing search history"""
        advanced_search.track_search('query1')
        advanced_search.track_search('query2')

        advanced_search.clear_search_history()

        assert len(advanced_search.search_history) == 0
        assert len(advanced_search.popular_terms) == 0

    def test_get_language_helper(self):
        """Test _get_language helper method"""
        memory = {'metadata': '{"language": "en"}'}
        lang = advanced_search._get_language(memory)
        assert lang == 'en'

    def test_get_memory_type_helper(self):
        """Test _get_memory_type helper method"""
        memory = {'metadata': '{"memory_type": "feature"}'}
        mtype = advanced_search._get_memory_type(memory)
        assert mtype == 'feature'

    def test_get_category_helper(self):
        """Test _get_category helper method"""
        memory = {'metadata': '{"category": "trading"}'}
        category = advanced_search._get_category(memory)
        assert category == 'trading'

    def test_helper_defaults(self):
        """Test helper methods return defaults"""
        memory = {'metadata': '{}'}

        assert advanced_search._get_language(memory) == 'en'
        assert advanced_search._get_memory_type(memory) == 'general'
        assert advanced_search._get_category(memory) == 'uncategorized'

    def test_is_date_in_range_helper(self):
        """Test _is_date_in_range helper method"""
        memory = {'created_at': '2026-02-06T10:00:00'}

        assert advanced_search._is_date_in_range(
            memory,
            '2026-02-01',
            '2026-02-28'
        ) is True

        assert advanced_search._is_date_in_range(
            memory,
            '2026-03-01',
            '2026-03-31'
        ) is False


@pytest.mark.unit
class TestAdvancedSearchEdgeCases:
    """Test edge cases and error handling"""

    def test_faceted_search_invalid_metadata(self):
        """Test faceted search with invalid metadata"""
        memories = [
            {'id': '1', 'metadata': 'invalid json'},
            {'id': '2', 'metadata': None},
        ]

        # Should handle gracefully
        filtered = advanced_search.faceted_search(memories, filters={'language': ['en']})
        assert isinstance(filtered, list)

    async def test_fuzzy_search_similarity_scores(self):
        """Test that similarity scores are in valid range"""
        memories = [
            {'id': '1', 'content': 'test content here'},
        ]

        results = await advanced_search.fuzzy_search(
            query='test',
            memories=memories,
            threshold=0.0
        )

        for result in results:
            assert 0.0 <= result['similarity'] <= 1.0

    async def test_fuzzy_search_ranking(self):
        """Test that fuzzy search results are ranked by similarity"""
        memories = [
            {'id': '1', 'content': 'test content'},
            {'id': '2', 'content': 'test'},
            {'id': '3', 'content': 'completely different'},
        ]

        results = await advanced_search.fuzzy_search(
            query='test',
            memories=memories,
            threshold=0.0
        )

        # Results should be sorted by similarity (highest first)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]['similarity'] >= results[i+1]['similarity']

    async def test_get_search_suggestions_with_history(self):
        """Test suggestions include search history"""
        advanced_search.track_search('momentum strategy')
        advanced_search.track_search('momentum trading')

        memories = [{'id': '1', 'content': 'test content'}]

        suggestions = await advanced_search.get_search_suggestions(
            partial_query='momentum',
            memories=memories,
            limit=10
        )

        # Should include history suggestions
        history_suggestions = [s for s in suggestions if s.get('type') == 'history']
        assert len(history_suggestions) > 0

    def test_date_range_facet_format(self):
        """Test that date range facet uses correct format"""
        memories = [
            {'id': '1', 'created_at': '2026-02-06T10:00:00', 'metadata': '{}'},
        ]

        facets = advanced_search.get_facet_counts(memories)
        assert '2026-02' in facets['date_range']

    def test_singleton_instance(self):
        """Test that advanced_search is a singleton"""
        from src.advanced_search import advanced_search as as1
        from src.advanced_search import advanced_search as as2
        assert as1 is as2
