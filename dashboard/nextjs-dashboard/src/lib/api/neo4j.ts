/**
 * Neo4j Graph API
 *
 * API client for fetching graph data from Neo4j.
 */

import { apiClient } from "./client";

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
  importance?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
  strength?: number;
  properties?: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: {
    totalNodes: number;
    totalEdges: number;
    nodeTypes: Record<string, number>;
    edgeTypes: Record<string, number>;
  };
}

export interface GraphQueryParams {
  limit?: number;
  nodeType?: string;
  edgeType?: string;
  relationshipStrength?: number;
  nodeId?: string;
  depth?: number;
}

/**
 * Fetch graph data from Neo4j
 */
export async function getGraphData(
  params?: GraphQueryParams
): Promise<GraphData> {
  const response = await apiClient.get<GraphData>("/api/graph", {
    params: {
      limit: params?.limit || 100,
      node_type: params?.nodeType,
      edge_type: params?.edgeType,
      relationship_strength: params?.relationshipStrength,
      node_id: params?.nodeId,
      depth: params?.depth || 2,
    },
  });
  return response.data;
}

/**
 * Fetch neighbors for a specific node
 */
export async function getNodeNeighbors(
  nodeId: string,
  depth: number = 1
): Promise<GraphData> {
  const response = await apiClient.get<GraphData>(`/api/graph/node/${nodeId}`, {
    params: { depth },
  });
  return response.data;
}

/**
 * Search for nodes by label
 */
export async function searchNodes(query: string, limit: number = 20): Promise<GraphNode[]> {
  const response = await apiClient.get<GraphNode[]>("/api/graph/search", {
    params: { query, limit },
  });
  return response.data;
}

/**
 * Get node details with connections
 */
export async function getNodeDetails(nodeId: string): Promise<{
  node: GraphNode;
  connections: GraphEdge[];
  relatedNodes: GraphNode[];
}> {
  const response = await apiClient.get(`/api/graph/node/${nodeId}/details`);
  return response.data;
}

/**
 * Get graph statistics
 */
export async function getGraphStats(): Promise<{
  totalNodes: number;
  totalEdges: number;
  nodeTypeDistribution: Record<string, number>;
  edgeTypeDistribution: Record<string, number>;
  avgDegree: number;
  connectedComponents: number;
}> {
  const response = await apiClient.get("/api/graph/stats");
  return response.data;
}
