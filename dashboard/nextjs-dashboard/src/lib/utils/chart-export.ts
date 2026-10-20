/**
 * Chart Export Utilities
 *
 * Utilities for exporting charts as PNG, SVG, and PDF files.
 */

import html2canvas from "html2canvas";
import jsPDF from "jspdf";

/**
 * Export a chart as PNG
 */
export async function exportChartAsPNG(
  chartRef: React.RefObject<HTMLElement | null>,
  filename: string = "chart.png",
  options?: {
    backgroundColor?: string;
    scale?: number;
  }
): Promise<void> {
  if (!chartRef.current) {
    throw new Error("Chart ref not found");
  }

  try {
    const canvas = await html2canvas(chartRef.current, {
      backgroundColor: options?.backgroundColor || "#0f172a",
      scale: options?.scale || 2,
    });

    canvas.toBlob((blob) => {
      if (blob) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }
    });
  } catch (error) {
    console.error("Error exporting chart as PNG:", error);
    throw new Error("Failed to export chart as PNG");
  }
}

/**
 * Export a chart as SVG (requires chart to be SVG-based)
 */
export async function exportChartAsSVG(
  chartRef: React.RefObject<SVGElement | null>,
  filename: string = "chart.svg"
): Promise<void> {
  if (!chartRef.current) {
    throw new Error("Chart ref not found");
  }

  try {
    const svgData = new XMLSerializer().serializeToString(chartRef.current);
    const svgBlob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Error exporting chart as SVG:", error);
    throw new Error("Failed to export chart as SVG");
  }
}

/**
 * Export a chart as PDF
 */
export async function exportChartAsPDF(
  chartRef: React.RefObject<HTMLElement | null>,
  filename: string = "chart.pdf",
  options?: {
    width?: number;
    height?: number;
    orientation?: "portrait" | "landscape";
  }
): Promise<void> {
  if (!chartRef.current) {
    throw new Error("Chart ref not found");
  }

  try {
    const canvas = await html2canvas(chartRef.current, {
      backgroundColor: "#ffffff",
      scale: 2,
    });

    const imgData = canvas.toDataURL("image/png");

    // Get canvas dimensions
    const imgWidth = options?.width || canvas.width;
    const imgHeight = options?.height || canvas.height;

    // Create PDF with appropriate orientation
    const pdf = new jsPDF({
      orientation: options?.orientation || (imgWidth > imgHeight ? "landscape" : "portrait"),
      unit: "px",
      format: [imgWidth, imgHeight],
    });

    pdf.addImage(imgData, "PNG", 0, 0, imgWidth, imgHeight);
    pdf.save(filename);
  } catch (error) {
    console.error("Error exporting chart as PDF:", error);
    throw new Error("Failed to export chart as PDF");
  }
}

/**
 * Export multiple charts as a single PDF
 */
export async function exportChartsAsPDF(
  chartRefs: React.RefObject<HTMLElement | null>[],
  filename: string = "charts.pdf"
): Promise<void> {
  if (chartRefs.length === 0) {
    throw new Error("No chart refs provided");
  }

  try {
    const canvases = await Promise.all(
      chartRefs.map((ref) =>
        html2canvas(ref.current!, {
          backgroundColor: "#ffffff",
          scale: 2,
        })
      )
    );

    // Calculate total height
    const maxHeight = Math.max(...canvases.map((c) => c.height));
    const totalWidth = canvases.reduce((sum, c) => sum + c.width, 0) + 20 * (canvases.length - 1);
    const padding = 20;

    const pdf = new jsPDF({
      orientation: totalWidth > maxHeight ? "landscape" : "portrait",
      unit: "px",
      format: [totalWidth + padding * 2, maxHeight + padding * 2],
    });

    let xOffset = padding;
    canvases.forEach((canvas) => {
      const imgData = canvas.toDataURL("image/png");
      pdf.addImage(imgData, "PNG", xOffset, padding, canvas.width, canvas.height);
      xOffset += canvas.width + 20;
    });

    pdf.save(filename);
  } catch (error) {
    console.error("Error exporting charts as PDF:", error);
    throw new Error("Failed to export charts as PDF");
  }
}

/**
 * Get chart data as base64 string
 */
export async function getChartAsBase64(
  chartRef: React.RefObject<HTMLElement | null>
): Promise<string> {
  if (!chartRef.current) {
    throw new Error("Chart ref not found");
  }

  try {
    const canvas = await html2canvas(chartRef.current, {
      backgroundColor: "#0f172a",
      scale: 2,
    });

    return canvas.toDataURL("image/png");
  } catch (error) {
    console.error("Error getting chart as base64:", error);
    throw new Error("Failed to get chart as base64");
  }
}
