"use client";

import React from "react";
import { X } from "lucide-react";
import { IconButton } from "@/components/ui/elements/IconButton";
import { useNodeDetails } from "@/lib/hooks/useGraphData";
import type { GraphNode } from "@/lib/api/neo4j";

export interface GraphNodeDetailsProps {
  nodeId: string | null;
  onClose: () => void;
  className?: string;
}

/**
 * Graph Node Details Panel
 *
 * Shows detailed information about a selected graph node.
 */
export function GraphNodeDetails({
  nodeId,
  onClose,
  className = "",
}: GraphNodeDetailsProps) {
  const { data: nodeData, isLoading, error } = useNodeDetails(nodeId || "", !!nodeId);

  if (!nodeId) {
    return (
      <div className={`bg-slate-800 rounded-lg p-6 ${className}`}>
        <div className="text-center text-slate-400">
          <p>Select a node to view details</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={`bg-slate-800 rounded-lg p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-slate-700 rounded w-3/4 mb-4"></div>
          <div className="h-4 bg-slate-700 rounded w-1/2 mb-4"></div>
          <div className="h-20 bg-slate-700 rounded mb-4"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-slate-800 rounded-lg p-6 ${className}`}>
        <div className="text-red-500">
          Error loading node details: {(error as Error).message}
        </div>
      </div>
    );
  }

  const { node, connections, relatedNodes } = nodeData!;

  return (
    <div className={`bg-slate-800 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-slate-200 mb-1">{node.label}</h3>
          <p className="text-sm text-slate-400 capitalize">Type: {node.type}</p>
        </div>
        <IconButton onClick={onClose} size="sm" icon={<X className="w-4 h-4" />} />
      </div>

      {/* Properties */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-slate-300 mb-3">Properties</h4>
        <div className="space-y-2">
          {Object.entries(node.properties).map(([key, value]) => (
            <div key={key} className="flex items-baseline gap-2">
              <span className="text-sm text-slate-400 w-32">{key}:</span>
              <span className="text-sm text-slate-200">
                {typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}
              </span>
            </div>
          ))}
          {node.importance && (
            <div className="flex items-baseline gap-2">
              <span className="text-sm text-slate-400 w-32">Importance:</span>
              <span className="text-sm text-slate-200">{node.importance.toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Connections */}
      {connections.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-slate-300 mb-3">
            Connections ({connections.length})
          </h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {connections.map((connection) => (
              <div
                key={connection.id}
                className="p-2 bg-slate-700 rounded border border-slate-600"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-300">{connection.label}</span>
                  <span className="text-xs text-slate-400 capitalize">
                    {connection.type}
                  </span>
                </div>
                {connection.strength && (
                  <div className="mt-1">
                    <div className="h-1 bg-slate-600 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500"
                        style={{ width: `${connection.strength * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related Nodes */}
      {relatedNodes.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-slate-300 mb-3">
            Related Nodes ({relatedNodes.length})
          </h4>
          <div className="flex flex-wrap gap-2">
            {relatedNodes.map((relatedNode) => (
              <div
                key={relatedNode.id}
                className="px-3 py-1.5 bg-slate-700 rounded-full border border-slate-600"
              >
                <span className="text-sm text-slate-300">{relatedNode.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
