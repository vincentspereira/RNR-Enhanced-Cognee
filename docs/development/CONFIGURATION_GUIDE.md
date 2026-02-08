# Enhanced Cognee Configuration Guide

**⚠️ CRITICAL CLARIFICATION**: Enhanced Cognee is **NOT hardcoded** to specific prefixes like `ats_`, `oma_`, `smc_`. Those are **Multi-Agent System (MAS) specific**. Your project can define **ANY categories and prefixes** that make sense for your use case.

---

## 📋 Table of Contents

1. [Understanding the Configuration System](#understanding-the-configuration-system)
2. [Quick Start for New Projects](#quick-start-for-new-projects)
3. [Configuration File Format](#configuration-file-format)
4. [Example Configurations](#example-configurations)
5. [Common Use Cases](#common-use-cases)
6. [Troubleshooting](#troubleshooting)

---

## 🔍 Understanding the Configuration System

### What This Guide Covers

Enhanced Cognee provides a **flexible, project-specific configuration system** for memory categorization. This document explains how to configure Enhanced Cognee for **YOUR** project's needs.

### What This is NOT

- ❌ **NOT** a requirement to use `ats_`, `oma_`, `smc_` prefixes
- ❌ **NOT** a mandate to organize agents into specific categories
- ❌ **NOT** a one-size-fits-all architecture

### What It IS

- ✅ A **configurable system** where YOU define categories and prefixes
- ✅ A **framework** that can adapt to YOUR project's structure
- ✅ A **flexible approach** to memory organization

---

## 🚀 Quick Start for New Projects

### Step 1: Create Your Configuration File

In your project's root directory, create a `.enhanced-cognee-config.json` file:

```bash
# In your project root
touch .enhanced-cognee-config.json
```

### Step 2: Define Your Categories

Edit the file with your project-specific configuration:

```json
{
  "project_name": "My Project",
  "description": "Description of your project",
  "categories": {
    "CATEGORY1": {
      "name": "CATEGORY1",
      "description": "First category",
      "prefix": "cat1_",
      "retention_days": 30,
      "priority": 1
    },
    "CATEGORY2": {
      "name": "CATEGORY2",
      "description": "Second category",
      "prefix": "cat2_",
      "retention_days": 60,
      "priority": 2
    }
  },
  "agents": {
    "my-agent": {
      "agent_id": "my-agent",
      "category": "CATEGORY1",
      "prefix": "cat1_",
      "description": "My custom agent",
      "memory_types": ["factual", "procedural"],
      "priority": 1,
      "data_retention_days": 30
    }
  }
}
```

### Step 3: Configure MCP Server

Update your MCP configuration to point to Enhanced Cognee:

```json
{
  "mcpServers": {
    "enhanced-cognee": {
      "command": "python",
      "args": ["PATH/TO/enhanced-cognee/cognee-mcp/src/server.py"],
      "type": "stdio",
      "env": {
        "LLM_API_KEY": "${ANTHROPIC_API_KEY}",
        "DB_HOST": "localhost",
        "DB_PORT": "25432",
        "VECTOR_DB_URL": "http://localhost:26333",
        "GRAPH_DATABASE_URL": "bolt://localhost:27687",
        "REDIS_PORT": "26379"
      }
    }
  }
}
```

### Step 4: Start Using Enhanced Cognee

The MCP server will automatically load your `.enhanced-cognee-config.json` file and use your custom categories and prefixes.

---

## 📁 Configuration File Format

### Complete Schema

```json
{
  "project_name": "string (required) - Your project name",
  "description": "string (optional) - Project description",
  "version": "string (optional) - Configuration version",
  "categories": {
    "CATEGORY_NAME": {
      "name": "string (required) - Category name",
      "description": "string (required) - Category description",
      "prefix": "string (required) - Memory prefix for this category",
      "retention_days": "integer (optional) - Default data retention in days",
      "priority": "integer (optional) - Category priority (1=highest)"
    }
  },
  "agents": {
    "agent_id": {
      "agent_id": "string (required) - Unique agent identifier",
      "category": "string (required) - Must match a category name",
      "prefix": "string (required) - Prefix for this agent's memories",
      "description": "string (required) - Agent description",
      "memory_types": "array (optional) - Memory types this agent uses",
      "priority": "integer (optional) - Agent priority",
      "data_retention_days": "integer (optional) - Retention for this agent's data",
      "critical": "boolean (optional) - Is this a critical agent?"
    }
  }
}
```

### Field Descriptions

#### Category Fields

- **name**: Unique identifier for the category (e.g., "ANALYTICS", "TRADING")
- **description**: Human-readable description of the category's purpose
- **prefix**: String prefix used in memory keys for this category (e.g., "analytics_", "trading_")
- **retention_days**: Default number of days to retain memories in this category
- **priority**: Numerical priority where 1 is highest, used for resource allocation

#### Agent Fields

- **agent_id**: Unique identifier for the agent (used in memory operations)
- **category**: Must reference a category defined in the `categories` section
- **prefix**: Override the category prefix for this specific agent (optional)
- **description**: Human-readable description of the agent's function
- **memory_types**: Array of memory types this agent uses (factual, procedural, episodic, semantic, working)
- **priority**: Agent-specific priority (overrides category priority if lower)
- **data_retention_days**: Retention period for this agent's data
- **critical**: Mark critical agents that should always be initialized

---

## 🎨 Example Configurations

### Example 1: Simple Single-Agent Project

```json
{
  "project_name": "Personal Assistant",
  "description": "A simple AI personal assistant",
  "categories": {
    "DEFAULT": {
      "name": "DEFAULT",
      "description": "Default memory category",
      "prefix": "",
      "retention_days": 30,
      "priority": 1
    }
  },
  "agents": {
    "assistant": {
      "agent_id": "assistant",
      "category": "DEFAULT",
      "prefix": "",
      "description": "Personal assistant agent",
      "memory_types": ["episodic", "semantic"],
      "priority": 1,
      "data_retention_days": 30
    }
  }
}
```

### Example 2: E-commerce Platform

```json
{
  "project_name": "E-Commerce Platform",
  "description": "AI agents for e-commerce operations",
  "categories": {
    "INVENTORY": {
      "name": "INVENTORY",
      "description": "Inventory management and forecasting",
      "prefix": "inv_",
      "retention_days": 90,
      "priority": 1
    },
    "CUSTOMER": {
      "name": "CUSTOMER",
      "description": "Customer service and support",
      "prefix": "cust_",
      "retention_days": 365,
      "priority": 2
    },
    "ANALYTICS": {
      "name": "ANALYTICS",
      "description": "Sales analytics and reporting",
      "prefix": "analytics_",
      "retention_days": 180,
      "priority": 3
    }
  },
  "agents": {
    "inventory-manager": {
      "agent_id": "inventory-manager",
      "category": "INVENTORY",
      "prefix": "inv_",
      "description": "Manages stock levels and predicts demand",
      "memory_types": ["factual", "procedural"],
      "priority": 1,
      "data_retention_days": 90
    },
    "customer-support": {
      "agent_id": "customer-support",
      "category": "CUSTOMER",
      "prefix": "cust_",
      "description": "Handles customer inquiries and issues",
      "memory_types": ["episodic", "procedural"],
      "priority": 2,
      "data_retention_days": 365
    },
    "sales-analyst": {
      "agent_id": "sales-analyst",
      "category": "ANALYTICS",
      "prefix": "analytics_",
      "description": "Analyzes sales trends and generates reports",
      "memory_types": ["semantic", "factual"],
      "priority": 3,
      "data_retention_days": 180
    }
  }
}
```

### Example 3: Healthcare System

```json
{
  "project_name": "Healthcare AI System",
  "description": "AI agents for healthcare operations",
  "categories": {
    "DIAGNOSTIC": {
      "name": "DIAGNOSTIC",
      "description": "Diagnostic and analysis tools",
      "prefix": "diag_",
      "retention_days": 365,
      "priority": 1
    },
    "PATIENT_CARE": {
      "name": "PATIENT_CARE",
      "description": "Patient care and monitoring",
      "prefix": "care_",
      "retention_days": 2555,  // 7 years for medical records
      "priority": 1
    },
    "ADMIN": {
      "name": "ADMIN",
      "description": "Administrative and scheduling",
      "prefix": "admin_",
      "retention_days": 90,
      "priority": 2
    }
  },
  "agents": {
    "diagnostic-agent": {
      "agent_id": "diagnostic-agent",
      "category": "DIAGNOSTIC",
      "prefix": "diag_",
      "description": "Analyzes symptoms and medical data",
      "memory_types": ["factual", "semantic"],
      "priority": 1,
      "data_retention_days": 365,
      "critical": true
    },
    "patient-monitor": {
      "agent_id": "patient-monitor",
      "category": "PATIENT_CARE",
      "prefix": "care_",
      "description": "Monitors patient vitals and alerts",
      "memory_types": ["episodic", "factual"],
      "priority": 1,
      "data_retention_days": 2555,
      "critical": true
    },
    "scheduler": {
      "agent_id": "scheduler",
      "category": "ADMIN",
      "prefix": "admin_",
      "description": "Schedules appointments and manages calendars",
      "memory_types": ["procedural", "working"],
      "priority": 2,
      "data_retention_days": 90
    }
  }
}
```

---

## 💡 Common Use Cases

### Use Case 1: No Categorization Needed

If your project only has one or a few agents and doesn't need complex categorization:

```json
{
  "project_name": "Simple Bot",
  "categories": {
    "DEFAULT": {
      "name": "DEFAULT",
      "description": "Default",
      "prefix": "",
      "retention_days": 30,
      "priority": 1
    }
  },
  "agents": {}
}
```

### Use Case 2: Team-Based Organization

For projects organized by teams:

```json
{
  "project_name": "Multi-Team Project",
  "categories": {
    "TEAM_A": {
      "name": "TEAM_A",
      "description": "Team A agents",
      "prefix": "team_a_",
      "retention_days": 30,
      "priority": 1
    },
    "TEAM_B": {
      "name": "TEAM_B",
      "description": "Team B agents",
      "prefix": "team_b_",
      "retention_days": 30,
      "priority": 1
    }
  },
  "agents": {}
}
```

### Use Case 3: Functional Organization

For projects organized by function:

```json
{
  "project_name": "Functional System",
  "categories": {
    "INPUT": {
      "name": "INPUT",
      "description": "Input processing agents",
      "prefix": "in_",
      "retention_days": 7,
      "priority": 1
    },
    "PROCESSING": {
      "name": "PROCESSING",
      "description": "Data processing agents",
      "prefix": "proc_",
      "retention_days": 14,
      "priority": 2
    },
    "OUTPUT": {
      "name": "OUTPUT",
      "description": "Output generation agents",
      "prefix": "out_",
      "retention_days": 7,
      "priority": 3
    }
  },
  "agents": {}
}
```

---

## 🔧 Troubleshooting

### Issue: Configuration Not Loading

**Problem**: Enhanced Cognee is using default categories instead of your custom ones.

**Solutions**:
1. Verify config file location: Must be in project root or parent directories
2. Check filename: Must be exactly `.enhanced-cognee-config.json`
3. Set environment variable: `export ENHANCED_COGNEE_CONFIG_PATH=/path/to/config`
4. Check JSON syntax: Use `jq . .enhanced-cognee-config.json` to validate

### Issue: Agent Not Found

**Problem**: Error about agent not being in registry.

**Solutions**:
1. Verify agent_id matches config exactly
2. Check category is defined in `categories` section
3. Ensure `category` field in agent config matches category name exactly

### Issue: Prefix Not Applied

**Problem**: Memories not using the expected prefix.

**Solutions**:
1. Check prefix is defined in category config
2. Verify MCP server is restarted after config changes
3. Check for typos in prefix field

### Issue: Memory Retention Not Working

**Problem**: Old memories not being cleaned up.

**Solutions**:
1. Verify `retention_days` is set in config
2. Check cleanup jobs are running in Enhanced Cognee
3. Manually trigger cleanup: Use `prune` MCP tool

---

## 📚 Additional Resources

- [Enhanced Cognee README](../README.md) - Main Enhanced Cognee documentation
- [MCP Protocol Guide](https://modelcontextprotocol.io/) - MCP specification
- [Configuration Examples](../examples/) - More example configurations

---

## 🤝 Contributing

When creating configurations for new projects, please consider sharing them as examples by submitting a pull request to the `examples/` directory.

---

**Last Updated**: January 2, 2026
**Version**: 1.0.0
**Maintained By**: Enhanced Cognee Team
