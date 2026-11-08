/**
 * Dynamic imports for code splitting and lazy loading
 * This improves initial bundle size and time to interactive
 */

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/atoms/Skeleton";

// Loading components
const TimelineSkeleton = () => (
  <div className="space-y-4">
    {[...Array(5)].map((_, i) => (
      <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
        <Skeleton className="h-20 w-full" />
      </div>
    ))}
  </div>
);

const GraphSkeleton = () => (
  <div className="flex items-center justify-center h-96 bg-white rounded-lg border border-gray-200">
    <div className="text-center">
      <div className="animate-pulse text-gray-400">Loading graph...</div>
    </div>
  </div>
);

const AnalyticsSkeleton = () => (
  <div className="space-y-6">
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-6">
          <Skeleton className="h-12 w-full" />
        </div>
      ))}
    </div>
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <Skeleton className="h-64 w-full" />
    </div>
  </div>
);

// Heavy components with dynamic imports
export const TimelineView = dynamic(
  () => import("@/components/organisms/TimelineView").then((mod) => mod.TimelineView),
  {
    loading: () => <TimelineSkeleton />,
    ssr: false, // Timeline doesn't need SSR
  }
);

export const KnowledgeGraph = dynamic(
  () => import("@/components/organisms/KnowledgeGraph").then((mod) => mod.KnowledgeGraph),
  {
    loading: () => <GraphSkeleton />,
    ssr: false, // Graph visualization is client-side only
  }
);

export const AnalyticsDashboard = dynamic(
  () =>
    import("@/components/organisms/AnalyticsDashboard").then(
      (mod) => mod.AnalyticsDashboard
    ),
  {
    loading: () => <AnalyticsSkeleton />,
  }
);

export const SessionsList = dynamic(
  () => import("@/components/organisms/SessionsList").then((mod) => mod.SessionsList),
  {
    loading: () => <TimelineSkeleton />,
  }
);

export const SearchInterface = dynamic(
  () =>
    import("@/components/organisms/SearchInterface").then((mod) => mod.SearchInterface),
  {
    loading: () => <div className="p-4">Loading search...</div>,
    ssr: false,
  }
);

export const ActivityHeatmap = dynamic(
  () =>
    import("@/components/organisms/ActivityHeatmap").then((mod) => mod.ActivityHeatmap),
  {
    loading: () => <Skeleton className="h-48 w-full" />,
  }
);

// Modals
export const AddMemoryModal = dynamic(
  () => import("@/components/organisms/AddMemoryModal").then((mod) => mod.AddMemoryModal),
  {
    loading: () => null, // Don't show loading for modal
    ssr: false,
  }
);

export const EditMemoryModal = dynamic(
  () =>
    import("@/components/organisms/EditMemoryModal").then((mod) => mod.EditMemoryModal),
  {
    loading: () => null,
    ssr: false,
  }
);
