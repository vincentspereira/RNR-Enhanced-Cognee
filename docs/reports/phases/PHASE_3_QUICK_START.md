# Phase 3 Visualizations - Quick Start Guide

**Enhanced Cognee Dashboard - Data Visualization Features**

---

## Overview

Phase 3 adds comprehensive data visualization capabilities to the Enhanced Cognee Dashboard. This guide helps you get started with the new features.

---

## New Pages & Routes

### 1. Timeline View
**URL:** `/memories/timeline`

**Features:**
- Chronological memory visualization
- Zoom levels: Day, Week, Month, Year, All Time
- Filter by memory type (bugfix, feature, decision, etc.)
- Pan left/right through time
- Click memories to view details
- Export timeline as PNG

**How to Use:**
1. Navigate to Memories > Timeline in the sidebar
2. Use zoom controls to change time range
3. Click memory type buttons to filter
4. Pan through time using arrow buttons
5. Click on any memory bar to view details

---

### 2. Knowledge Graph
**URL:** `/memories/graph`

**Features:**
- Interactive Neo4j graph visualization
- Force-directed, hierarchical, circle, and concentric layouts
- Node search and filtering by type
- Click nodes to view details
- Zoom and pan interactions
- Export as PNG

**How to Use:**
1. Navigate to Memories > Graph in the sidebar
2. Search for nodes using the search bar
3. Filter by node type using the dropdown
4. Change layout using the layout selector
5. Click on any node to view its details in the sidebar
6. Drag nodes to reposition
7. Use zoom controls or mouse wheel to zoom in/out

---

### 3. Analytics Dashboard
**URL:** `/analytics`

**Features:**
- KPI cards with trends
- Memory growth chart
- Memory type distribution
- Agent activity visualization
- Token usage trends
- Database health status
- Real-time updates

**How to Use:**
1. Navigate to Analytics in the sidebar
2. View KPI cards at the top for quick stats
3. Explore charts below for detailed insights
4. Database status shown at bottom
5. Data auto-refreshes every 30-60 seconds

---

### 4. Activity Heatmap
**URL:** `/analytics/activity`

**Features:**
- GitHub-style contribution graph
- 365 days of activity
- Color-coded activity levels
- Click days to view memories
- Filter by agent

**How to Use:**
1. Navigate to Analytics > Activity in the sidebar
2. View your activity pattern over the last year
3. Hover over cells to see activity count
4. Click on any colored cell to view that day's memories
5. Scroll horizontally on mobile to see full year

---

### 5. Sessions Timeline
**URL:** `/sessions`

**Features:**
- List of all sessions
- Session timeline with memory breakdown
- Duration badges
- Memory counts per session
- Expandable session details

**How to Use:**
1. Navigate to Sessions in the sidebar
2. Browse session list on the left
3. Click on a session to view its timeline
4. Timeline shows memories chronologically
5. Click on memories to view details

---

## Visualization Settings

### Access Settings
Settings are available from any visualization page:

**Location:** Click the gear icon (Settings) in the top-right of any chart

### Settings Options

**Theme:**
- Color Scheme: Default, Vibrant, Pastel, Monochrome
- Theme: Dark, Light

**Charts:**
- Default Chart Type: Line, Bar, Pie
- Enable Animations: On/Off
- Data Density: Compact, Comfortable, Spacious

**Export:**
- Default Format: PNG, SVG, PDF
- Export Quality: Low, Medium, High

**Persistence:** Settings are saved to localStorage and persist across sessions

---

## Exporting Charts

### Export Options

All charts support export to multiple formats:

**PNG (Raster Image):**
- Best for: Presentations, documents, web
- Quality: High (2x scale by default)
- Transparent background option

**SVG (Vector Graphics):**
- Best for: Print, scaling without quality loss
- Editable in vector editors (Illustrator, Inkscape)
- Smaller file size for simple charts

**PDF (Document):**
- Best for: Reports, printing
- Multiple pages supported
- High quality

### How to Export

1. Locate the Export button on any chart
2. Click the Export button (usually top-right of chart)
3. Select format (PNG, SVG, PDF)
4. File downloads automatically

