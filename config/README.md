# Enhanced Cognee Configuration

This directory contains all configuration files for Enhanced Cognee.

## Structure

### `docker/`
Docker Compose configuration files for different deployment scenarios:
- `docker-compose.yml` - Standard development setup
- `docker-compose-enhanced-cognee.yml` - Enhanced stack with all databases
- `docker-compose-enhanced-hierarchical.yml` - Hierarchical configuration

**Usage:**
```bash
# Start Enhanced stack
docker compose -f config/docker/docker-compose-enhanced-cognee.yml up -d

# Start standard stack
docker compose -f config/docker/docker-compose.yml up -d
```

### `environments/`
Environment variable templates:
- `.env.template` - Standard environment template
- `.env.production.template` - Production environment template

**Usage:**
```bash
# Copy template to .env
cp config/environments/.env.template .env

# Edit with your settings
nano .env
```

### `automation/`
Automation and scheduling configuration files:
- `automation_config.json` - General automation settings
- `deduplication_config.json` - Deduplication schedule and rules
- `maintenance_config.json` - Maintenance task configuration
- `summarization_config.json` - Summarization settings

**Usage:**
These files are loaded automatically by the Enhanced Cognee system. Edit them to customize automation behavior.

## Port Mappings

The Enhanced stack uses non-standard ports to avoid conflicts:

- PostgreSQL: 25432 (not 5432)
- Qdrant: 26333 (not 6333)
- Neo4j: 27687 (not 7687)
- Redis: 26379 (not 6379)

## For More Information

See the [Configuration Guide](../docs/development/CONFIGURATION_GUIDE.md) in the documentation.
