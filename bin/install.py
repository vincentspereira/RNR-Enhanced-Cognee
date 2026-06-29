#!/usr/bin/env python3
"""
RNR Enhanced Cognee MCP Server - Automated Installer
This script handles the complete installation process for new users.
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path
import shutil

class EnhancedCogneeInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.home_dir = Path.home()
        self.install_dir = self.home_dir / "enhanced-cognee-mcp"

    def print_banner(self):
        """Print installation banner"""
        print("=" * 70)
        print("[MEM] RNR Enhanced Cognee MCP Server - Automated Installer")
        print("=" * 70)
        print("This installer will set up RNR Enhanced Cognee with:")
        print("  [OK] PostgreSQL+pgVector database")
        print("  [OK] Qdrant vector database")
        print("  [OK] Neo4j graph database")
        print("  [OK] Redis cache layer")
        print("  [OK] Project-aware memory categorization")
        print("  [OK] Cross-IDE compatibility")
        print("=" * 70)

    def check_prerequisites(self):
        """Check if required software is installed"""
        print("\n[INFO] Checking prerequisites...")

        # Check Python
        try:
            python_version = sys.version_info
            if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
                print("[ERROR] Python 3.8+ is required")
                return False
            print(f"[OK] Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        except:
            print("[ERROR] Python not found")
            return False

        # Check Node.js
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] Node.js {result.stdout.strip()}")
            else:
                print("[ERROR] Node.js not found")
                return False
        except:
            print("[ERROR] Node.js not found")
            return False

        # Check Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] Docker {result.stdout.strip()}")
            else:
                print("[ERROR] Docker not found")
                return False
        except:
            print("[ERROR] Docker not found")
            return False

        # Check Docker Compose
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] Docker Compose {result.stdout.strip()}")
            else:
                print("[ERROR] Docker Compose not found")
                return False
        except:
            try:
                # Try docker compose (without hyphen)
                result = subprocess.run(['docker', 'compose', 'version'], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"[OK] Docker Compose {result.stdout.strip()}")
                else:
                    print("[ERROR] Docker Compose not found")
                    return False
            except:
                print("[ERROR] Docker Compose not found")
                return False

        return True

    def install_enhanced_cognee(self):
        """Install RNR Enhanced Cognee package"""
        print("\n[INFO] Installing RNR Enhanced Cognee...")

        # Create installation directory
        self.install_dir.mkdir(exist_ok=True)

        # Copy RNR Enhanced Cognee files (assuming we're running from the repo)
        current_dir = Path(__file__).parent

        # Required files and directories
        files_to_copy = [
            "cognee_mcp_universal.py",
            "cognee_mcp_wrapper.py",
            "config/docker/docker-compose-enhanced-cognee.yml",
            "requirements.txt",
            "pyproject.toml",
            "README.md",
            "cognee/"
        ]

        for item in files_to_copy:
            src = current_dir / item
            if src.exists():
                dst = self.install_dir / item
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                print(f"[OK] Copied {item}")
            else:
                print(f"[WARNING] {item} not found, skipping")

        # Create virtual environment
        print("\n[INFO] Creating Python virtual environment...")
        venv_dir = self.install_dir / "venv"

        # Path validation for security
        import sys
        sys.path.insert(0, str(self.install_dir / "src"))
        from security_mcp import validate_path_safe

        # Validate venv_dir is within allowed directory
        try:
            venv_dir = validate_path_safe(str(venv_dir), str(self.install_dir))
        except Exception as e:
            print(f"[ERROR] Path validation failed: {e}")
            raise

        if self.system == "windows":
            subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)], check=True)
            python_exe = venv_dir / "Scripts" / "python.exe"
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:
            subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)], check=True)
            python_exe = venv_dir / "bin" / "python"
            pip_exe = venv_dir / "bin" / "pip"

        # Install Python dependencies
        print("\n[INFO] Installing Python dependencies...")
        requirements_file = self.install_dir / "requirements.txt"

        # Validate requirements_file path
        try:
            requirements_file = validate_path_safe(str(requirements_file), str(self.install_dir))
        except Exception as e:
            print(f"[ERROR] Path validation failed: {e}")
            raise

        if requirements_file.exists():
            subprocess.run([str(pip_exe), 'install', '-r', str(requirements_file)], check=True)
        else:
            subprocess.run([str(pip_exe), 'install', '-e', str(self.install_dir)], check=True)

        return str(python_exe)

    def setup_docker_network(self):
        """Set up Docker network and containers"""
        print("\n[INFO] Setting up Docker network and containers...")

        # Change to installation directory
        os.chdir(self.install_dir)

        # Validate paths before docker operations
        import sys
        sys.path.insert(0, str(self.install_dir / "src"))
        from security_mcp import validate_path_safe

        # Create Docker network
        try:
            network_valid = True  # Network creation doesn't need path validation
            if network_valid:
                subprocess.run(['docker', 'network', 'create', 'enhanced-cognee-network'],
                             capture_output=True, check=True)
                print("[OK] Created Docker network")
        except subprocess.CalledProcessError:
            print("[INFO] Docker network already exists")

        # Start containers
        compose_file = self.install_dir / "config/docker/docker-compose-enhanced-cognee.yml"

        # Validate compose_file path
        try:
            compose_file = validate_path_safe(str(compose_file), str(self.install_dir))
        except Exception as e:
            print(f"[ERROR] Path validation failed: {e}")
            raise

        if compose_file.exists():
            try:
                subprocess.run(['docker-compose', '-f', str(compose_file), 'up', '-d'],
                             check=True)
                print("[OK] Started Docker containers")

                # Wait for containers to be ready
                print("[INFO] Waiting for containers to be ready...")
                import time
                time.sleep(10)

                # Check if containers are running
                result = subprocess.run(['docker', 'ps', '--filter', 'name=cognee'],
                                      capture_output=True, text=True)
                if 'cognee' in result.stdout:
                    print("[OK] All containers are running")
                else:
                    print("[WARNING] Some containers may not be ready yet")

            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed to start containers: {e}")
                return False

        return True

    def create_configuration_files(self, python_exe):
        """Create configuration files for IDEs"""
        print("\n[INFO] Creating configuration files...")

        config_dir = self.install_dir / "config"
        config_dir.mkdir(exist_ok=True)

        # MCP Server configuration
        mcp_config = {
            "mcpServers": {
                "enhanced-cognee": {
                    "command": str(python_exe),
                    "args": [str(self.install_dir / "cognee_mcp_universal.py")],
                    "env": {
                        "PYTHONPATH": str(self.install_dir)
                    }
                }
            }
        }

        # Claude Desktop config
        claude_config_path = config_dir / "claude_desktop_config.json"
        with open(claude_config_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        print(f"[OK] Created Claude config: {claude_config_path}")

        # VS Code Continue config
        continue_config_path = config_dir / "continue_config.json"
        with open(continue_config_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        print(f"[OK] Created Continue config: {continue_config_path}")

        # Cursor config
        cursor_config_path = config_dir / "cursor_config.json"
        with open(cursor_config_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        print(f"[OK] Created Cursor config: {cursor_config_path}")

        # Environment template
        env_template_path = config_dir / ".env.template"
        env_template = """# RNR Enhanced Cognee MCP Server Configuration
