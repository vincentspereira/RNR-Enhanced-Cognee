"use client";

import React, { useState, useMemo } from "react";
import { format, isSameDay, parseISO } from "date-fns";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { MemoryResponse } from "@/lib/api/types";

export interface TimelineDetailProps {
  memories: MemoryResponse[];
  className?: string;
  onMemoryClick?: (memoryId: string) => void;
}

interface GroupedMemories {
  date: string;
  memories: MemoryResponse[];
}

/**
 * Timeline Detail Component
 *
 * Shows memories grouped by date with expandable/collapsible sections.
 */
export function TimelineDetail({
  memories,
  className = "",
  onMemoryClick,
}: TimelineDetailProps) {
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set());

  // Group memories by date
  const groupedMemories = useMemo(() => {
    const groups: Record<string, MemoryResponse[]> = {};

    memories.forEach((memory) => {
      const date = format(parseISO(memory.created_at), "MMMM d, yyyy");
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(memory);
    });

    // Convert to array and sort by date (descending)
    return Object.entries(groups)
      .map(([date, mems]) => ({
        date,
        memories: mems.sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        ),
      }))
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }, [memories]);

  const toggleDate = (date: string) => {
    const newExpanded = new Set(expandedDates);
    if (newExpanded.has(date)) {
      newExpanded.delete(date);
    } else {
      newExpanded.add(date);
    }
    setExpandedDates(newExpanded);
  };

  const expandAll = () => {
    setExpandedDates(new Set(groupedMemories.map((g) => g.date)));
  };

  const collapseAll = () => {
    setExpandedDates(new Set());
  };

  return (
    <div className={`bg-slate-900 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-200">Memory Details</h3>
          <span className="text-sm text-slate-400">({memories.length} memories)</span>
        </div>

        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="px-3 py-1.5 text-sm text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
          >
            Expand All
          </button>
          <button
            onClick={collapseAll}
            className="px-3 py-1.5 text-sm text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Grouped Memories */}
      <div className="space-y-4">
        {groupedMemories.map(({ date, memories: dayMemories }) => {
          const isExpanded = expandedDates.has(date);

          return (
            <div
              key={date}
              className="border border-slate-700 rounded-lg overflow-hidden"
            >
              {/* Date Header */}
              <button
                onClick={() => toggleDate(date)}
                className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-750 flex items-center justify-between transition-colors"
              >
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-slate-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-slate-400" />
                  )}
                  <span className="text-sm font-medium text-slate-200">{date}</span>
                </div>
                <span className="text-sm text-slate-400">
                  {dayMemories.length} {dayMemories.length === 1 ? "memory" : "memories"}
                </span>
              </button>

              {/* Memories List */}
              {isExpanded && (
                <div className="p-4 space-y-3 bg-slate-900">
                  {dayMemories.map((memory) => (
                    <div
                      key={memory.memory_id}
                      onClick={() => onMemoryClick?.(memory.memory_id)}
                      className="p-4 bg-slate-800 rounded-lg border border-slate-700 hover:border-slate-600 cursor-pointer transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          {/* Badges */}
                          <div className="flex items-center gap-2 mb-2">
                            {memory.memory_type && (
                              <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-500/20 text-blue-300 capitalize">
                                {memory.memory_type}
                              </span>
                            )}
                            {memory.memory_concept && (
                              <span className="px-2 py-0.5 text-xs font-medium rounded bg-violet-500/20 text-violet-300">
                                {memory.memory_concept}
                              </span>
                            )}
                          </div>

                          {/* Summary */}
                          <p className="text-sm text-slate-300 line-clamp-2 mb-2">
                            {memory.summary || memory.content.slice(0, 200)}
                          </p>

                          {/* Metadata */}
                          <div className="flex items-center gap-4 text-xs text-slate-400">
                            <span>
                              {format(parseISO(memory.created_at), "h:mm a")}
                            </span>
                            <span>Agent: {memory.data_type}</span>
                            {memory.estimated_tokens && (
                              <span>{memory.estimated_tokens} tokens</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Empty State */}
      {groupedMemories.length === 0 && (
        <div className="flex items-center justify-center h-[200px] text-slate-400">
          <p>No memories to display</p>
        </div>
      )}
    </div>
  );
}
