"use client";

import React, { useMemo } from "react";
import { format, subDays, startOfDay, isSameDay } from "date-fns";
import type { MemoryResponse } from "@/lib/api/types";

export interface ActivityHeatmapProps {
  memories: MemoryResponse[];
  days?: number; // Number of days to show (default: 365)
  className?: string;
  onDayClick?: (date: Date) => void;
}

/**
 * Get activity level color
 */
function getActivityColor(count: number): string {
  if (count === 0) return "#1e293b"; // slate-800
  if (count <= 2) return "#065f46"; // emerald-800
  if (count <= 5) return "#059669"; // emerald-600
  if (count <= 10) return "#10b981"; // emerald-500
  if (count <= 20) return "#34d399"; // emerald-400
  return "#6ee7b7"; // emerald-300
}

/**
 * Activity Heatmap Component
 *
 * GitHub-style contribution graph showing activity over the last year.
 */
export function ActivityHeatmap({
  memories,
  days = 365,
  className = "",
  onDayClick,
}: ActivityHeatmapProps) {
  // Calculate activity data
  const activityData = useMemo(() => {
    const data: Record<string, number> = {};
    const now = new Date();

    // Initialize all days with 0
    for (let i = 0; i < days; i++) {
      const date = startOfDay(subDays(now, days - 1 - i));
      const key = date.toISOString().split("T")[0];
      data[key] = 0;
    }

    // Count memories per day
    memories.forEach((memory) => {
      const date = startOfDay(new Date(memory.created_at));
      const key = date.toISOString().split("T")[0];
      if (data.hasOwnProperty(key)) {
        data[key]++;
      }
    });

    return data;
  }, [memories, days]);

  // Organize data into weeks
  const weeks = useMemo(() => {
    const weeksData: Array<Array<{ date: Date; count: number }>> = [];
    const now = new Date();
    let currentWeek: Array<{ date: Date; count: number }> = [];
    let dayOfWeek = now.getDay(); // 0 = Sunday, 6 = Saturday

    // Start from the first day
    const startDate = startOfDay(subDays(now, days - 1));

    for (let i = 0; i < days; i++) {
      const date = startOfDay(new Date(startDate.getTime() + i * 24 * 60 * 60 * 1000));
      const key = date.toISOString().split("T")[0];
      const count = activityData[key] || 0;

      currentWeek.push({ date, count });

      // If we've completed a week (Sunday), start a new week
      if ((date.getDay() + 1) % 7 === 0 || i === days - 1) {
        weeksData.push(currentWeek);
        currentWeek = [];
      }
    }

    return weeksData;
  }, [activityData, days]);

  const totalActivity = useMemo(() => {
    return Object.values(activityData).reduce((sum, count) => sum + count, 0);
  }, [activityData]);

  const maxActivity = useMemo(() => {
    return Math.max(...Object.values(activityData));
  }, [activityData]);

  const handleDayClick = (date: Date, count: number) => {
    if (count > 0 && onDayClick) {
      onDayClick(date);
    }
  };

  return (
    <div className={`bg-slate-900 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-200">Activity Heatmap</h3>
          <span className="text-sm text-slate-400">({totalActivity} activities)</span>
        </div>
      </div>

      {/* Heatmap */}
      <div className="overflow-x-auto">
        <div className="flex gap-1 min-w-max">
          {/* Day Labels */}
          <div className="flex flex-col gap-1 mr-2 text-xs text-slate-500">
            <div className="h-3" />
            <div className="h-3">Mon</div>
            <div className="h-3" />
            <div className="h-3">Wed</div>
            <div className="h-3" />
            <div className="h-3">Fri</div>
            <div className="h-3" />
          </div>

          {/* Weeks */}
          {weeks.map((week, weekIndex) => (
            <div key={weekIndex} className="flex flex-col gap-1">
              {week.map(({ date, count }) => {
                const color = getActivityColor(count);
                const isToday = isSameDay(date, new Date());

                return (
                  <div
                    key={date.toISOString()}
                    onClick={() => handleDayClick(date, count)}
                    className={`
                      w-3 h-3 rounded-sm cursor-pointer transition-all hover:scale-110
                      ${count > 0 ? "hover:ring-2 hover:ring-emerald-400" : ""}
                      ${isToday ? "ring-2 ring-blue-400" : ""}
                    `}
                    style={{
                      backgroundColor: color,
                    }}
                    title={`${format(date, "MMM d, yyyy")}: ${count} ${count === 1 ? "memory" : "memories"}`}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-end gap-2 mt-4 text-xs text-slate-400">
        <span>Less</span>
        {[0, 1, 2, 3, 4].map((level) => (
          <div
            key={level}
            className="w-3 h-3 rounded-sm"
            style={{
              backgroundColor: getActivityColor(level === 0 ? 0 : level * 5),
            }}
          />
        ))}
        <span>More</span>
      </div>

      {/* Empty State */}
      {totalActivity === 0 && (
        <div className="flex items-center justify-center h-[200px] text-slate-400 mt-6">
          <p>No activity data available</p>
        </div>
      )}
    </div>
  );
}
