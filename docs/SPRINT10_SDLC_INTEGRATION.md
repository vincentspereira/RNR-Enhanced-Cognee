# Sprint 10 SDLC Sub-Agent Integration Guide

## Overview

This guide explains how to integrate Sprint 10 Advanced AI Features (Intelligent Summarization and Advanced Search) with the SDLC sub-agent coordination system.

## Architecture

```
Sprint 10 Advanced AI Features
├── Intelligent Memory Summarization
│   ├── LLM-based summarization (OpenAI, Anthropic, Ollama)
│   ├── Semantic memory clustering
│   ├── Knowledge extraction
│   └── Auto-summarization of old memories
└── Advanced Search with Re-ranking
    ├── Query expansion using LLMs
    ├── Multi-modal search (text + semantic)
    ├── Multiple re-ranking strategies
    └── Result highlighting

        ↓ Coordination Layer

SDLC Sub-Agent Coordination System
├── SubAgentCoordinator (21 agents)
├── TaskOrchestrationEngine
├── Sprint10CoordinationIntegration
└── Distributed task execution

        ↓ Agent Registry

21 Sub-Agents across categories:
├── ATS (7 agents): Trading system agents
├── OMA (10 agents): Development tools
└── SMC (6 agents): Coordination tools
```

## Sprint 10 Coordination Tasks

### 1. Automatic Memory Summarization

**Purpose:** Periodically summarize old memories using LLMs

**Capable Agents:**
- `knowledge-graph` - Primary agent for knowledge management
- `data-processor` - Handles batch data processing

**Schedule:** Monthly (configurable)

**Usage:**
```python
from src.coordination.sprint10_coordination import Sprint10CoordinationIntegration

# Initialize coordination integration
coord = Sprint10CoordinationIntegration(
    intelligent_summarizer=summarizer,
    advanced_search_engine=search_engine,
    coordinator=coordinator
)

# Assign summarization task
result = await coord.assign_summarization_task(
    task_id="summarize_001",
    created_by="system",
    days_old=30,
    dry_run=False  # Set True for testing
)

print(f"Summarization Result: {result}")
```

### 2. Semantic Memory Clustering

**Purpose:** Cluster related memories using semantic similarity

**Capable Agents:**
- `knowledge-graph` - Manages knowledge graph
- `data-processor` - Processes data for clustering

**Schedule:** Weekly

**Usage:**
```python
# Assign clustering task
result = await coord.assign_clustering_task(
    task_id="cluster_001",
    created_by="knowledge-graph",
    category=None,  # All categories
    agent_id=None,  # All agents
    limit=100
)

print(f"Clustering Result: {result}")
```

### 3. Advanced Search Indexing

**Purpose:** Maintain semantic search indexes and embeddings

**Capable Agents:**
- `knowledge-graph` - Updates knowledge graph
- `data-processor` - Processes search indexes

**Schedule:** Daily

**Usage:**
```python
# Assign search task
result = await coord.assign_search_task(
    task_id="search_001",
    created_by="user",
    query="machine learning algorithms",
    user_id="default",
    agent_id=None,
    strategy="combined"  # relevance, recency, combined, personalized
)

print(f"Search Result: {result}")
```

## MCP Tool Integration

Sprint 10 tools are now available through the MCP server:

### Intelligent Summarization Tools

```bash
# Summarize a specific memory
call_tool: intelligent_summarize
parameters:
  memory_id: "uuid-here"
  strategy: "standard"  # concise, standard, detailed, extractive
  llm_provider: "openai"  # openai, anthropic, ollama

# Auto-summarize old memories
call_tool: auto_summarize_old_memories
parameters:
  days_old: 30
  min_length: 500
  dry_run: false
  strategy: "standard"

# Cluster memories
call_tool: cluster_memories
parameters:
  category: null  # optional filter
  agent_id: null  # optional filter
  limit: 100
```

### Advanced Search Tools

```bash
# Advanced search with re-ranking
call_tool: advanced_search
parameters:
  query: "machine learning"
  user_id: "default"
  agent_id: null  # optional filter
  limit: 20
  rerank: true
  strategy: "combined"  # relevance, recency, combined, personalized
  expand_query: true

# Expand search query
call_tool: expand_search_query
parameters:
  query: "trading strategy"
  max_expansions: 5

# Get search analytics
call_tool: get_search_analytics
parameters:
  days_back: 30
```

