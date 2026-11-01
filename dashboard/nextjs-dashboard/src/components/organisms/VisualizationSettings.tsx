"use client";

import React, { useState, useMemo } from "react";
import { useStoredPreference, writeStoredPreference } from "@/lib/hooks/useStoredPreference";
import { X, Palette, Settings, Download } from "lucide-react";
import { NeutralButton } from "@/components/ui/elements/NeutralButton";
import { IconButton } from "@/components/ui/elements/IconButton";
import { Select } from "@/components/ui/elements/Select";

export interface VisualizationSettings {
  theme: "dark" | "light";
  defaultChartType: "line" | "bar" | "pie";
  animationsEnabled: boolean;
  dataDensity: "compact" | "comfortable" | "spacious";
  exportFormat: "png" | "svg" | "pdf";
  exportQuality: "low" | "medium" | "high";
  colorScheme: "default" | "vibrant" | "pastel" | "monochrome";
}

const DEFAULT_SETTINGS: VisualizationSettings = {
  theme: "dark",
  defaultChartType: "line",
  animationsEnabled: true,
  dataDensity: "comfortable",
  exportFormat: "png",
  exportQuality: "high",
  colorScheme: "default",
};

export interface VisualizationSettingsProps {
  isOpen: boolean;
  onClose: () => void;
  onSave?: (settings: VisualizationSettings) => void;
  className?: string;
}

/**
 * Visualization Settings Panel
 *
 * Configure chart preferences, themes, animations, and export options.
 */
