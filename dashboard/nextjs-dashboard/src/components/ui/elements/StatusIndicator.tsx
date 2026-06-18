"use client";

import React from "react";
import { cn } from "@/lib/utils";

export type StatusType = "ok" | "warning" | "error" | "unknown";

export interface StatusIndicatorProps {
  status: StatusType | string;
  label?: string;
  className?: string;
}

export function StatusIndicator({ status, label, className }: StatusIndicatorProps) {
  const normalizedStatus = ((): StatusType => {
    const s = status?.toString().toLowerCase();
    if (s === "ok" || s === "connected" || s === "healthy") return "ok";
    if (s === "warning" || s === "degraded") return "warning";
    if (s === "error" || s === "disconnected" || s === "unhealthy") return "error";
    return "unknown";
  })();

  const colorClasses: Record<StatusType, string> = {
    ok: "bg-green-500",
    warning: "bg-yellow-500",
    error: "bg-red-500",
    unknown: "bg-gray-400",
  };

  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span
        className={cn("h-2 w-2 rounded-full", colorClasses[normalizedStatus])}
        aria-hidden="true"
      />
      {label && <span className="text-sm">{label}</span>}
    </span>
  );
}

export function StatusDot({ status, className }: { status: StatusType | string; className?: string }) {
  return <StatusIndicator status={status} className={className} />;
}
