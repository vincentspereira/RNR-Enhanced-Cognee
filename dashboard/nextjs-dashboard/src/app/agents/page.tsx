"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/atoms";
import { Button } from "@/components/atoms";
import { Skeleton } from "@/components/atoms";
import { apiClient } from "@/lib/api/client";
import { formatRelativeTime } from "@/lib/utils";
import { Users, Database, Activity, ArrowRight, RefreshCw } from "lucide-react";

interface AgentRecord {
  agent_id: string;
  memory_count: number;
  last_activity: string | null;
  category_count: number;
}

async function getAgents(): Promise<AgentRecord[]> {
  const response = await apiClient.get<AgentRecord[]>("/api/agents");
  return response.data;
}

export default function AgentsPage() {
  const router = useRouter();

  const { data: agents, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["agents"],
    queryFn: getAgents,
  });

  const handleAgentClick = (agentId: string) => {
    router.push(`/memories?agent_id=${encodeURIComponent(agentId)}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground">
            Manage and monitor your AI agents
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-16 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
          <p className="text-destructive mb-4">
            Error loading agents: {error instanceof Error ? error.message : "Unknown error"}
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      ) : agents && agents.length > 0 ? (
        <div className="space-y-3">
          {/* Table Header */}
          <div className="hidden md:grid grid-cols-4 gap-4 px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            <span>Agent ID</span>
            <span className="text-center">Memories</span>
            <span className="text-center">Categories</span>
            <span>Last Activity</span>
          </div>

          {agents.map((agent) => (
            <Card
              key={agent.agent_id}
              className="hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => handleAgentClick(agent.agent_id)}
            >
              <CardContent className="p-4">
                {/* Mobile layout */}
                <div className="md:hidden space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-medium truncate">
                      {agent.agent_id}
                    </span>
                    <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Database className="h-3.5 w-3.5" />
                      {agent.memory_count} memories
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="h-3.5 w-3.5" />
                      {agent.category_count} categories
                    </span>
                  </div>
                  {agent.last_activity && (
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      <Activity className="h-3 w-3" />
                      {formatRelativeTime(agent.last_activity)}
                    </p>
                  )}
                </div>

                {/* Desktop layout */}
                <div className="hidden md:grid grid-cols-4 gap-4 items-center">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Users className="h-4 w-4 text-primary" />
                    </div>
                    <span className="font-mono text-sm font-medium truncate">
                      {agent.agent_id}
                    </span>
                  </div>
                  <div className="flex items-center justify-center gap-1 text-sm">
                    <Database className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-medium">{agent.memory_count}</span>
                  </div>
                  <div className="flex items-center justify-center gap-1 text-sm text-muted-foreground">
                    <span>{agent.category_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      {agent.last_activity
                        ? formatRelativeTime(agent.last_activity)
                        : "Never"}
                    </span>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          No agents found. Agents will appear here when memories are added with an agent ID.
        </div>
      )}
    </div>
  );
}
