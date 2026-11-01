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



  const handleSaveToken = () => {
    if (token.trim()) {
      sessionStorage.setItem("auth_token", token.trim());
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
          <h1 className="text-2xl font-bold tracking-tight">RNR Enhanced Cognee</h1>
          <p className="text-muted-foreground mt-1">AI Memory Management Dashboard</p>
        </div>

        <Card>
          <CardContent className="p-6 space-y-4">
            {/* Local mode notice */}
            <div className="flex items-start gap-3 rounded-md bg-blue-500/10 border border-blue-500/20 p-3">
              <Info className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-blue-700 dark:text-blue-300">Project access required</p>
                <p className="text-muted-foreground mt-0.5">
                  Paste your short-lived project access token. It determines which project and reviewed shared memories you can use.
                </p>
              </div>
            </div>

            {/* Optional token field */}
            <div className="space-y-2">
              <label htmlFor="token" className="text-sm font-medium">
                Project access token
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
                Kept only for this browser tab session. Use a restricted project token, never a service or recovery key.
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

            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