## Sub-Agent Capability Mapping

### Knowledge-Graph Agent

**Primary Responsibilities:**
- Semantic search indexing
- Memory clustering
- Knowledge graph management

**Sprint 10 Tasks:**
- Auto-summarization coordination
- Semantic clustering execution
- Advanced search indexing

### Data-Processor Agent

**Primary Responsibilities:**
- Batch data processing
- ETL operations
- Data transformation

**Sprint 10 Tasks:**
- Large-scale summarization
- Clustering batch processing
- Index updates

### API-Gateway Agent

**Primary Responsibilities:**
- API management
- Request routing
- Rate limiting

**Sprint 10 Tasks:**
- Query expansion service
- Search request routing
- Result formatting

### Context-Manager Agent

**Primary Responsibilities:**
- Context sharing
- Session management
- State tracking

**Sprint 10 Tasks:**
- Search personalization learning
- User preference tracking
- Result caching

## Task Orchestration Workflows

### Workflow 1: Memory Optimization Pipeline

```python
from src.coordination.task_orchestration import (
    TaskOrchestrationEngine, WorkflowDefinition, AgentTask, TaskDependency,
    TaskPriority
)

# Define tasks
summarize_task = AgentTask(
    task_id="auto_summarize",
    title="Auto-summarize old memories",
    description="Summarize memories older than 30 days",
    assigned_to=[],
    created_by="system",
    priority=TaskPriority.NORMAL
)

cluster_task = AgentTask(
    task_id="cluster_memories",
    title="Cluster related memories",
    description="Create semantic clusters",
    assigned_to=[],
    created_by="system",
    priority=TaskPriority.NORMAL
)

# Create dependencies
dependencies = [
    TaskDependency("cluster_memories", "auto_summarize", "completion")
]

# Create workflow
workflow = WorkflowDefinition(
    workflow_id="memory_optimization_001",
    name="Memory Optimization Workflow",
    description="Summarize and cluster old memories",
    created_by="system",
    tasks=[summarize_task, cluster_task],
    dependencies=dependencies
)

# Execute workflow
orchestrator = TaskOrchestrationEngine(coordinator)
workflow_id = await orchestrator.create_workflow(workflow)
execution_id = await orchestrator.execute_workflow(workflow_id)

# Monitor progress
status = await orchestrator.get_workflow_status(execution_id)
print(f"Workflow Status: {status}")
```

### Workflow 2: Intelligent Search Pipeline

```python
# Define search-related tasks
expand_task = AgentTask(
    task_id="expand_query",
    title="Expand search query",
    description="Use LLM to expand search query",
    assigned_to=["api-gateway"],
    created_by="user",
    priority=TaskPriority.HIGH
)

search_task = AgentTask(
    task_id="advanced_search",
    title="Perform advanced search",
    description="Search with re-ranking",
    assigned_to=["knowledge-graph"],
    created_by="user",
    priority=TaskPriority.HIGH
)

rerank_task = AgentTask(
    task_id="rerank_results",
    title="Re-rank search results",
    description="Apply personalized re-ranking",
    assigned_to=["context-manager"],
    created_by="user",
    priority=TaskPriority.HIGH
)

# Create workflow
dependencies = [
    TaskDependency("advanced_search", "expand_query", "completion"),
    TaskDependency("rerank_results", "advanced_search", "success")
]

workflow = WorkflowDefinition(
    workflow_id="intelligent_search_001",
    name="Intelligent Search Workflow",
    description="Advanced search with query expansion and re-ranking",
    created_by="user",
    tasks=[expand_task, search_task, rerank_task],
    dependencies=dependencies
)
```

## Configuration

### LLM Configuration

Set in `.env`:

```bash
# LLM Provider Configuration
LLM_PROVIDER=openai  # openai, anthropic, ollama
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4-turbo  # or claude-3-5-sonnet-20241022, llama2

# For Anthropic Claude
ANTHROPIC_API_KEY=your-api-key-here

# For Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### Sprint 10 Settings

```python
# Intelligent Summarization settings
min_memory_age_days = 30  # Summarize memories older than 30 days
min_memory_length = 500    # Only summarize if longer than 500 chars
batch_size = 10            # Process memories in batches
clustering_threshold = 0.75  # Similarity threshold for clustering

