/**
 * forgetData - v1.0.9 /v1/forget endpoint client
 *
 * Deletes data from the cognee knowledge graph.
 * Corresponds to the `forget_memory` MCP tool in the Enhanced stack.
 */
import { fetch } from "@/utils";

export interface ForgetOptions {
  /** Dataset name to delete (optional - deletes everything if omitted) */
  dataset?: string;
  /** Specific data item ID to delete */
  dataId?: string;
  /** If true, deletes all data in all datasets */
  everything?: boolean;
}

export interface ForgetResult {
  status: string;
  message?: string;
}

export default async function forgetData(
  options: ForgetOptions = {},
  useCloud: boolean = false,
): Promise<ForgetResult> {
  return fetch("/v1/forget", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      dataset: options.dataset ?? null,
      dataId: options.dataId ?? null,
      everything: options.everything ?? false,
    }),
  }, useCloud).then((response) => response.json());
}
