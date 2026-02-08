"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Card, CardContent, Badge } from "@/components/atoms";
import { MemoryDetailSkeleton } from "@/components/organisms";
import {
  ArrowLeft,
  Edit,
  Trash2,
  Copy,
  Download,
  Clock,
  User,
  FileText,
  Calendar,
  Hash,
  CheckCircle
} from "lucide-react";
import { format } from "date-fns";
import { exportSingleMemoryAsMarkdown } from "@/lib/utils/export";
import { useToast } from "@/hooks/use-toast";

export default function MemoryDetailPage() {
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const memoryId = params.id as string;

  const [copiedId, setCopiedId] = useState(false);

  // Fetch memory detail
  const {
    data: memory,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["memory", memoryId],
    queryFn: async () => {
      const response = await fetch(`/api/memories/${memoryId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch memory");
      }
      return response.json();
    },
    enabled: !!memoryId,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`/api/memories/${memoryId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Failed to delete memory");
      }
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Memory deleted",
        description: "The memory has been deleted successfully.",
        variant: "default",
      });
      router.push("/memories");
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Copy memory ID to clipboard
  const handleCopyId = async () => {
    try {
      await navigator.clipboard.writeText(memoryId);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  // Handle delete
  const handleDelete = () => {
    if (confirm("Are you sure you want to delete this memory? This action cannot be undone.")) {
      deleteMutation.mutate();
    }
  };

  // Handle export
  const handleExport = () => {
    if (memory) {
      exportSingleMemoryAsMarkdown(memory);
    }
  };

  // Get badge color based on memory type
  const getTypeColor = (type?: string) => {
    const colors: Record<string, string> = {
      bugfix: "bg-red-500/10 text-red-500 border-red-500/20",
      feature: "bg-blue-500/10 text-blue-500 border-blue-500/20",
      decision: "bg-purple-500/10 text-purple-500 border-purple-500/20",
      refactor: "bg-orange-500/10 text-orange-500 border-orange-500/20",
      discovery: "bg-green-500/10 text-green-500 border-green-500/20",
      general: "bg-gray-500/10 text-gray-500 border-gray-500/20",
    };
    return type && colors[type] ? colors[type] : colors.general;
  };

  // Get concept color
  const getConceptColor = (concept?: string) => {
    const colors: Record<string, string> = {
      "how-it-works": "bg-cyan-500/10 text-cyan-500 border-cyan-500/20",
      gotcha: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
      "trade-off": "bg-pink-500/10 text-pink-500 border-pink-500/20",
      pattern: "bg-indigo-500/10 text-indigo-500 border-indigo-500/20",
      general: "bg-gray-500/10 text-gray-500 border-gray-500/20",
    };
    return concept && colors[concept] ? colors[concept] : colors.general;
  };

  if (isLoading) {
    return <MemoryDetailSkeleton />;
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
          <p className="text-destructive mb-4">Error loading memory: {error.message}</p>
          <Button variant="outline" onClick={() => router.push("/memories")}>
            Go to Memories List
          </Button>
        </div>
      </div>
    );
  }

  if (!memory) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => router.back()} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <div className="text-center py-12">
          <p className="text-muted-foreground">Memory not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button
          onClick={() => router.push("/memories")}
          className="hover:text-foreground transition-colors"
        >
          Memories
        </button>
        <span>/</span>
        <span className="text-foreground font-medium">Memory Detail</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Memory Detail</h1>
          <p className="text-muted-foreground">View and manage memory details</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button variant="outline" size="sm" onClick={() => router.push(`/memories/${memoryId}/edit`)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Memory ID */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Hash className="h-4 w-4 text-muted-foreground" />
              <code className="text-sm">{memoryId}</code>
            </div>
            <Button variant="ghost" size="sm" onClick={handleCopyId}>
              {copiedId ? (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-2" />
                  Copy
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Metadata Badges */}
      <div className="flex flex-wrap items-center gap-4">
        {memory.memory_type && (
          <Badge variant="outline" className={getTypeColor(memory.memory_type)}>
            {memory.memory_type}
          </Badge>
        )}
        {memory.memory_concept && (
          <Badge variant="outline" className={getConceptColor(memory.memory_concept)}>
            {memory.memory_concept}
          </Badge>
        )}
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <User className="h-4 w-4" />
          <span>Agent: {memory.data_type || "default"}</span>
        </div>
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Calendar className="h-4 w-4" />
          <span>{format(new Date(memory.created_at), "MMM d, yyyy 'at' h:mm a")}</span>
        </div>
        {memory.updated_at && memory.updated_at !== memory.created_at && (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Updated: {format(new Date(memory.updated_at), "MMM d, yyyy 'at' h:mm a")}</span>
          </div>
        )}
        {memory.estimated_tokens && (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <FileText className="h-4 w-4" />
            <span>{memory.estimated_tokens.toLocaleString()} tokens</span>
          </div>
        )}
      </div>

      {/* Content */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold mb-4">Content</h2>
          <div className="prose dark:prose-invert max-w-none">
            <p className="whitespace-pre-wrap leading-relaxed">{memory.content}</p>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      {memory.summary && (
        <Card>
          <CardContent className="p-6">
            <h2 className="text-lg font-semibold mb-4">Summary</h2>
            <p className="text-muted-foreground">{memory.summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      {memory.metadata && Object.keys(memory.metadata).length > 0 && (
        <Card>
          <CardContent className="p-6">
            <h2 className="text-lg font-semibold mb-4">Metadata</h2>
            <dl className="space-y-3">
              {Object.entries(memory.metadata).map(([key, value]) => (
                <div key={key} className="grid grid-cols-3 gap-4">
                  <dt className="text-sm font-medium text-muted-foreground">{key}</dt>
                  <dd className="col-span-2 text-sm font-mono bg-muted px-2 py-1 rounded">
                    {String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      )}

      {/* Structured Data */}
      {(memory.before_state || memory.after_state || memory.files || memory.facts) && (
        <Card>
          <CardContent className="p-6 space-y-6">
            <h2 className="text-lg font-semibold">Structured Data</h2>

            {memory.before_state && (
              <div>
                <h3 className="text-sm font-medium mb-2">Before State</h3>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {memory.before_state}
                </p>
              </div>
            }

            {memory.after_state && (
              <div>
                <h3 className="text-sm font-medium mb-2">After State</h3>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {memory.after_state}
                </p>
              </div>
            )}

            {memory.files && memory.files.length > 0 && (
              <div>
                <h3 className="text-sm font-medium mb-2">Related Files</h3>
                <ul className="space-y-1">
                  {memory.files.map((file: string, idx: number) => (
                    <li key={idx} className="text-sm font-mono text-muted-foreground">
                      - {file}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {memory.facts && memory.facts.length > 0 && (
              <div>
                <h3 className="text-sm font-medium mb-2">Key Facts</h3>
                <ul className="space-y-2">
                  {memory.facts.map((fact: string, idx: number) => (
                    <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="text-primary">•</span>
                      <span>{fact}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Related Memories */}
      {memory.related_memories && memory.related_memories.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">
                Related Memories ({memory.related_memories.length})
              </h2>
            </div>
            <div className="space-y-3">
              {memory.related_memories.map((related: any) => (
                <div
                  key={related.id}
                  className="flex items-start justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors cursor-pointer"
                  onClick={() => router.push(`/memories/${related.id}`)}
                >
                  <div className="flex-1">
                    <p className="text-sm mb-1">
                      {related.summary || related.content.slice(0, 100)}...
                    </p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      {related.memory_type && (
                        <Badge variant="outline" className="text-xs">
                          {related.memory_type}
                        </Badge>
                      )}
                      <span>{format(new Date(related.created_at), "MMM d, yyyy")}</span>
                    </div>
                  </div>
                  {related.similarity && (
                    <div className="text-sm font-medium text-primary">
                      {(related.similarity * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
