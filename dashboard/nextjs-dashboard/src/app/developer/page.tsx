"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/atoms";
import { Button } from "@/components/atoms";
import { Input } from "@/components/atoms";
import { useSSE } from "@/lib/hooks/useSSE";
import {
  ExternalLink,
  Play,
  RefreshCw,
  Radio,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const EXAMPLE_ENDPOINTS = [
  "/health",
  "/api/stats",
  "/api/memories?limit=5",
  "/api/agents",
  "/api/sessions?limit=5",
  "/api/graph/stats",
  "/api/structured-stats",
];

export default function DeveloperPage() {
  const { status: sseStatus, reconnect } = useSSE();

  const [endpoint, setEndpoint] = useState("/health");
  const [response, setResponse] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);

  const handleFetch = async () => {
    const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const url = `${API_URL}${path}`;
    setIsLoading(true);
    setRequestError(null);
    setResponse(null);
    try {
      const res = await fetch(url);
      const text = await res.text();
      try {
        const json = JSON.parse(text);
        setResponse(JSON.stringify(json, null, 2));
      } catch {
        setResponse(text);
      }
      if (!res.ok) {
        setRequestError(`HTTP ${res.status} ${res.statusText}`);
      }
    } catch (err) {
      setRequestError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setIsLoading(false);
    }
  };

  const sseStatusColor =
    sseStatus === "connected"
      ? "text-green-500"
      : sseStatus === "connecting"
      ? "text-yellow-500"
      : "text-red-500";

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Developer Tools</h1>
        <p className="text-muted-foreground">
          Explore the API and monitor real-time events
        </p>
      </div>

      {/* API Docs */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold mb-1">API Documentation</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Interactive Swagger UI for the Enhanced Cognee API.
          </p>
          <div className="flex flex-wrap gap-3">
            <a
              href={`${API_URL}/docs`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline">
                <ExternalLink className="h-4 w-4 mr-2" />
                Swagger UI ({API_URL}/docs)
              </Button>
            </a>
            <a
              href={`${API_URL}/redoc`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline">
                <ExternalLink className="h-4 w-4 mr-2" />
                ReDoc ({API_URL}/redoc)
              </Button>
            </a>
          </div>
        </CardContent>
      </Card>

      {/* SSE Stream Status */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold mb-1">Real-time Stream (SSE)</h2>
          <p className="text-sm text-muted-foreground mb-4">
            The dashboard subscribes to{" "}
            <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">
              {API_URL}/api/stream
            </code>{" "}
            for live memory change events.
          </p>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Radio className={`h-4 w-4 ${sseStatusColor}`} />
              <span className={`text-sm font-medium ${sseStatusColor}`}>
                {sseStatus.charAt(0).toUpperCase() + sseStatus.slice(1)}
              </span>
            </div>
            {sseStatus !== "connected" && (
              <Button variant="outline" size="sm" onClick={reconnect}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Reconnect
              </Button>
            )}
            {sseStatus === "connected" && (
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            )}
          </div>
        </CardContent>
      </Card>

      {/* API Explorer */}
      <Card>
        <CardContent className="p-6 space-y-4">
          <h2 className="text-lg font-semibold mb-1">API Explorer</h2>
          <p className="text-sm text-muted-foreground">
            Send a GET request to any API endpoint and inspect the JSON response.
          </p>

          {/* Quick examples */}
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_ENDPOINTS.map((ep) => (
              <button
                key={ep}
                onClick={() => setEndpoint(ep)}
                className={`text-xs px-2 py-1 rounded font-mono border transition-colors ${
                  endpoint === ep
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-input hover:bg-accent"
                }`}
              >
                {ep}
              </button>
            ))}
          </div>

          {/* Endpoint input */}
          <div className="flex gap-2">
            <div className="flex items-center px-3 bg-muted border border-input rounded-l-md text-sm text-muted-foreground font-mono border-r-0 flex-shrink-0">
              {API_URL}
            </div>
            <Input
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              className="font-mono rounded-l-none flex-1"
              placeholder="/api/memories"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleFetch();
              }}
            />
            <Button onClick={handleFetch} disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              <span className="ml-2 hidden sm:inline">Send</span>
            </Button>
          </div>

          {/* Error */}
          {requestError && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <XCircle className="h-4 w-4 flex-shrink-0" />
              {requestError}
            </div>
          )}

          {/* Response */}
          {response !== null && (
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">Response</span>
                <button
                  onClick={() => navigator.clipboard.writeText(response)}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Copy
                </button>
              </div>
              <pre className="bg-muted rounded-md p-4 text-xs font-mono overflow-auto max-h-96 whitespace-pre-wrap break-words">
                {response}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
