#!/usr/bin/env python3
"""
Enhanced Cognee MCP Server - Universal Project-Aware Version
This version automatically detects the current project and applies appropriate memory categorization.
"""

import os
import sys
import json
from pathlib import Path

# Add cognee-mcp to path
cognee_path = Path(__file__).parent / "cognee-mcp" / "src"
sys.path.insert(0, str(cognee_path))

def detect_project_type(current_path=None):
    """Detect project type and configuration based on current working directory"""

    if current_path is None:
        current_path = Path.cwd()
    else:
        current_path = Path(current_path)

    project_info = {
        "path": str(current_path),
        "name": current_path.name,
        "type": "general",
        "memory_config": "default",
        "prefixes": {}
    }

    # Check for Multi-Agent System project
    multi_agent_indicators = [
        "21-agent", "multi-agent", "agents/", "claude.md",
        "enhanced-cognee", "algorithmic-trading", "risk-management",
        "portfolio-optimizer", "market-analyzer", "execution-engine"
    ]

    if any(indicator in current_path.parts for indicator in multi_agent_indicators):
        project_info.update({
            "type": "multi_agent_system",
            "memory_config": "ats_oma_smc",
            "prefixes": {
                "ats_prefix": "ats_",
                "oma_prefix": "oma_",
                "smc_prefix": "smc_",
                "custom_categories": True
            }
        })
        return project_info

    # Check for web development projects
    web_indicators = ["package.json", "next.config", "react", "vue", "angular", "svelte"]
    if any((current_path / indicator).exists() for indicator in web_indicators):
        project_info.update({
            "type": "web_development",
            "memory_config": "web_dev",
            "prefixes": {
                "frontend_prefix": "fe_",
                "backend_prefix": "be_",
                "devops_prefix": "dev_",
                "custom_categories": True
            }
        })
        return project_info

    # Check for Python projects
    python_indicators = ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]
    if any((current_path / indicator).exists() for indicator in python_indicators):
        project_info.update({
            "type": "python",
            "memory_config": "python_dev",
            "prefixes": {
                "code_prefix": "code_",
                "data_prefix": "data_",
                "config_prefix": "config_",
                "custom_categories": True
            }
        })
        return project_info

    # Check for data science projects
    ds_indicators = ["notebooks/", ".ipynb", "pandas", "jupyter", "mlflow"]
    if any(indicator in str(current_path).lower() or
           (current_path / indicator).exists() for indicator in ds_indicators):
        project_info.update({
            "type": "data_science",
            "memory_config": "data_science",
            "prefixes": {
                "model_prefix": "model_",
                "data_prefix": "data_",
                "experiment_prefix": "exp_",
                "custom_categories": True
            }
        })
        return project_info

    # Default general project
    project_info.update({
        "type": "general",
        "memory_config": "default",
        "prefixes": {
            "general_prefix": "mem_",
            "task_prefix": "task_",
            "note_prefix": "note_",
            "custom_categories": False
        }
    })

    return project_info

