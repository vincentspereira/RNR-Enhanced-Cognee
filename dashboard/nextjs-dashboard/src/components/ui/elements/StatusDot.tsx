"use client";

import React from "react";
import { cn } from "@/lib/utils";

export type StatusType = "healthy" | "warning" | "error" | "neutral" | "ok" | "connected" | "disconnected" | string;

export interface StatusDotProps {
  status: StatusType;
  size?: "xs" | "sm" | "md" | "lg";
  className?: string;
}

export function StatusDot({ status, size = "md", className }: StatusDotProps) {
  const sizeClasses: Record<string, string> = {
    xs: "h-1.5 w-1.5",
    sm: "h-2 w-2",
    md: "h-2.5 w-2.5",
    lg: "h-3 w-3",
  };

  const colorClasses = (): string => {
    const s = status?.toString().toLowerCase();
    if (s === "healthy" || s === "ok" || s === "connected") return "bg-green-500";
    if (s === "warning" || s === "degraded") return "bg-yellow-500";
    if (s === "error" || s === "disconnected" || s === "unhealthy") return "bg-red-500";
    return "bg-gray-400";
  };

  return (
    <span
      className={cn("inline-block rounded-full", sizeClasses[size] ?? sizeClasses.md, colorClasses(), className)}
      aria-hidden="true"
    />
  );
}
