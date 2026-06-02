#!/usr/bin/env python3
"""
Cognee MCP Server with Z.ai + Ollama Fallback Configuration
This script provides automatic fallback from Z.ai to Ollama when Z.ai fails
"""

import os
import sys
import signal
from pathlib import Path

# Add cognee-mcp to path
cognee_path = Path(__file__).parent / "cognee-mcp" / "src"
sys.path.insert(0, str(cognee_path))

def setup_environment():
    """Configure environment with fallback logic"""

    # Set up Ollama for LLM (local inference)
    os.environ["LLM_API_KEY"] = "ollama"
    os.environ["LLM_MODEL"] = "glm-4.7-flash:q4_K_M"
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["LLM_ENDPOINT"] = "http://localhost:11434/v1"

    # Ollama as fallback for embeddings
    os.environ["EMBEDDING_PROVIDER"] = "ollama"
    os.environ["EMBEDDING_MODEL"] = "qwen3-embedding:4b-q4_K_M"
    os.environ["EMBEDDING_ENDPOINT"] = "http://localhost:11434/api/embed"
    os.environ["EMBEDDING_DIMENSIONS"] = "2560"
    os.environ["HUGGINGFACE_TOKENIZER"] = "Qwen/Qwen3-Embedding"

    # Default database settings
    os.environ["DB_PROVIDER"] = "sqlite"
    os.environ["DB_NAME"] = "cognee_db"
    os.environ["VECTOR_DB_PROVIDER"] = "lancedb"
    os.environ["GRAPH_DATABASE_PROVIDER"] = "kuzu"

    # Security settings
    os.environ["ACCEPT_LOCAL_FILE_PATH"] = "True"
    os.environ["ALLOW_HTTP_REQUESTS"] = "True"
    os.environ["ALLOW_CYPHER_QUERY"] = "True"
    os.environ["ENV"] = "local"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    print("Environment configured with Z.ai as primary, Ollama as fallback")

def test_z_ai_connection():
    """Test if Z.ai is accessible"""
    try:
        import requests

        headers = {
            "Authorization": f"Bearer {os.environ['LLM_API_KEY']}",
            "Content-Type": "application/json"
        }

        # Simple test request to Z.ai
        response = requests.get(
            f"{os.environ['LLM_ENDPOINT']}/models",
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            print("Z.ai connection successful")
            return True
        else:
            print(f"⚠️  Z.ai returned status {response.status_code}")
            return False

    except Exception as e:
        print(f"⚠️  Z.ai connection failed: {e}")
        return False

def fallback_to_ollama():
    """Switch to Ollama configuration"""
    print("🔄 Switching to Ollama as fallback...")

    os.environ["LLM_API_KEY"] = "ollama"
    os.environ["LLM_MODEL"] = "gpt-oss:20b"
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["LLM_ENDPOINT"] = "http://localhost:11434/v1"

    print("✅ Fallback to Ollama configured")

def test_ollama_connection():
    """Test if Ollama is accessible"""
    try:
        import requests

        response = requests.get(
            "http://localhost:11434/api/tags",
            timeout=5
        )

        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            if os.environ["LLM_MODEL"] in model_names:
                print("✅ Ollama connection successful")
                return True
            else:
                print(f"⚠️  Model {os.environ['LLM_MODEL']} not found in Ollama")
                return False
        else:
            print(f"⚠️  Ollama returned status {response.status_code}")
            return False

    except Exception as e:
        print(f"⚠️  Ollama connection failed: {e}")
        return False

def start_cognee_server():
    """Start the Cognee MCP server"""
    try:
        # Change to cognee directory
        os.chdir(Path(__file__).parent)

        # Import and start the server
        from server import mcp

        print("🚀 Starting Cognee MCP server...")
        print("📊 Available tools: cognify, search, list_data, delete, prune, codify")
        print("🔧 Z.ai is primary, Ollama is fallback")

        # Start the server
        mcp.run()

    except Exception as e:
        print(f"❌ Failed to start Cognee server: {e}")
        sys.exit(1)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n🛑 Shutting down Cognee MCP server...")
    sys.exit(0)

def main():
    """Main entry point"""
    print("Cognee MCP Server with Smart Fallback")
    print("=" * 50)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Configure environment
    setup_environment()

    # Test Z.ai connection
    if not test_z_ai_connection():
        print("⚠️  Z.ai not available, falling back to Ollama...")
        fallback_to_ollama()

        # Test Ollama connection
        if not test_ollama_connection():
            print("❌ Neither Z.ai nor Ollama are available!")
            print("💡 Please ensure:")
            print("   - Z.ai API key is valid and service is accessible")
            print("   - Ollama is running on localhost:11434")
            print("   - Model 'gpt-oss:20b' is available in Ollama")
            sys.exit(1)

    print("\n🎯 Configuration complete - Starting server...")
    start_cognee_server()

if __name__ == "__main__":
    main()