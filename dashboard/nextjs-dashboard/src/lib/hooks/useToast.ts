"use client";

import { toast } from "sonner";

type ToastProps = {
  title?: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
};

export function useToast() {
  const success = (message: string, props?: ToastProps) => {
    return toast.success(message, {
      description: props?.description,
      action: props?.action
        ? {
            label: props.action.label,
            onClick: props.action.onClick,
          }
        : undefined,
    });
  };

  const error = (message: string, props?: ToastProps) => {
    return toast.error(message, {
      description: props?.description,
      action: props?.action
        ? {
            label: props.action.label,
            onClick: props.action.onClick,
          }
        : undefined,
    });
  };

  const warning = (message: string, props?: ToastProps) => {
    return toast.warning(message, {
      description: props?.description,
      action: props?.action
        ? {
            label: props.action.label,
            onClick: props.action.onClick,
          }
        : undefined,
    });
  };

  const info = (message: string, props?: ToastProps) => {
    return toast.info(message, {
      description: props?.description,
      action: props?.action
        ? {
            label: props.action.label,
            onClick: props.action.onClick,
          }
        : undefined,
    });
  };

  const loading = (message: string, props?: Omit<ToastProps, "action">) => {
    return toast.loading(message, {
      description: props?.description,
    });
  };

  const dismiss = (id?: string | number) => {
    toast.dismiss(id);
  };

  return {
    success,
    error,
    warning,
    info,
    loading,
    dismiss,
  };
}
