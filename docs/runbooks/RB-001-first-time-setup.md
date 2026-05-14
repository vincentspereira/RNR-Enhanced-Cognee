# Runbook RB-001: First-Time Setup

**Applies to:** Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Developers setting up Enhanced Cognee for the first time

---

## Prerequisites

- Python 3.10 or later (3.12 recommended)
- Docker Desktop 4.x or Docker Engine 24.x with Compose v2
- Git (to clone the repository)
- 4 GB free RAM for the four database containers

---

## Step 1: Clone and Enter the Repository

    git clone <repository-url>
    cd enhanced-cognee

---

## Step 2: Install the Package

Install in editable mode so the enhanced-cognee CLI is available:

    pip install -e .

Verify the CLI is on your PATH:

    enhanced-cognee version
    # Expected output: Enhanced Cognee 1.0.9-enhanced

---

## Step 3: Run the Interactive Setup Wizard

The setup wizard creates the .env file and .enhanced-cognee-config.json:

    enhanced-cognee setup

The wizard asks for:
- Database passwords (defaults are safe for local development)
- Category names for your project
- LLM API key for cognify operations (optional; can be added later)

When the wizard finishes, confirm that .env exists in the project root:

    dir .env       # Windows
    ls -la .env    # Linux / macOS

---

## Step 4: Start the Database Containers

    enhanced-cognee docker up

This runs docker compose with the config/docker/docker-compose-enhanced-cognee.yml
file. First run downloads container images; allow 2-5 minutes.

Confirm all four containers are running:

    docker ps --filter name=enhanced

Expected containers: postgres-enhanced, qdrant-enhanced, neo4j-enhanced, redis-enhanced

---

## Step 5: Run a Health Check

    enhanced-cognee health

Expected output:

    Enhanced Cognee Health Check
    --------------------------------
    [OK] PostgreSQL  localhost:25432
    [OK] Qdrant      localhost:26333
    [OK] Neo4j       localhost:27687
    [OK] Redis       localhost:26379

If any line shows [FAIL], see the Troubleshooting section below.

---

## Step 6: Start the MCP Server

    enhanced-cognee start

The server prints startup messages ending with "MCP server ready". Leave this
terminal open. Configure your MCP client (e.g., Claude Code) to connect using
the path in ~/.claude.json (populated by the setup wizard).

---

## Troubleshooting

### Docker not found

    enhanced-cognee docker up
    [ERR] Docker not found. Install Docker Desktop and ensure it is running.

Install Docker Desktop from https://docs.docker.com/desktop/ and start it before
retrying.

### Port conflict

    [ERR] PostgreSQL port 25432 is already in use.

Another process is using the Enhanced Cognee port. Find the process:

    # Windows
    netstat -ano | findstr :25432

    # Linux / macOS
    lsof -i :25432

Stop the conflicting process or change the port in .env (POSTGRES_PORT) and in
docker-compose-enhanced-cognee.yml.

### Missing .env file

If the setup wizard did not finish, the .env file may be absent. Copy the example:

    cp .env.example .env

Then edit the passwords and re-run enhanced-cognee health to verify connectivity.
