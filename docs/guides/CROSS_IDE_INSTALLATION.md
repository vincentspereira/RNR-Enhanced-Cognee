# Enhanced Cognee MCP Server - Cross-IDE Installation Guide

This guide explains how to install and use the Enhanced Cognee MCP server across various IDEs and editors.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Supported IDEs](#supported-ides)
3. [Universal Installation Steps](#universal-installation-steps)
4. [IDE-Specific Instructions](#ide-specific-instructions)
5. [Configuration](#configuration)
6. [Testing the Installation](#testing-the-installation)
7. [Troubleshooting](#troubleshooting)

## 🎯 Prerequisites

### Required Software
- **Python 3.8+** (Enhanced Cognee is Python-based)
- **Node.js 18+** (for MCP protocol support)
- **Docker & Docker Compose** (for database stack)
- **Git** (for cloning repositories)

### System Requirements
- **RAM**: Minimum 8GB (Recommended 16GB+)
- **Storage**: Minimum 10GB free space
- **Network**: Internet connection for LLM API calls

## 🖥️ Supported IDEs

### ✅ Fully Supported
- **VS Code** (via Continue, Cursor, etc.)
- **Cursor** (built-in MCP support)
- **Windsurf** (built-in MCP support)
- **Google's Antigravity** (MCP compatible)
- **JetBrains IDEs** (via plugins)

### 🔄 Work in Progress
- **PyCharm** (experimental MCP support)
- **WebStorm** (via Community plugins)
- **IntelliJ IDEA** (via plugins)

## 🔧 Universal Installation Steps

### Step 1: Clone Enhanced Cognee Repository

```bash
git clone https://github.com/your-username/enhanced-cognee.git
cd enhanced-cognee
```

### Step 2: Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -e .
```

### Step 3: Start Docker Database Stack

```bash
# Start the enhanced database stack
docker-compose -f docker-compose-enhanced-cognee.yml up -d

# Verify containers are running
docker ps | grep cognee
```

### Step 4: Test Enhanced Cognee Server

```bash
# Test the universal server
python cognee_mcp_universal.py
```

## 💻 IDE-Specific Instructions

### VS Code

#### Method 1: Using Continue Extension

1. **Install Continue Extension**
   ```json
   // In VS Code extensions marketplace
   search: "Continue"
   ```

2. **Configure Continue for MCP**
   ```json
   // ~/.continue/config.json
   {
     "mcpServers": {
       "enhanced-cognee": {
         "command": "python",
         "args": ["/path/to/enhanced-cognee/cognee_mcp_universal.py"],
         "env": {
           "PYTHONPATH": "/path/to/enhanced-cognee"
         }
       }
     }
   }
   ```

3. **Restart VS Code**

#### Method 2: Using Kilo Code Extension

1. **Install Kilo Code Extension**
2. **Configure MCP settings** in extension preferences
3. **Add Enhanced Cognee server** configuration

#### Method 3: Using Claude in VS Code

1. **Install Claude Dev Extension**
2. **Enable MCP mode** in settings
3. **Configure Enhanced Cognee** as memory provider

### Cursor

1. **Open Cursor Settings**
2. **Navigate to MCP Configuration**
3. **Add Enhanced Cognee Server:**
   ```json
   {
     "enhanced-cognee": {
       "command": "python",
       "args": ["/full/path/to/enhanced-cognee/cognee_mcp_universal.py"],
       "env": {
         "PYTHONPATH": "/full/path/to/enhanced-cognee"
       }
     }
   }
   ```

4. **Restart Cursor**

### Windsurf

1. **Open Windsurf Settings**
2. **Go to Extensions → MCP Servers**
3. **Add New Server:**
   - Name: `enhanced-cognee`
   - Command: `python`
   - Args: `["/path/to/enhanced-cognee/cognee_mcp_universal.py"]`
   - Environment: `{"PYTHONPATH": "/path/to/enhanced-cognee"}`

### Google's Antigravity

1. **Open Antigravity Settings**
2. **Enable MCP Protocol**
3. **Configure Enhanced Cognee:**
   ```json
   {
     "mcp": {
       "servers": {
         "enhanced-cognee": {
           "executable": "python",
           "args": ["/path/to/cognee_mcp_universal.py"],
           "cwd": "/path/to/enhanced-cognee"
         }
       }
     }
   }
   ```

### JetBrains IDEs (PyCharm, WebStorm, IntelliJ)

1. **Install MCP Plugin** (if available)
2. **Configure Plugin Settings:**
   - Server executable: `python`
   - Arguments: path to `cognee_mcp_universal.py`
   - Working directory: Enhanced Cognee directory
   - Environment variables: `PYTHONPATH`

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the Enhanced Cognee directory:

```env
# LLM Configuration
LLM_API_KEY=your_api_key_here
LLM_MODEL=glm-4.6
LLM_PROVIDER=zai

# Database Configuration (if using custom ports)
POSTGRES_HOST=localhost
POSTGRES_PORT=25432
QDRANT_HOST=localhost
QDRANT_PORT=26333
NEO4J_URI=bolt://localhost:27687
REDIS_HOST=localhost
REDIS_PORT=26379

# Embedding Configuration
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=snowflake-arctic-embed2:568m
EMBEDDING_ENDPOINT=http://localhost:11434/api/embed
```

### IDE-Specific Memory Prefixes

The Enhanced Cognee server automatically detects project type and applies appropriate prefixes:

- **Multi-Agent Systems**: `ats_`, `oma_`, `smc_`
- **Web Development**: `fe_`, `be_`, `dev_`
- **Python Projects**: `code_`, `data_`, `config_`
- **Data Science**: `model_`, `data_`, `exp_`
- **General Projects**: `mem_`, `task_`, `note_`

## 🧪 Testing the Installation

### 1. Test Database Connections

```bash
cd enhanced-cognee
python -c "
import psycopg2, redis, qdrant_client, neo4j
# Test connections...
print('All databases connected successfully!')
"
```

### 2. Test Enhanced Cognee Server

```bash
python cognee_mcp_universal.py
```

### 3. Test in IDE

In your IDE, try these commands:
- "Remember this code architecture"
- "What did we learn about user authentication?"
- "Store this design decision in memory"
- "Find similar patterns from our projects"

## 🔧 Troubleshooting

### Common Issues

#### 1. Port Conflicts
```bash
# Check which ports are in use
netstat -tulpn | grep -E "(25432|26333|27687|26379)"

# Change ports in docker-compose.yml if needed
```

#### 2. Python Path Issues
```bash
# Verify Python can find Enhanced Cognee
export PYTHONPATH=/path/to/enhanced-cognee:$PYTHONPATH
python -c "import cognee"
```

#### 3. Docker Container Issues
```bash
# Check container status
docker-compose -f docker-compose-enhanced-cognee.yml ps

# Restart containers
docker-compose -f docker-compose-enhanced-cognee.yml restart

# View logs
docker-compose -f docker-compose-enhanced-cognee.yml logs
```

#### 4. IDE Connection Issues

**VS Code:**
- Check Continue extension logs
- Verify configuration file paths
- Restart VS Code completely

**Cursor/Windsurf:**
- Check IDE console for MCP errors
- Verify server executable path
- Check environment variables

**General:**
- Ensure Enhanced Cognee server is running
- Verify Python environment is activated
- Check firewall settings for Docker ports

### Getting Help

1. **Check Logs**: Look at IDE console and server logs
2. **Verify Configuration**: Double-check all paths and environment variables
3. **Test Components**: Test each component individually
4. **Community Support**: Check GitHub issues and community forums

## 🚀 Next Steps

Once installed, you can:

1. **Use Enhanced Memory Commands** in any supported IDE
2. **Switch Between Projects** and maintain memory separation
3. **Leverage Cross-Project Insights** for better development
4. **Customize Memory Categories** for your specific workflows

## 📚 Additional Resources

- [Enhanced Cognee Documentation](./README.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Docker Troubleshooting Guide](./DOCKER_TROUBLESHOOTING.md)
- [IDE-Specific Configuration Examples](./IDE_EXAMPLES.md)

---

**Need Help?** Check the [GitHub Issues](https://github.com/your-username/enhanced-cognee/issues) or join our [Discord Community](https://discord.gg/enhanced-cognee).