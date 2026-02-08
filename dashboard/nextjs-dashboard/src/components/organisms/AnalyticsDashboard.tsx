"use client";

import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Database, Server, Activity, Zap } from "lucide-react";
import { KPICard } from "@/components/molecules/KPICard";
import { LineChart } from "@/components/molecules/LineChart";
import { BarChart } from "@/components/molecules/BarChart";
import { PieChart } from "@/components/molecules/PieChart";
import { getSystemStats, getStructuredStats, checkHealth } from "@/lib/api/analytics";
import { StatusIndicator } from "@/components/ui/elements/StatusIndicator";

export interface AnalyticsDashboardProps {
  className?: string;
}

/**
 * Analytics Dashboard Component
 *
 * Comprehensive dashboard with KPIs, charts, and database status monitoring.
 */
export function AnalyticsDashboard({ className = "" }: AnalyticsDashboardProps) {
  // Fetch data
  const { data: systemStats, isLoading: statsLoading } = useQuery({
    queryKey: ["analytics", "system-stats"],
    queryFn: getSystemStats,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const { data: structuredStats } = useQuery({
    queryKey: ["analytics", "structured-stats"],
    queryFn: getStructuredStats,
    refetchInterval: 60000, // Refetch every minute
  });

  const { data: health } = useQuery({
    queryKey: ["analytics", "health"],
    queryFn: checkHealth,
    refetchInterval: 30000,
  });

  // Process memory growth data (mock for now - would come from API)
  const memoryGrowthData = useMemo(() => {
    const days = 30;
    const data = [];
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      data.push({
        date: date.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        memories: Math.floor(Math.random() * 50) + 10 + (days - i) * 2,
      });
    }
    return data;
  }, []);

  // Process memory type distribution
  const memoryTypeData = useMemo(() => {
    if (!structuredStats) return [];
    return [
      { name: "Bugfix", value: structuredStats.bugfix_count, color: "#ef4444" },
      { name: "Feature", value: structuredStats.feature_count, color: "#3b82f6" },
      { name: "Decision", value: structuredStats.decision_count, color: "#10b981" },
      { name: "Refactor", value: structuredStats.refactor_count, color: "#f59e0b" },
      { name: "Discovery", value: structuredStats.discovery_count, color: "#8b5cf6" },
      { name: "General", value: structuredStats.general_count, color: "#64748b" },
    ];
  }, [structuredStats]);

  // Process agent activity data (mock)
  const agentActivityData = useMemo(() => {
    return [
      { agent: "Claude Code", memories: 245, searches: 120, updates: 45 },
      { agent: "Trading Bot", memories: 189, searches: 98, updates: 32 },
      { agent: "Dev Assistant", memories: 156, searches: 87, updates: 28 },
      { agent: "Analysis Agent", memories: 134, searches: 76, updates: 21 },
    ];
  }, []);

  // Generate sparkline data
  const sparklineData = useMemo(() => {
    return Array.from({ length: 12 }, () => Math.floor(Math.random() * 50) + 50);
  }, []);

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const stats = systemStats!;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Memories"
          value={stats.total_memories.toLocaleString()}
          trend={{ value: 12, label: "vs last month" }}
          status="healthy"
          icon={<Database className="w-5 h-5" />}
          sparkline={sparklineData}
        />

        <KPICard
          title="Active Sessions"
          value={stats.active_sessions}
          trend={{ value: 8, label: "vs last hour" }}
          status="healthy"
          icon={<Activity className="w-5 h-5" />}
        />

        <KPICard
          title="Token Efficiency"
          value={`${stats.token_efficiency_percent.toFixed(1)}%`}
          trend={{ value: 5, label: "improvement" }}
          status="healthy"
          icon={<Zap className="w-5 h-5" />}
        />

        <KPICard
          title="System Status"
          value={health?.status || "unknown"}
          status={health?.status === "healthy" ? "healthy" : "warning"}
          icon={<Server className="w-5 h-5" />}
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Memory Growth Chart */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Memory Growth</h3>
          <LineChart
            data={memoryGrowthData}
            lines={[
              {
                dataKey: "memories",
                name: "Memories",
                color: "#3b82f6",
              },
            ]}
            xAxisKey="date"
            height={300}
          />
        </div>

        {/* Memory Type Distribution */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Memory Type Distribution</h3>
          <PieChart
            data={memoryTypeData}
            height={300}
            donut={true}
            showLabels={true}
          />
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agent Activity */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Agent Activity</h3>
          <BarChart
            data={agentActivityData}
            bars={[
              { dataKey: "memories", name: "Memories", color: "#3b82f6" },
              { dataKey: "searches", name: "Searches", color: "#10b981" },
              { dataKey: "updates", name: "Updates", color: "#f59e0b" },
            ]}
            xAxisKey="agent"
            height={300}
          />
        </div>

        {/* Token Usage Trends */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-slate-200 mb-4">Token Usage Trends</h3>
          <LineChart
            data={memoryGrowthData.map((item) => ({
              date: item.date,
              tokens: item.memories * 150, // Mock conversion
            }))}
            lines={[
              {
                dataKey: "tokens",
                name: "Tokens",
                color: "#8b5cf6",
                strokeWidth: 2,
              },
            ]}
            xAxisKey="date"
            height={300}
            curveType="monotone"
          />
        </div>
      </div>

      {/* Database Status Panel */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-slate-200 mb-4">Database Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <DatabaseStatusCard
            name="PostgreSQL"
            status={stats.database_status.postgresql ? "healthy" : "error"}
            details="Primary database"
          />
          <DatabaseStatusCard
            name="Qdrant"
            status={stats.database_status.qdrant ? "healthy" : "error"}
            details="Vector search"
          />
          <DatabaseStatusCard
            name="Neo4j"
            status={stats.database_status.neo4j ? "healthy" : "error"}
            details="Graph database"
          />
          <DatabaseStatusCard
            name="Redis"
            status={stats.database_status.redis ? "healthy" : "error"}
            details="Cache layer"
          />
        </div>
      </div>
    </div>
  );
}

interface DatabaseStatusCardProps {
  name: string;
  status: "healthy" | "warning" | "error";
  details: string;
}

function DatabaseStatusCard({ name, status, details }: DatabaseStatusCardProps) {
  return (
    <div className="flex items-center gap-3 p-3 bg-slate-700 rounded-lg border border-slate-600">
      <StatusIndicator status={status} />
      <div>
        <p className="text-sm font-medium text-slate-200">{name}</p>
        <p className="text-xs text-slate-400">{details}</p>
      </div>
    </div>
  );
}
