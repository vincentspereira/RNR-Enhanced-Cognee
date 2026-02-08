"use client";

import React, { useState } from "react";
import { useSessions } from "@/lib/hooks";
import { Card, CardContent, Skeleton } from "@/components/atoms";
import { formatRelativeTime } from "@/lib/utils";
import { SessionsList, SessionTimeline } from "@/components/organisms/SessionsList";
import type { SessionResponse, MemoryResponse } from "@/lib/api/types";

export default function SessionsPage() {
  const { data: sessions, isLoading, error } = useSessions({ limit: 20 });
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-100">Sessions</h1>
        <p className="text-slate-400">
          View and manage agent sessions with timeline visualization
        </p>
      </div>

      {/* Enhanced Sessions View */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SessionsList
          sessions={(sessions || []) as SessionResponse[]}
          onSessionClick={setSelectedSessionId}
        />
        <div>
          {selectedSessionId ? (
            <div className="bg-slate-900 rounded-lg p-6">
              <p className="text-slate-400">Session timeline would appear here</p>
            </div>
          ) : (
            <div className="bg-slate-900 rounded-lg p-6 flex items-center justify-center h-[400px] text-slate-400">
              <p>Select a session to view its timeline</p>
            </div>
          )}
        </div>
      </div>

      {/* Original View as Backup */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold text-slate-200 mb-4">All Sessions</h2>

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
            <Card key={session.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold">Session: {session.id.slice(0, 8)}...</h3>
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
                  <div className="flex gap-2">
                    <button className="text-sm text-primary hover:underline">
                      View Details
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-slate-400">
          No sessions found. Sessions will appear here when agents are active.
        </div>
      )}
      </div>
    </div>
  );
}
