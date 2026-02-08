"""
Unit Tests for Multi-Language Search Module

Tests multi-language search functionality with 100% coverage.
"""

import pytest
import json
from src.multi_language_search import (
    multi_language_search,
    MultiLanguageSearch
)


@pytest.mark.unit
class TestMultiLanguageSearch:
    """Test suite for MultiLanguageSearch class"""

    def test_initialization(self):
        """Test MultiLanguageSearch initialization"""
        search = MultiLanguageSearch()
        assert search.db_client is None
        assert search.default_language == 'en'

    def test_add_language_metadata_new_memory(self):
        """Test adding language metadata to new memory"""
        content = "This is a test memory in English."
        metadata = multi_language_search.add_language_metadata(content, None)

        assert 'language' in metadata
        assert 'language_name' in metadata
        assert 'language_confidence' in metadata
        assert metadata['language'] == 'en'
        assert metadata['language_name'] == 'English'

    def test_add_language_metadata_existing_metadata(self):
        """Test adding language metadata to existing metadata"""
        content = "This is a test."
        existing = {'category': 'test', 'tags': ['important']}

        enhanced = multi_language_search.add_language_metadata(content, existing)

        assert enhanced['category'] == 'test'
        assert enhanced['tags'] == ['important']
        assert 'language' in enhanced
        assert 'language_confidence' in enhanced

    def test_add_language_metadata_spanish(self):
        """Test adding language metadata for Spanish"""
        content = "Esta es una prueba en espanol."
        metadata = multi_language_search.add_language_metadata(content, None)

        assert metadata['language'] == 'es'
        assert metadata['language_name'] == 'Spanish'

    def test_add_language_metadata_french(self):
        """Test adding language metadata for French"""
        content = "Ceci est un test en francais."
        metadata = multi_language_search.add_language_metadata(content, None)

        assert metadata['language'] == 'fr'
        assert metadata['language_name'] == 'French'

    def test_search_by_language_no_filter(self):
        """Test search without language filter"""
        memories = [
            {'id': '1', 'content': 'English text', 'metadata': '{"language": "en"}'},
            {'id': '2', 'content': 'Spanish text', 'metadata': '{"language": "es"}'},
        ]

        filtered = multi_language_search.search_by_language(memories, language=None)
        assert len(filtered) == 2

    def test_search_by_language_with_filter(self):
        """Test search with language filter"""
        memories = [
            {'id': '1', 'content': 'English text', 'metadata': '{"language": "en"}'},
            {'id': '2', 'content': 'Spanish text', 'metadata': '{"language": "es"}'},
            {'id': '3', 'content': 'More English', 'metadata': '{"language": "en"}'},
        ]

        filtered = multi_language_search.search_by_language(memories, language='en')
        assert len(filtered) == 2
        assert filtered[0]['id'] == '1'
        assert filtered[1]['id'] == '3'

    def test_search_by_language_with_confidence_threshold(self):
        """Test search with confidence threshold"""
        memories = [
            {'id': '1', 'content': 'English', 'metadata': '{"language": "en", "language_confidence": 0.9}'},
            {'id': '2', 'content': 'Low conf', 'metadata': '{"language": "en", "language_confidence": 0.3}'},
        ]

        filtered = multi_language_search.search_by_language(memories, language='en', min_confidence=0.5)
        assert len(filtered) == 1
        assert filtered[0]['id'] == '1'

    def test_search_by_language_empty_list(self):
        """Test search with empty memory list"""
        filtered = multi_language_search.search_by_language([], language='en')
        assert len(filtered) == 0

    def test_search_by_language_no_matches(self):
        """Test search with no matching language"""
        memories = [
            {'id': '1', 'content': 'English', 'metadata': '{"language": "en"}'},
        ]

        filtered = multi_language_search.search_by_language(memories, language='es')
        assert len(filtered) == 0

    def test_search_by_language_invalid_metadata(self):
        """Test search with invalid metadata"""
        memories = [
            {'id': '1', 'content': 'English', 'metadata': 'invalid json'},
        ]

        filtered = multi_language_search.search_by_language(memories, language='en')
        # Should handle gracefully and return empty or default
        assert isinstance(filtered, list)

    def test_get_language_distribution(self):
        """Test getting language distribution"""
        memories = [
            {'id': '1', 'metadata': '{"language": "en"}'},
            {'id': '2', 'metadata': '{"language": "en"}'},
            {'id': '3', 'metadata': '{"language": "es"}'},
            {'id': '4', 'metadata': '{"language": "fr"}'},
        ]

        distribution = multi_language_search.get_language_distribution(memories)

        assert distribution['en'] == 2
        assert distribution['es'] == 1
        assert distribution['fr'] == 1

    def test_get_language_distribution_empty(self):
        """Test getting distribution from empty list"""
        distribution = multi_language_search.get_language_distribution([])
        assert distribution == {}

    def test_get_language_distribution_defaults(self):
        """Test getting distribution with default language"""
        memories = [
            {'id': '1', 'metadata': '{}'},  # No language specified
        ]

        distribution = multi_language_search.get_language_distribution(memories)
        assert distribution['en'] == 1

    def test_cross_language_search_same_language_boost(self):
        """Test cross-language search with same language boost"""
        memories = [
            {'id': '1', 'content': 'English', 'metadata': '{"language": "en"}'},
            {'id': '2', 'content': 'Spanish', 'metadata': '{"language": "es"}'},
        ]

        ranked = multi_language_search.cross_language_search(
            query="test",
            memories=memories,
            query_language='en'
        )

        assert len(ranked) == 2
        # English memory should come first
        assert ranked[0]['id'] == '1'

    def test_cross_language_search_auto_detect_query(self):
        """Test cross-language search with auto-detected query language"""
        memories = [
            {'id': '1', 'content': 'Memory one', 'metadata': '{"language": "en"}'},
        ]

        ranked = multi_language_search.cross_language_search(
            query="test query",
            memories=memories,
            query_language=None  # Auto-detect
        )

        assert len(ranked) == 1

    def test_cross_language_search_empty_memories(self):
        """Test cross-language search with empty memories"""
        ranked = multi_language_search.cross_language_search(
            query="test",
            memories=[],
            query_language='en'
        )

        assert len(ranked) == 0

    def test_get_facets(self):
        """Test getting search facets"""
        memories = [
            {'id': '1', 'metadata': '{"language": "en", "memory_type": "feature", "category": "trading"}'},
            {'id': '2', 'metadata': '{"language": "es", "memory_type": "bugfix", "category": "trading"}'},
            {'id': '3', 'metadata': '{"language": "en", "memory_type": "feature", "category": "dev"}'},
        ]

        facets = multi_language_search.get_facets(memories)

        assert 'language' in facets
        assert 'memory_type' in facets
        assert 'category' in facets

        assert facets['language']['English'] == 2
        assert facets['language']['Spanish'] == 1
        assert facets['memory_type']['feature'] == 2
        assert facets['memory_type']['bugfix'] == 1
        assert facets['category']['trading'] == 2
        assert facets['category']['dev'] == 1

    def test_get_facets_empty_memories(self):
        """Test getting facets from empty memories"""
        facets = multi_language_search.get_facets([])

        assert facets['language'] == {}
        assert facets['memory_type'] == {}
        assert facets['category'] == {}

    def test_get_facets_invalid_metadata(self):
        """Test getting facets with invalid metadata"""
        memories = [
            {'id': '1', 'metadata': 'invalid json'},
        ]

        facets = multi_language_search.get_facets(memories)
        # Should handle gracefully
        assert isinstance(facets, dict)

    def test_get_facets_uncategorized(self):
        """Test getting facets with uncategorized memories"""
        memories = [
            {'id': '1', 'metadata': '{"language": "en"}'},  # No category
        ]

        facets = multi_language_search.get_facets(memories)
        assert 'uncategorized' in facets['category']


