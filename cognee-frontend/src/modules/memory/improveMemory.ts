/**
 * improveMemory - v1.0.9 /v1/improve endpoint client
 *
 * Triggers the 4-stage feedback improvement pipeline:
 * 1. Apply feedback weights
 * 2. Persist sessions
 * 3. Re-embed triplets
 * 4. Sync to cache
 *
 * Corresponds to the `improve` MCP tool in the Enhanced stack.
 */
import { fetch } from "@/utils";

export interface ImproveOptions {
  /** Dataset name to improve (default: all datasets) */
  dataset?: string;
  /** Session IDs to include in the improvement run */
  sessionIds?: string[];
  /** Run improvement in the background (non-blocking) */
  runInBackground?: boolean;
}

export interface ImproveResult {
  status: string;
  message?: string;
  pipelineRunId?: string;
}

export default async function improveMemory(
  options: ImproveOptions = {},
  useCloud: boolean = false,
): Promise<ImproveResult> {
  return fetch("/v1/improve", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      dataset: options.dataset ?? null,
      sessionIds: options.sessionIds ?? null,
      runInBackground: options.runInBackground ?? false,
    }),
  }, useCloud).then((response) => response.json());
}
