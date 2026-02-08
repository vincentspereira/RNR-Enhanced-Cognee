"use client";

import React, { useState, useMemo, useRef } from "react";
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  BarChart,
  Bar,
  type TooltipProps,
} from "recharts";
import { format, subDays, subMonths, subYears, startOfDay } from "date-fns";
import { ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Download, Filter } from "lucide-react";
import { NeutralButton } from "@/components/ui/elements/NeutralButton";
import { IconButton } from "@/components/ui/elements/IconButton";
import { exportChartAsPNG } from "@/lib/utils/chart-export";
import type { MemoryResponse } from "@/lib/api/types";

export type MemoryType = "bugfix" | "feature" | "decision" | "refactor" | "discovery" | "general";

export interface TimelineViewProps {
  memories: MemoryResponse[];
  className?: string;
}

type ZoomLevel = "day" | "week" | "month" | "year" | "all";

const MEMORY_TYPE_COLORS: Record<MemoryType, string> = {
  bugfix: "#ef4444", // red
  feature: "#3b82f6", // blue
  decision: "#10b981", // emerald
  refactor: "#f59e0b", // amber
  discovery: "#8b5cf6", // violet
  general: "#64748b", // slate
};

/**
 * Custom Tooltip
 */
const CustomTooltip = ({ active, payload, label }: TooltipProps<string, string>) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-slate-200 text-sm font-medium mb-2">{label}</p>
        {payload.map((entry) => (
          <p key={entry.name} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

/**
 * Timeline View Component
 *
 * Displays memories chronologically with zoom, pan, and filtering capabilities.
 */
export function TimelineView({ memories, className = "" }: TimelineViewProps) {
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>("month");
  const [selectedTypes, setSelectedTypes] = useState<Set<MemoryType>>(
    new Set(Object.keys(MEMORY_TYPE_COLORS) as MemoryType[])
  );
  const [dateOffset, setDateOffset] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);

  // Process memories into timeline data
  const timelineData = useMemo(() => {
    const now = new Date();
    let startDate: Date;
    let groupBy: string;

    switch (zoomLevel) {
      case "day":
        startDate = subDays(now, 1);
        groupBy = "hour";
        break;
      case "week":
        startDate = subDays(now, 7);
        groupBy = "day";
        break;
      case "month":
        startDate = subMonths(now, 1);
        groupBy = "day";
        break;
      case "year":
        startDate = subYears(now, 1);
        groupBy = "week";
        break;
      case "all":
        startDate = new Date(0); // Epoch
        groupBy = "month";
        break;
      default:
        startDate = subMonths(now, 1);
        groupBy = "day";
    }

    // Apply date offset
    startDate = new Date(startDate.getTime() + dateOffset * (24 * 60 * 60 * 1000));

    // Group memories by date
    const grouped: Record<string, Record<MemoryType, number>> = {};

    memories.forEach((memory) => {
      const memoryDate = new Date(memory.created_at);
      if (memoryDate < startDate) return;

      const memoryType = (memory.memory_type || "general") as MemoryType;
      if (!selectedTypes.has(memoryType)) return;

      let key: string;
      switch (groupBy) {
        case "hour":
          key = format(memoryDate, "MMM d, ha");
          break;
        case "day":
          key = format(memoryDate, "MMM d, yyyy");
          break;
        case "week":
          const weekStart = startOfDay(memoryDate);
          weekStart.setDate(weekStart.getDate() - weekStart.getDay());
          key = format(weekStart, "MMM d, yyyy");
          break;
        case "month":
          key = format(memoryDate, "MMM yyyy");
          break;
        default:
          key = format(memoryDate, "MMM d, yyyy");
      }

      if (!grouped[key]) {
        grouped[key] = {
          bugfix: 0,
          feature: 0,
          decision: 0,
          refactor: 0,
          discovery: 0,
          general: 0,
        };
      }

      grouped[key][memoryType]++;
    });

    // Convert to array and sort
    return Object.entries(grouped)
      .map(([date, counts]) => ({
        date,
        ...counts,
      }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [memories, zoomLevel, selectedTypes, dateOffset]);

  const handleExportPNG = async () => {
    try {
      await exportChartAsPNG(chartRef, "timeline.png");
    } catch (error) {
      console.error("Failed to export timeline:", error);
    }
  };

  const toggleType = (type: MemoryType) => {
    const newSelected = new Set(selectedTypes);
    if (newSelected.has(type)) {
      newSelected.delete(type);
    } else {
      newSelected.add(type);
    }
    setSelectedTypes(newSelected);
  };

  const zoomIn = () => {
    const levels: ZoomLevel[] = ["all", "year", "month", "week", "day"];
    const currentIndex = levels.indexOf(zoomLevel);
    if (currentIndex < levels.length - 1) {
      setZoomLevel(levels[currentIndex + 1]);
    }
  };

  const zoomOut = () => {
    const levels: ZoomLevel[] = ["all", "year", "month", "week", "day"];
    const currentIndex = levels.indexOf(zoomLevel);
    if (currentIndex > 0) {
      setZoomLevel(levels[currentIndex - 1]);
    }
  };

  const panLeft = () => setDateOffset((prev) => prev - 1);
  const panRight = () => setDateOffset((prev) => prev + 1);

  return (
    <div className={`bg-slate-900 rounded-lg p-6 ${className}`} ref={chartRef}>
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-200">Memory Timeline</h3>
          <span className="text-sm text-slate-400">
            ({timelineData.length} time periods)
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom Controls */}
          <div className="flex items-center gap-1 border border-slate-700 rounded-lg p-1">
            <NeutralButton onClick={zoomOut} size="sm" disabled={zoomLevel === "all"}>
              <ZoomOut className="w-4 h-4" />
            </NeutralButton>
            <span className="px-2 text-sm text-slate-300 capitalize">{zoomLevel}</span>
            <NeutralButton onClick={zoomIn} size="sm" disabled={zoomLevel === "day"}>
              <ZoomIn className="w-4 h-4" />
            </NeutralButton>
          </div>

          {/* Pan Controls */}
          <div className="flex items-center gap-1 border border-slate-700 rounded-lg p-1">
            <IconButton onClick={panLeft} size="sm" icon={<ChevronLeft className="w-4 h-4" />} />
            <IconButton onClick={panRight} size="sm" icon={<ChevronRight className="w-4 h-4" />} />
          </div>

          {/* Filter Toggle */}
          <NeutralButton onClick={() => setShowFilters(!showFilters)} size="sm">
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </NeutralButton>

          {/* Export */}
          <NeutralButton onClick={handleExportPNG} size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export
          </NeutralButton>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="mb-6 p-4 bg-slate-800 rounded-lg border border-slate-700">
          <h4 className="text-sm font-medium text-slate-300 mb-3">Filter by Memory Type</h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(MEMORY_TYPE_COLORS).map(([type, color]) => {
              const isSelected = selectedTypes.has(type as MemoryType);
              return (
                <button
                  key={type}
                  onClick={() => toggleType(type as MemoryType)}
                  className={`
                    px-3 py-1.5 rounded-md text-sm font-medium capitalize transition-colors
                    ${isSelected ? "text-white" : "text-slate-400"}
                  `}
                  style={{
                    backgroundColor: isSelected ? color : "#334155",
                  }}
                >
                  {type}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Timeline Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={timelineData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />

          <XAxis
            dataKey="date"
            stroke="#94a3b8"
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            tickLine={{ stroke: "#334155" }}
            angle={-45}
            textAnchor="end"
            height={80}
          />

          <YAxis
            stroke="#94a3b8"
            tick={{ fill: "#94a3b8" }}
            tickLine={{ stroke: "#334155" }}
          />

          <Tooltip content={<CustomTooltip />} />

          <Legend wrapperStyle={{ color: "#cbd5e1" }} />

          {Array.from(selectedTypes).map((type) => (
            <Bar
              key={type}
              dataKey={type}
              name={type}
              fill={MEMORY_TYPE_COLORS[type]}
              stackId="timeline"
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Empty State */}
      {timelineData.length === 0 && (
        <div className="flex items-center justify-center h-[400px] text-slate-400">
          <p>No memories found for the selected time range and filters</p>
        </div>
      )}
    </div>
  );
}
