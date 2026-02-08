"use client";

import React, { useState } from "react";
import { format, parseISO, differenceInMinutes } from "date-fns";
import { ChevronDown, ChevronRight, Clock, MessageSquare } from "lucide-react";
import type { SessionResponse } from "@/lib/api/types";

export interface SessionsListProps {
  sessions: SessionResponse[];
  onSessionClick?: (sessionId: string) => void;
  className?: string;
}

/**
 * Sessions List Component
 *
 * Displays a list of sessions with expandable timeline visualization.
 */
export function SessionsList({
  sessions,
  onSessionClick,
  className = "",
}: SessionsListProps) {
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set());

  const toggleSession = (sessionId: string) => {
    const newExpanded = new Set(expandedSessions);
    if (newExpanded.has(sessionId)) {
      newExpanded.delete(sessionId);
    } else {
      newExpanded.add(sessionId);
    }
    setExpandedSessions(newExpanded);
  };

  const getDuration = (session: SessionResponse) => {
    if (!session.end_time) return null;
    const start = parseISO(session.start_time);
    const end = parseISO(session.end_time);
    const minutes = differenceInMinutes(end, start);

    if (minutes < 60) {
      return `${minutes}m`;
    }
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
  };

  return (
    <div className={`bg-slate-900 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-200">Sessions</h3>
          <span className="text-sm text-slate-400">({sessions.length} sessions)</span>
        </div>
      </div>

      {/* Sessions List */}
      <div className="space-y-4">
        {sessions.map((session) => {
          const isExpanded = expandedSessions.has(session.session_id);
          const duration = getDuration(session);

          return (
            <div
              key={session.session_id}
              className="border border-slate-700 rounded-lg overflow-hidden"
            >
              {/* Session Header */}
              <button
                onClick={() => {
                  toggleSession(session.session_id);
                  onSessionClick?.(session.session_id);
                }}
                className="w-full px-4 py-4 bg-slate-800 hover:bg-slate-750 flex items-center justify-between transition-colors"
              >
                <div className="flex items-center gap-4 flex-1">
                  {/* Expand Icon */}
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-slate-400 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
                  )}

                  {/* Session Info */}
                  <div className="flex-1 text-left min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-slate-200">
                        {format(parseISO(session.start_time), "MMMM d, yyyy")}
                      </span>
                      <span className="px-2 py-0.5 text-xs font-medium rounded bg-violet-500/20 text-violet-300">
                        {session.agent_id}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-slate-400">
                      <span>
                        {format(parseISO(session.start_time), "h:mm a")}
                        {session.end_time && ` - ${format(parseISO(session.end_time), "h:mm a")}`}
                      </span>
                      {duration && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {duration}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" />
                        {session.memory_count} memories
                      </span>
                    </div>
                  </div>
                </div>
              </button>

              {/* Session Summary (when expanded) */}
              {isExpanded && session.summary && (
                <div className="p-4 bg-slate-900 border-t border-slate-700">
                  <p className="text-sm text-slate-300">{session.summary}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Empty State */}
      {sessions.length === 0 && (
        <div className="flex items-center justify-center h-[200px] text-slate-400">
          <p>No sessions to display</p>
        </div>
      )}
    </div>
  );
}
