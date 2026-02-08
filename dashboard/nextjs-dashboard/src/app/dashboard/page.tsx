"use client";

import { useMemories, useSystemStats } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/atoms";
import { Skeleton } from "@/components/atoms";
import { formatNumber, formatRelativeTime } from "@/lib/utils";

export default function DashboardPage() {
  const { data: memories, isLoading: memoriesLoading, error: memoriesError } = useMemories({ limit: 10 });
  const { data: stats, isLoading: statsLoading } = useSystemStats();

  const totalMemories = stats?.total_memories || memories?.length || 0;
  const totalSessions = stats?.total_sessions || 0;
  const activeSessions = stats?.active_sessions || 0;
  const tokenEfficiency = stats?.token_efficiency_percent || 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your Enhanced Cognee memory system
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Memories
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">{formatNumber(totalMemories)}</div>
                <p className="text-xs text-muted-foreground">
                  +12% from last month
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Agents
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">{activeSessions}</div>
                <p className="text-xs text-muted-foreground">
                  {activeSessions} currently active
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Sessions
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">{formatNumber(totalSessions)}</div>
                <p className="text-xs text-muted-foreground">
                  All time sessions
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Token Efficiency
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">{tokenEfficiency.toFixed(1)}%</div>
                <p className="text-xs text-muted-foreground">
                  Compression ratio
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {memoriesLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : memoriesError ? (
            <div className="text-destructive text-center py-8">
              Error loading memories: {memoriesError.message}
            </div>
          ) : memories && memories.length > 0 ? (
            <div className="space-y-4">
              {memories.slice(0, 5).map((memory) => (
                <div key={memory.id} className="flex items-center space-x-4">
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {memory.summary || memory.content.slice(0, 80)}...
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Agent: {memory.memory_type || "N/A"} • {formatRelativeTime(memory.created_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No memories found. Start by adding your first memory!
            </div>
          )}
        </CardContent>
      </Card>

      {/* Database Status */}
      {stats?.database_status && (
        <Card>
          <CardHeader>
            <CardTitle>System Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {Object.entries(stats.database_status).map(([db, status]) => (
                <div key={db} className="flex items-center space-x-2">
                  <div className={`h-2 w-2 rounded-full ${status ? "bg-green-500" : "bg-red-500"}`} />
                  <span className="text-sm font-medium capitalize">{db}</span>
                  <span className={`text-xs ${status ? "text-green-600" : "text-red-600"}`}>
                    {status ? "OK" : "Error"}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
