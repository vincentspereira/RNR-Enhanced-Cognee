"use client";

import React, { useRef } from "react";
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type TooltipProps,
} from "recharts";
import { exportChartAsPNG, exportChartAsPDF } from "@/lib/utils/chart-export";
import { Download } from "lucide-react";
import { NeutralButton } from "@/components/ui/elements/NeutralButton";

export interface BarChartProps {
  data: Array<Record<string, string | number>>;
  bars: Array<{
    dataKey: string;
    name: string;
    color: string;
  }>;
  xAxisKey: string;
  height?: number;
  horizontal?: boolean;
  showLegend?: boolean;
  showGrid?: boolean;
  showTooltip?: boolean;
  stacked?: boolean;
  className?: string;
}

/**
 * Custom Tooltip component
 */
const CustomTooltip = ({ active, payload, label }: TooltipProps<string, string>) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-slate-200 text-sm font-medium mb-2">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

/**
 * Bar Chart Component
 *
 * A reusable bar chart component with horizontal/vertical orientation and stacking support.
 */
export function BarChart({
  data,
  bars,
  xAxisKey,
  height = 400,
  horizontal = false,
  showLegend = true,
  showGrid = true,
  showTooltip = true,
  stacked = false,
  className = "",
}: BarChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const handleExportPNG = async () => {
    try {
      await exportChartAsPNG(chartRef, "bar-chart.png");
    } catch (error) {
      console.error("Failed to export chart:", error);
    }
  };

  const handleExportPDF = async () => {
    try {
      await exportChartAsPDF(chartRef, "bar-chart.pdf");
    } catch (error) {
      console.error("Failed to export chart:", error);
    }
  };

  return (
    <div className={className} ref={chartRef}>
      <div className="flex justify-end gap-2 mb-4">
        <NeutralButton onClick={handleExportPNG} size="sm">
          <Download className="w-4 h-4 mr-2" />
          PNG
        </NeutralButton>
        <NeutralButton onClick={handleExportPDF} size="sm">
          <Download className="w-4 h-4 mr-2" />
          PDF
        </NeutralButton>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <RechartsBarChart
          data={data}
          layout={horizontal ? "horizontal" : "vertical"}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#334155" />}

          <XAxis
            dataKey={horizontal ? undefined : xAxisKey}
            type={horizontal ? "number" : "category"}
            stroke="#94a3b8"
            tick={{ fill: "#94a3b8" }}
            tickLine={{ stroke: "#334155" }}
          />

          <YAxis
            dataKey={horizontal ? xAxisKey : undefined}
            type={horizontal ? "category" : "number"}
            stroke="#94a3b8"
            tick={{ fill: "#94a3b8" }}
            tickLine={{ stroke: "#334155" }}
          />

          {showTooltip && <Tooltip content={<CustomTooltip />} />}

          {showLegend && <Legend wrapperStyle={{ color: "#cbd5e1" }} />}

          {bars.map((bar) => (
            <Bar
              key={bar.dataKey}
              dataKey={bar.dataKey}
              name={bar.name}
              fill={bar.color}
              stackId={stacked ? "stack" : undefined}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}
