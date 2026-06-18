"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/atoms";
import { Button } from "@/components/atoms";
import { Badge } from "@/components/atoms";
import { useUIStore } from "@/lib/stores";
import { checkHealth } from "@/lib/api/analytics";
import { Sun, Moon, Monitor, RefreshCw, CheckCircle2, XCircle } from "lucide-react";

type Theme = "light" | "dark" | "system";

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (theme === "system") {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.classList.toggle("dark", prefersDark);
  } else {
    root.classList.toggle("dark", theme === "dark");
  }
}

export default function SettingsPage() {
  const { theme, setTheme } = useUIStore();
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [healthResult, setHealthResult] = useState<{
    status: string;
    databases?: Record<string, boolean>;
  } | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Apply theme on mount and on change
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    applyTheme(newTheme);
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setHealthError(null);
    setHealthResult(null);
    try {
      const result = await checkHealth();
      setHealthResult(result as { status: string; databases?: Record<string, boolean> });
    } catch (error) {
      setHealthError(error instanceof Error ? error.message : "Connection failed");
    } finally {
      setIsTestingConnection(false);
    }
  };

  const themeOptions: { value: Theme; label: string; icon: React.ReactNode }[] = [
    { value: "light", label: "Light", icon: <Sun className="h-4 w-4" /> },
    { value: "dark", label: "Dark", icon: <Moon className="h-4 w-4" /> },
    { value: "system", label: "System", icon: <Monitor className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Configure your Enhanced Cognee dashboard
        </p>
      </div>

      {/* Theme Section */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold mb-1">Appearance</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Choose how the dashboard looks on your device.
          </p>
          <div className="flex gap-3">
            {themeOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => handleThemeChange(option.value)}
                className={`flex items-center gap-2 px-4 py-2 rounded-md border text-sm font-medium transition-colors ${
                  theme === option.value
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input bg-background hover:bg-accent hover:text-accent-foreground"
                }`}
                aria-pressed={theme === option.value}
              >
                {option.icon}
                {option.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* API Connection Section */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold mb-1">API Connection</h2>
          <p className="text-sm text-muted-foreground mb-4">
            The backend API this dashboard is connected to.
          </p>

          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-muted-foreground w-24">API URL</span>
              <code className="text-sm bg-muted px-2 py-1 rounded font-mono">{apiUrl}</code>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-muted-foreground w-24">Auth Mode</span>
              <Badge variant="outline">Local (no auth required)</Badge>
            </div>
          </div>

          <div className="mt-4">
            <Button
              variant="outline"
              onClick={handleTestConnection}
              disabled={isTestingConnection}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isTestingConnection ? "animate-spin" : ""}`} />
              Test Connection
            </Button>
          </div>

          {/* Health Result */}
          {healthError && (
            <div className="mt-4 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              Connection failed: {healthError}
            </div>
          )}

          {healthResult && (
            <div className="mt-4 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <span className="text-sm font-medium">
                  Connected ({healthResult.status})
                </span>
              </div>
              {healthResult.databases && (
                <div className="space-y-1 ml-6">
                  {Object.entries(healthResult.databases).map(([db, ok]) => (
                    <div key={db} className="flex items-center gap-2 text-sm">
                      {ok ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />
                      )}
                      <span className="capitalize">{db}</span>
                      <span className={ok ? "text-green-600" : "text-red-600"}>
                        {ok ? "OK" : "ERR"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
