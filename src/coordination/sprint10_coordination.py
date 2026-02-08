#!/usr/bin/env python3
"""
Sprint 10 Coordination Integration
Connects Intelligent Summarization and Advanced Search with SDLC Sub-Agents
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


class Sprint10CoordinationIntegration:
    """
    Integration layer for Sprint 10 Advanced AI Features
    Coordinates intelligent summarization and advanced search with sub-agents
    """

    def __init__(
        self,
        intelligent_summarizer=None,
        advanced_search_engine=None,
        coordinator=None
    ):
        """
        Initialize Sprint 10 coordination integration

        Args:
            intelligent_summarizer: IntelligentMemorySummarizer instance
            advanced_search_engine: AdvancedSearchEngine instance
            coordinator: SubAgentCoordinator instance
        """
        self.summarizer = intelligent_summarizer
        self.search_engine = advanced_search_engine
        self.coordinator = coordinator

        # Coordination tasks
        self.coordination_tasks = {
            "auto_summarization": {
                "name": "Automatic Memory Summarization",
                "description": "Periodically summarize old memories using LLMs",
                "capable_agents": ["knowledge-graph", "data-processor"],
                "priority": "normal",
                "schedule": "monthly"
            },
            "semantic_clustering": {
                "name": "Semantic Memory Clustering",
                "description": "Cluster related memories using semantic similarity",
                "capable_agents": ["knowledge-graph", "data-processor"],
                "priority": "normal",
                "schedule": "weekly"
            },
            "advanced_search_indexing": {
                "name": "Advanced Search Indexing",
                "description": "Maintain semantic search indexes and embeddings",
                "capable_agents": ["knowledge-graph", "data-processor"],
                "priority": "high",
                "schedule": "daily"
            },
            "query_expansion": {
                "name": "Query Expansion Service",
                "description": "Expand search queries using LLM for better results",
                "capable_agents": ["knowledge-graph", "api-gateway"],
                "priority": "normal",
                "schedule": "on_demand"
            },
            "personalization_learning": {
                "name": "Search Personalization Learning",
                "description": "Learn user preferences for personalized search results",
                "capable_agents": ["knowledge-graph", "context-manager"],
                "priority": "low",
                "schedule": "weekly"
            }
        }

    async def assign_summarization_task(
        self,
        task_id: str,
        created_by: str,
        days_old: int = 30,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Assign automatic summarization task to appropriate sub-agents

        Args:
            task_id: Unique task identifier
            created_by: Agent or user creating the task
            days_old: Age threshold for summarization
            dry_run: If True, simulate without actual summarization

        Returns:
            Task assignment result
        """
        try:
            if not self.summarizer:
                return {
                    "status": "error",
                    "error": "Intelligent Summarizer not available"
                }

            # Find suitable agents for summarization
            suitable_agents = []
            for agent_id in self.coordination_tasks["auto_summarization"]["capable_agents"]:
                if agent_id in self.coordinator.agent_registry:
                    suitable_agents.append(agent_id)

            if not suitable_agents:
                # Default to knowledge-graph agent
                suitable_agents = ["knowledge-graph"]

            # Execute summarization
            result = await self.summarizer.auto_summarize_old_memories(dry_run=dry_run)

            # Store task completion in coordination memory
            await self._store_coordination_result(
                task_id=task_id,
                task_type="auto_summarization",
                result=result,
                assigned_agents=suitable_agents
            )

            logger.info(f"Assigned summarization task {task_id} to agents: {suitable_agents}")

            return {
                "status": "success",
                "task_id": task_id,
                "assigned_agents": suitable_agents,
                "result": result
            }

        except Exception as e:
            logger.error(f"Failed to assign summarization task {task_id}: {e}")
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(e)
            }

    async def assign_clustering_task(
        self,
        task_id: str,
        created_by: str,
        category: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Assign semantic clustering task to appropriate sub-agents

        Args:
            task_id: Unique task identifier
            created_by: Agent or user creating the task
            category: Optional category filter
            agent_id: Optional agent ID filter
            limit: Maximum memories to process

        Returns:
            Task assignment result
        """
        try:
            if not self.summarizer:
                return {
                    "status": "error",
                    "error": "Intelligent Summarizer not available"
                }

            # Find suitable agents
            suitable_agents = []
            for agent_id in self.coordination_tasks["semantic_clustering"]["capable_agents"]:
                if agent_id in self.coordinator.agent_registry:
                    suitable_agents.append(agent_id)

            if not suitable_agents:
                suitable_agents = ["knowledge-graph"]

            # Get memories to cluster
            from ..agent_memory_integration import AgentMemoryIntegration
            integration = AgentMemoryIntegration()
            await integration.initialize()

            # Find memories
            memories = await self.summarizer.find_summarizable_memories(
                days_old=7,  # Recent memories for clustering
                limit=limit
            )

            # Perform clustering
            clusters = await self.summarizer.cluster_memories(memories)

            result = {
                "clusters_created": len(clusters),
                "total_memories_clustered": sum(c.memory_count for c in clusters),
                "cluster_themes": [c.cluster_theme for c in clusters if c.cluster_theme]
            }

            # Store result
            await self._store_coordination_result(
                task_id=task_id,
                task_type="semantic_clustering",
                result=result,
                assigned_agents=suitable_agents
            )

            await integration.close()

            logger.info(f"Assigned clustering task {task_id} to agents: {suitable_agents}")

            return {
                "status": "success",
                "task_id": task_id,
                "assigned_agents": suitable_agents,
                "result": result
            }

        except Exception as e:
            logger.error(f"Failed to assign clustering task {task_id}: {e}")
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(e)
            }

    async def assign_search_task(
        self,
        task_id: str,
        created_by: str,
        query: str,
        user_id: str = "default",
        agent_id: Optional[str] = None,
        strategy: str = "combined"
    ) -> Dict[str, Any]:
        """
        Assign advanced search task to appropriate sub-agents

        Args:
            task_id: Unique task identifier
            created_by: Agent or user creating the task
            query: Search query
            user_id: User identifier
            agent_id: Optional agent filter
            strategy: Re-ranking strategy

        Returns:
            Task assignment result with search results
        """
        try:
            if not self.search_engine:
                return {
                    "status": "error",
                    "error": "Advanced Search Engine not available"
                }

            # Find suitable agents for search
            suitable_agents = []
            for agent_id in self.coordination_tasks["advanced_search_indexing"]["capable_agents"]:
                if agent_id in self.coordinator.agent_registry:
                    suitable_agents.append(agent_id)

            if not suitable_agents:
                suitable_agents = ["knowledge-graph"]

            # Perform advanced search
            from src.advanced_search_reranking import ReRankingStrategy
            rerank_strategy = ReRankingStrategy(strategy.lower())

            results = await self.search_engine.search(
                query=query,
                user_id=user_id,
                agent_id=agent_id,
                limit=20,
                rerank=True,
                strategy=rerank_strategy
            )

            # Format results
            result = {
                "query": query,
                "results_count": len(results),
                "top_results": [
                    {
                        "memory_id": r.memory_id,
                        "rank": r.rank,
                        "score": r.reranked_score,
                        "reason": r.relevance_reason,
                        "content_preview": r.content[:100]
                    }
                    for r in results[:5]
                ]
            }

            # Store search analytics
            await self._store_coordination_result(
                task_id=task_id,
                task_type="advanced_search",
                result=result,
                assigned_agents=suitable_agents
            )

            logger.info(f"Assigned search task {task_id} to agents: {suitable_agents}")

            return {
                "status": "success",
                "task_id": task_id,
                "assigned_agents": suitable_agents,
                "result": result
            }

        except Exception as e:
            logger.error(f"Failed to assign search task {task_id}: {e}")
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(e)
            }

    async def get_coordination_capabilities(self) -> Dict[str, Any]:
        """
        Get all Sprint 10 coordination capabilities

        Returns:
            Available coordination tasks and their configurations
        """
        return {
            "status": "success",
            "coordination_tasks": self.coordination_tasks,
            "available_features": {
                "intelligent_summarization": self.summarizer is not None,
                "advanced_search": self.search_engine is not None,
                "coordination_enabled": self.coordinator is not None
            },
            "total_tasks": len(self.coordination_tasks)
        }

    async def _store_coordination_result(
        self,
        task_id: str,
        task_type: str,
        result: Dict[str, Any],
        assigned_agents: List[str]
    ):
        """Store coordination task result in memory"""
        try:
            if not self.coordinator:
                return

            # Store using SMC wrapper
            from ..agents.smc.smc_memory_wrapper import SMCMemoryWrapper
            smc_wrapper = SMCMemoryWrapper(self.coordinator.integration)

            await smc_wrapper.store_task(
                agent_id="sprint10_coordinator",
                task_data={
                    "task_id": task_id,
                    "type": f"sprint10_{task_type}",
                    "task_type": task_type,
                    "assigned_agents": assigned_agents,
                    "result": result,
                    "status": "completed",
                    "completed_at": datetime.now(UTC).isoformat()
                }
            )

            logger.info(f"Stored coordination result for task {task_id}")

        except Exception as e:
            logger.error(f"Failed to store coordination result: {e}")


# Example usage
async def example_sprint10_coordination():
    """Example usage of Sprint 10 coordination integration"""
    from ..agent_memory_integration import AgentMemoryIntegration
    from .sub_agent_coordinator import SubAgentCoordinator
    from src.intelligent_summarization import IntelligentMemorySummarizer
    from src.advanced_search_reranking import AdvancedSearchEngine

    # Initialize components
    integration = AgentMemoryIntegration()
    await integration.initialize()

    coordinator = SubAgentCoordinator(integration)

    # Create Sprint 10 coordination integration
    # (In real usage, pass actual summarizer and search engine instances)
    sprint10_coord = Sprint10CoordinationIntegration(
        intelligent_summarizer=None,
        advanced_search_engine=None,
        coordinator=coordinator
    )

    # Example 1: Get available capabilities
    capabilities = await sprint10_coord.get_coordination_capabilities()
    print(f"Sprint 10 Capabilities: {capabilities}")

    # Example 2: Assign summarization task
    # summarization_result = await sprint10_coord.assign_summarization_task(
    #     task_id="summarize_001",
    #     created_by="system",
    #     days_old=30,
    #     dry_run=True
    # )
    # print(f"Summarization Result: {summarization_result}")

    # Example 3: Assign advanced search task
    # search_result = await sprint10_coord.assign_search_task(
    #     task_id="search_001",
    #     created_by="user",
    #     query="machine learning algorithms",
    #     user_id="default",
    #     strategy="combined"
    # )
    # print(f"Search Result: {search_result}")

    await integration.close()


if __name__ == "__main__":
    asyncio.run(example_sprint10_coordination())