# Advanced Search settings
reranking_weights = {
    "semantic": 0.5,
    "keyword": 0.3,
    "recency": 0.2
}
default_limit = 20
query_expansion_enabled = True
```

## Performance Considerations

### Scalability

- **Parallel Processing:** Use multiple sub-agents for large-scale summarization
- **Batch Operations:** Process memories in batches (default: 10-100)
- **Caching:** Redis caches query expansions and search results

### Resource Optimization

- **LLM Rate Limiting:** Respect LLM provider rate limits
- **Query Expansion:** Cache expanded queries for 1 hour
- **Embedding Generation:** Batch embedding generation for efficiency

### Monitoring

Track Sprint 10 metrics:
```python
# Get summarization stats
stats = await intelligent_summarizer.get_summarization_statistics()

# Get search analytics
analytics = await advanced_search_engine.get_search_analytics(days_back=30)

# Get coordination overview
overview = await coordinator.get_coordination_overview()
```

## Troubleshooting

### Issue: Summarization fails with LLM API error

**Solution:**
- Check API key is configured
- Verify LLM provider is accessible
- Check rate limits
- Try alternative LLM provider

### Issue: Search returns no results

**Solution:**
- Verify Qdrant is running
- Check embeddings are generated
- Verify query expansion is working
- Try different re-ranking strategy

### Issue: Clustering is slow

**Solution:**
- Reduce `limit` parameter
- Increase `clustering_threshold`
- Use fewer memories for clustering
- Check Qdrant performance

## Best Practices

1. **Start with Dry Run:** Always use `dry_run=True` for testing
2. **Monitor LLM Costs:** Track token usage and costs
3. **Use Appropriate Strategy:** Choose summarization strategy based on use case
4. **Personalize Results:** Use personalized re-ranking for better UX
5. **Cache Results:** Leverage Redis caching for frequently accessed data
6. **Schedule Maintenance:** Use maintenance scheduler for periodic tasks

## Examples

### Example 1: Daily Memory Maintenance

```python
async def daily_memory_maintenance():
    """Run daily memory optimization tasks"""

    # 1. Auto-summarize old memories (dry run first)
    summary_result = await coord.assign_summarization_task(
        task_id=f"daily_summary_{datetime.now().strftime('%Y%m%d')}",
        created_by="maintenance_scheduler",
        days_old=30,
        dry_run=False
    )

    # 2. Cluster recent memories
    cluster_result = await coord.assign_clustering_task(
        task_id=f"daily_cluster_{datetime.now().strftime('%Y%m%d')}",
        created_by="maintenance_scheduler",
        limit=50
    )

    return {
        "summarization": summary_result,
        "clustering": cluster_result
    }
```

### Example 2: Intelligent Search for User Query

```python
async def intelligent_user_query(query: str, user_id: str):
    """Perform intelligent search for user query"""

    # 1. Expand query
    expanded = await advanced_search_engine._expand_query(query)
    print(f"Expanded Queries: {expanded}")

    # 2. Perform advanced search with combined strategy
    results = await advanced_search_engine.search(
        query=query,
        user_id=user_id,
        limit=10,
        rerank=True,
        strategy=ReRankingStrategy.COMBINED
    )

    # 3. Format results with highlights
    formatted = []
    for result in results:
        formatted.append({
            "content": result.content,
            "highlights": result.highlights,
            "relevance_reason": result.relevance_reason,
            "score": result.reranked_score
        })

    return formatted
```

## Next Steps

1. **Configure LLM Provider:** Set up API keys in `.env`
2. **Test Integration:** Run dry-run tests for summarization and search
3. **Configure Scheduling:** Set up periodic tasks via maintenance scheduler
4. **Monitor Performance:** Track metrics and optimize as needed
5. **Scale Agents:** Add more agents for large-scale deployments

---

**Version:** Sprint 10
**Last Updated:** 2026-02-06
**Status:** Production Ready
