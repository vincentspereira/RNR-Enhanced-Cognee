"use client";

import type { ReactNode } from "react";
import { toast as notify, type ExternalToast } from "sonner";

type ToastOptions = Omit<ExternalToast, "id"> & {
  title?: ReactNode;
  description?: ReactNode;
  variant?: "default" | "destructive";
};

// Keep the existing page API connected to the Sonner toaster mounted by the app.
function toast(initial: ToastOptions) {
  let current = initial;
  const show = (options: ToastOptions, id?: string | number) => {
    const { title, variant, ...rest } = options;
    return variant === "destructive"
      ? notify.error(title ?? "Error", { duration: 6000, ...rest, id })
      : notify(title ?? "", { ...rest, id });
  };
  const id = show(current);
  return {
    id: String(id),
    dismiss: () => notify.dismiss(id),
    update: (changes: Partial<ToastOptions>) => {
      current = { ...current, ...changes };
      show(current, id);
    },
  };
}

function useToast() {
  return { toast, dismiss: notify.dismiss };
}

export { useToast, toast };
