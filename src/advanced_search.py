"""
Advanced Search Module for Enhanced Cognee

Provides faceted search, autocomplete suggestions, and fuzzy search.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from collections import Counter
import re

logger = logging.getLogger(__name__)

class AdvancedSearch:
    """Advanced search features with faceting and suggestions"""

    def __init__(self):
        self.search_history = []
        self.popular_terms = Counter()

    def faceted_search(
        self,
        memories: List[Dict],
        filters: Dict[str, Any]
    ) -> List[Dict]:
        """
        Perform faceted search with multiple filters.

        Args:
            memories: List of memory dictionaries
            filters: Dictionary of facet filters
                - language: List of language codes
                - memory_type: List of memory types
                - category: List of categories
                - date_range: Tuple of (start_date, end_date)

        Returns:
            Filtered list of memories
        """
        filtered = memories

        # Filter by language
        if 'language' in filters and filters['language']:
            filtered = [
                m for m in filtered
                if self._get_language(m) in filters['language']
            ]

        # Filter by memory type
        if 'memory_type' in filters and filters['memory_type']:
            filtered = [
                m for m in filtered
                if self._get_memory_type(m) in filters['memory_type']
            ]

        # Filter by category
        if 'category' in filters and filters['category']:
            filtered = [
                m for m in filtered
                if self._get_category(m) in filters['category']
            ]

        # Filter by date range
        if 'date_range' in filters and filters['date_range']:
            start_date, end_date = filters['date_range']
            filtered = [
                m for m in filtered
                if self._is_date_in_range(m, start_date, end_date)
            ]

        logger.info(f"Faceted search: {len(memories)} -> {len(filtered)} memories")
        return filtered

    async def get_search_suggestions(
        self,
        partial_query: str,
        memories: List[Dict],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get autocomplete suggestions for search query.

        Args:
            partial_query: Partial search query
            memories: List of memories to analyze
            limit: Maximum suggestions

        Returns:
            List of suggestion dictionaries
        """
        suggestions = []

        # Extract words from partial query
        query_words = set(partial_query.lower().split())

        # Find frequent terms in memories
        all_terms = Counter()
        for memory in memories:
            content = memory.get('content', '').lower()
            words = re.findall(r'\b\w+\b', content)
            all_terms.update(words)

        # Suggest completions based on partial query
        for term, count in all_terms.most_common(limit * 5):
            if term.startswith(partial_query.lower()) or any(
                word in term for word in query_words
            ):
                suggestions.append({
                    'term': term,
                    'count': count,
                    'type': 'term'
                })

                if len(suggestions) >= limit:
                    break

        # Add popular search history suggestions
        for query in self.popular_terms:
            if query.startswith(partial_query.lower()):
                suggestions.append({
                    'term': query,
                    'count': self.popular_terms[query],
                    'type': 'history'
                })

        return sorted(suggestions, key=lambda x: x['count'], reverse=True)[:limit]

    async def fuzzy_search(
        self,
        query: str,
        memories: List[Dict],
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform fuzzy search with typo tolerance.

        Args:
            query: Search query
            memories: List of memories to search
            threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            List of memories with similarity scores
        """
        results = []
        query_words = set(query.lower().split())

        for memory in memories:
            content = memory.get('content', '').lower()
            content_words = set(re.findall(r'\b\w+\b', content))

            # Calculate Jaccard similarity
            intersection = query_words & content_words
            union = query_words | content_words

            if len(union) > 0:
                similarity = len(intersection) / len(union)
            else:
                similarity = 0.0

            if similarity >= threshold:
                results.append({
                    'memory': memory,
                    'similarity': similarity
                })

        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)

        return results

    def get_facet_counts(
        self,
        memories: List[Dict]
    ) -> Dict[str, Dict[str, int]]:
        """
        Get facet value counts for filtering UI.

        Args:
            memories: List of memory dictionaries

        Returns:
            Dictionary of facet names to value counts
        """
        facets = {
            'language': Counter(),
            'memory_type': Counter(),
            'category': Counter(),
            'date_range': Counter()
        }

        for memory in memories:
            facets['language'][self._get_language(memory)] += 1
            facets['memory_type'][self._get_memory_type(memory)] += 1
            facets['category'][self._get_category(memory)] += 1

            # Date range facet (by month)
            date_str = memory.get('created_at', '')[:7]  # YYYY-MM
            if date_str:
                facets['date_range'][date_str] += 1

        return {k: dict(v) for k, v in facets.items()}

    def _get_language(self, memory: Dict) -> str:
        """Extract language from memory metadata"""
        metadata = memory.get('metadata') or {}
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        return metadata.get('language', 'en')

    def _get_memory_type(self, memory: Dict) -> str:
        """Extract memory type from metadata"""
        metadata = memory.get('metadata') or {}
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        return metadata.get('memory_type', 'general')

    def _get_category(self, memory: Dict) -> str:
        """Extract category from metadata"""
        metadata = memory.get('metadata') or {}
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        return metadata.get('category', 'uncategorized')

    def _is_date_in_range(
        self,
        memory: Dict,
        start_date: str,
        end_date: str
    ) -> bool:
        """Check if memory date is in range"""
        created_at = memory.get('created_at', '')
        return start_date <= created_at[:10] <= end_date

    def track_search(self, query: str):
        """Track search query for suggestions"""
        self.search_history.append({
            'query': query,
            'timestamp': self._get_timestamp()
        })
        self.popular_terms[query] += 1

    def get_search_history(self, limit: int = 10) -> List[Dict]:
        """Get recent search history"""
        return self.search_history[-limit:]

    def clear_search_history(self):
        """Clear search history"""
        self.search_history.clear()
        self.popular_terms.clear()
        logger.info("OK Search history cleared")

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

# Singleton instance
advanced_search = AdvancedSearch()
