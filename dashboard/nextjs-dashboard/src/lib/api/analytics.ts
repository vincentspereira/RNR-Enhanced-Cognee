import { apiClient } from "./client";
import type {
  SystemStatsResponse,
  StructuredStatsResponse,
} from "./types";

export async function getSystemStats(): Promise<SystemStatsResponse> {
  const response = await apiClient.get<SystemStatsResponse>("/api/stats");
  return response.data;
}

export async function getStructuredStats(): Promise<StructuredStatsResponse> {
  const response = await apiClient.get<StructuredStatsResponse>(
    "/api/structured-stats"
  );
  return response.data;
}

export async function checkHealth(): Promise<{
  status: string;
  timestamp: string;
  version: string;
}> {
  const response = await apiClient.get("/health");
  return response.data;
}
