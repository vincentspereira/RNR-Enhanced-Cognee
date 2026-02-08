# Enhanced Cognee Memory Dashboard - UX/UI Specification

**Version:** 1.0.0
**Last Updated:** 2025-02-06
**Status:** Design Specification
**Target Platform:** Web Application (Next.js 14 + TypeScript + Tailwind CSS)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design Principles](#design-principles)
3. [Information Architecture](#information-architecture)
4. [Layout Structure](#layout-structure)
5. [Navigation Design](#navigation-design)
6. [Component Specifications](#component-specifications)
7. [Visual Design System](#visual-design-system)
8. [Data Visualization](#data-visualization)
9. [User Flows](#user-flows)
10. [Responsive Design](#responsive-design)
11. [Accessibility](#accessibility)
12. [Technical Implementation](#technical-implementation)

---

## Executive Summary

### Project Overview

The Enhanced Cognee Memory Dashboard is a sophisticated web application for visualizing, managing, and analyzing an enterprise-grade AI memory system. It provides real-time insights into memory operations, knowledge graph relationships, agent coordination, and system performance.

### Key Design Goals

1. **Professional & Modern:** Enterprise-grade aesthetic that communicates reliability and sophistication
2. **Information-Dense:** Present complex data without overwhelming users
3. **Fast & Responsive:** Sub-second page loads, smooth animations, real-time updates
4. **Intuitive Navigation:** Logical organization that matches user mental models
5. **Accessible:** WCAG 2.1 AA compliance with full keyboard navigation
6. **Dark Mode First:** Dark theme as default with light theme option

### Target Users

- **Primary:** AI researchers, ML engineers, system administrators
- **Secondary:** Data analysts, project managers, technical stakeholders
- **Skill Level:** Intermediate to advanced technical users

---

## Design Principles

### 1. Clarity Over Density

**Principle:** Prioritize clarity and readability over displaying maximum information.

**Implementation:**
- Use progressive disclosure for complex data
- Group related information with clear visual hierarchy
- Provide concise summaries before detailed views
- Use whitespace intentionally to reduce cognitive load

**Example:**
```
Memory List View:
- Primary: Memory summary, relevance score, timestamp
- Secondary: Category, agent ID, metadata badges (collapsed by default)
- Tertiary: Full content, embeddings, relationships (on expand/click)
```

### 2. Consistency Creates Confidence

**Principle:** Maintain consistent patterns across all interfaces.

**Implementation:**
- Standardized color meanings (green = success, red = error, amber = warning)
- Consistent component behaviors (buttons, inputs, modals)
- Predictable navigation patterns
- Uniform data formatting (dates, numbers, IDs)

### 3. Feedback For Every Action

**Principle:** Users should always understand what's happening.

**Implementation:**
- Loading states for all async operations
- Success/error messages for all mutations
- Hover states for interactive elements
- Progress indicators for long-running operations
- Real-time updates for live data

### 4. Accessibility Is Non-Negotiable

**Principle:** All users must be able to use the application effectively.

**Implementation:**
- WCAG 2.1 AA compliance (minimum)
- Full keyboard navigation
- Screen reader compatibility
- High contrast mode support
- Focus indicators always visible
- Text alternatives for all non-text content

### 5. Performance Is a Feature

**Principle:** Fast interfaces feel better and work better.

**Implementation:**
- Optimistic UI updates for mutations
- Virtual scrolling for large lists
- Lazy loading for images and heavy components
- Code splitting by route
- Debounced search and filtering

---

## Information Architecture

### Site Structure

```
Enhanced Cognee Dashboard
├── Dashboard (Home)
│   ├── Overview (stats, health, recent activity)
│   ├── Quick Actions (add memory, run search)
│   └── System Status (database connections, active agents)
│
├── Memories
│   ├── List View (filterable, sortable, batch operations)
│   ├── Detail View (single memory with full context)
│   ├── Timeline View (chronological visualization)
│   └── Graph View (knowledge graph visualization)
│
├── Search
│   ├── Simple Search (single input, semantic search)
│   ├── Advanced Search (filters by type, category, date range)
│   └── Search Results (with relevance scores and snippets)
│
├── Sessions
│   ├── Session List (grouped by agent)
│   ├── Session Timeline (chronological view)
│   └── Session Detail (memory breakdown per session)
│
├── Analytics
│   ├── Overview Dashboard (key metrics, trends)
│   ├── Memory Growth (storage over time)
│   ├── Token Efficiency (compression stats)
│   ├── Agent Activity (per-agent metrics)
│   ├── Performance Metrics (query times, cache hits)
│   └── Deduplication Stats (storage savings)
│
├── Agents
│   ├── Agent List (all registered agents)
│   ├── Agent Detail (activity, performance, coordination)
│   └── Coordination View (real-time sync status)
│
├── Settings
│   ├── General (theme, language, preferences)
│   ├── Categories (dynamic category configuration)
│   ├── Data Management (export, import, archival)
│   ├── Sharing Policies (cross-agent access control)
│   └── API Keys (MCP server credentials)
│
└── Developer Tools
    ├── API Documentation (interactive API docs)
    ├── MCP Tool Tester (test MCP tools directly)
    ├── Database Inspector (query PostgreSQL, Qdrant, Neo4j)
    ├── Query Performance Analyzer (slow query detection)
    └── System Logs (real-time log viewer)
```

### Navigation Model

**Primary Navigation:** Left sidebar (desktop) / Bottom nav (mobile)
- Persistent across all pages
- Icon + label for each section
- Active state clearly highlighted
- Collapse to icon-only on smaller screens

**Secondary Navigation:** Tabs within sections
- Example: Analytics > Overview, Memory Growth, Token Efficiency
- Horizontal scroll on mobile
- Breadcrumbs for deep navigation

**Tertiary Navigation:** Within-page anchors
- Table of contents for long pages
- Quick jump links to sections

---

## Layout Structure

### Global Layout

```
+------------------------------------------------------------------+
|  HEADER (64px height)                                             |
|  +----------------+  Enhanced Cognee    [Search]  [User] [Gear] |
|  | Logo           |                                                 |
|  +----------------+                                                 |
+------------------------------------------------------------------+
|           |                                                        |
|  SIDEBAR  |  MAIN CONTENT AREA                                    |
|  (240px)  |  (flexible, min 320px)                                |
|           |                                                        |
|  +------> |  +--------------------------------------------------+  |
|  | Nav    |  |  PAGE HEADER (optional)                          |  |
|  | Items  |  |  Title, Breadcrumbs, Actions                     |  |
|  |        |  +--------------------------------------------------+  |
|  |        |                                                        |
|  |        |  +--------------------------------------------------+  |
|  |        |  |                                                  |  |
|  |        |  |  CONTENT                                         |  |
|  |        |  |  (scrollable)                                    |  |
|  |        |  |                                                  |  |
|  |        |  |                                                  |  |
|  |        |  +--------------------------------------------------+  |
|  |        |                                                        |
|  |        |  +--------------------------------------------------+  |
|  |        |  |  FOOTER (optional)                                |  |
|  |        |  |  Status indicators, version info                  |  |
|  |        |  +--------------------------------------------------+  |
|           |                                                        |
+------------------------------------------------------------------+
```

### Header (64px)

**Purpose:** Global navigation, search, user actions

**Components:**
- Logo (left) - Links to home
- Breadcrumbs (center-left) - Current location
- Global Search (center) - Quick search across all memories
- System Status (right) - Health indicator
- User Menu (far right) - Avatar dropdown

**States:**
- Default: Full header with all components
- Scrolled: Sticky header with shadow
- Focus: Clear visual indicator on focused element

### Sidebar (240px expanded, 64px collapsed)

**Purpose:** Primary navigation between major sections

**Navigation Items:**
1. Dashboard (Home icon)
2. Memories (Database icon)
3. Search (Search icon)
4. Sessions (Clock icon)
5. Analytics (Chart icon)
6. Agents (Users icon)
7. Settings (Gear icon)
8. Developer Tools (Code icon)

**Collapsible States:**
- Expanded (240px): Icon + label + badge (if applicable)
- Collapsed (64px): Icon only, label on hover
- Hidden (mobile): Off-canvas drawer

**Responsive Behavior:**
- Desktop (> 1024px): Always visible, collapsible
- Tablet (768px - 1024px): Icon-only by default
- Mobile (< 768px): Bottom navigation bar (48px height)

### Main Content Area

**Purpose:** Display page-specific content

**Structure:**
- Page Header (optional): Title, breadcrumbs, action buttons
- Content: Scrollable area with page-specific components
- Footer (optional): Status indicators, pagination

**Max Width:** 1600px (centered with auto margins)
**Padding:** 24px (desktop), 16px (tablet), 12px (mobile)

---

## Navigation Design

### Left Sidebar Navigation

**Visual Design:**
- Background: Dark surface (slate-900 in dark mode)
- Border: Right border with subtle contrast
- Text: Muted when inactive, bright when active
- Icons: 20x20px, consistent stroke width
- Hover: Background highlight with smooth transition

**Active State:**
- Left accent bar (3px wide, brand color)
- Brighter text color
- Background: Slightly lighter than inactive

**Badge Indicators:**
- Notification count: Red circle with white text
- Status dot: Green (healthy), Amber (warning), Red (error)
- Positioned 8px from icon right edge

**Collapse Toggle:**
- Bottom of sidebar
- Chevron icon pointing left (expanded) or right (collapsed)
- Smooth width transition (300ms ease)

### Bottom Navigation (Mobile)

**Height:** 48px
**Position:** Fixed at bottom
**Background:** Dark surface with top border
**Items:** 5-7 icons from sidebar, prioritized by frequency

**Priority Order:**
1. Dashboard (always visible)
2. Memories (always visible)
3. Search (always visible)
4. Analytics (visible on larger mobile screens)
5. More menu (overflow for remaining items)

### Breadcrumbs

**Location:** Page header, below title
**Separator:** Right chevron (>)
**Clickability:** All segments clickable except current page

**Format:**
```
Dashboard > Memories > Memory Detail
```

**Styling:**
- Muted color for parent paths
- Current page in bright color
- Hover underline for clickable segments

---

## Component Specifications

### 1. Data Table

**Purpose:** Display structured, sortable, filterable data

**Structure:**
```
+----------------------------------------------------------------+
| [Filter Input]     [Export Button]       [Columns Settings]    |
+----------------------------------------------------------------+
| Column Header 1 | Column Header 2 | Column Header 3 | Actions |
+----------------------------------------------------------------+
| Row 1 Cell 1    | Row 1 Cell 2    | Row 1 Cell 3    | [Edit]  |
| Row 2 Cell 1    | Row 2 Cell 2    | Row 2 Cell 3    | [Edit]  |
| Row 3 Cell 1    | Row 3 Cell 2    | Row 3 Cell 3    | [Edit]  |
+----------------------------------------------------------------+
| < Prev | 1 | 2 | 3 | ... | 10 | Next >                   |
+----------------------------------------------------------------+
```

**Features:**
- **Sorting:** Click column header to sort, toggle ascending/descending
- **Filtering:** Text input above table filters all columns
- **Pagination:** 25, 50, 100 rows per page
- **Row Selection:** Checkbox column for batch operations
- **Virtual Scrolling:** For > 100 rows
- **Sticky Header:** Header stays visible while scrolling
- **Row Actions:** Edit/Delete buttons in last column
- **Row Hover:** Subtle background highlight

**Column Types:**
- Text: Left-aligned, truncate with ellipsis
- Number: Right-aligned, formatted with locale
- Date: Left-aligned, relative time (e.g., "2 hours ago")
- Status: Badge with color coding
- Actions: Right-aligned, icon buttons

**Accessibility:**
- Keyboard navigation (arrow keys, Enter, Space)
- ARIA labels for sortable columns
- Focus visible on all interactive elements

### 2. Memory Card

**Purpose:** Display memory summary in grid/list view

**Layout:**
```
+--------------------------------------------------------------+
| [Category Badge]          [Timestamp]                        |
|                                                              |
| Memory summary text (2-3 lines max, truncate with ellipsis)  |
|                                                              |
| [Agent ID]  [Relevance: 0.95]  [Actions Menu]                |
+--------------------------------------------------------------+
```

**States:**
- Default: Regular border, neutral background
- Hover: Elevated shadow, border highlight
- Selected: Accent border, brighter background
- Disabled: Muted colors, no hover effect

**Variants:**
1. **Compact:** 280px width, essential info only
2. **Standard:** 400px width, summary + metadata
3. **Detailed:** 600px width, includes snippet + relationships

**Interactions:**
- Click: Navigate to detail view
- Right-click: Context menu (copy, share, delete)
- Long-press (mobile): Show context menu

### 3. Search Interface

**Simple Search:**
```
+----------------------------------------------------------------+
| [Search Icon]  Enter your search query...        [Clear Icon]  |
+----------------------------------------------------------------+
| Suggested: "TypeScript preferences"  "authentication flow"    |
+----------------------------------------------------------------+
```

**Features:**
- **Autocomplete:** Suggest queries from history
- **Recent Searches:** Dropdown of 5 recent searches
- **Search As You Type:** Debounced search with 300ms delay
- **Clear Button:** Visible when input has content

**Advanced Search:**
```
+----------------------------------------------------------------+
| Query: [________________]                           [Search]   |
+----------------------------------------------------------------+
| Filters:                                                      |
| + [Category Dropdown]  + [Date Range Picker]                  |
| + [Agent Multi-Select]  + [Min Relevance Slider]              |
| + [Memory Type Checkboxes]                                    |
+----------------------------------------------------------------+
| Search Type: ( ) Semantic  ( ) Keyword  (*) Hybrid             |
+----------------------------------------------------------------+
```

**Search Results:**
```
+----------------------------------------------------------------+
| Found 23 results for "TypeScript" (0.42 seconds)              |
+----------------------------------------------------------------+
| [Memory Card 1] - Relevance: 0.98                             |
| [Memory Card 2] - Relevance: 0.95                             |
| [Memory Card 3] - Relevance: 0.89                             |
+----------------------------------------------------------------+
```

### 4. Timeline Visualization

**Purpose:** Display memories chronologically with context

**Layout:**
```
     Time Axis
        |
+-------+-------+
|       |       |
Jan    Feb    Mar
|       |       |
v       v       v
[Memory] [Memory] [Memory]
  12       5       18

Zoom: [Day] [Week] [Month] [Year]
```

**Features:**
- **Time Axis:** Horizontal or vertical based on screen size
- **Memory Markers:** Dots or bars on timeline
- **Grouping:** By day, week, month, or year
- **Zoom Controls:** Slider or preset buttons
- **Filters:** Category, agent, type
- **Click to Expand:** Show memory details

**Interactions:**
- Drag timeline to pan
- Scroll/pinch to zoom
- Click marker to view memory
- Hover for quick preview (tooltip)

### 5. Knowledge Graph Visualization

**Purpose:** Visualize Neo4j knowledge graph with entities and relationships

**Technology:** react-force-graph-2d or Cytoscape.js

**Layout:**
```
+----------------------------------------------------------------+
| [Zoom In] [Zoom Out] [Fit] [Layout] [Filter]           [Help] |
+----------------------------------------------------------------+
|                                                                |
|                     Graph Canvas                                |
|                                                                |
|              [Entity Nodes] + [Relationship Edges]             |
|                                                                |
+----------------------------------------------------------------+
| Legend: [Person] [Organization] [Concept] [Event]             |
+----------------------------------------------------------------+
```

**Visual Encoding:**
- **Node Size:** Based on importance/connections
- **Node Color:** By entity type
- **Edge Thickness:** By relationship strength
- **Edge Color:** By relationship type
- **Labels:** Show on hover or zoom

**Interactions:**
- **Drag Node:** Reposition (temporary)
- **Click Node:** Expand connections or show details
- **Hover:** Highlight connected nodes
- **Zoom/Pan:** Mouse wheel, drag canvas
- **Layout:** Force-directed, hierarchical, circular

**Performance:**
- Virtual rendering for > 1000 nodes
- Level-of-detail based on zoom
- Progressive loading of edges

### 6. Statistics Cards

**Purpose:** Display key metrics at a glance

**Layout:**
```
+--------------------------------+
|  Total Memories       1,234    |
|  +12% from last month          |
+--------------------------------+
```

**Components:**
- **Label:** Metric name
- **Value:** Large, prominent number
- **Trend:** Percentage change with icon (up/down)
- **Sparkline:** Mini chart showing trend over time

**Color Coding:**
- Green: Positive trend (e.g., memory growth)
- Red: Negative trend (e.g., storage usage)
- Blue: Neutral information

**Variants:**
- **Small:** 200px width, value + trend
- **Medium:** 300px width, value + trend + sparkline
- **Large:** 400px width, value + trend + sparkline + breakdown

### 7. Status Indicators

**Purpose:** Show system health at a glance

**Design:**
- **Dot:** 8px diameter circle
- **Pulse:** Animated ring for "active" state
- **Label:** Text description next to dot

**States:**
- **Healthy:** Green dot, "All systems operational"
- **Warning:** Amber dot, "Some services degraded"
- **Error:** Red dot, "Service unavailable"
- **Loading:** Blue dot with spinner, "Checking..."

**Location:**
- Header: Global system status
- Database cards: Individual service status
- Agent cards: Agent health status

### 8. Modal / Dialog

**Purpose:** Focus user attention on specific task or information

**Structure:**
```
+--------------------------------------------------+
| [Close Icon]  Modal Title              [Actions] |
+--------------------------------------------------+
|                                                  |
|  Modal Content                                   |
|                                                  |
|  (scrollable if needed)                          |
|                                                  |
+--------------------------------------------------+
|                 [Cancel]  [Primary Action]       |
+--------------------------------------------------+
```

**Features:**
- **Backdrop:** Dark overlay with 60% opacity
- **Animation:** Fade in + scale up (300ms ease)
- **Focus Trap:** Keyboard focus stays within modal
- **Close On:** Click backdrop, press Escape, click close icon
- **Size:** Small (400px), Medium (600px), Large (800px), Full (90vw)

**Accessibility:**
- `role="dialog"` or `role="alertdialog"`
- `aria-modal="true"`
- `aria-labelledby` points to title
- Focus moves to first interactive element on open
- Focus returns to trigger element on close

### 9. Form Components

**Input Field:**
```
+----------------------------------------+
| Label (optional)                       |
| +----------------------------------+   |
| | Placeholder text...              |   |
| +----------------------------------+   |
|   Helper text (optional)               |
+----------------------------------------+
```

**States:**
- Default: Neutral border
- Focus: Brand color border, shadow
- Error: Red border, error message below
- Disabled: Muted background, no interactions
- Valid: Green border (optional validation feedback)

**Text Area:**
- Same as input but resizable
- Minimum height: 120px
- Auto-expand on content overflow

**Select Dropdown:**
```
+----------------------------------------+
| [Selected Option]          [Chevron]   |
+----------------------------------------+
|   v Dropdown Options                    |
|   - Option 1                           |
|   - Option 2 (selected)                |
|   - Option 3                           |
+----------------------------------------+
```

**Checkbox Group:**
```
+----------------------------------------+
| [x] Option 1                           |
| [ ] Option 2                           |
| [ ] Option 3                           |
+----------------------------------------+
```

**Radio Group:**
```
+----------------------------------------+
| ( ) Option 1                           |
| (*) Option 2                           |
| ( ) Option 3                           |
+----------------------------------------+
```

### 10. Toast Notifications

**Purpose:** Display temporary feedback for user actions

**Position:** Top-right or Top-center (stackable)

**Types:**
- **Success:** Green check icon, auto-dismiss after 5s
- **Error:** Red error icon, manual dismiss
- **Warning:** Amber warning icon, auto-dismiss after 7s
- **Info:** Blue info icon, auto-dismiss after 3s

**Animation:**
- Slide in from right (300ms ease)
- Fade out before dismiss (200ms ease)

**Actions:**
- Dismiss button (X icon)
- Optional action button (e.g., "Undo")

### 11. Loading States

**Skeleton Screens:**
- Gray placeholders matching content shape
- Shimmer animation (left-to-right gradient)
- Used for initial page loads

**Spinner:**
- 32px circular spinner
- Brand color stroke
- 60-degree rotation animation
- Used for button actions, modal loading

**Progress Bar:**
- Horizontal bar with percentage label
- Animated fill from left to right
- Used for file uploads, batch operations

**Inline Loading:**
- Small 16px spinner next to text
- Used for table actions, inline updates

---

## Visual Design System

### Color Palette

**Primary Colors (Dark Mode):**

```css
/* Backgrounds */
--bg-primary: #0f172a;      /* slate-900 - Main background */
--bg-secondary: #1e293b;    /* slate-800 - Cards, panels */
--bg-tertiary: #334155;     /* slate-700 - Elevated elements */
--bg-hover: #475569;        /* slate-600 - Hover states */

/* Text */
--text-primary: #f8fafc;    /* slate-50 - Primary text */
--text-secondary: #cbd5e1;  /* slate-300 - Secondary text */
--text-muted: #64748b;      /* slate-500 - Muted text */
--text-inverse: #0f172a;    /* slate-900 - Text on brand bg */

/* Brand Colors */
--brand-primary: #3b82f6;   /* blue-500 - Primary actions */
--brand-hover: #2563eb;     /* blue-600 - Hover state */
--brand-light: #93c5fd;     /* blue-300 - Accents, highlights */

/* Semantic Colors */
--success: #10b981;         /* emerald-500 - Success, healthy */
--success-light: #6ee7b7;   /* emerald-300 - Success bg */
--warning: #f59e0b;         /* amber-500 - Warning, caution */
--warning-light: #fcd34d;   /* amber-300 - Warning bg */
--error: #ef4444;           /* red-500 - Error, danger */
--error-light: #fca5a5;     /* red-300 - Error bg */
--info: #06b6d4;            /* cyan-500 - Information */
--info-light: #67e8f9;      /* cyan-300 - Info bg */

/* Borders */
--border-default: #334155;  /* slate-700 - Default borders */
--border-subtle: #1e293b;   /* slate-800 - Subtle borders */
--border-focus: #3b82f6;    /* blue-500 - Focus rings */

/* Data Visualization */
--chart-1: #3b82f6;         /* blue-500 */
--chart-2: #10b981;         /* emerald-500 */
--chart-3: #f59e0b;         /* amber-500 */
--chart-4: #ef4444;         /* red-500 */
--chart-5: #8b5cf6;         /* violet-500 */
--chart-6: #06b6d4;         /* cyan-500 */
```

**Light Mode Variants:**
```css
/* Backgrounds */
--bg-primary: #ffffff;      /* White */
--bg-secondary: #f1f5f9;    /* slate-100 */
--bg-tertiary: #e2e8f0;     /* slate-200 */
--bg-hover: #cbd5e1;        /* slate-300 */

/* Text */
--text-primary: #0f172a;    /* slate-900 */
--text-secondary: #475569;  /* slate-600 */
--text-muted: #94a3b8;      /* slate-400 */

/* Other colors remain similar but adjusted for contrast */
```

### Typography

**Font Family:**
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
             Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
```

**Type Scale:**

| Name | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Display | 48px | 700 | 1.1 | Page titles (hero) |
| H1 | 36px | 700 | 1.2 | Main page headings |
| H2 | 30px | 600 | 1.3 | Section headings |
| H3 | 24px | 600 | 1.4 | Subsection headings |
| H4 | 20px | 600 | 1.5 | Card titles |
| Body Large | 18px | 400 | 1.6 | Lead paragraphs |
| Body | 16px | 400 | 1.6 | Body text |
| Body Small | 14px | 400 | 1.6 | Secondary text |
| Caption | 12px | 400 | 1.5 | Labels, captions |
| Overline | 12px | 600 | 1.5 | Uppercase labels |

**Font Weights:**
- Regular (400): Body text, descriptions
- Medium (500): Emphasized text, labels
- Semibold (600): Headings, important text
- Bold (700): Display text, strong emphasis

### Spacing System

**Scale:** Based on 4px base unit

```css
--space-0: 0;
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
--space-20: 80px;
--space-24: 96px;
```

**Usage Guidelines:**
- **Tight spacing (4-8px):** Related elements within a component
- **Normal spacing (16-24px):** Between components, padding
- **Loose spacing (32-48px):** Section separators
- **Extra loose (64px+):** Major page sections

### Border Radius

```css
--radius-sm: 4px;   /* Small elements: badges, tags */
--radius-md: 8px;   /* Buttons, inputs, cards */
--radius-lg: 12px;  /* Large cards, modals */
--radius-xl: 16px;  /* Hero sections, featured content */
--radius-full: 9999px; /* Pills, circles */
```

### Shadows

```css
/* Elevation system */
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1),
            0 2px 4px -2px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1),
            0 4px 6px -4px rgb(0 0 0 / 0.1);
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1),
            0 8px 10px -6px rgb(0 0 0 / 0.1);

/* Colored shadows for emphasis */
--shadow-brand: 0 4px 14px 0 rgb(59 130 246 / 0.39);
--shadow-success: 0 4px 14px 0 rgb(16 185 129 / 0.39);
--shadow-error: 0 4px 14px 0 rgb(239 68 68 / 0.39);
```

### Icons

**Icon Library:** Lucide React or Heroicons

**Specifications:**
- **Size:** 16px (small), 20px (default), 24px (large), 32px (extra large)
- **Stroke Width:** 2px (consistent across all icons)
- **Color:** Inherit from text color (use text utilities for colors)

**Usage Guidelines:**
- Use icons sparingly and meaningfully
- Pair icons with text labels for clarity
- Ensure icons have text alternatives for accessibility
- Maintain consistent visual weight

### Animations

**Duration:**
```css
--duration-fast: 150ms;     /* Hover states, simple transitions */
--duration-normal: 300ms;   /* Modal open, page transitions */
--duration-slow: 500ms;     /* Complex animations, page load */
```

**Easing:**
```css
--ease-in: cubic-bezier(0.4, 0, 1, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
```

**Common Animations:**

1. **Fade In:**
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

2. **Slide In From Right:**
```css
@keyframes slideInRight {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
```

3. **Scale In:**
```css
@keyframes scaleIn {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
```

4. **Spinner:**
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

**Reduced Motion:**
Respect `prefers-reduced-motion` media query:
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Data Visualization

### Chart Library

**Recommendation:** Recharts or Chart.js with React bindings

**Why Recharts:**
- Built for React
- Composable components
- Responsive by default
- Good TypeScript support
- Accessible (SVG-based)
- Lightweight (~50KB gzipped)

### Chart Types & Usage

#### 1. Line Chart

**Purpose:** Show trends over time

**Use Cases:**
- Memory growth over time
- Query performance metrics
- Agent activity trends

**Design:**
- Smooth curves (Bézier) or straight lines
- Multiple lines with legend
- Tooltip on hover
- Zoom on scroll (optional)
- Area fill below line (optional)

**Color Coding:**
- Use semantic colors when meaningful
- Use brand colors for emphasis
- Maintain accessible contrast

#### 2. Bar Chart

**Purpose:** Compare quantities across categories

**Use Cases:**
- Memory counts by category
- Agent performance comparison
- Storage usage by database

**Design:**
- Horizontal or vertical based on label length
- Grouped bars for comparison
- Stacked bars for composition
- Value labels on bars (if space permits)

#### 3. Area Chart

**Purpose:** Show volume over time with emphasis on magnitude

**Use Cases:**
- Total memory storage
- Cache hit/miss ratio over time
- Token usage trends

**Design:**
- Gradient fill (fading to transparent)
- Multiple overlapping areas
- Clear distinction between layers

#### 4. Pie / Donut Chart

**Purpose:** Show composition of whole

**Use Cases:**
- Memory distribution by type
- Agent load distribution
- Category breakdown

**Design:**
- Donut chart (preferred) for modern look
- Interactive legend (click to highlight)
- Percentage labels
- Max 7 categories (group small categories as "Other")

**Accessibility Warning:**
- Always provide data table alternative
- Don't rely solely on color

#### 5. Heatmap

**Purpose:** Show patterns in two-dimensional data

**Use Cases:**
- Agent activity by hour/day
- Memory access patterns
- Query performance matrix

**Design:**
- Color scale from light to dark
- Tooltip with exact values
- Clear axis labels
- Color legend

#### 6. Scatter Plot

**Purpose:** Show correlation between two variables

**Use Cases:**
- Memory age vs. relevance
- Query time vs. result count
- Agent activity vs. performance

**Design:**
- Semi-transparent points for density visibility
- Zoom and pan
- Tooltip on hover
- Trend line (optional)

### Graph Visualization (Knowledge Graph)

**Technology:** Cytoscape.js or react-force-graph-2d

**Visual Encoding:**

**Node Properties:**
- **Size:** Degree centrality (number of connections)
- **Color:** Entity type (Person, Organization, Concept, etc.)
- **Border:** Highlighted when selected
- **Label:** Entity name (show on hover or zoom)

**Edge Properties:**
- **Thickness:** Relationship strength
- **Color:** Relationship type
- **Style:** Solid (strong), Dashed (weak)
- **Label:** Relationship type (optional, show on hover)

**Layout Options:**
1. **Force-Directed:** Default, good for exploration
2. **Hierarchical:** For tree-like structures
3. **Circular:** For comparing categories
4. **Concentric:** Center around key entity

**Interactions:**
- **Drag Nodes:** Reposition temporarily
- **Click Node:** Highlight connections, show details
- **Hover Node:** Highlight neighbors, dim others
- **Zoom/Pan:** Mouse wheel, drag canvas
- **Select Multiple:** Shift+click or drag selection box

**Performance:**
- Virtual rendering for > 1000 nodes
- Level-of-detail based on zoom (hide labels when zoomed out)
- Progressive loading (edges load after nodes)
- Web worker for layout calculation

### Timeline Visualization

**Technology:** Custom D3.js or Vis.js Timeline

**Design:**

**Time Axis:**
- Horizontal orientation (desktop)
- Vertical orientation (mobile, optional)
- Granularity: Day, Week, Month, Year
- Tick marks and labels

**Memory Markers:**
- **Position:** On timeline based on timestamp
- **Size:** Based on importance (relevance, connections)
- **Color:** Based on category
- **Shape:** Circle (default), Diamond (selected)
- **Cluster:** Stack nearby memories with count badge

**Interactions:**
- **Drag:** Pan timeline
- **Scroll/Pinch:** Zoom in/out
- **Click Marker:** Show memory details (modal or side panel)
- **Hover:** Quick preview (tooltip)

**Grouping:**
- By category (color-coded)
- By agent (grouped rows)
- By type (different marker shapes)

### Statistics Dashboard

**Layout:** Grid-based responsive layout

**Components:**

1. **KPI Cards (Top Row)**
   - 4 cards in a row (desktop)
   - 2 cards per row (tablet)
   - 1 card per row (mobile)
   - Each card: Value, trend, sparkline

2. **Main Chart (Middle)**
   - Line chart: Memory growth over time
   - Height: 400px (desktop), 300px (mobile)
   - Time range selector: Day, Week, Month, Year, All

3. **Secondary Charts (Bottom)**
   - 2 columns (desktop), 1 column (mobile)
   - Left: Bar chart (memories by category)
   - Right: Donut chart (agent distribution)

4. **Recent Activity (Side Panel)**
   - List of recent memories
   - Timestamp, summary, agent
   - Max 10 items, link to full list

**Real-Time Updates:**
- WebSocket connection for live data
- Optimistic updates for better UX
- Debounced updates to avoid flickering

---

## User Flows

### Flow 1: View Memory Details

**Entry Points:**
- Dashboard > Recent Memories > Click memory
- Memories List > Click memory card
- Search Results > Click result
- Timeline > Click memory marker

**Steps:**

1. **User clicks on memory**
   - Show loading skeleton
   - Fetch memory data via API
   - Navigate to detail page (or open modal)

2. **Display memory detail**
   - **Header:** Memory ID, timestamp, category badges
   - **Content:** Full memory text with formatting
   - **Metadata:** Agent ID, embedding vector (collapsible), relationships
   - **Actions:** Edit, Delete, Share, Export, Copy to clipboard

3. **Show related memories**
   - Section: "Related Memories"
   - List memories with high similarity
   - Click to navigate to related memory

4. **Show graph context**
   - Mini graph visualization
   - Highlight this memory's connections
   - Click to expand in full graph view

**Navigation Options:**
- Back button (browser history)
- Breadcrumb navigation
- Sidebar navigation
- Close button (if modal)

### Flow 2: Search Memories

**Entry Points:**
- Sidebar > Search
- Header > Global search
- Keyboard shortcut (Cmd/Ctrl + K)

**Steps:**

1. **Open search interface**
   - Focus search input
   - Show recent searches (if any)
   - Show search tips (first-time users)

2. **Enter search query**
   - Autocomplete suggestions from history
   - Search-as-you-type (debounced 300ms)
   - Show loading indicator

3. **View results**
   - Sort by relevance (default)
   - Show result count + search time
   - Highlight matching terms in snippets

4. **Refine search**
   - Click "Advanced Search" toggle
   - Apply filters: category, date range, agent, min relevance
   - Update results in real-time

5. **Select result**
   - Click result to view detail
   - Keyboard navigation: Arrow keys + Enter
   - Open in new tab (Ctrl/Cmd + Click)

**Exit Options:**
- Clear search button
- Escape key closes search (if modal)
- Navigate away via sidebar

### Flow 3: Add New Memory

**Entry Points:**
- Dashboard > Quick Actions > Add Memory
- Memories List > Add Button (+)
- Command palette: "Add memory"

**Steps:**

1. **Open add memory modal**
   - Textarea for memory content
   - Optional fields: category, agent ID, metadata
   - Character count (optional)

2. **Enter memory content**
   - Markdown support (optional)
   - Live preview (if markdown enabled)
   - Validation: min 10 chars, max 10,000 chars

3. **Select category (optional)**
   - Dropdown with dynamic categories
   - Or create new category

4. **Add metadata (optional)**
   - Key-value pairs
   - JSON editor for advanced users

5. **Submit**
   - Validate input
   - Show loading state
   - Call API to add memory
   - Show success toast
   - Close modal

6. **Confirmation**
   - Navigate to new memory detail (optional)
   - Or return to previous view

**Error Handling:**
- Validation errors: Inline messages
- Network errors: Toast notification
- Duplicate detection: Warn user, offer to merge

### Flow 4: Export Memories

**Entry Points:**
- Memories List > Export Button
- Memory Detail > Export
- Settings > Data Management > Export

**Steps:**

1. **Open export modal**
   - Format selection: JSON, CSV, XML
   - Filter options: date range, category, agent
   - Preview: Count of memories to export

2. **Select format**
   - JSON: Full data with metadata
   - CSV: Tabular format, limited fields
   - XML: Structured format

3. **Apply filters (optional)**
   - Date range picker
   - Category multi-select
   - Agent multi-select

4. **Preview export**
   - Show count of memories
   - Estimated file size
   - Warning if > 10,000 memories

5. **Generate export**
   - Show progress bar
   - Generate file on server
   - Download file when ready

6. **Completion**
   - Success toast with download link
   - Option to save export settings

**Background Jobs:**
- Large exports (> 10,000 memories): Run in background
- Notify user when ready via toast or email

### Flow 5: Configure Categories

**Entry Points:**
- Settings > Categories
- Dashboard > Quick Setup (first-time users)

**Steps:**

1. **View categories**
   - List all configured categories
   - Show prefix, description, memory count
   - Edit/delete buttons for each

2. **Add new category**
   - Click "Add Category" button
   - Form: Name, prefix, description
   - Validation: Unique name, valid prefix format

3. **Edit category**
   - Click edit icon on category card
   - Update fields
   - Save changes

4. **Delete category**
   - Click delete icon
   - Confirmation modal: "Memories in this category will become uncategorized"
   - Confirm deletion

5. **Save configuration**
   - Save to `.enhanced-cognee-config.json`
   - Show success toast
   - Refresh affected views

**Validation:**
- Category name: alphanumeric, spaces, hyphens
- Prefix: alphanumeric + underscore, must end with underscore
- Description: max 200 chars

---

## Responsive Design

### Breakpoints

```css
/* Mobile First Approach */
--bp-xs: 375px;   /* Small phones */
--bp-sm: 640px;   /* Large phones, portrait tablets */
--bp-md: 768px;   /* Tablets, landscape */
--bp-lg: 1024px;  /* Small laptops, large tablets */
--bp-xl: 1280px;  /* Desktops */
--bp-2xl: 1536px; /* Large desktops */
```

### Layout Adaptations

#### Mobile (< 768px)

**Navigation:**
- Bottom navigation bar (48px height)
- 5 primary items, rest in "More" menu
- Hamburger menu for settings, developer tools

**Content:**
- Single column layout
- Full-width cards
- Stacked form fields
- Horizontal scroll for tab navigation

**Typography:**
- Base font size: 16px (minimum readable size)
- H1: 28px (reduced from 36px)
- H2: 24px (reduced from 30px)

**Spacing:**
- Reduced padding: 12-16px
- Tighter spacing between sections

**Components:**
- Tables: Horizontal scroll or card view
- Charts: Simplified, hide legends in drawer
- Graph: Read-only, hide advanced controls
- Modals: Full-screen (90vw)

#### Tablet (768px - 1024px)

**Navigation:**
- Left sidebar (icon-only by default)
- Expand on hover
- Bottom navigation not used

**Content:**
- 2-column grid where appropriate
- Side-by-side form fields (label + input)
- Tab navigation: horizontal scroll

**Components:**
- Tables: Show 5-6 columns, scroll for rest
- Charts: Full legends visible
- Graph: Basic controls visible

#### Desktop (> 1024px)

**Navigation:**
- Left sidebar (expanded by default)
- All navigation items visible
- Collapse to icon-only available

**Content:**
- 3-column grid maximum
- Optimal reading width: 65-75 characters per line
- Side-by-side panels (e.g., list + detail)

**Components:**
- All columns in tables visible
- Full interactivity in all visualizations
- Keyboard shortcuts available

### Touch Targets

**Minimum Size:** 44x44px (WCAG AAA standard)

**Implementation:**
- Buttons: Min height 44px, padding 12px
- Links: Inline text or block with padding
- Icons: In 44x44px container
- Form inputs: Min height 44px
- Checkboxes/Radios: Scale to 44px tap area

### Responsive Images

**Technique:** `srcset` attribute with sizes

```html
<img
  src="image-320w.jpg"
  srcset="image-320w.jpg 320w,
          image-640w.jpg 640w,
          image-1280w.jpg 1280w"
  sizes="(max-width: 768px) 100vw,
         (max-width: 1024px) 50vw,
         33vw"
  alt="Descriptive text"
/>
```

---

## Accessibility

### WCAG 2.1 AA Compliance

#### Color Contrast

**Minimum Contrast Ratios:**
- Normal text (< 18px): 4.5:1
- Large text (18px+ or 14px bold): 3:1
- UI components: 3:1
- Graphical objects: 3:1

**Verification:**
- Use automated tools: axe DevTools, WAVE
- Manual testing with color blindness simulators
- Test in grayscale mode

#### Keyboard Navigation

**Tab Order:** Logical, follows visual layout

**Focus Indicators:**
- Visible 2px outline in brand color
- Never remove outline (use `outline: none` only if replacing with custom indicator)
- Skip links for main content

**Keyboard Shortcuts:**

| Shortcut | Action |
|----------|--------|
| Tab / Shift+Tab | Navigate forward/backward |
| Enter / Space | Activate buttons, links |
| Escape | Close modals, clear search |
| Arrow Keys | Navigate lists, grids |
| Home / End | Jump to start/end of list |
| Page Up/Down | Scroll by page |
| Cmd/Ctrl + K | Open search |
| Cmd/Ctrl + / | Open keyboard shortcuts modal |

#### Screen Reader Support

**Semantic HTML:**
- Use proper heading hierarchy (h1 > h2 > h3)
- Use landmark roles: `role="main"`, `role="navigation"`, etc.
- Use ARIA labels for interactive elements without text
- Use `aria-live` regions for dynamic content

**Example:**
```html
<button aria-label="Close modal">
  <CloseIcon />
</button>

<div role="status" aria-live="polite">
  {toastMessage}
</div>
```

#### Alt Text for Images

**Guidelines:**
- Decorative images: `alt=""` (empty)
- Informative images: Concise description of content
- Functional images: Describe function, not appearance
- Complex images: Use longdesc or adjacent text

#### Form Accessibility

**Labels:**
- Every input has a visible label or `aria-label`
- `for` attribute matches input `id`

**Error Messages:**
- `aria-invalid="true"` on invalid inputs
- `aria-describedby` links to error message
- Error messages announced to screen readers

**Example:**
```html
<label for="email">Email</label>
<input
  id="email"
  type="email"
  aria-invalid={hasError}
  aria-describedby={hasError ? "email-error" : undefined}
/>
{hasError && (
  <span id="email-error" role="alert">
    Please enter a valid email address
  </span>
)}
```

#### Focus Management

**Modals:**
- Focus trap: Tab stays within modal
- Initial focus: First interactive element
- Return focus: Element that opened modal

**Dynamic Content:**
- Announce changes to screen readers
- `aria-live="polite"` for updates
- `aria-live="assertive"` for critical errors

### Testing Checklist

- [ ] All functionality available via keyboard
- [ ] Focus visible at all times
- [ ] Tab order logical
- [ ] Skip links work
- [ ] Forms have labels
- [ ] Error messages announced
- [ ] Color contrast meets WCAG AA
- [ ] Images have alt text
- [ ] Screen reader testing (NVDA, JAWS, VoiceOver)
- [ ] Zoom testing (200% magnification)

---

## Technical Implementation

### Technology Stack

**Frontend Framework:**
- Next.js 14 (App Router)
- React 19
- TypeScript 5

**UI Component Library:**
- Tailwind CSS 4.x (utility-first CSS)
- Headless UI or Radix UI (accessible primitives)
- Or custom components with Tailwind

**Data Visualization:**
- Recharts (charts)
- Cytoscape.js or react-force-graph-2d (knowledge graph)
- D3.js (custom visualizations, timelines)

**State Management:**
- React Query (server state)
- Zustand or Jotai (client state)
- React Context (global theme, auth)

**Forms:**
- React Hook Form (performance, validation)
- Zod (schema validation)

**Icons:**
- Lucide React (lightweight, consistent)

### Project Structure

```
cognee-frontend/
├── src/
│   ├── app/                          # Next.js app router
│   │   ├── (auth)/                   # Auth layout group
│   │   │   ├── login/
│   │   │   └── signup/
│   │   ├── dashboard/                # Dashboard pages
│   │   │   ├── page.tsx              # Dashboard overview
│   │   │   └── layout.tsx            # Dashboard layout
│   │   ├── memories/                 # Memory pages
│   │   │   ├── page.tsx              # Memory list
│   │   │   ├── [id]/                 # Memory detail
│   │   │   │   └── page.tsx
│   │   │   ├── timeline/
│   │   │   └── graph/
│   │   ├── search/                   # Search pages
│   │   │   ├── page.tsx              # Search interface
│   │   │   └── [query]/              # Search results (optional)
│   │   ├── sessions/                 # Session pages
│   │   ├── analytics/                # Analytics pages
│   │   │   ├── page.tsx              # Analytics overview
│   │   │   ├── memory-growth/
│   │   │   ├── token-efficiency/
│   │   │   └── agent-activity/
│   │   ├── agents/                   # Agent pages
│   │   ├── settings/                 # Settings pages
│   │   └── developer/                # Developer tools
│   │       ├── api-docs/
│   │       ├── mcp-tester/
│   │       ├── db-inspector/
│   │       └── query-analyzer/
│   │   ├── layout.tsx                # Root layout
│   │   └── page.tsx                  # Home page
│   │
│   ├── components/                   # React components
│   │   ├── ui/                       # Base UI components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── modal.tsx
│   │   │   ├── table.tsx
│   │   │   └── ...
│   │   ├── layout/                   # Layout components
│   │   │   ├── header.tsx
│   │   │   ├── sidebar.tsx
│   │   │   ├── footer.tsx
│   │   │   └── bottom-nav.tsx
│   │   ├── features/                 # Feature-specific components
│   │   │   ├── memories/
│   │   │   │   ├── memory-card.tsx
│   │   │   │   ├── memory-list.tsx
│   │   │   │   ├── memory-timeline.tsx
│   │   │   │   └── memory-graph.tsx
│   │   │   ├── search/
│   │   │   │   ├── search-bar.tsx
│   │   │   │   ├── advanced-search.tsx
│   │   │   │   └── search-results.tsx
│   │   │   ├── analytics/
│   │   │   │   ├── stat-card.tsx
│   │   │   │   ├── charts/
│   │   │   │   └── dashboard.tsx
│   │   │   └── sessions/
│   │   ├── graphs/                   # Graph visualizations
│   │   └── visualizations/           # Data visualizations
│   │
│   ├── lib/                          # Utilities
│   │   ├── api/                      # API client
│   │   │   ├── client.ts             # Base client setup
│   │   │   ├── memories.ts           # Memory endpoints
│   │   │   ├── search.ts             # Search endpoints
│   │   │   ├── analytics.ts          # Analytics endpoints
│   │   │   └── agents.ts             # Agent endpoints
│   │   ├── hooks/                    # Custom React hooks
│   │   │   ├── useMemories.ts
│   │   │   ├── useSearch.ts
│   │   │   ├── useAnalytics.ts
│   │   │   └── useDebounce.ts
│   │   ├── utils/                    # Helper functions
│   │   │   ├── format.ts             # Date, number formatting
│   │   │   ├── validation.ts         # Input validation
│   │   │   └── color.ts              # Color utilities
│   │   └── constants.ts              # App constants
│   │
│   ├── styles/                       # Global styles
│   │   ├── globals.css               # Tailwind imports, custom styles
│   │   └── tailwind.css              # Tailwind directives
│   │
│   └── types/                        # TypeScript types
│       ├── api.ts                    # API response types
│       ├── memory.ts                 # Memory types
│       ├── analytics.ts              # Analytics types
│       └── agent.ts                  # Agent types
│
├── public/                           # Static assets
│   ├── icons/                        # Custom icons
│   └── images/                       # Images
│
├── tailwind.config.ts                # Tailwind configuration
├── tsconfig.json                     # TypeScript configuration
├── next.config.js                    # Next.js configuration
└── package.json                      # Dependencies
```

### API Integration

**Base URL Configuration:**
```typescript
// lib/api/client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

**Example API Endpoints:**
```typescript
// lib/api/memories.ts
export interface Memory {
  id: string;
  content: string;
  category: string;
  agent_id: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

export async function getMemories(params?: {
  category?: string;
  agent_id?: string;
  limit?: number;
  offset?: number;
}): Promise<Memory[]> {
  const response = await apiClient.get('/api/v1/memories', { params });
  return response.data;
}

export async function getMemory(id: string): Promise<Memory> {
  const response = await apiClient.get(`/api/v1/memories/${id}`);
  return response.data;
}

export async function createMemory(data: {
  content: string;
  category?: string;
  metadata?: Record<string, unknown>;
}): Promise<Memory> {
  const response = await apiClient.post('/api/v1/memories', data);
  return response.data;
}
```

### State Management with React Query

**Setup:**
```typescript
// app/providers.tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      cacheTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

**Usage:**
```typescript
// components/features/memories/memory-list.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getMemories } from '@/lib/api/memories';

export function MemoryList() {
  const { data: memories, isLoading, error } = useQuery({
    queryKey: ['memories'],
    queryFn: () => getMemories({ limit: 50 }),
  });

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div>
      {memories?.map(memory => (
        <MemoryCard key={memory.id} memory={memory} />
      ))}
    </div>
  );
}
```

### Performance Optimization

**Code Splitting:**
```typescript
// Dynamic imports for heavy components
const GraphVisualization = dynamic(
  () => import('@/components/features/memories/memory-graph'),
  { loading: () => <LoadingSpinner /> }
);
```

**Image Optimization:**
```typescript
import Image from 'next/image';

<Image
  src="/logo.png"
  alt="Enhanced Cognee"
  width={200}
  height={50}
  priority // For above-the-fold images
/>
```

**Virtual Scrolling:**
```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

function MemoryList({ memories }: { memories: Memory[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: memories.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100, // Estimated row height
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map(virtualItem => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <MemoryCard memory={memories[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Testing

**Unit Tests:**
```typescript
// components/ui/__tests__/button.test.tsx
import { render, screen } from '@testing-library/react';
import { Button } from '../button';

describe('Button', () => {
  it('renders children correctly', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    screen.getByText('Click me').click();
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

**E2E Tests:**
```typescript
// e2e/memory-flow.spec.ts
import { test, expect } from '@playwright/test';

test('add and view memory', async ({ page }) => {
  await page.goto('/dashboard');

  // Click add memory button
  await page.click('[data-testid="add-memory-button"]');

  // Fill form
  await page.fill('[data-testid="memory-content"]', 'Test memory content');
  await page.selectOption('[data-testid="memory-category"]', 'trading');

  // Submit
  await page.click('[data-testid="submit-memory"]');

  // Verify success
  await expect(page.locator('[data-testid="toast-success"]')).toBeVisible();

  // Navigate to memories list
  await page.goto('/memories');
  await expect(page.locator('text=Test memory content')).toBeVisible();
});
```

---

## Design Deliverables

### Design Artifacts (Recommended)

1. **Wireframes**
   - Low-fidelity sketches for each major view
   - Focus on layout and information hierarchy

2. **Mockups**
   - High-fidelity designs for key screens
   - Desktop, tablet, and mobile versions

3. **Prototype**
   - Interactive prototype using Figma or similar
   - Test user flows before development

4. **Component Library**
   - Document all reusable components
   - Include variants, states, and usage guidelines

5. **Style Guide**
   - Colors, typography, spacing, icons
   - Animation and transition specifications

### Developer Handoff

**Provide:**
- Design files (Figma link or export)
- Component specifications (props, variants)
- Assets (icons, images, logos)
- Token files (design tokens for CSS variables)
- Interactive prototype for reference

**Documentation:**
- This UX/UI specification document
- Component storybook (Storybook.js)
- API documentation
- Accessibility checklist

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Setup:**
- [ ] Initialize Next.js 14 project with TypeScript
- [ ] Configure Tailwind CSS
- [ ] Setup component library (Headless UI or Radix UI)
- [ ] Configure ESLint, Prettier
- [ ] Setup Git repository and CI/CD

**Base Components:**
- [ ] Button (variants: primary, secondary, ghost, danger)
- [ ] Input (text, textarea, select, checkbox, radio)
- [ ] Modal/Dialog
- [ ] Toast notifications
- [ ] Loading states (spinner, skeleton)

**Layout:**
- [ ] Header with global search
- [ ] Sidebar navigation
- [ ] Bottom navigation (mobile)
- [ ] Footer

### Phase 2: Core Features (Week 3-5)

**Memories:**
- [ ] Memory list view (with filtering, sorting, pagination)
- [ ] Memory detail view
- [ ] Add memory modal/form
- [ ] Edit memory functionality
- [ ] Delete memory with confirmation

**Search:**
- [ ] Simple search interface
- [ ] Advanced search with filters
- [ ] Search results with relevance scores
- [ ] Search history

**Sessions:**
- [ ] Session list (grouped by agent)
- [ ] Session timeline view
- [ ] Session detail with memory breakdown

### Phase 3: Visualization (Week 6-7)

**Timeline:**
- [ ] Timeline visualization component
- [ ] Zoom and pan controls
- [ ] Memory markers with tooltips
- [ ] Group by day/week/month

**Knowledge Graph:**
- [ ] Graph visualization (Cytoscape.js or react-force-graph)
- [ ] Node and edge styling
- [ ] Interactive features (zoom, pan, click, hover)
- [ ] Layout options

**Charts:**
- [ ] Line charts (trends over time)
- [ ] Bar charts (comparisons)
- [ ] Donut/Pie charts (composition)
- [ ] Stat cards with sparklines

### Phase 4: Analytics & Agents (Week 8)

**Analytics Dashboard:**
- [ ] Overview dashboard with KPIs
- [ ] Memory growth chart
- [ ] Token efficiency metrics
- [ ] Agent activity visualization
- [ ] Performance metrics (query times, cache hits)
- [ ] Deduplication statistics

**Agents:**
- [ ] Agent list with status indicators
- [ ] Agent detail view
- [ ] Real-time coordination view
- [ ] Agent performance metrics

### Phase 5: Settings & Developer Tools (Week 9)

**Settings:**
- [ ] General settings (theme, language)
- [ ] Category management (CRUD)
- [ ] Data management (export, import, archival)
- [ ] Sharing policies configuration
- [ ] API key management

**Developer Tools:**
- [ ] API documentation viewer
- [ ] MCP tool testing interface
- [ ] Database inspector
- [ ] Query performance analyzer
- [ ] System log viewer

### Phase 6: Polish & Launch (Week 10)

**Testing:**
- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)
- [ ] Device testing (iOS, Android, desktop)
- [ ] Accessibility audit (axe DevTools)
- [ ] Performance optimization (Lighthouse)
- [ ] Security audit

**Documentation:**
- [ ] User guide
- [ ] Admin guide
- [ ] API documentation
- [ ] Component documentation (Storybook)

**Launch:**
- [ ] Production deployment
- [ ] Monitoring setup (Sentry, Analytics)
- [ ] User onboarding flow
- [ ] Feedback mechanism

---

## Appendix

### Recommended UI Component Libraries

**Option 1: Headless UI + Tailwind CSS**
- **Pros:** Fully customizable, accessible, lightweight
- **Cons:** Requires more custom styling
- **Best for:** Complete design control, unique brand identity

**Option 2: Radix UI + Tailwind CSS**
- **Pros:** Comprehensive primitives, accessible, unstyled
- **Cons:** More components to assemble
- **Best for:** Complex interfaces, accessibility first

**Option 3: shadcn/ui**
- **Pros:** Copy-paste components, fully customizable, modern design
- **Cons:** Requires manual updates
- **Best for:** Rapid development with design control

**Option 4: Chakra UI**
- **Pros:** Feature-complete, accessible, theming built-in
- **Cons:** Larger bundle size, harder to customize deeply
- **Best for:** Fast development, consistent design system

**Recommendation:** shadcn/ui or Radix UI + Tailwind CSS for optimal balance of customization, accessibility, and development speed.

### Design Tools

**Figma:**
- UI design
- Prototyping
- Component variants
- Developer handoff

**Framer Motion:**
- Advanced animations
- Gesture interactions
- Page transitions

**Storybook:**
- Component development
- Component documentation
- Design system preview

### Accessibility Tools

**axe DevTools:** Browser extension for accessibility testing

**WAVE:** Web accessibility evaluation tool

**NVDA / JAWS:** Screen reader testing (Windows)

**VoiceOver:** Screen reader testing (macOS/iOS)

**Keyboard Only:** Unplug mouse and test full functionality

### Performance Tools

**Lighthouse:** Page speed, accessibility, best practices

**WebPageTest:** Detailed performance analysis

**React DevTools Profiler:** Component performance

**Bundle Analyzer:** Webpack bundle size analysis

### References & Inspiration

**Design Systems:**
- [Material Design 3](https://m3.material.io/)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Atlassian Design System](https://atlassian.design/)
- [Carbon Design System (IBM)](https://carbondesignsystem.com/)

**Data Visualization:**
- [Data Visualization Society](https://datavisualizationsociety.com/)
- [D3.js Gallery](https://gallery.d3js.org/)
- [Observable](https://observablehq.com/)

**Accessibility:**
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [A11y Project](https://www.a11yproject.com/)
- [WebAIM](https://webaim.org/)

---

**Document Version:** 1.0.0
**Last Updated:** 2025-02-06
**Authors:** UX/UI Design Specification for Enhanced Cognee Memory Dashboard
**Status:** Ready for Implementation

---

## Next Steps

1. **Review this specification** with stakeholders and development team
2. **Create wireframes** for each major view based on this spec
3. **Build prototype** for user testing
4. **Begin Phase 1** of implementation roadmap
5. **Iterate** based on feedback and testing results

For questions or clarifications about this specification, please refer to the Enhanced Cognee project documentation or create an issue in the project repository.
