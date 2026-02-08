"use client";

import React, { useState } from "react";
import { KnowledgeGraph } from "@/components/organisms/KnowledgeGraph";
import { GraphNodeDetails } from "@/components/organisms/GraphNodeDetails";

export default function GraphPage() {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100 mb-2">Knowledge Graph</h1>
        <p className="text-slate-400">
          Visualize relationships between memories and concepts
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Graph */}
        <div className="lg:col-span-2">
          <KnowledgeGraph onNodeClick={setSelectedNodeId} />
        </div>

        {/* Node Details */}
        <div>
          <GraphNodeDetails
            nodeId={selectedNodeId}
            onClose={() => setSelectedNodeId(null)}
          />
        </div>
      </div>
    </div>
  );
}
