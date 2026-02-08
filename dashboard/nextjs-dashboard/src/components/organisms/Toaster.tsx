"use client";

import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      expand={false}
      richColors
      closeButton
      toastOptions={{
        duration: 4000,
        error: {
          duration: 6000,
        },
        loading: {
          duration: Infinity, // Loading toasts stay until dismissed
        },
      }}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-white group-[.toaster]:text-gray-950 group-[.toaster]:border-gray-200 group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-gray-500",
          actionButton:
            "group-[.toast]:bg-blue-600 group-[.toast]:text-white group-[.toast]:hover:bg-blue-700",
          cancelButton:
            "group-[.toast]:bg-gray-100 group-[.toast]:text-gray-900 group-[.toast]:hover:bg-gray-200",
          success: "group-[.toaster]:border-green-500",
          error: "group-[.toaster]:border-red-500",
          warning: "group-[.toaster]:border-yellow-500",
          info: "group-[.toaster]:border-blue-500",
        },
      }}
    />
  );
}
