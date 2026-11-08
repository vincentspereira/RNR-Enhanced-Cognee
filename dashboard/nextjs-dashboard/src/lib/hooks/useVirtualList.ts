/**
 * Virtual scrolling hook for large lists
 * Uses @tanstack/react-virtual for efficient rendering
 */

import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef } from "react";

interface UseVirtualListOptions {
  count: number;
  estimateSize?: () => number;
  overscan?: number;
  getScrollElement?: () => HTMLElement | null;
}

export function useVirtualList({
  count,
  estimateSize = () => 100, // Default estimated height
  overscan = 5,
  getScrollElement,
}: UseVirtualListOptions) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count,
    getScrollElement: getScrollElement || (() => parentRef.current),
    estimateSize,
    overscan,
  });

  return {
    parentRef,
    virtualizer,
    virtualItems: virtualizer.getVirtualItems(),
    totalSize: virtualizer.getTotalSize(),
  };
}
