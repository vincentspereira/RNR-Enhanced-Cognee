"use client";

import React, { useRef } from "react";
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  type TooltipProps,
} from "recharts";
import { exportChartAsPNG, exportChartAsPDF } from "@/lib/utils/chart-export";
import { Download } from "lucide-react";
import { NeutralButton } from "@/components/ui/elements/NeutralButton";

export interface PieChartProps {
  data: Array<{
    name: string;
    value: number;
    color?: string;
  }>;
  height?: number;
  donut?: boolean;
  showLabels?: boolean;
  showLegend?: boolean;
  showTooltip?: boolean;
  innerRadius?: number;
  outerRadius?: number;
  className?: string;
  colors?: string[];
}

const DEFAULT_COLORS = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#84cc16", // lime
];

/**
 * Custom Tooltip component
 */
const CustomTooltip = ({ active, payload }: TooltipProps<string, string>) => {
  if (active && payload && payload.length) {
    const data = payload[0];
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 shadow-lg">
        <p className="text-slate-200 text-sm font-medium">{data.name}</p>
        <p className="text-sm" style={{ color: data.payload.color }}>
          {data.value} ({data.payload.percent.toFixed(1)}%)
        </p>
      </div>
    );
  }
  return null;
};

/**
 * Custom Label component
 */
const CustomLabel = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
}: {
  cx: number;
  cy: number;
  midAngle: number;
  innerRadius: number;
  outerRadius: number;
  percent: number;
}) => {
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor={x > cx ? "start" : "end"}
      dominantBaseline="central"
      fontSize="12"
      fontWeight="500"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

/**
 * Pie/Donut Chart Component
 *
 * A reusable pie chart component with donut mode option.
 */
export function PieChart({
  data,
  height = 400,
  donut = true,
  showLabels = false,
  showLegend = true,
  showTooltip = true,
  innerRadius = 60,
  outerRadius = 100,
  className = "",
  colors = DEFAULT_COLORS,
}: PieChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  const handleExportPNG = async () => {
    try {
      await exportChartAsPNG(chartRef, "pie-chart.png");
    } catch (error) {
      console.error("Failed to export chart:", error);
    }
  };

  const handleExportPDF = async () => {
    try {
      await exportChartAsPDF(chartRef, "pie-chart.pdf");
    } catch (error) {
      console.error("Failed to export chart:", error);
    }
  };

  // Assign colors to data
  const dataWithColors = data.map((item, index) => ({
    ...item,
    color: item.color || colors[index % colors.length],
  }));

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
        <RechartsPieChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <Pie
            data={dataWithColors}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={showLabels ? CustomLabel : false}
            innerRadius={donut ? innerRadius : 0}
            outerRadius={outerRadius}
            paddingAngle={2}
            dataKey="value"
          >
            {dataWithColors.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>

          {showTooltip && <Tooltip content={<CustomTooltip />} />}

          {showLegend && (
            <Legend
              wrapperStyle={{ color: "#cbd5e1" }}
              iconType="circle"
              verticalAlign="bottom"
              height={36}
            />
          )}
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  );
}
