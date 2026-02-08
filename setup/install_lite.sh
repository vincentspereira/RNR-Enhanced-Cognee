#!/bin/bash
################################################################################
# Enhanced Cognee Lite Mode - Installation Script (Linux/Mac)
#
# Lightweight setup with SQLite, no Docker required.
# Setup time: <2 minutes
#
# Author: Enhanced Cognee Team
# Version: 1.0.0
# Date: 2026-02-06
################################################################################

set -e  # Exit on error

# Colors (ASCII-only fallback)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERR]${NC} $1"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LITE_DIR="$SCRIPT_DIR/src/lite_mode"
CONFIG_FILE="$LITE_DIR/lite_config.json"
DB_FILE="$SCRIPT_DIR/cognee_lite.db"

print_info "Enhanced Cognee Lite Mode Installation"
echo "==========================================="
echo ""

# Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    print_info "Please install Python 3.8 or higher:"
    print_info "  Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    print_info "  macOS: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_info "Found Python $PYTHON_VERSION"

# Check if Python version >= 3.8
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    print_error "Python 3.8 or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

# Check if pip is available
print_info "Checking pip..."
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed"
    print_info "Install pip:"
    print_info "  Ubuntu/Debian: sudo apt-get install python3-pip"
    print_info "  macOS: python3 -m ensurepip --upgrade"
    exit 1
fi

# Install dependencies
print_info "Installing dependencies..."
pip3 install --upgrade pip

# Install SQLite support (usually built-in)
print_info "Checking SQLite support..."
python3 -c "import sqlite3; print(sqlite3.sqlite_version)" 2>/dev/null || {
    print_error "SQLite support not found"
    exit 1
}

# Optional: Install APScheduler for maintenance tasks
print_info "Installing APScheduler for maintenance scheduling..."
pip3 install apscheduler 2>/dev/null || print_warn "Failed to install APScheduler (optional)"

# Create directories
print_info "Creating directories..."
mkdir -p "$SCRIPT_DIR/src/lite_mode"
mkdir -p "$SCRIPT_DIR/migrations"
mkdir -p "$SCRIPT_DIR/backups"
mkdir -p "$SCRIPT_DIR/logs"

# Check if schema file exists
if [ ! -f "$SCRIPT_DIR/migrations/create_lite_schema.sql" ]; then
    print_error "Schema file not found: migrations/create_lite_schema.sql"
    exit 1
fi

# Initialize database
print_info "Initializing SQLite database..."
if [ -f "$DB_FILE" ]; then
    print_warn "Database already exists: $DB_FILE"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$DB_FILE"
        print_info "Creating new database..."
    else
        print_info "Using existing database"
    fi
fi

# Create database and initialize schema
python3 - <<EOF
import sqlite3
import os

db_path = "$DB_FILE"
schema_path = "$SCRIPT_DIR/migrations/create_lite_schema.sql"

if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    # Split and execute each statement
    for statement in schema_sql.split(';'):
        statement = statement.strip()
        if statement:
            try:
                conn.execute(statement)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    print(f"[WARN] {e}")

    conn.commit()
    conn.close()
    print("[OK] Database created: " + db_path)
else:
    print("[INFO] Database already exists: " + db_path)
EOF

# Test Lite MCP Server
print_info "Testing Lite MCP Server..."
python3 - <<EOF
import sys
sys.path.insert(0, "$SCRIPT_DIR")

from src.lite_mode.sqlite_manager import SQLiteManager

db = SQLiteManager("$DB_FILE")
health = db.health_check()

if health['status'] == 'OK':
    print("[OK] Lite mode database ready")
    print(f"     Database: {health['database']}")
    print(f"     Path: {health['path']}")
    print(f"     Mode: {health['mode']}")
else:
    print("[ERR] Database health check failed")
    sys.exit(1)

# Test adding a memory
doc_id = db.add_document(
    data_id="test_memory",
    data_text="Enhanced Cognee Lite Mode installation test",
    data_type="test",
    metadata={"test": True},
    user_id="installer",
    agent_id="install_script"
)

print(f"[OK] Test memory added: {doc_id}")

# Test search
results = db.search_documents("installation", user_id="installer", limit=1)
if results:
    print(f"[OK] Full-text search working: found {len(results)} result(s)")
else:
    print("[WARN] Full-text search returned no results")

db.close()
EOF

if [ $? -eq 0 ]; then
    print_info "Lite mode installation successful!"
else
    print_error "Lite mode installation failed"
    exit 1
fi

# Create startup script
print_info "Creating startup script..."
cat > "$SCRIPT_DIR/start_lite.sh" <<'EOF'
#!/bin/bash
# Enhanced Cognee Lite Mode - Startup Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Enhanced Cognee Lite Mode..."
echo "Database: $SCRIPT_DIR/cognee_lite.db"
echo ""

# Start Lite MCP Server
python3 src/lite_mode/lite_mcp_server.py
EOF

chmod +x "$SCRIPT_DIR/start_lite.sh"

# Print summary
echo ""
print_info "Installation complete!"
echo ""
echo "Summary:"
echo "--------"
echo "  Database: $DB_FILE"
echo "  Config: $CONFIG_FILE"
echo "  Logs: $SCRIPT_DIR/logs/"
echo "  Backups: $SCRIPT_DIR/backups/"
echo ""
echo "Next Steps:"
echo "----------"
echo "1. Test Lite mode:"
echo "   python3 src/lite_mode/lite_mcp_server.py"
echo ""
echo "2. Start Lite mode:"
echo "   ./start_lite.sh"
echo ""
echo "3. Configure Claude Code:"
echo "   Add to ~/.claude.json:"
echo '   {"mcpServers": {"cognee-lite": {"command": "python3", "args": ["'"$SCRIPT_DIR"'/src/lite_mode/lite_mcp_server.py"]}}}'
echo ""
echo "For more information, see docs/LITE_MODE_GUIDE.md"
echo ""
print_info "Setup time: <2 minutes (no Docker required!)"
echo ""
