"""
Advanced Search with Re-ranking for Enhanced Cognee
Implements semantic search with intelligent re-ranking, query expansion, and multi-modal search
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, UTC
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class ReRankingStrategy(Enum):
    """Re-ranking strategies"""
    RELEVANCE = "relevance"  # Pure relevance score
    RECENCY = "recency"  # Prefer recent results
    COMBINED = "combined"  # Balance relevance and recency
    PERSONALIZED = "personalized"  # Based on user behavior


@dataclass
class SearchResult:
    """Enhanced search result with re-ranking metadata"""
    memory_id: str
    content: str
    metadata: Dict[str, Any]
    score: float  # Initial search score
    reranked_score: float  # Final score after re-ranking
    rank: int
    highlights: List[str] = None  # Highlighted text snippets
    relevance_reason: str = ""  # Why this result was ranked highly
    created_at: Optional[datetime] = None
    agent_id: Optional[str] = None


class AdvancedSearchEngine:
    """
    Advanced Search Engine with Re-ranking

    Features:
    - Semantic search with vector embeddings
    - Intelligent query re-ranking
    - Query understanding and expansion
    - Multi-modal search (text + metadata)
    - Result highlighting
    """

    def __init__(
        self,
        postgres_pool,
        qdrant_client,
        redis_client=None,
        llm_config=None
    ):
        """
        Initialize advanced search engine

        Args:
            postgres_pool: PostgreSQL connection pool
            qdrant_client: Qdrant client for vector search
            redis_client: Redis client for caching
            llm_config: LLM configuration for query expansion
        """
        self.postgres_pool = postgres_pool
        self.qdrant_client = qdrant_client
        self.redis_client = redis_client
        self.llm_config = llm_config

        # Search settings
        self.default_limit = 20
        self.reranking_weights = {
            "semantic": 0.5,
            "keyword": 0.3,
            "recency": 0.2
        }

    async def search(
        self,
        query: str,
        user_id: str = "default",
        agent_id: Optional[str] = None,
        limit: int = 20,
        rerank: bool = True,
        strategy: ReRankingStrategy = ReRankingStrategy.COMBINED,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Perform advanced search with re-ranking

        Args:
            query: Search query
            user_id: User ID for personalization
            agent_id: Filter by agent ID
            limit: Maximum results
            rerank: Whether to apply re-ranking
            strategy: Re-ranking strategy
            filters: Optional filters (category, date range, etc.)

        Returns:
            List of re-ranked search results
        """
        try:
            # Step 1: Query expansion
            expanded_queries = await self._expand_query(query)

            # Step 2: Multi-modal search
            initial_results = await self._multi_modal_search(
                expanded_queries,
                filters
            )

            # Step 3: Re-ranking
            if rerank:
                results = await self._rerank_results(
                    initial_results,
                    query,
                    user_id,
                    strategy
                )
            else:
                results = initial_results

            # Step 4: Apply limit
            results = results[:limit]

            # Step 5: Add highlights
            for result in results:
                result.highlights = self._extract_highlights(
                    query,
                    result.content
                )

            return results

        except Exception as e:
            logger.error(f"Error in advanced search: {e}")
            return []

    async def _expand_query(self, query: str) -> List[str]:
        """
        Expand query with synonyms and related terms

        Args:
            query: Original query

        Returns:
            List of expanded queries
        """
        expanded = [query]

        try:
            # Check cache first
            cache_key = f"query_expansion:{hash(query)}"
            if self.redis_client:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)

            # Use LLM for query expansion
            if self.llm_config:
                llm_expansions = await self._llm_expand_query(query)
                expanded.extend(llm_expansions)

            # Add keyword-based expansions
            keyword_expansions = self._extract_keywords_for_expansion(query)
            expanded.extend(keyword_expansions)

            # Remove duplicates while preserving order
            seen = set()
            unique_expanded = []
            for q in expanded:
                if q.lower() not in seen:
                    seen.add(q.lower())
                    unique_expanded.append(q)

            # Cache results
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key,
                    3600,  # 1 hour
                    json.dumps(unique_expanded)
                )

            return unique_expanded[:5]  # Limit to 5 expanded queries

        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return [query]

    async def _llm_expand_query(self, query: str) -> List[str]:
        """Use LLM to generate related search queries"""
        try:
            provider = self.llm_config.get('provider', 'anthropic')

            if provider == 'anthropic':
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=self.llm_config.get('api_key'))

                message = await client.messages.create(
                    model=self.llm_config.get('model', 'claude-3-5-haiku-20241022'),
                    max_tokens=200,
                    temperature=0.5,
                    messages=[
                        {"role": "user", "content": f"""Generate 3-4 related search queries for this query. Return only the queries, one per line.

Query: {query}

Related queries:""""}
                    ]
                )

                response_text = message.content[0].text
                queries = [line.strip() for line in response_text.split('\n') if line.strip()]
                return queries

            elif provider == 'openai':
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=self.llm_config.get('api_key'))

                response = await client.chat.completions.create(
                    model=self.llm_config.get('model', 'gpt-4'),
                    messages=[
                        {"role": "system", "content": "Generate 3-4 related search queries, one per line."},
                        {"role": "user", "content": f"Query: {query}\n\nRelated queries:"}
                    ],
                    temperature=0.5
                )

                content = response.choices[0].message.content
                queries = [line.strip() for line in content.split('\n') if line.strip()]
                return queries

            else:
                return []

        except Exception as e:
            logger.error(f"LLM query expansion error: {e}")
            return []

    def _extract_keywords_for_expansion(self, query: str) -> List[str]:
        """Extract keywords and generate variant queries"""
        # Extract significant terms (words longer than 3 chars)
        words = re.findall(r'\b\w{4,}\b', query.lower())

        expansions = []

        # Add synonyms/variants for each keyword
        for word in words[:5]:  # Limit to 5 keywords
            # Simple synonym expansion (in production, use a thesaurus)
            synonyms = self._get_synonyms(word)
            expansions.extend(synonyms)

            # Phrase variants
            expansions.append(f'"{word}"')  # Exact phrase
            expansions.append(f'*{word}*')  # Fuzzy

        return expansions[:10]  # Limit expansions

    def _get_synonyms(self, word: str) -> List[str]:
        """Get synonyms for a word (simplified implementation)"""
        # In production, integrate with WordNet or similar
        # For now, return empty
        return []

    async def _multi_modal_search(
        self,
        queries: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Perform multi-modal search (text + metadata)

        Args:
            queries: Expanded query list
            filters: Optional filters

        Returns:
            List of search results with combined scores
        """
        all_results = {}

        for query in queries:
            # Text search (PostgreSQL full-text search)
            text_results = await self._text_search(query, filters)

            # Semantic search (Qdrant)
            semantic_results = await self._semantic_search(query, filters)

            # Combine results for this query
            for result in text_results:
                memory_id = result['memory_id']
                if memory_id not in all_results:
                    all_results[memory_id] = result
                    all_results[memory_id]['semantic_score'] = 0.0

            # Update semantic scores
            for sem_result in semantic_results:
                memory_id = sem_result['memory_id']
                if memory_id in all_results:
                    all_results[memory_id]['semantic_score'] = sem_result['score']

        # Calculate combined scores
        results = []
        for memory_id, data in all_results.items():
            # Combine text and semantic scores
            text_score = data.get('rank_score', 0.0)
            semantic_score = data.get('semantic_score', 0.0)

            # Normalize scores
            combined_score = (
                text_score * self.reranking_weights['keyword'] +
                semantic_score * self.reranking_weights['semantic']
            )

            results.append(SearchResult(
                memory_id=memory_id,
                content=data.get('content', ''),
                metadata=data.get('metadata', {}),
                score=combined_score,
                reranked_score=0.0,  # Will be set in rerank step
                rank=0,
                created_at=data.get('created_at'),
                agent_id=data.get('agent_id')
            ))

        return results

    async def _text_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Full-text search using PostgreSQL"""
        try:
            async with self.postgres_pool.acquire() as conn:
                # Build query with filters
                where_clauses = []
                params = []

                # Base text search
                search_query = """
                    SELECT
                        id as memory_id,
                        content,
                        metadata,
                        agent_id,
                        created_at,
                        ts_rank(to_tsvector('english', coalesce(content, '')), 1) as rank_score
                    FROM shared_memory.documents
                    WHERE to_tsvector('english', coalesce(content, '')) @@ plainto_tsquery('english', $1)
                """
                params.append(query)

                # Add filters
                if filters:
                    if 'agent_id' in filters:
                        where_clauses.append("agent_id = $2")
                        params.append(filters['agent_id'])

                    if 'category' in filters:
                        where_clauses.append("metadata->>'memory_category' = $3")
                        params.append(filters['category'])

                    if 'start_date' in filters:
                        where_clauses.append("created_at >= $4")
                        params.append(filters['start_date'])

                if where_clauses:
                    search_query += " AND " + " AND ".join(where_clauses)

                search_query += " ORDER BY rank_score DESC LIMIT 50"

                results = await conn.fetch(search_query, *params)

                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Text search error: {e}")
            return []

    async def _semantic_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search using Qdrant"""
        try:
            if not self.qdrant_client:
                logger.warning("Qdrant not available, skipping semantic search")
                return []

            # Get query embedding
            query_vector = self._get_embedding(query)

            # Search in Qdrant
            search_result = self.qdrant_client.search(
                collection_name="cognee_general_memory",
                query_vector=query_vector,
                limit=50,
                score_threshold=0.6  # Only include relevant results
            )

            results = []
            for hit in search_result:
                memory_data = hit.payload or {}
                results.append({
                    'memory_id': hit.id,
                    'score': hit.score,
                    'content': memory_data.get('content', ''),
                    'metadata': memory_data.get('metadata', {}),
                    'agent_id': memory_data.get('agent_id', ''),
                    'created_at': memory_data.get('created_at')
                })

            return results

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    async def _rerank_results(
        self,
        results: List[SearchResult],
        original_query: str,
        user_id: str,
        strategy: ReRankingStrategy
    ) -> List[SearchResult]:
        """
        Re-rank search results based on strategy

        Args:
            results: Initial search results
            original_query: Original search query
            user_id: User ID for personalization
            strategy: Re-ranking strategy

        Returns:
            Re-ranked search results
        """
        try:
            for i, result in enumerate(results):
                # Base score from initial search
                base_score = result.score

                # Apply re-ranking based on strategy
                if strategy == ReRankingStrategy.RELEVANCE:
                    reranked_score = base_score
                    result.relevance_reason = "high_relevance"

                elif strategy == ReRankingStrategy.RECENCY:
                    # Boost recent results
                    if result.created_at:
                        days_old = (datetime.now(UTC) - result.created_at).days
                        recency_boost = max(0.1, 1.0 - (days_old / 365))
                        reranked_score = base_score * (1 + recency_boost)
                        result.relevance_reason = f"recent ({days_old} days old)"
                    else:
                        reranked_score = base_score
                        result.relevance_reason = "recency_boost"

                elif strategy == ReRankingStrategy.COMBINED:
                    # Combined scoring
                    reranked_score = base_score

                    # Recency boost
                    if result.created_at:
                        days_old = (datetime.now(UTC) - result.created_at).days
                        if days_old < 7:
                            reranked_score *= 1.2  # Boost recent memories
                            result.relevance_reason = "recent_and_relevant"
                        elif days_old < 30:
                            reranked_score *= 1.1
                            result.relevance_reason = "moderately_recent"
                        else:
                            reranked_score *= 0.9
                            result.relevance_reason = "older_but_relevant"

                elif strategy == ReRankingStrategy.PERSONALIZED:
                    # Personalized based on user behavior
                    reranked_score = await self._personalized_score(
                        result,
                        user_id,
                        original_query
                    )
                    result.relevance_reason = "personalized"

                result.reranked_score = reranked_score

            # Sort by reranked score
            results.sort(key=lambda x: x.reranked_score, reverse=True)

            # Update ranks
            for i, result in enumerate(results):
                result.rank = i + 1

            return results

        except Exception as e:
            logger.error(f"Re-ranking error: {e}")
            return results

    async def _personalized_score(
        self,
        result: SearchResult,
        user_id: str,
        query: str
    ) -> float:
        """Calculate personalized score based on user behavior"""
        try:
            # In a real implementation, this would:
            # 1. Check user's past interactions with this memory
            # 2. Boost memories the user has viewed/clicked
            # 3. Boost memories from the user's preferred agents
            # 4. Consider time of day and user's search patterns

            # For now, apply simple personalization
            score = result.score

            # Boost if from same agent
            if result.agent_id == user_id:
                score *= 1.3

            # TODO: Add more sophisticated personalization
            # - Track user search history in Redis
            # - Calculate affinity scores
            # - Apply collaborative filtering

            return score

        except Exception as e:
            logger.error(f"Personalization error: {e}")
            return result.score

    def _extract_highlights(self, query: str, content: str) -> List[str]:
        """
        Extract highlighted snippets from content

        Args:
            query: Search query
            content: Memory content

        Returns:
            List of highlighted text snippets
        """
        highlights = []

        try:
            # Split query into terms
            terms = re.findall(r'\w+', query.lower())

            # Split content into sentences
            sentences = re.split(r'[.!?]+', content)

            for sentence in sentences:
                sentence_lower = sentence.lower()
                # Check if sentence contains query terms
                matched_terms = [term for term in terms if term in sentence_lower]

                if matched_terms:
                    # Truncate to reasonable length
                    snippet = sentence.strip()[:200]
                    if len(snippet) > 50:  # Only meaningful snippets
                        highlights.append(snippet)

                    if len(highlights) >= 3:  # Limit highlights
                        break

        except Exception as e:
            logger.error(f"Highlight extraction error: {e}")

        return highlights[:3]

    def _get_embedding(self, text: str) -> List[float]:
        """Get text embedding for semantic search"""
        # This would use an embedding model
        # For now, return a placeholder
        # In production, use: sentence-transformers, openai embeddings, etc.
        import random
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        random.seed(hash_val)

        return [random.random() for _ in range(1536)]

    async def get_search_analytics(
        self,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get search analytics and statistics"""
        try:
            async with self.postgres_pool.acquire() as conn:
                # Total searches
                total_searches = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM search_analytics
                    WHERE timestamp > NOW() - INTERVAL '%s days'
                """, days_back)

                # Average query length
                avg_query_length = await conn.fetchval("""
                    SELECT AVG(LENGTH(query))
                    FROM search_analytics
                    WHERE timestamp > NOW() - INTERVAL '%s days'
                """, days_back)

                # Top search terms
                top_terms = await conn.fetch("""
                    SELECT query_term, COUNT(*) as count
                    FROM search_analytics
                    WHERE timestamp > NOW() - INTERVAL '%s days'
                    GROUP BY query_term
                    ORDER BY count DESC
                    LIMIT 10
                """, days_back)

                # Zero result rate
                zero_results = await conn.fetchval("""
                    SELECT COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM search_analytics
                    WHERE timestamp > NOW() - INTERVAL '%s days'), 0)
                    FROM search_analytics
                    WHERE timestamp > NOW() - INTERVAL '%s days'
                    AND results_count = 0
                """, days_back)

                return {
                    "status": "success",
                    "total_searches": total_searches,
                    "avg_query_length": float(avg_query_length) if avg_query_length else 0,
                    "top_search_terms": [dict(row) for row in top_terms],
                    "zero_results_rate": float(zero_results) if zero_results else 0.0
                }

        except Exception as e:
            logger.error(f"Error getting search analytics: {e}")
            return {"status": "error", "error": str(e)}