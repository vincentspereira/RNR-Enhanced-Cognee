"use client";

import React, { useMemo } from "react";
import { useSystemStats, useStructuredStats } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/atoms";
import { Skeleton } from "@/components/atoms";
import { AnalyticsDashboard } from "@/components/organisms/AnalyticsDashboard";

export default function AnalyticsPage() {
  const { data: systemStats, isLoading: systemLoading } = useSystemStats();
  const { data: structuredStats, isLoading: structuredLoading } = useStructuredStats();

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-100">Analytics</h1>
        <p className="text-slate-400">
          System performance and memory statistics
        </p>
      </div>

      {/* Enhanced Dashboard with Visualizations */}
      <AnalyticsDashboard />

      {/* Original Stats Cards as Backup */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold text-slate-200 mb-4">Detailed Statistics</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>System Overview</CardTitle>
          </CardHeader>
          <CardContent>
            {systemLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : systemStats ? (
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Memories:</span>
                  <span className="font-semibold">{systemStats.total_memories}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Sessions:</span>
                  <span className="font-semibold">{systemStats.total_sessions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Active Sessions:</span>
                  <span className="font-semibold">{systemStats.active_sessions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Avg Tokens/Memory:</span>
                  <span className="font-semibold">
                    {systemStats.avg_tokens_per_memory.toFixed(1)}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">No data available</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Structured Memories</CardTitle>
          </CardHeader>
          <CardContent>
            {structuredLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : structuredStats ? (
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Observations:</span>
                  <span className="font-semibold">{structuredStats.total_observations}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Bugfixes:</span>
                  <span className="font-semibold">{structuredStats.bugfix_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Features:</span>
                  <span className="font-semibold">{structuredStats.feature_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Decisions:</span>
                  <span className="font-semibold">{structuredStats.decision_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Refactors:</span>
                  <span className="font-semibold">{structuredStats.refactor_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Discoveries:</span>
                  <span className="font-semibold">{structuredStats.discovery_count}</span>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">No data available</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Database Status</CardTitle>
          </CardHeader>
          <CardContent>
            {systemLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : systemStats ? (
              <div className="space-y-2">
                {Object.entries(systemStats.database_status).map(([db, status]) => (
                  <div key={db} className="flex justify-between items-center">
                    <span className="text-muted-foreground capitalize">{db}:</span>
                    <span className={`font-semibold ${status ? "text-green-600" : "text-red-600"}`}>
                      {status ? "Connected" : "Disconnected"}
                    </span>
                  </div>
                ))}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Server Uptime:</span>
                  <span className="font-semibold">{systemStats.server_uptime}</span>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">No data available</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Token Efficiency</CardTitle>
        </CardHeader>
        <CardContent>
          {systemLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : systemStats ? (
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Compression Efficiency</span>
                  <span className="text-sm font-semibold">{systemStats.token_efficiency_percent.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-secondary rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all"
                    style={{ width: `${systemStats.token_efficiency_percent}%` }}
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                This metric represents the percentage of token savings achieved through memory compression and summarization.
              </p>
            </div>
          ) : (
            <p className="text-muted-foreground">No data available</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
