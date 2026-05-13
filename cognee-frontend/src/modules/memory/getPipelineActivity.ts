/**
 * getPipelineActivity - v1.0.9 /v1/activity/pipeline-runs endpoint client
 *
 * Returns a list of recent pipeline run records (cognify, improve, memify runs).
 * Useful for a status / history panel in the dashboard.
 *
 * New in v1.0.9 upstream; not present in the v0.5.1 baseline.
 */
import { fetch } from "@/utils";

export interface PipelineRun {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  pipeline: string;
  dataset?: string;
  startedAt?: string;
  finishedAt?: string;
  errorMessage?: string;
}

export interface PipelineActivityResult {
  runs: PipelineRun[];
  total: number;
}

export default async function getPipelineActivity(
  useCloud: boolean = false,
): Promise<PipelineActivityResult> {
  return fetch("/v1/activity/pipeline-runs", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  }, useCloud)
    .then((response) => response.json())
    .then((data) => {
      // Normalise upstream response shape
      if (Array.isArray(data)) {
        return { runs: data as PipelineRun[], total: data.length };
      }
      return data as PipelineActivityResult;
    });
}
