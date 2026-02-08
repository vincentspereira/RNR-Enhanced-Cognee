"use client";

import { useSSE } from "@/lib/hooks/useSSE";

export function ConnectionStatus() {
  const { status, isConnected, isConnecting } = useSSE();

  const statusConfig = {
    connected: {
      color: "bg-green-500",
      label: "Connected",
      description: "Real-time updates active",
    },
    connecting: {
      color: "bg-yellow-500",
      label: "Connecting...",
      description: "Establishing connection",
    },
    disconnected: {
      color: "bg-red-500",
      label: "Disconnected",
      description: "Connection lost. Reconnecting...",
    },
  };

  const config = statusConfig[status];

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="group relative flex items-center gap-2 bg-white rounded-lg shadow-lg px-3 py-2 border border-gray-200">
        <div className="flex items-center gap-2">
          {/* Status indicator dot */}
          <div
            className={`w-2 h-2 rounded-full ${config.color} ${
              isConnecting ? "animate-pulse" : ""
            }`}
            aria-hidden="true"
          />

          {/* Status label */}
          <span className="text-sm font-medium text-gray-700">
            {config.label}
          </span>
        </div>

        {/* Tooltip */}
        <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block w-48">
          <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 shadow-lg">
            <div className="font-semibold mb-1">Connection Status</div>
            <div>{config.description}</div>
            {/* Arrow */}
            <div className="absolute top-full right-3 -mt-1">
              <div className="border-4 border-transparent border-t-gray-900" />
            </div>
          </div>
        </div>

        {/* Screen reader only text */}
        <span className="sr-only">
          Connection status: {config.label}. {config.description}
        </span>
      </div>
    </div>
  );
}