def setup_project_environment(project_info):
    """Set up environment variables based on project type"""

    # Common Enhanced Cognee settings
    os.environ["ENHANCED_COGNEE_MODE"] = "true"
    os.environ["PROJECT_TYPE"] = project_info["type"]
    os.environ["PROJECT_NAME"] = project_info["name"]
    os.environ["PROJECT_PATH"] = project_info["path"]

    # Multi-Provider LLM Configuration (Ollama - Local)
    os.environ["LLM_API_KEY"] = "ollama"
    os.environ["LLM_MODEL"] = "glm-4.7-flash:q4_K_M"
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["LLM_ENDPOINT"] = "http://localhost:11434/v1"

    # Enhanced Database Stack Configuration
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "25432"
    os.environ["POSTGRES_DB"] = "cognee_db"
    os.environ["POSTGRES_USER"] = "cognee_user"
    os.environ["POSTGRES_PASSWORD"] = "cognee_password"
    os.environ["DB_PROVIDER"] = "postgres"
    os.environ["DB_NAME"] = "cognee_db"

    # Qdrant Vector Database
    os.environ["QDRANT_HOST"] = "localhost"
    os.environ["QDRANT_PORT"] = "26333"
    # Secret must be provided via environment/.env -- never hardcode.
    # Only propagate QDRANT_API_KEY if it is already set; leave unset otherwise.
    _qdrant_api_key = os.environ.get("QDRANT_API_KEY")
    if _qdrant_api_key:
        os.environ["QDRANT_API_KEY"] = _qdrant_api_key
    os.environ["QDRANT_COLLECTION_PREFIX"] = f"{project_info['name']}_"
    os.environ["VECTOR_DB_PROVIDER"] = "qdrant"

    # Neo4j Graph Database
    os.environ["NEO4J_URI"] = "bolt://localhost:27687"
    os.environ["NEO4J_USER"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "cognee_password"
    os.environ["NEO4J_DATABASE"] = "neo4j"
    os.environ["GRAPH_DATABASE_PROVIDER"] = "neo4j"

    # Redis Cache Layer
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "26379"
    os.environ["REDIS_PASSWORD"] = ""
    os.environ["REDIS_DB"] = "0"
    os.environ["REDIS_CACHE_TTL"] = "3600"

    # Enhanced Embedding Configuration
    os.environ["EMBEDDING_PROVIDER"] = "ollama"
    os.environ["EMBEDDING_MODEL"] = "qwen3-embedding:4b-q4_K_M"
    os.environ["EMBEDDING_ENDPOINT"] = "http://localhost:11434/api/embed"
    os.environ["EMBEDDING_DIMENSIONS"] = "2560"
    os.environ["HUGGINGFACE_TOKENIZER"] = "Qwen/Qwen3-Embedding"

    # Project-Specific Memory Configuration
    os.environ["MEMORY_CATEGORIZATION"] = "true"

    if project_info["memory_config"] == "ats_oma_smc":
        # Multi-Agent System specific prefixes
        os.environ["MEMORY_PREFIX_MODE"] = "agent_based"
        os.environ["ATS_MEMORY_PREFIX"] = "ats_"
        os.environ["OMA_MEMORY_PREFIX"] = "oma_"
        os.environ["SMC_MEMORY_PREFIX"] = "smc_"
        os.environ["CUSTOM_CATEGORIES"] = "true"

    elif project_info["memory_config"] == "web_dev":
        # Web development specific prefixes
        os.environ["MEMORY_PREFIX_MODE"] = "web_dev"
        os.environ["FRONTEND_MEMORY_PREFIX"] = "fe_"
        os.environ["BACKEND_MEMORY_PREFIX"] = "be_"
        os.environ["DEVOPS_MEMORY_PREFIX"] = "dev_"
        os.environ["CUSTOM_CATEGORIES"] = "true"

    elif project_info["memory_config"] == "python_dev":
        # Python development specific prefixes
        os.environ["MEMORY_PREFIX_MODE"] = "python_dev"
        os.environ["CODE_MEMORY_PREFIX"] = "code_"
        os.environ["DATA_MEMORY_PREFIX"] = "data_"
        os.environ["CONFIG_MEMORY_PREFIX"] = "config_"
        os.environ["CUSTOM_CATEGORIES"] = "true"

    elif project_info["memory_config"] == "data_science":
        # Data science specific prefixes
        os.environ["MEMORY_PREFIX_MODE"] = "data_science"
        os.environ["MODEL_MEMORY_PREFIX"] = "model_"
        os.environ["DATA_MEMORY_PREFIX"] = "data_"
        os.environ["EXPERIMENT_MEMORY_PREFIX"] = "exp_"
        os.environ["CUSTOM_CATEGORIES"] = "true"

    else:
        # Default/General project
        os.environ["MEMORY_PREFIX_MODE"] = "general"
        os.environ["GENERAL_MEMORY_PREFIX"] = "mem_"
        os.environ["TASK_MEMORY_PREFIX"] = "task_"
        os.environ["NOTE_MEMORY_PREFIX"] = "note_"
        os.environ["CUSTOM_CATEGORIES"] = "false"

    # Performance and security settings
    os.environ["PERFORMANCE_MONITORING"] = "true"
    os.environ["AUTO_OPTIMIZATION"] = "true"
    os.environ["INTELLIGENT_CACHING"] = "true"
    os.environ["ACCEPT_LOCAL_FILE_PATH"] = "True"
    os.environ["ALLOW_HTTP_REQUESTS"] = "True"
    os.environ["ALLOW_CYPHER_QUERY"] = "True"
    os.environ["ENV"] = "local"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

def print_project_info(project_info):
    """Print project detection and configuration information"""
    print("=" * 60)
    print("Enhanced Cognee MCP Server - Universal Edition")
    print("=" * 60)
    print(f"Project Path: {project_info['path']}")
    print(f"Project Name: {project_info['name']}")
    print(f"Project Type: {project_info['type']}")
    print(f"Memory Config: {project_info['memory_config']}")

    if project_info["prefixes"]:
        print("Memory Prefixes:")
        for key, value in project_info["prefixes"].items():
            if key.endswith("_prefix"):
                print(f"   {key.replace('_', ' ').title()}: {value}")

    print("\nDatabase Stack: PostgreSQL+pgVector | Qdrant | Neo4j | Redis")
    print("LLM: Z.ai (primary) + Ollama (embeddings)")
    print("Features: Project-aware categorization + Intelligent caching")

def main():
    """Main entry point - Project-aware Enhanced Cognee MCP"""

    # Detect current project
    project_info = detect_project_type()

    # Set up environment based on project
    setup_project_environment(project_info)

    # Print project information
    print_project_info(project_info)

    # Change to cognee directory
    os.chdir(Path(__file__).parent)

    try:
        # Import and start the server
        from server import mcp
        print("\nStarting Enhanced Cognee MCP Server...")
        print("Available tools: cognify, search, list_data, delete, prune, codify")
        print(f"Memory categorization: {project_info['memory_config']} mode")
        mcp.run()
    except Exception as e:
        print(f"Failed to start Cognee server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()