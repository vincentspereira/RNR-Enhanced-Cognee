"use client";

import { useEffect } from "react";
import { AlertTriangle, Home, Bug } from "lucide-react";
import { Button } from "@/components/atoms/Button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error to error reporting service
    console.error("Application error:", error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
      <div className="max-w-lg w-full">
        <div className="bg-white rounded-lg shadow-xl border border-red-200 p-8">
          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div className="bg-red-100 rounded-full p-4">
              <AlertTriangle className="w-12 h-12 text-red-500" />
            </div>
          </div>

          {/* Error message */}
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Something went wrong
            </h1>
            <p className="text-gray-600">
              We apologize for the inconvenience. An unexpected error has
              occurred.
            </p>
          </div>

          {/* Error details (development only) */}
          {process.env.NODE_ENV === "development" && (
            <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-md">
              <p className="text-sm font-mono text-gray-800 break-words">
                {error.message}
              </p>
              {error.digest && (
                <p className="text-xs text-gray-500 mt-2">
                  Error ID: {error.digest}
                </p>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button onClick={reset} className="flex-1 sm:flex-none">
              Try Again
            </Button>
            <Button
              variant="outline"
              onClick={() => (window.location.href = "/")}
              className="flex-1 sm:flex-none"
            >
              <Home className="w-4 h-4 mr-2" />
              Go to Dashboard
            </Button>
          </div>

          {/* Report error */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => {
                // TODO: Open bug report form
                console.log("Report error:", error);
              }}
            >
              <Bug className="w-4 h-4 mr-2" />
              Report This Issue
            </Button>
          </div>
        </div>

        {/* Additional help */}
        <div className="mt-6 text-center text-sm text-gray-600">
          <p>If the problem persists, please contact support.</p>
        </div>
      </div>
    </div>
  );
}