**Batch Export:** Some pages support exporting all charts at once as a single PDF.

---

## Keyboard Shortcuts

### Navigation
- `Cmd/Ctrl + K` - Quick search
- `Cmd/Ctrl + /` - Keyboard shortcuts help
- `Esc` - Close modals/panels

### Graph Interactions
- `Mouse Wheel` - Zoom in/out
- `Click + Drag` - Pan around graph
- `Click Node` - Select node
- `Double Click Node` - Expand/collapse connections

### Timeline
- `Arrow Keys` - Navigate between time periods
- `+` - Zoom in
- `-` - Zoom out

---

## Tips & Tricks

### Performance
- **Large Datasets:** Graph visualization performs best with <1000 nodes
- **Mobile:** Use compact data density setting for better performance
- **Cache:** Charts cache data for 5-10 minutes to improve performance

### Customization
- **Colors:** Change color scheme in Settings to match your preference
- **Density:** Use "Compact" mode to see more data at once
- **Animations:** Disable animations on slower devices

### Data Exploration
- **Timeline:** Use "All Time" zoom to see entire memory history
- **Graph:** Search for specific concepts to find related memories
- **Heatmap:** Look for patterns in your activity (e.g., more active on weekdays)
- **Analytics:** Monitor token efficiency trends to optimize memory usage

---

## Troubleshooting

### Graph Not Loading
**Problem:** Knowledge graph shows "No data"

**Solutions:**
1. Check Neo4j database connection: `/health` endpoint
2. Ensure Neo4j has data (migrations run?)
3. Check browser console for errors
4. Try refreshing the page

### Timeline Empty
**Problem:** Timeline shows no memories

**Solutions:**
1. Check if memories exist in database
2. Try changing zoom level to "All Time"
3. Clear filters (select all memory types)
4. Check date range (pan to different time period)

### Export Fails
**Problem:** Export button doesn't work

**Solutions:**
1. Check browser permissions (downloading files)
2. Try a different export format
3. Check browser console for errors
4. Ensure sufficient disk space

### Slow Performance
**Problem:** Visualizations are slow/laggy

**Solutions:**
1. Reduce data density in Settings
2. Disable animations
3. Use zoom to show less data at once
4. Close other browser tabs
5. Check system resources

---

## API Integration

### Backend Endpoints

The dashboard connects to these backend endpoints:

```typescript
// Graph data
GET /api/graph              // Get Neo4j graph
GET /api/graph/node/{id}    // Get node neighbors
GET /api/graph/search       // Search nodes
GET /api/graph/stats        // Graph statistics

// Analytics
GET /api/stats              // System statistics
GET /api/structured-stats   // Memory type stats
GET /api/activity           // Activity data

// Sessions
GET /api/sessions           // List sessions
GET /api/sessions/{id}      // Session details

// Timeline
GET /api/timeline/{id}      // Memory timeline context
```

### Custom Integration

To integrate these visualizations into your own application:

```typescript
import { TimelineView } from "@/components/organisms/TimelineView";
import { KnowledgeGraph } from "@/components/organisms/KnowledgeGraph";
import { AnalyticsDashboard } from "@/components/organisms/AnalyticsDashboard";

// Use in your components
<TimelineView memories={myMemories} />
<KnowledgeGraph onNodeClick={(id) => console.log(id)} />
<AnalyticsDashboard />
```

---

## Getting Help

### Documentation
- Main README: `README.md`
- UX/UI Spec: `docs/UX_UI_SPECIFICATION.md`
- Wireframes: `docs/UX_UI_WIREFRAMES.md`
- Phase 3 Report: `PHASE_3_COMPLETION_REPORT.md`

### Issues
- Report bugs: Create GitHub issue
- Feature requests: Create GitHub issue with "enhancement" label
- Questions: Check existing issues or discussions

---

## What's Next?

**Phase 4** will include:
- Advanced filtering and search
- Real-time collaboration features
- Custom dashboard builder
- Advanced graph analytics
- Memory deduplication visualization
- Performance optimization dashboard

Stay tuned for more features!

---

**Last Updated:** February 6, 2026
**Version:** 1.0.0
