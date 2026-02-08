"use client";

import React, { useState, useEffect } from "react";
import { X, Palette, Settings, Download } from "lucide-react";
import { NeutralButton } from "@/components/ui/elements/NeutralButton";
import { IconButton } from "@/components/ui/elements/IconButton";
import { Select } from "@/components/ui/elements/Select";
import { Input } from "@/components/ui/elements/Input";

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
  const [settings, setSettings] = useState<VisualizationSettings>(DEFAULT_SETTINGS);

  // Load settings from localStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("visualizationSettings");
      if (saved) {
        try {
          setSettings(JSON.parse(saved));
        } catch (error) {
          console.error("Failed to parse visualization settings:", error);
        }
      }
    }
  }, []);

  const handleSave = () => {
    // Save to localStorage
    if (typeof window !== "undefined") {
      localStorage.setItem("visualizationSettings", JSON.stringify(settings));
    }

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
          <IconButton onClick={onClose} size="sm" icon={<X className="w-5 h-5" />} />
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
                <label className="block text-sm text-slate-400 mb-1">Color Scheme</label>
                <Select
                  value={settings.colorScheme}
                  onChange={(e) => setSettings({ ...settings, colorScheme: e.target.value as any })}
                  className="w-full"
                >
                  <option value="default">Default (Blue/Emerald)</option>
                  <option value="vibrant">Vibrant (High Saturation)</option>
                  <option value="pastel">Pastel (Soft Colors)</option>
                  <option value="monochrome">Monochrome (Grayscale)</option>
                </Select>
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-1">Theme</label>
                <Select
                  value={settings.theme}
                  onChange={(e) => setSettings({ ...settings, theme: e.target.value as any })}
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
                <label className="block text-sm text-slate-400 mb-1">Default Chart Type</label>
                <Select
                  value={settings.defaultChartType}
                  onChange={(e) => setSettings({ ...settings, defaultChartType: e.target.value as any })}
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
                <label className="block text-sm text-slate-400 mb-1">Data Density</label>
                <Select
                  value={settings.dataDensity}
                  onChange={(e) => setSettings({ ...settings, dataDensity: e.target.value as any })}
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
                <label className="block text-sm text-slate-400 mb-1">Default Format</label>
                <Select
                  value={settings.exportFormat}
                  onChange={(e) => setSettings({ ...settings, exportFormat: e.target.value as any })}
                  className="w-full"
                >
                  <option value="png">PNG (Raster Image)</option>
                  <option value="svg">SVG (Vector Graphics)</option>
                  <option value="pdf">PDF (Document)</option>
                </Select>
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-1">Export Quality</label>
                <Select
                  value={settings.exportQuality}
                  onChange={(e) => setSettings({ ...settings, exportQuality: e.target.value as any })}
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

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 p-6 border-t border-slate-700">
          <NeutralButton onClick={handleReset} size="sm">
            Reset to Defaults
          </NeutralButton>
          <NeutralButton onClick={onClose} size="sm">
            Cancel
          </NeutralButton>
          <NeutralButton onClick={handleSave} size="sm" variant="primary">
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
  const [settings, setSettings] = useState<VisualizationSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("visualizationSettings");
      if (saved) {
        try {
          setSettings(JSON.parse(saved));
        } catch (error) {
          console.error("Failed to parse visualization settings:", error);
        }
      }
    }
  }, []);

  const updateSettings = (newSettings: Partial<VisualizationSettings>) => {
    const updated = { ...settings, ...newSettings };
    setSettings(updated);

    if (typeof window !== "undefined") {
      localStorage.setItem("visualizationSettings", JSON.stringify(updated));
    }
  };

  return { settings, updateSettings };
}
