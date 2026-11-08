import { apiClient } from "./client";
import type {
  Memory,
  MemoryResponse,
  MemoryFilters,
} from "./types";

export async function getMemories(filters?: MemoryFilters): Promise<Memory[]> {
  const response = await apiClient.get<MemoryResponse[]>("/api/memories", {
    params: filters,
  });
  return response.data.map((m) => ({ ...m, id: m.memory_id }));
}

export async function getMemory(id: string): Promise<Memory> {
  const response = await apiClient.get<MemoryResponse>(`/api/memories/${id}`);
  return { ...response.data, id: response.data.memory_id };
}

export async function createMemory(data: {
  content: string;
  idempotency_key: string;
  agent_id?: string;
  memory_type?: string;
  memory_concept?: string;
}): Promise<Memory> {
  const response = await apiClient.post<MemoryResponse>("/api/memories", data);
  return { ...response.data, id: response.data.memory_id };
}

export async function searchMemories(filters: {
  query: string;
  agent_id?: string;
  limit?: number;
}): Promise<{
  query: string;
  result_count: number;
  results: Memory[];
}> {
  const response = await apiClient.get("/api/search", { params: filters });
  return {
    query: response.data.query,
    result_count: response.data.result_count,
    results: response.data.results.map((m: MemoryResponse) => ({ ...m, id: m.memory_id })),
  };
}

export async function updateMemory(
  id: string,
  data: {
    expected_version: number;
    content?: string;
    memory_type?: string;
    memory_concept?: string;
  }
): Promise<Memory> {
  const response = await apiClient.patch<MemoryResponse>(`/api/memories/${id}`, data);
  return { ...response.data, id: response.data.memory_id };
}

export async function deleteMemory(id: string, expectedVersion: number): Promise<void> {
  // Historical function name retained; this only retracts and keeps history.
  await apiClient.post(`/api/memories/${encodeURIComponent(id)}/retract`, null, {
    params: { expected_version: expectedVersion },
  });
}
