/**
 * Export utilities for memories
 */

import { format } from "date-fns";

export interface Memory {
  id: string;
  content: string;
  summary?: string;
  memory_type?: string;
  memory_concept?: string;
  data_type?: string;
  created_at: string;
  updated_at?: string;
  char_count?: number;
  estimated_tokens?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Export memories as JSON file
 */
export function exportToJSON(memories: Memory[], filename?: string): void {
  const data = {
    exported_at: new Date().toISOString(),
    total_count: memories.length,
    memories: memories,
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  downloadBlob(blob, filename || `memories-${Date.now()}.json`);
}

/**
 * Export memories as CSV file
 */
export function exportToCSV(memories: Memory[], filename?: string): void {
  if (memories.length === 0) {
    throw new Error("No memories to export");
  }

  // CSV headers
  const headers = [
    "ID",
    "Content",
    "Summary",
    "Type",
    "Concept",
    "Agent",
    "Created At",
    "Updated At",
    "Character Count",
    "Estimated Tokens",
  ];

  // Convert memories to CSV rows
  const rows = memories.map((memory) => [
    escapeCSV(memory.id),
    escapeCSV(memory.content),
    escapeCSV(memory.summary || ""),
    escapeCSV(memory.memory_type || ""),
    escapeCSV(memory.memory_concept || ""),
    escapeCSV(memory.data_type || ""),
    escapeCSV(format(new Date(memory.created_at), "yyyy-MM-dd HH:mm:ss")),
    escapeCSV(
      memory.updated_at
        ? format(new Date(memory.updated_at), "yyyy-MM-dd HH:mm:ss")
        : ""
    ),
    memory.char_count?.toString() || "",
    memory.estimated_tokens?.toString() || "",
  ]);

  // Combine headers and rows
  const csvContent = [headers.join(","), ...rows.map((row) => row.join(","))].join(
    "\n"
  );

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  downloadBlob(blob, filename || `memories-${Date.now()}.csv`);
}

/**
 * Export memories as Markdown file
 */
export function exportToMarkdown(memories: Memory[], filename?: string): void {
  const markdown = memories
    .map((memory) => {
      const date = format(new Date(memory.created_at), "yyyy-MM-dd HH:mm:ss");
      const badges = [
        memory.memory_type && `[${memory.memory_type}]`,
        memory.memory_concept && `(${memory.memory_concept})`,
      ]
        .filter(Boolean)
        .join(" ");

      return `## ${memory.id}

${badges ? `${badges}\n\n` : ""}**Date:** ${date}  |  **Agent:** ${
        memory.data_type || "default"
      }  |  **Tokens:** ${memory.estimated_tokens || "N/A"}

${memory.content}

---
`;
    })
    .join("\n");

  const header = `# Exported Memories

**Exported At:** ${format(new Date(), "yyyy-MM-dd HH:mm:ss")}  |  **Total Count:** ${memories.length}

---

${markdown}
`;

  const blob = new Blob([header], { type: "text/markdown;charset=utf-8;" });
  downloadBlob(blob, filename || `memories-${Date.now()}.md`);
}

/**
 * Export a single memory as Markdown
 */
export function exportSingleMemoryAsMarkdown(
  memory: Memory,
  filename?: string
): void {
  const date = format(new Date(memory.created_at), "yyyy-MM-dd HH:mm:ss");
  const badges = [
    memory.memory_type && `[${memory.memory_type}]`,
    memory.memory_concept && `(${memory.memory_concept})`,
  ]
    .filter(Boolean)
    .join(" ");

  const markdown = `# Memory: ${memory.id}

${badges ? `${badges}\n\n` : ""}**Date:** ${date}  |  **Agent:** ${
    memory.data_type || "default"
  }  |  **Tokens:** ${memory.estimated_tokens || "N/A"}

${
  memory.updated_at
    ? `**Updated:** ${format(new Date(memory.updated_at), "yyyy-MM-dd HH:mm:ss")}\n\n`
    : ""
}
## Content

${memory.content}

---
`;

  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8;" });
  downloadBlob(blob, filename || `memory-${memory.id}.md`);
}

/**
 * Helper function to download a blob as a file
 */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Helper function to escape CSV values
 */
function escapeCSV(value: string): string {
  // If value contains comma, quote, or newline, wrap in quotes and escape quotes
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/**
 * Get export file size estimate
 */
export function estimateExportSize(
  memories: Memory[],
  format: "json" | "csv" | "markdown"
): string {
  const avgCharCount =
    memories.reduce((sum, m) => sum + (m.char_count || m.content.length), 0) /
    memories.length;

  const multipliers = {
    json: 2, // JSON adds formatting overhead
    csv: 1.1, // CSV adds commas and quotes
    markdown: 1.5, // Markdown adds formatting
  };

  const estimatedBytes = memories.length * avgCharCount * multipliers[format];
  return formatBytes(estimatedBytes);
}

/**
 * Format bytes to human-readable string
 */
function formatBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
}