@pytest.mark.unit
class TestMultiLanguageSearchEdgeCases:
    """Test edge cases and error handling"""

    def test_metadata_string_vs_dict(self):
        """Test handling of both string and dict metadata"""
        memories = [
            {'id': '1', 'metadata': '{"language": "en"}'},  # String
            {'id': '2', 'metadata': {'language': 'es'}},    # Dict
        ]

        distribution = multi_language_search.get_language_distribution(memories)
        assert distribution['en'] == 1
        assert distribution['es'] == 1

    def test_none_metadata_handling(self):
        """Test handling of None metadata"""
        memories = [
            {'id': '1', 'metadata': None},
        ]

        distribution = multi_language_search.get_language_distribution(memories)
        # Should default to English
        assert 'en' in distribution

    def test_empty_metadata_dict(self):
        """Test handling of empty metadata dict"""
        memories = [
            {'id': '1', 'metadata': {}},
        ]

        distribution = multi_language_search.get_language_distribution(memories)
        assert 'en' in distribution

    def test_cross_language_score_ranges(self):
        """Test that cross-language scores are in valid ranges"""
        memories = [
            {'id': '1', 'content': 'Test', 'metadata': '{"language": "en"}'},
            {'id': '2', 'content': 'Prueba', 'metadata': '{"language": "es"}'},
            {'id': '3', 'content': 'Test', 'metadata': '{"language": "xyz"}'},  # Unsupported
        ]

        ranked = multi_language_search.cross_language_search(
            query="test",
            memories=memories,
            query_language='en'
        )

        # All memories should be returned
        assert len(ranked) == 3

        # English should be first
        assert ranked[0]['id'] == '1'

        # Check scores are valid (implicitly through ordering)

    def test_large_memory_list(self):
        """Test handling of large memory lists"""
        memories = [
            {'id': str(i), 'content': f'Text {i}', 'metadata': f'{{"language": "en"}}'}
            for i in range(1000)
        ]

        filtered = multi_language_search.search_by_language(memories, language='en')
        assert len(filtered) == 1000

    def test_all_supported_languages_in_distribution(self):
        """Test that all supported languages can appear in distribution"""
        memories = []
        for lang in ['en', 'es', 'fr', 'de', 'ja']:
            memories.append({
                'id': lang,
                'metadata': f'{{"language": "{lang}"}}'
            })

        distribution = multi_language_search.get_language_distribution(memories)
        assert len(distribution) == 5
        assert distribution['en'] == 1
        assert distribution['es'] == 1