# Copy this file to .env and fill in your API keys

# LLM Configuration
LLM_API_KEY=your_zai_api_key_here
LLM_MODEL=glm-4.6
LLM_PROVIDER=zai
# Z.ai endpoint (coding plan). Standard plan: /api/paas/v4. Do NOT use /v1 (404s).
LLM_ENDPOINT=https://api.z.ai/api/coding/paas/v4

# Database Configuration (Auto-configured)
POSTGRES_HOST=localhost
POSTGRES_PORT=25432
POSTGRES_DB=cognee_db
POSTGRES_USER=cognee_user
POSTGRES_PASSWORD=change-me-strong-password

QDRANT_HOST=localhost
QDRANT_PORT=26333
QDRANT_API_KEY=your-qdrant-api-key-here

NEO4J_URI=bolt://localhost:27687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me-strong-password
NEO4J_DATABASE=neo4j

REDIS_HOST=localhost
REDIS_PORT=26379
REDIS_PASSWORD=

# Embedding Configuration
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=qwen3-embedding:4b-q4_K_M
EMBEDDING_ENDPOINT=http://localhost:11434/api/embed
EMBEDDING_DIMENSIONS=2560
"""

        with open(env_template_path, 'w') as f:
            f.write(env_template)
        print(f"[OK] Created environment template: {env_template_path}")

        return config_dir

    def create_desktop_shortcuts(self, python_exe):
        """Create desktop shortcuts for easy access"""
        print("\n[INFO] Creating desktop shortcuts...")

        desktop_dir = self.home_dir / "Desktop"
        if not desktop_dir.exists():
            desktop_dir = self.home_dir / "Desktop"

        if self.system == "windows":
            # Windows batch file
            start_script = desktop_dir / "Start RNR Enhanced Cognee.bat"
            with open(start_script, 'w') as f:
                f.write(f'''@echo off
echo Starting RNR Enhanced Cognee MCP Server...
cd /d "{self.install_dir}"
"{python_exe}" cognee_mcp_universal.py
pause
''')
            print(f"[OK] Created Windows shortcut: {start_script}")

        else:
            # Unix shell script
            start_script = desktop_dir / "start-enhanced-cognee.sh"
            with open(start_script, 'w') as f:
                f.write(f'''#!/bin/bash
echo "Starting RNR Enhanced Cognee MCP Server..."
cd "{self.install_dir}"
"{python_exe}" cognee_mcp_universal.py
''')
            os.chmod(start_script, 0o755)
            print(f"[OK] Created Unix shortcut: {start_script}")

    def test_installation(self, python_exe):
        """Test the installation"""
        print("\n[INFO] Testing installation...")

        # Test RNR Enhanced Cognee import
        try:
            result = subprocess.run([python_exe, '-c', 'import sys; sys.path.append("' + str(self.install_dir) + '"); import cognee_mcp_universal'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("[OK] RNR Enhanced Cognee import successful")
            else:
                print(f"[WARNING] Import test failed: {result.stderr}")
        except Exception as e:
            print(f"[WARNING] Import test failed: {e}")

        # Test database connections
        try:
            test_script = '''
import psycopg2, redis, qdrant_client, neo4j
import os

# Test PostgreSQL (credentials come from the environment/.env -- never hardcoded)
try:
    pg_password = os.environ.get("POSTGRES_PASSWORD")
    if not pg_password:
        print("[WARNING] POSTGRES_PASSWORD not set; skipping PostgreSQL connection test")
    else:
        conn = psycopg2.connect(host="localhost", port=25432, database="cognee_db", user="cognee_user", password=pg_password)
        conn.close()
        print("[OK] PostgreSQL connection successful")
except Exception as e:
    print(f"[ERROR] PostgreSQL failed: {e}")

# Test Redis
try:
    r = redis.Redis(host="localhost", port=26379)
    r.ping()
    print("[OK] Redis connection successful")
except Exception as e:
    print(f"[ERROR] Redis failed: {e}")

# Test Qdrant
try:
    client = qdrant_client.QdrantClient(host="localhost", port=26333)
    client.get_collections()
    print("[OK] Qdrant connection successful")
except Exception as e:
    print(f"[ERROR] Qdrant failed: {e}")

# Test Neo4j (credentials come from the environment/.env -- never hardcoded)
try:
    neo4j_password = os.environ.get("NEO4J_PASSWORD")
    if not neo4j_password:
        print("[WARNING] NEO4J_PASSWORD not set; skipping Neo4j connection test")
    else:
        driver = neo4j.GraphDatabase.driver("bolt://localhost:27687", auth=("neo4j", neo4j_password))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        print("[OK] Neo4j connection successful")
except Exception as e:
    print(f"[ERROR] Neo4j failed: {e}")
'''

            result = subprocess.run([python_exe, '-c', test_script],
                                  capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print("Warnings:")
                print(result.stderr)

        except Exception as e:
            print(f"[WARNING] Database test failed: {e}")

    def print_next_steps(self, config_dir):
        """Print next steps for the user"""
        print("\n" + "=" * 70)
        print("[OK] Installation Complete!")
        print("=" * 70)
        print("\n[INFO] Installation Directory:")
        print(f"   {self.install_dir}")

        print("\n[INFO] Configuration Files:")
        print(f"   Claude Desktop: {config_dir / 'claude_desktop_config.json'}")
        print(f"   VS Code Continue: {config_dir / 'continue_config.json'}")
        print(f"   Cursor: {config_dir / 'cursor_config.json'}")
        print(f"   Environment: {config_dir / '.env.template'}")

        print("\n[INFO] Next Steps:")
        print("1. Copy .env.template to .env and add your API keys")
        print("2. Import the appropriate config file into your IDE")
        print("3. Start using RNR Enhanced Cognee in any supported IDE!")

        print("\n[INFO] IDE Configuration:")
        print("- Claude Desktop: Copy config to AppData/Roaming/Claude/")
        print("- VS Code: Import continue_config.json to Continue extension")
        print("- Cursor: Import cursor_config.json in MCP settings")
        print("- Others: Use the provided configuration as template")

        print("\n[INFO] Documentation:")
        print("- User Guide: docs/USER_GUIDE.md")
        print("- Cross-IDE Setup: docs/CROSS_IDE_INSTALLATION.md")
        print("- Troubleshooting: docs/TROUBLEUBLESHOOTING.md")

        print("\n[INFO] Docker Status:")
        print("- Check containers: docker ps | grep cognee")
        print("- View logs: docker-compose -f config/docker/docker-compose-enhanced-cognee.yml logs")
        print("- Restart: docker-compose -f config/docker/docker-compose-enhanced-cognee.yml restart")

        print("\n[INFO] Need Help?")
        print("- GitHub Issues: https://github.com/your-username/enhanced-cognee/issues")
        print("- Discord Community: https://discord.gg/enhanced-cognee")
        print("- Documentation: https://docs.enhanced-cognee.io")

    def run(self):
        """Run the complete installation"""
        try:
            self.print_banner()

            # Check prerequisites
            if not self.check_prerequisites():
                print("\n[ERROR] Prerequisites not met. Please install required software.")
                return False

            # Install RNR Enhanced Cognee
            python_exe = self.install_enhanced_cognee()

            # Set up Docker
            if not self.setup_docker_network():
                print("\n[ERROR] Docker setup failed")
                return False

            # Create configuration files
            config_dir = self.create_configuration_files(python_exe)

            # Create desktop shortcuts
            self.create_desktop_shortcuts(python_exe)

            # Test installation
            self.test_installation(python_exe)

            # Print next steps
            self.print_next_steps(config_dir)

            return True

        except KeyboardInterrupt:
            print("\n\n[ERROR] Installation cancelled by user")
            return False
        except Exception as e:
            print(f"\n[ERROR] Installation failed: {e}")
            return False

def main():
    """Main entry point"""
    installer = EnhancedCogneeInstaller()
    success = installer.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()