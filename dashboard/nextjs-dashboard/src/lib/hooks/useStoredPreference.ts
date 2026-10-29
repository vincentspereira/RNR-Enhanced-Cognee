"use client";

import { useSyncExternalStore } from "react";

const changed = "enhanced-cognee-preference-changed";

function subscribe(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener(changed, listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener(changed, listener);
  };
}

export function useStoredPreference(key: string): string | null {
  return useSyncExternalStore(subscribe, () => {
    try { return window.localStorage.getItem(key); }
    catch { return null; }
  }, () => null);
}

export function writeStoredPreference(key: string, value: string): boolean {
  try {
    window.localStorage.setItem(key, value);
    window.dispatchEvent(new Event(changed));
    return true;
  } catch {
    return false;
  }
}
