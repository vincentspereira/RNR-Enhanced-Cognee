"use client";

import React, { useState, useEffect, useRef } from "react";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import { useGraphData, useGraphStats } from "@/lib/hooks/useGraphData";
import { Search, ZoomIn, ZoomOut, Maximize, Download, Settings } from "lucide-react";
import { Input } from "@/components/ui/elements/Input";
import { Select } from "@/components/ui/elements/Select";
import { NeutralButton } from "@/components/ui/elements/NeutralButton";
import { IconButton } from "@/components/ui/elements/IconButton";
import { exportChartAsPNG } from "@/lib/utils/chart-export";

type LayoutType = "force" | "hierarchical" | "circle" | "concentric";

const LAYOUT_OPTIONS: Record<
  LayoutType,
  { name: string; displayName: string }
> = {
  force: { name: "force", displayName: "Force Directed" },
  hierarchical: { name: "breadthfirst", displayName: "Hierarchical" },
  circle: { name: "circle", displayName: "Circle" },
  concentric: { name: "concentric", displayName: "Concentric" },
};

export interface KnowledgeGraphProps {
  className?: string;
  onNodeClick?: (nodeId: string) => void;
}

/**
 * Knowledge Graph Component
 *
 * Cytoscape.js-based graph visualization with multiple layouts, zoom, pan, and filtering.
 */
export function KnowledgeGraph({
  className = "",
  onNodeClick,
}: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [layout, setLayout] = useState<LayoutType>("force");
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // Fetch graph data
  const { data: graphData, isLoading, error } = useGraphData(
    { limit: 200 },
    true
  );

  const { data: stats } = useGraphStats(true);

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Convert API data to Cytoscape elements
    const elements: ElementDefinition[] = [
      ...graphData.nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          type: node.type,
          importance: node.importance || 1,
        },
      })),
      ...graphData.edges.map((edge) => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.label,
          type: edge.type,
          strength: edge.strength || 1,
        },
      })),
    ];

    // Initialize Cytoscape
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#3b82f6",
            "border-color": "#60a5fa",
            "border-width": 2,
            color: "#ffffff",
            "font-size": "12px",
            "text-valign": "center",
            "text-halign": "center",
            label: "data(label)",
            "text-wrap": "wrap",
            "text-max-width": "80px",
            width: (ele: any) => 20 + (ele.data("importance") || 1) * 10,
            height: (ele: any) => 20 + (ele.data("importance") || 1) * 10,
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#f59e0b",
            "border-width": 4,
          },
        },
        {
          selector: "edge",
          style: {
            width: (ele: any) => 1 + (ele.data("strength") || 1) * 2,
            "line-color": "#64748b",
            "target-arrow-color": "#64748b",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 1,
          },
        },
        {
          selector: "edge:selected",
          style: {
            "line-color": "#f59e0b",
            "target-arrow-color": "#f59e0b",
          },
        },
      ],
      layout: {
        name: LAYOUT_OPTIONS[layout].name,
        animate: true,
        animationDuration: 500,
        fit: true,
        padding: 50,
      },
      minZoom: 0.1,
      maxZoom: 5,
    });

    // Event handlers
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      const nodeId = node.id();
      setSelectedNode(nodeId);
      onNodeClick?.(nodeId);
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData, layout]);

  // Apply filters
  useEffect(() => {
    if (!cyRef.current) return;

    const cy = cyRef.current;

    if (nodeTypeFilter === "all") {
      cy.nodes().show();
      cy.edges().show();
    } else {
      cy.nodes().filter((node) => node.data("type") === nodeTypeFilter).show();
      cy.nodes().filter((node) => node.data("type") !== nodeTypeFilter).hide();
      cy.edges().show();
    }

    // Apply search
    if (searchQuery) {
      const matchingNodes = cy
        .nodes()
        .filter((node) =>
          node.data("label").toLowerCase().includes(searchQuery.toLowerCase())
        );
      cy.nodes().difference(matchingNodes).hide();
      matchingNodes.show();
    }
  }, [nodeTypeFilter, searchQuery]);

  const handleZoomIn = () => {
    cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  };

  const handleZoomOut = () => {
    cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  };

  const handleFit = () => {
    cyRef.current?.fit(undefined, 50);
  };

  const handleExport = async () => {
    if (containerRef.current) {
      try {
        const png = cyRef.current?.png({ full: true, scale: 2 });
        if (png) {
          const link = document.createElement("a");
          link.href = png;
          link.download = "knowledge-graph.png";
          link.click();
        }
      } catch (error) {
        console.error("Failed to export graph:", error);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-500">Error loading graph: {(error as Error).message}</div>
      </div>
    );
  }

  const nodeTypes = stats?.nodeTypeDistribution || {};

  return (
    <div className={`bg-slate-900 rounded-lg p-6 ${className}`}>
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-200">Knowledge Graph</h3>
          <span className="text-sm text-slate-400">
            ({graphData?.nodes.length || 0} nodes, {graphData?.edges.length || 0} edges)
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search nodes..."
              className="pl-10 w-64"
            />
          </div>

          {/* Node Type Filter */}
          <Select
            value={nodeTypeFilter}
            onChange={(e) => setNodeTypeFilter(e.target.value)}
            className="w-40"
          >
            <option value="all">All Types</option>
            {Object.keys(nodeTypes).map((type) => (
              <option key={type} value={type}>
                {type} ({nodeTypes[type]})
              </option>
            ))}
          </Select>

          {/* Layout Selector */}
          <Select
            value={layout}
            onChange={(e) => setLayout(e.target.value as LayoutType)}
            className="w-40"
          >
            {Object.entries(LAYOUT_OPTIONS).map(([key, { displayName }]) => (
              <option key={key} value={key}>
                {displayName}
              </option>
            ))}
          </Select>

          {/* Zoom Controls */}
          <div className="flex items-center gap-1 border border-slate-700 rounded-lg p-1">
            <IconButton onClick={handleZoomIn} size="sm" icon={<ZoomIn className="w-4 h-4" />} />
            <IconButton onClick={handleZoomOut} size="sm" icon={<ZoomOut className="w-4 h-4" />} />
            <IconButton onClick={handleFit} size="sm" icon={<Maximize className="w-4 h-4" />} />
          </div>

          {/* Export */}
          <NeutralButton onClick={handleExport} size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export
          </NeutralButton>
        </div>
      </div>

      {/* Graph Container */}
      <div
        ref={containerRef}
        className="w-full bg-slate-800 rounded-lg border border-slate-700"
        style={{ height: "600px" }}
      />

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-300">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-blue-500"></div>
          <span>Node</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-slate-500"></div>
          <span>Relationship</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2 border-amber-500 bg-blue-500"></div>
          <span>Selected</span>
        </div>
      </div>
    </div>
  );
}