export function VisualizationSettings({
  isOpen,
  onClose,
  onSave,
  className = "",
}: VisualizationSettingsProps) {
  const { settings: savedSettings, updateSettings } = useVisualizationSettings();
  const [draft, setDraft] = useState<VisualizationSettings | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const settings = draft ?? savedSettings;
  const setSettings = setDraft;
  const handleClose = () => { setDraft(null); setSaveError(null); onClose(); };

  const handleSave = () => {
    if (!updateSettings(settings)) {
      setSaveError("Unable to save preferences in this browser. Your changes have not been saved.");
      return;
    }
    setSaveError(null);
    setDraft(null);

    // Call onSave callback
    onSave?.(settings);

    // Close panel
    onClose();
  };

  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS);
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className={`bg-slate-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto ${className}`}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-slate-400" />
            <h2 className="text-xl font-semibold text-slate-200">Visualization Settings</h2>
          </div>
          <IconButton onClick={handleClose} aria-label="Close settings" size="sm" icon={<X className="w-5 h-5" />} />
        </div>

        {/* Settings */}
        <div className="p-6 space-y-6">
          {/* Theme Settings */}
          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <Palette className="w-4 h-4" />
              Theme
            </h3>
            <div className="space-y-3">
              <div>
                <label htmlFor="visualization-colorScheme" className="block text-sm text-slate-400 mb-1">Color Scheme</label>
                <Select
                  id="visualization-colorScheme" value={settings.colorScheme}
                  onChange={(e) => setSettings({ ...settings, colorScheme: e.target.value as VisualizationSettings["colorScheme"] })}
                  className="w-full"
                >
                  <option value="default">Default (Blue/Emerald)</option>
                  <option value="vibrant">Vibrant (High Saturation)</option>
                  <option value="pastel">Pastel (Soft Colors)</option>
                  <option value="monochrome">Monochrome (Grayscale)</option>
                </Select>
              </div>

              <div>
                <label htmlFor="visualization-theme" className="block text-sm text-slate-400 mb-1">Theme</label>
                <Select
                  id="visualization-theme" value={settings.theme}
                  onChange={(e) => setSettings({ ...settings, theme: e.target.value as VisualizationSettings["theme"] })}
                  className="w-full"
                >
                  <option value="dark">Dark</option>
                  <option value="light">Light</option>
                </Select>
              </div>
            </div>
          </div>

          {/* Chart Settings */}
          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-3">Charts</h3>
            <div className="space-y-3">
              <div>
                <label htmlFor="visualization-defaultChartType" className="block text-sm text-slate-400 mb-1">Default Chart Type</label>
                <Select
                  id="visualization-defaultChartType" value={settings.defaultChartType}
                  onChange={(e) => setSettings({ ...settings, defaultChartType: e.target.value as VisualizationSettings["defaultChartType"] })}
                  className="w-full"
                >
                  <option value="line">Line Chart</option>
                  <option value="bar">Bar Chart</option>
                  <option value="pie">Pie/Donut Chart</option>
                </Select>
              </div>

              <div className="flex items-center justify-between">
                <label className="text-sm text-slate-400">Enable Animations</label>
                <button
                  onClick={() => setSettings({ ...settings, animationsEnabled: !settings.animationsEnabled })}
                  className={`
                    relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                    ${settings.animationsEnabled ? "bg-blue-600" : "bg-slate-600"}
                  `}
                >
                  <span
                    className={`
                      inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                      ${settings.animationsEnabled ? "translate-x-6" : "translate-x-1"}
                    `}
                  />
                </button>
              </div>

              <div>
                <label htmlFor="visualization-dataDensity" className="block text-sm text-slate-400 mb-1">Data Density</label>
                <Select
                  id="visualization-dataDensity" value={settings.dataDensity}
                  onChange={(e) => setSettings({ ...settings, dataDensity: e.target.value as VisualizationSettings["dataDensity"] })}
                  className="w-full"
                >
                  <option value="compact">Compact (More Data)</option>
                  <option value="comfortable">Comfortable (Balanced)</option>
                  <option value="spacious">Spacious (Less Data)</option>
                </Select>
              </div>
            </div>
          </div>

          {/* Export Settings */}
          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export
            </h3>
            <div className="space-y-3">
              <div>
                <label htmlFor="visualization-exportFormat" className="block text-sm text-slate-400 mb-1">Default Format</label>
                <Select
                  id="visualization-exportFormat" value={settings.exportFormat}
                  onChange={(e) => setSettings({ ...settings, exportFormat: e.target.value as VisualizationSettings["exportFormat"] })}
                  className="w-full"
                >
                  <option value="png">PNG (Raster Image)</option>
                  <option value="svg">SVG (Vector Graphics)</option>
                  <option value="pdf">PDF (Document)</option>
                </Select>
              </div>

              <div>
                <label htmlFor="visualization-exportQuality" className="block text-sm text-slate-400 mb-1">Export Quality</label>
                <Select
                  id="visualization-exportQuality" value={settings.exportQuality}
                  onChange={(e) => setSettings({ ...settings, exportQuality: e.target.value as VisualizationSettings["exportQuality"] })}
                  className="w-full"
                >
                  <option value="low">Low (Fast, Smaller File)</option>
                  <option value="medium">Medium (Balanced)</option>
                  <option value="high">High (Best Quality, Larger File)</option>
                </Select>
              </div>
            </div>
          </div>
        </div>

        {saveError && <p role="alert" className="px-6 text-red-400">{saveError}</p>}
        {/* Footer */}
        <div className="flex items-center justify-end gap-2 p-6 border-t border-slate-700">
          <NeutralButton onClick={handleReset} size="sm">
            Reset to Defaults
          </NeutralButton>
          <NeutralButton onClick={handleClose} size="sm">
            Cancel
          </NeutralButton>
          <NeutralButton onClick={handleSave} size="sm" variant="default">
            Save Settings
          </NeutralButton>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to use visualization settings
 */
export function useVisualizationSettings() {
  const saved = useStoredPreference("visualizationSettings");
  const settings = useMemo((): VisualizationSettings => {
    try {
      const parsed: unknown = JSON.parse(saved || "null");
      if (!parsed || typeof parsed !== "object") return DEFAULT_SETTINGS;
      const values = parsed as Record<string, unknown>;
      return {
        theme: values.theme === "light" ? "light" : "dark",
        defaultChartType: values.defaultChartType === "bar" || values.defaultChartType === "pie" ? values.defaultChartType : "line",
        animationsEnabled: typeof values.animationsEnabled === "boolean" ? values.animationsEnabled : true,
        dataDensity: values.dataDensity === "compact" || values.dataDensity === "spacious" ? values.dataDensity : "comfortable",
        exportFormat: values.exportFormat === "svg" || values.exportFormat === "pdf" ? values.exportFormat : "png",
        exportQuality: values.exportQuality === "low" || values.exportQuality === "medium" ? values.exportQuality : "high",
        colorScheme: values.colorScheme === "vibrant" || values.colorScheme === "pastel" || values.colorScheme === "monochrome" ? values.colorScheme : "default",
      };
    } catch { return DEFAULT_SETTINGS; }
  }, [saved]);

  const updateSettings = (changes: Partial<VisualizationSettings>) => {
    return writeStoredPreference("visualizationSettings", JSON.stringify({ ...settings, ...changes }));
  };
  return { settings, updateSettings };
}
