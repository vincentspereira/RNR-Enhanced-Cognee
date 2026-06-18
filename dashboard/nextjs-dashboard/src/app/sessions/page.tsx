"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSessions } from "@/lib/hooks";
import { Card, CardContent, Skeleton } from "@/components/atoms";
import { formatRelativeTime } from "@/lib/utils";
import { SessionsList } from "@/components/organisms/SessionsList";
import { SessionTimeline } from "@/components/organisms/SessionTimeline";
import { apiClient } from "@/lib/api/client";
import type { SessionResponse, MemoryResponse } from "@/lib/api/types";

function useSessionMemories(sessionId: string | null) {
  return useQuery({
    queryKey: ["session-memories", sessionId],
    queryFn: async () => {
      if (!sessionId) return [];
      // Fetch session to get agent_id, then fetch memories for that agent
      const sessionRes = await apiClient.get<SessionResponse>(`/api/sessions/${sessionId}`);
      const session = sessionRes.data;
      // Fetch memories for this agent around the session time window
      const memoriesRes = await apiClient.get<{ memories: MemoryResponse[] }>(
        `/api/memories?limit=50&agent_id=${encodeURIComponent(session.agent_id)}`
      );
      return memoriesRes.data.memories || [];
    },
    enabled: !!sessionId,
  });
}

export default function SessionsPage() {
  const { data: sessions, isLoading, error } = useSessions({ limit: 20 });
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  const { data: sessionMemories, isLoading: isLoadingMemories } =
    useSessionMemories(selectedSessionId);

  const handleSessionClick = (sessionId: string) => {
    setSelectedSessionId((prev) => (prev === sessionId ? null : sessionId));
  };

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Sessions</h1>
        <p className="text-muted-foreground">
          View and manage agent sessions with timeline visualization
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sessions List */}
        {isLoading ? (
          <div className="bg-slate-900 rounded-lg p-6 space-y-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
            <p className="text-destructive">Error loading sessions: {error.message}</p>
          </div>
        ) : (
          <SessionsList
            sessions={(sessions || []) as SessionResponse[]}
            onSessionClick={handleSessionClick}
          />
        )}

        {/* Timeline Panel */}
        <div>
          {selectedSessionId ? (
            isLoadingMemories ? (
              <div className="bg-slate-900 rounded-lg p-6 space-y-4">
                <Skeleton className="h-6 w-48" />
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-24 w-full" />
                ))}
              </div>
            ) : (
              <SessionTimeline
                memories={sessionMemories || []}
                onMemoryClick={(memoryId) => {
                  if (typeof window !== "undefined") {
                    window.location.href = `/memories/${memoryId}`;
                  }
                }}
              />
            )
          ) : (
            <div className="bg-slate-900 rounded-lg p-6 flex items-center justify-center h-[400px] text-slate-400">
              <p>Select a session to view its timeline</p>
            </div>
          )}
        </div>
      </div>

      {/* Full Sessions Table */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">All Sessions</h2>

        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <Skeleton className="h-20 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : error ? (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
            <p className="text-destructive">Error loading sessions: {error.message}</p>
          </div>
        ) : sessions && sessions.length > 0 ? (
          <div className="space-y-4">
            {sessions.map((session) => (
              <Card
                key={session.session_id}
                className={`hover:shadow-md transition-shadow cursor-pointer ${
                  selectedSessionId === session.session_id ? "ring-2 ring-primary" : ""
                }`}
                onClick={() => handleSessionClick(session.session_id)}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold">
                          Session: {session.session_id.slice(0, 8)}...
                        </h3>
                        <span className="text-xs text-muted-foreground">
                          Agent: {session.agent_id}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        Started: {formatRelativeTime(session.start_time)}
                      </p>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-muted-foreground">
                          Memories: {session.memory_count}
                        </span>
                        {session.end_time && (
                          <span className="text-muted-foreground">
                            Ended: {formatRelativeTime(session.end_time)}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      className="text-sm text-primary hover:underline"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSessionClick(session.session_id);
                      }}
                    >
                      {selectedSessionId === session.session_id
                        ? "Hide Timeline"
                        : "View Details"}
                    </button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            No sessions found. Sessions will appear here when agents are active.
          </div>
        )}
      </div>
    </div>
  );
}
