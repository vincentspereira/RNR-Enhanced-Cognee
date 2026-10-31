import { apiClient } from "./client";
import type {
  Session,
  SessionResponse,
  SessionFilters,
  TimelineResponse,
} from "./types";

export async function getSessions(filters?: SessionFilters): Promise<Session[]> {
  const response = await apiClient.get<SessionResponse[]>("/api/sessions", {
    params: filters,
  });
  return response.data.map((s) => ({ ...s, id: s.session_id }));
}

export async function getSession(id: string): Promise<Session> {
  const response = await apiClient.get<SessionResponse>(`/api/sessions/${id}`);
  return { ...response.data, id: response.data.session_id };
}

export async function getTimeline(
  memoryId: string,
  filters?: { before?: number; after?: number }
): Promise<TimelineResponse> {
  const response = await apiClient.get<TimelineResponse>(
    `/api/timeline/${memoryId}`,
    { params: filters }
  );
  return response.data;
}
