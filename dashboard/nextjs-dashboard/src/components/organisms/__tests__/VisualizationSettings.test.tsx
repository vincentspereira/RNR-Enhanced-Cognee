import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { VisualizationSettings, useVisualizationSettings } from "../VisualizationSettings";
import { writeStoredPreference } from "@/lib/hooks/useStoredPreference";

beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe("persisted visualization preferences", () => {
  it("updates other subscribers in the same tab and rejects malformed stored values", () => {
    const first = renderHook(() => useVisualizationSettings());
    const second = renderHook(() => useVisualizationSettings());
    act(() => { first.result.current.updateSettings({ theme: "light" }); });
    expect(second.result.current.settings.theme).toBe("light");
    act(() => { writeStoredPreference("visualizationSettings", '{"theme":42,"exportFormat":"executable"}'); });
    expect(second.result.current.settings.theme).toBe("dark");
    expect(second.result.current.settings.exportFormat).toBe("png");
    act(() => { writeStoredPreference("visualizationSettings", "not JSON"); });
    expect(second.result.current.settings.animationsEnabled).toBe(true);
  });

  it("cancels a draft without changing saved preferences", () => {
    const onClose = vi.fn();
    const view = render(<VisualizationSettings isOpen onClose={onClose} />);
    fireEvent.change(screen.getByLabelText("Theme"), { target: { value: "light" } });
    fireEvent.click(screen.getByRole("button", { name: "Close settings" }));
    view.rerender(<VisualizationSettings isOpen={false} onClose={onClose} />);
    view.rerender(<VisualizationSettings isOpen onClose={onClose} />);
    expect(screen.getByLabelText("Theme")).toHaveValue("dark");
    expect(localStorage.getItem("visualizationSettings")).toBeNull();
  });

  it("does not report success or close when the browser refuses persistence", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("Synthetic quota failure"); });
    const onSave = vi.fn(), onClose = vi.fn();
    render(<VisualizationSettings isOpen onSave={onSave} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Save Settings" }));
    expect(screen.getByRole("alert")).toHaveTextContent("have not been saved");
    expect(onSave).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
  });
});
