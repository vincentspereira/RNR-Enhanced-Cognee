"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { StatusDot } from "@/components/ui/elements/StatusDot";

export interface KPICardProps {
  title: string;
  value: string | number;
  trend?: {
    value: number;
    label: string;
  };
  status?: "healthy" | "warning" | "error" | "neutral";
  icon?: React.ReactNode;
  sparkline?: number[];
  className?: string;
}

/**
 * KPI Card Component
 *
 * Displays a key performance indicator with value, trend, and status.
 */
export function KPICard({
  title,
  value,
  trend,
  status = "neutral",
  icon,
  sparkline,
  className = "",
}: KPICardProps) {
  const trendIcon = trend && trend.value > 0 ? TrendingUp : trend && trend.value < 0 ? TrendingDown : Minus;
  const trendColor = trend && trend.value > 0 ? "text-emerald-400" : trend && trend.value < 0 ? "text-red-400" : "text-slate-400";

  return (
    <div className={`bg-slate-800 rounded-lg p-6 border border-slate-700 ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          {icon && <div className="text-slate-400">{icon}</div>}
          <h3 className="text-sm font-medium text-slate-400">{title}</h3>
        </div>
        <StatusDot status={status} size="sm" />
      </div>

      {/* Value */}
      <div className="mb-2">
        <p className="text-3xl font-bold text-slate-100">{value}</p>
      </div>

      {/* Trend */}
      {trend && (
        <div className="flex items-center gap-1 text-sm">
          {trendIcon && <trendIcon className={`w-4 h-4 ${trendColor}`} />}
          <span className={trendColor}>
            {trend.value > 0 ? "+" : ""}
            {trend.value}%
          </span>
          <span className="text-slate-400 ml-1">{trend.label}</span>
        </div>
      )}

      {/* Sparkline (optional) */}
      {sparkline && sparkline.length > 0 && (
        <div className="mt-4 h-12 flex items-end gap-0.5">
          {sparkline.map((value, index) => (
            <div
              key={index}
              className="flex-1 bg-blue-500/50 hover:bg-blue-500 transition-colors rounded-t"
              style={{
                height: `${((value - Math.min(...sparkline)) / (Math.max(...sparkline) - Math.min(...sparkline))) * 100}%`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
