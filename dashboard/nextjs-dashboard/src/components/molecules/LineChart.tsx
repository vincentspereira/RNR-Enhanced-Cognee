"use client";

import React, { useRef } from "react";
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type TooltipProps,
} from "recharts";
import { exportChartAsPNG, exportChartAsPDF, exportChartAsSVG } from "@/lib/utils/chart-export";
import { Download } from "lucide-react";
import { NeutralButton } from "@/components/ui/elements/NeutralButton";

export interface LineChartProps {
  data: Array<Record<string, string | number>>;
  lines: Array<{
    dataKey: string;
    name: string;
    color: string;
    strokeWidth?: number;
    dot?: boolean;
  }>;
  xAxisKey: string;
  height?: number;
  showLegend?: boolean;
  showGrid?: boolean;
  showTooltip?: boolean;
  curveType?: "monotone" | "linear" | "step" | "stepBefore" | "stepAfter";
  className?: string;
}

/**
 * Custom Tooltip component with better styling
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
 * Line Chart Component
 *
 * A reusable line chart component built on Recharts with export functionality.
 */
export function LineChart({
  data,
  lines,
  xAxisKey,
  height = 400,
  showLegend = true,
  showGrid = true,
  showTooltip = true,
  curveType = "monotone",
  className = "",
}: LineChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const handleExportPNG = async () => {
    try {
      await exportChartAsPNG(chartRef, "line-chart.png");
    } catch (error) {
      console.error("Failed to export chart:", error);
    }
  };

  const handleExportPDF = async () => {
    try {
      await exportChartAsPDF(chartRef, "line-chart.pdf");
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
        <RechartsLineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#334155" />}

          <XAxis
            dataKey={xAxisKey}
            stroke="#94a3b8"
            tick={{ fill: "#94a3b8" }}
            tickLine={{ stroke: "#334155" }}
          />

          <YAxis
            stroke="#94a3b8"
            tick={{ fill: "#94a3b8" }}
            tickLine={{ stroke: "#334155" }}
          />

          {showTooltip && <Tooltip content={<CustomTooltip />} />}

          {showLegend && <Legend wrapperStyle={{ color: "#cbd5e1" }} />}

          {lines.map((line) => (
            <Line
              key={line.dataKey}
              type={curveType}
              dataKey={line.dataKey}
              name={line.name}
              stroke={line.color}
              strokeWidth={line.strokeWidth || 2}
              dot={line.dot !== false ? { fill: line.color, strokeWidth: 2, r: 4 } : false}
              activeDot={{ r: 6, fill: line.color, strokeWidth: 0 }}
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
}
