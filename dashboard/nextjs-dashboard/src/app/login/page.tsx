"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/atoms";
import { Input } from "@/components/atoms";
import { Card, CardContent } from "@/components/atoms";
import { Info, LogIn } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [token, setToken] = useState("");

  const handleContinue = () => {
    router.push("/dashboard");
  };

  const handleSaveToken = () => {
    if (token.trim()) {
      localStorage.setItem("auth_token", token.trim());
    }
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary mb-4">
            <span className="text-primary-foreground font-bold text-xl">E</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Enhanced Cognee</h1>
          <p className="text-muted-foreground mt-1">AI Memory Management Dashboard</p>
        </div>

        <Card>
          <CardContent className="p-6 space-y-4">
            {/* Local mode notice */}
            <div className="flex items-start gap-3 rounded-md bg-blue-500/10 border border-blue-500/20 p-3">
              <Info className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-blue-700 dark:text-blue-300">Local Mode Active</p>
                <p className="text-muted-foreground mt-0.5">
                  No login is required in local mode. Click &quot;Continue to Dashboard&quot; to proceed.
                  Optionally paste an API token below if your backend is configured with authentication.
                </p>
              </div>
            </div>

            {/* Optional token field */}
            <div className="space-y-2">
              <label htmlFor="token" className="text-sm font-medium">
                API Token (optional)
              </label>
              <Input
                id="token"
                type="password"
                placeholder="Paste token here..."
                value={token}
                onChange={(e) => setToken(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleSaveToken();
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                If provided, it will be stored in localStorage and sent as a Bearer token.
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-2 pt-2">
              {token.trim() && (
                <Button onClick={handleSaveToken} className="w-full">
                  <LogIn className="h-4 w-4 mr-2" />
                  Save Token and Continue
                </Button>
              )}
              <Button
                variant={token.trim() ? "outline" : "default"}
                onClick={handleContinue}
                className="w-full"
              >
                Continue to Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
