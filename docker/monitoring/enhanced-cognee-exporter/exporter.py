#!/usr/bin/env python3
"""
RNR Enhanced Cognee Prometheus Exporter
Exports RNR Enhanced Cognee metrics for Prometheus monitoring
"""

import asyncio
import json
import logging
import time
import os
from datetime import datetime
from typing import Dict, Any, List

import aiohttp
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Summary

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RNR Enhanced Cognee Metrics
# Memory Operations
MEMORY_OPERATIONS_TOTAL = Counter(
    'enhanced_cognee_memory_operations_total',
    'Total memory operations',
    ['operation', 'agent_id', 'category']
)

MEMORY_OPERATION_DURATION = Histogram(
    'enhanced_cognee_memory_operation_duration_seconds',
    'Duration of memory operations',
    ['operation', 'agent_id', 'category'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

MEMORY_STORAGE_BYTES = Gauge(
    'enhanced_cognee_memory_storage_bytes',
    'Total memory storage in bytes',
    ['category', 'agent_id']
)

MEMORY_SEARCH_RELEVANCE_SCORE = Gauge(
    'enhanced_cognee_memory_search_relevance_score',
    'Average search relevance score',
    ['agent_id']
)

# Agent Coordination Metrics
AGENT_LOAD_PERCENTAGE = Gauge(
    'enhanced_cognee_agent_load_percentage',
    'Agent load percentage',
    ['agent_id', 'category']
)

COORDINATION_TASKS_TOTAL = Counter(
    'enhanced_cognee_coordination_tasks_total',
    'Total coordination tasks',
    ['status', 'priority']
)

COORDINATION_TASKS_FAILED = Counter(
    'enhanced_cognee_coordination_tasks_failed',
    'Failed coordination tasks',
    ['agent_id', 'reason']
)

COORDINATION_MESSAGES_TOTAL = Counter(
    'enhanced_cognee_coordination_messages_total',
    'Total coordination messages',
    ['message_type', 'from_agent', 'to_agent']
)

# System Health Metrics
SYSTEM_COMPONENT_STATUS = Gauge(
    'enhanced_cognee_system_component_status',
    'System component status (1=up, 0=down)',
    ['component', 'instance']
)

SYSTEM_ACTIVE_AGENTS = Gauge(
    'enhanced_cognee_system_active_agents',
    'Number of active agents',
    ['category']
)

SYSTEM_ACTIVE_SESSIONS = Gauge(
    'enhanced_cognee_system_active_sessions',
    'Number of active sessions'
)

# Performance Metrics
MEMORY_SEARCH_DURATION = Histogram(
    'enhanced_cognee_memory_search_duration_seconds',
    'Duration of memory search operations',
    ['agent_id'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)

MEMORY_STORAGE_DURATION = Histogram(
    'enhanced_cognee_memory_storage_duration_seconds',
    'Duration of memory storage operations',
    ['agent_id'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

AGENT_RESPONSE_TIME = Summary(
    'enhanced_cognee_agent_response_time_seconds',
    'Agent response time summary',
    ['agent_id']
)

class EnhancedCogneeExporter:
    """RNR Enhanced Cognee Prometheus Exporter"""

    def __init__(self):
        self.api_url = os.getenv('ENHANCED_COGNEE_API_URL', 'http://enhanced-cognee-server:8080')
        self.polling_interval = int(os.getenv('POLLING_INTERVAL', 15))
        self.session = None

    async def start(self):
        """Start the exporter"""
        logger.info("Starting RNR Enhanced Cognee Prometheus Exporter")

        # Start HTTP server
        port = int(os.getenv('EXPORTER_PORT', 8000))
        start_http_server(port)
        logger.info(f"Prometheus exporter started on port {port}")

        # Start metrics collection
        await self.collect_metrics_loop()

    async def collect_metrics_loop(self):
        """Main metrics collection loop"""
        while True:
            try:
                await self.collect_all_metrics()
                await asyncio.sleep(self.polling_interval)
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(5)

    async def collect_all_metrics(self):
        """Collect all RNR Enhanced Cognee metrics"""
        try:
            # Initialize HTTP session
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10)
                )

            # Collect system health metrics
            await self.collect_system_health_metrics()

            # Collect coordination metrics
            await self.collect_coordination_metrics()

            # Collect memory metrics
            await self.collect_memory_metrics()

            # Collect performance metrics
            await self.collect_performance_metrics()

        except Exception as e:
            logger.error(f"Error in metrics collection: {e}")

    async def collect_system_health_metrics(self):
        """Collect system health metrics"""
        try:
            # Check system health
            async with self.session.get(f"{self.api_url}/health") as response:
                health_data = await response.json()

                # Update component status
                components = health_data.get('components', {})
                for component, status in components.items():
                    status_value = 1 if status == 'healthy' else 0
                    SYSTEM_COMPONENT_STATUS.labels(
                        component=component,
                        instance='enhanced-cognee'
                    ).set(status_value)

        except Exception as e:
            logger.error(f"Error collecting system health metrics: {e}")

        try:
            # Get coordination overview
            async with self.session.get(f"{self.api_url}/overview") as response:
                overview_data = await response.json()

                coordination_overview = overview_data.get('coordination_overview', {})

                # Update agent counts by category
                agent_stats = coordination_overview.get('agent_loads', {})
                category_stats = {
                    'ATS': 0,
                    'OMA': 0,
                    'SMC': 0
                }

                for agent_id, agent_data in agent_stats.items():
                    # Determine category
                    if agent_id.startswith('ats_'):
                        category = 'ATS'
                    elif agent_id.startswith('oma_'):
                        category = 'OMA'
                    elif agent_id.startswith('smc_'):
                        category = 'SMC'
                    else:
                        continue

                    # Update load
                    load = agent_data.get('load_percentage', 0)
                    AGENT_LOAD_PERCENTAGE.labels(
                        agent_id=agent_id,
                        category=category
                    ).set(load)

                    # Count active agents
                    if agent_data.get('status') == 'active':
                        category_stats[category] += 1

                # Update active agent counts
                for category, count in category_stats.items():
                    SYSTEM_ACTIVE_AGENTS.labels(category=category).set(count)

        except Exception as e:
            logger.error(f"Error collecting coordination metrics: {e}")

    async def collect_coordination_metrics(self):
        """Collect coordination metrics"""
        try:
            # Get task analytics
            async with self.session.get(f"{self.api_url}/analytics/tasks") as response:
                task_data = await response.json()

                total_tasks = task_data.get('total_tasks', 0)
                status_breakdown = task_data.get('status_breakdown', {})

                for status, count in status_breakdown.items():
                    COORDINATION_TASKS_TOTAL.labels(
                        status=status,
                        priority='all'
                    )._value._value = count  # Direct value setting

        except Exception as e:
            logger.error(f"Error collecting task analytics: {e}")

    async def collect_memory_metrics(self):
        """Collect memory metrics"""
        try:
            # This would integrate with actual RNR Enhanced Cognee memory statistics
            # For now, using placeholder data

            # Simulate memory storage metrics
            categories = ['ATS', 'OMA', 'SMC']
            for category in categories:
                storage_bytes = 1024 * 1024 * 100  # 100MB placeholder
                MEMORY_STORAGE_BYTES.labels(
                    category=category,
                    agent_id='all'
                ).set(storage_bytes)

            # Simulate search relevance scores
            relevance_score = 0.85  # 85% relevance placeholder
            MEMORY_SEARCH_RELEVANCE_SCORE.labels(
                agent_id='enhanced-cognee'
            ).set(relevance_score)

        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")

    async def collect_performance_metrics(self):
        """Collect performance metrics"""
        try:
            # Get system overview for performance data
            async with self.session.get(f"{self.api_url}/overview") as response:
                overview_data = await response.json()

                coordination_overview = overview_data.get('coordination_overview', {})

                # Update agent response times
                agent_stats = coordination_overview.get('agent_loads', {})
                for agent_id, agent_data in agent_stats.items():
                    # Simulate response time based on load
                    load = agent_data.get('load_percentage', 0)
                    response_time = 0.1 + (load / 100) * 2  # 0.1-2.1s based on load

                    AGENT_RESPONSE_TIME.labels(agent_id=agent_id).observe(response_time)

        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")

    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

async def main():
    """Main function"""
    exporter = EnhancedCogneeExporter()

    try:
        await exporter.start()
    except KeyboardInterrupt:
        logger.info("Shutting down RNR Enhanced Cognee exporter")
    finally:
        await exporter.close()

if __name__ == "__main__":
    asyncio.run(main())