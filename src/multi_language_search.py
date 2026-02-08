"""
Multi-Language Search Module for Enhanced Cognee

Provides language-aware search capabilities with support for 28 languages.
"""

import logging
from typing import List, Dict, Optional, Any
from .language_detector import language_detector

logger = logging.getLogger(__name__)

class MultiLanguageSearch:
    """Multi-language search with language filtering and cross-language support"""

    def __init__(self, db_client=None):
        self.db_client = db_client
        self.default_language = 'en'

    def add_language_metadata(
        self,
        content: str,
        existing_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Add language detection metadata to memory.

        Args:
            content: Memory content
            existing_metadata: Existing metadata to merge with

        Returns:
            Enhanced metadata with language information
        """
        # Detect language
        lang_metadata = language_detector.detect_with_metadata(content)

        # Merge with existing metadata
        if existing_metadata:
            metadata = existing_metadata.copy()
        else:
            metadata = {}

        # Add language metadata
        metadata.update({
            'language': lang_metadata['language_code'],
            'language_name': lang_metadata['language_name'],
            'language_confidence': lang_metadata['confidence'],
            'language_supported': lang_metadata['supported']
        })

        return metadata

    def search_by_language(
        self,
        memories: List[Dict],
        language: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Filter memories by language.

        Args:
            memories: List of memory dictionaries
            language: Language code to filter by (None = all languages)
            min_confidence: Minimum confidence threshold

        Returns:
            Filtered list of memories
        """
        if not language:
            # No language filter, return all
            return memories

        filtered = []
        for memory in memories:
            metadata = memory.get('metadata') or {}
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            memory_lang = metadata.get('language', self.default_language)
            # If language_confidence is not present, assume high confidence (1.0)
            confidence = metadata.get('language_confidence', 1.0)

            # Filter by language and confidence
            if memory_lang == language and confidence >= min_confidence:
                filtered.append(memory)

        logger.info(f"Filtered {len(memories)} memories to {len(filtered)} by language '{language}'")
        return filtered

    def get_language_distribution(self, memories: List[Dict]) -> Dict[str, int]:
        """
        Get distribution of languages across memories.

        Args:
            memories: List of memory dictionaries

        Returns:
            Dictionary mapping language codes to counts
        """
        distribution = {}

        for memory in memories:
            metadata = memory.get('metadata') or {}
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            lang = metadata.get('language', self.default_language)
            distribution[lang] = distribution.get(lang, 0) + 1

        return distribution

    def cross_language_search(
        self,
        query: str,
        memories: List[Dict],
        query_language: Optional[str] = None
    ) -> List[Dict]:
        """
        Perform cross-language search.

        Searches memories in any language, with relevance boosting
        for memories in the same language as the query.

        Args:
            query: Search query text
            memories: List of memory dictionaries
            query_language: Query language code (auto-detected if None)

        Returns:
            Ranked list of memories
        """
        # Detect query language if not provided
        if not query_language:
            query_language, _ = language_detector.detect_language(query)

        # Score memories based on language match
        scored_memories = []
        for memory in memories:
            metadata = memory.get('metadata') or {}
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            memory_lang = metadata.get('language', self.default_language)

            # Calculate language relevance score
            if memory_lang == query_language:
                lang_score = 1.0  # Same language
            elif language_detector.is_supported(memory_lang):
                lang_score = 0.7  # Different supported language
            else:
                lang_score = 0.5  # Unsupported language

            # Store with score
            scored_memories.append({
                'memory': memory,
                'lang_score': lang_score,
                'language': memory_lang
            })

        # Sort by language score
        scored_memories.sort(key=lambda x: x['lang_score'], reverse=True)

        # Return memories in order with language information
        for item in scored_memories:
            item['memory']['language'] = item['language']
        return [item['memory'] for item in scored_memories]

    def get_facets(self, memories: List[Dict]) -> Dict[str, Dict[str, int]]:
        """
        Get search facets for filtering.

        Args:
            memories: List of memory dictionaries

        Returns:
            Dictionary of facet names to facet values
        """
        facets = {
            'language': {},
            'memory_type': {},
            'category': {}
        }

        for memory in memories:
            metadata = memory.get('metadata') or {}
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            # Language facet
            lang = metadata.get('language', self.default_language)
            lang_name = language_detector.get_language_name(lang)
            facets['language'][lang_name] = facets['language'].get(lang_name, 0) + 1

            # Memory type facet
            memory_type = metadata.get('memory_type', 'general')
            facets['memory_type'][memory_type] = facets['memory_type'].get(memory_type, 0) + 1

            # Category facet
            category = metadata.get('category', 'uncategorized')
            facets['category'][category] = facets['category'].get(category, 0) + 1

        return facets

# Singleton instance
multi_language_search = MultiLanguageSearch()
