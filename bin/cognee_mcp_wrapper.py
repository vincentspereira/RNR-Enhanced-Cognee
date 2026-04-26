#!/usr/bin/env python3
"""
Cognee MCP Server with Z.ai + Ollama Fallback Configuration
"""

import os
import sys
from pathlib import Path

# Add cognee-mcp to path
cognee_path = Path(__file__).parent / "cognee-mcp" / "src"
sys.path.insert(0, str(cognee_path))

def main():
    """Main entry point - Enhanced Cognee MCP with Enterprise Stack"""

    # Enhanced Cognee Mode
    os.environ["ENHANCED_COGNEE_MODE"] = "true"

    # Multi-Provider LLM Configuration (Ollama - Local)
    os.environ["LLM_API_KEY"] = "ollama"
    os.environ["LLM_MODEL"] = "glm-4.7-flash:q4_K_M"
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["LLM_ENDPOINT"] = "http://localhost:11434/v1"

    # Enhanced Database Stack Configuration
    # PostgreSQL + pgVector (replaces SQLite)
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "25432"  # Mapped port from Docker
    os.environ["POSTGRES_DB"] = "cognee_db"
    os.environ["POSTGRES_USER"] = "cognee_user"
    os.environ["POSTGRES_PASSWORD"] = "cognee_password"
    os.environ["DB_PROVIDER"] = "postgres"
    os.environ["DB_NAME"] = "cognee_db"

    # Qdrant Vector Database (replaces LanceDB)
    os.environ["QDRANT_HOST"] = "localhost"
    os.environ["QDRANT_PORT"] = "26333"  # Mapped port from Docker
    os.environ["QDRANT_API_KEY"] = "***REMOVED***"
    os.environ["QDRANT_COLLECTION_PREFIX"] = "cognee_"
    os.environ["VECTOR_DB_PROVIDER"] = "qdrant"

    # Neo4j Graph Database (replaces Kuzu)
    os.environ["NEO4J_URI"] = "bolt://localhost:27687"  # Mapped port from Docker
    os.environ["NEO4J_USER"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "cognee_password"
    os.environ["NEO4J_DATABASE"] = "neo4j"
    os.environ["GRAPH_DATABASE_PROVIDER"] = "neo4j"

    # Redis Cache Layer (new component)
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "26379"  # Mapped port from Docker
    os.environ["REDIS_PASSWORD"] = ""
    os.environ["REDIS_DB"] = "0"
    os.environ["REDIS_CACHE_TTL"] = "3600"

    # Enhanced Embedding Configuration
    os.environ["EMBEDDING_PROVIDER"] = "ollama"
    os.environ["EMBEDDING_MODEL"] = "qwen3-embedding:4b-q4_K_M"
    os.environ["EMBEDDING_ENDPOINT"] = "http://localhost:11434/api/embed"
    os.environ["EMBEDDING_DIMENSIONS"] = "2560"
    os.environ["HUGGINGFACE_TOKENIZER"] = "Qwen/Qwen3-Embedding"

    # Enhanced Memory Features
    os.environ["MEMORY_CATEGORIZATION"] = "true"
    os.environ["ATS_MEMORY_PREFIX"] = "ats_"
    os.environ["OMA_MEMORY_PREFIX"] = "oma_"
    os.environ["SMC_MEMORY_PREFIX"] = "smc_"
    os.environ["PERFORMANCE_MONITORING"] = "true"
    os.environ["AUTO_OPTIMIZATION"] = "true"
    os.environ["INTELLIGENT_CACHING"] = "true"

    # Security settings
    os.environ["ACCEPT_LOCAL_FILE_PATH"] = "True"
    os.environ["ALLOW_HTTP_REQUESTS"] = "True"
    os.environ["ALLOW_CYPHER_QUERY"] = "True"
    os.environ["ENV"] = "local"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    print("Starting Enhanced Cognee MCP Server")
    print("Architecture: PostgreSQL+pgVector | Qdrant | Neo4j | Redis")
    print("LLM: Z.ai (primary) + Ollama (embeddings)")
    print("Memory: Enhanced categorization with ATS/OMA/SMC prefixes")
    print("Performance: Intelligent caching + Auto-optimization")

    # Change to cognee directory
    os.chdir(Path(__file__).parent)

    try:
        # Import and start the server
        from server import mcp
        print("Cognee MCP server starting...")
        print("Available tools: cognify, search, list_data, delete, prune, codify")
        mcp.run()
    except Exception as e:
        print(f"Failed to start Cognee server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()