# Enhanced Cognee Dashboard

**Version:** 1.0.0
**Status:** Phase 1 Foundation (Complete)

Enterprise-grade Next.js 14 dashboard for the Enhanced Cognee AI memory system.

## Overview

This dashboard provides a modern, responsive web interface for visualizing, managing, and analyzing memories in the Enhanced Cognee system. Built with Next.js 14 (App Router), TypeScript, Tailwind CSS, and TanStack Query.

## Features

### Phase 1 (Foundation) - Implemented

- [x] Next.js 14 project with App Router and TypeScript
- [x] Tailwind CSS 4.x with custom dark theme
- [x] Atomic component library (Button, Input, Card, Badge, Skeleton, etc.)
- [x] API client with error handling and interceptors
- [x] TanStack Query for server state management
- [x] Zustand for client state management
- [x] Layout components (Header, Sidebar)
- [x] Dashboard page with stats and recent activity
- [x] Memories list page with search and filtering
- [x] Sessions page
- [x] Analytics page with system stats
- [x] Responsive design (mobile, tablet, desktop)
- [x] Dark mode support
- [x] Testing setup with Vitest

### Upcoming Features (Phase 2+)

- [ ] Memory detail view
- [ ] Add/Edit memory modals
- [ ] Advanced search with filters
- [ ] Timeline visualization
- [ ] Knowledge graph visualization
- [ ] Agent management
- [ ] Settings and configuration
- [ ] Developer tools
- [ ] Real-time updates with SSE

## Tech Stack

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript 5
- **Styling:** Tailwind CSS 4.x
- **State Management:**
  - TanStack Query (React Query v5) - Server state
  - Zustand - Client state
- **Components:**
  - Radix UI - Accessible primitives
  - Lucide React - Icons
  - Custom atomic components
- **Forms:** React Hook Form + Zod
- **Data Visualization:** Recharts
- **Testing:** Vitest + Testing Library

### Backend API
- FastAPI (existing)
- PostgreSQL + Qdrant + Neo4j + Redis

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Enhanced Cognee backend API running on port 8000

### Installation

```bash
# Navigate to dashboard directory
cd dashboard/nextjs-dashboard

# Install dependencies
npm install
```

### Configuration

Create a `.env.local` file in the root directory:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

See `.env.local.example` for all available options.

### Development

```bash
# Start development server
npm run dev

# Open browser to http://localhost:9050
```

### Build

```bash
# Type check
npm run build

# Start production server
npm start
```

### Testing

```bash
# Run tests in watch mode
npm test

# Run tests once
npm run test:run

# Run tests with UI
npm run test:ui
```

## Project Structure

```
dashboard/nextjs-dashboard/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── dashboard/            # Dashboard page
│   │   ├── memories/             # Memories pages
│   │   ├── sessions/             # Sessions page
│   │   ├── analytics/            # Analytics page
│   │   ├── search/               # Search page (placeholder)
│   │   ├── agents/               # Agents page (placeholder)
│   │   ├── settings/             # Settings page (placeholder)
│   │   ├── developer/            # Developer tools (placeholder)
│   │   ├── layout.tsx            # Root layout
│   │   ├── page.tsx              # Home (redirects to dashboard)
│   │   ├── providers.tsx         # TanStack Query provider
│   │   └── globals.css           # Global styles
│   │
│   ├── components/               # React components
│   │   ├── atoms/                # Atomic components
│   │   │   ├── Button.tsx        # Button with variants
│   │   │   ├── Input.tsx         # Input component
│   │   │   ├── Badge.tsx         # Badge component
│   │   │   ├── Card.tsx          # Card components
│   │   │   ├── Skeleton.tsx      # Loading skeleton
│   │   │   ├── Spinner.tsx       # Loading spinner
│   │   │   ├── Textarea.tsx      # Textarea component
│   │   │   └── index.ts
│   │   │
│   │   └── layout/               # Layout components
│   │       ├── Header.tsx        # Top navigation header
│   │       ├── Sidebar.tsx       # Side navigation (collapsible)
│   │       └── index.ts
│   │
│   ├── lib/                      # Core libraries
│   │   ├── api/                  # API client
│   │   │   ├── client.ts         # Axios instance with interceptors
│   │   │   ├── types.ts          # API response types
│   │   │   ├── memories.ts       # Memory endpoints
│   │   │   ├── sessions.ts       # Session endpoints
│   │   │   ├── analytics.ts      # Analytics endpoints
│   │   │   └── index.ts
│   │   │
│   │   ├── query/                # TanStack Query setup
│   │   │   ├── queryClient.ts    # Query client factory
│   │   │   ├── queryKeys.ts      # Query keys factory
│   │   │   └── index.ts
│   │   │
│   │   ├── hooks/                # Custom React hooks
│   │   │   ├── useMemories.ts    # Memory hooks
│   │   │   ├── useSessions.ts    # Session hooks
│   │   │   ├── useAnalytics.ts   # Analytics hooks
│   │   │   └── index.ts
│   │   │
│   │   ├── stores/               # Zustand stores
│   │   │   ├── uiStore.ts        # UI state (sidebar, filters, etc.)
│   │   │   └── index.ts
│   │   │
│   │   └── utils.ts              # Utility functions (cn, formatDate, etc.)
│   │
│   └── config/                   # Configuration (future)
│
├── public/                       # Static assets
├── .env.local                    # Environment variables (not in git)
├── .env.local.example            # Environment variables template
├── next.config.ts                # Next.js configuration
├── tailwind.config.ts            # Tailwind CSS configuration
├── tsconfig.json                 # TypeScript configuration
├── vitest.config.ts              # Vitest configuration
├── vitest.setup.ts               # Vitest setup
└── package.json                  # Dependencies and scripts
```

## Component Usage Examples

### Button Component

```tsx
import { Button } from "@/components/atoms";

<Button variant="default" size="md" onClick={() => console.log("Clicked")}>
  Click Me
</Button>

<Button variant="destructive" size="sm">
  Delete
</Button>

<Button variant="outline" size="icon">
  <Icon />
</Button>
```

### Card Component

```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/atoms";

<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description goes here</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Card content</p>
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>
```

### Using API Hooks

```tsx
"use client";

import { useMemories, useCreateMemory } from "@/lib/hooks";

export function MyComponent() {
  const { data: memories, isLoading, error } = useMemories({ limit: 10 });
  const createMutation = useCreateMemory();

  const handleCreate = async () => {
    await createMutation.mutateAsync({
      content: "New memory content",
      agent_id: "my-agent",
    });
  };

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {memories?.map((memory) => (
        <div key={memory.id}>{memory.content}</div>
      ))}
      <button onClick={handleCreate}>Add Memory</button>
    </div>
  );
}
```

## API Integration

The dashboard integrates with the Enhanced Cognee backend API running on `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`).

### Available Endpoints

- `GET /api/memories` - List memories (paginated, filtered)
- `GET /api/memories/{id}` - Get specific memory
- `POST /api/memories` - Add new memory
- `GET /api/search` - Search memories
- `GET /api/sessions` - List sessions
- `GET /api/sessions/{id}` - Get session details
- `GET /api/timeline/{id}` - Get timeline context
- `GET /api/stats` - System statistics
- `GET /api/stream` - SSE streaming for real-time updates

### Type Safety

All API responses are fully typed with TypeScript interfaces defined in `src/lib/api/types.ts`.

## Styling

### Tailwind CSS

The dashboard uses Tailwind CSS with custom design tokens defined in `tailwind.config.ts`.

### Theme Colors

- **Primary:** Blue (`hsl(217.2, 91.2%, 59.8%)`)
- **Secondary:** Dark blue (`hsl(217.2, 32.6%, 17.5%)`)
- **Destructive:** Red (`hsl(0, 62.8%, 30.6%)`)
- **Background:** Dark slate (`hsl(222.2, 84%, 4.9%)`)
- **Foreground:** Light slate (`hsl(210, 40%, 98%)`)

### Dark Mode

Dark mode is enabled by default. The theme is controlled via CSS variables in `src/app/globals.css`.

## Accessibility

- WCAG 2.1 AA compliant
- Full keyboard navigation
- Screen reader support
- Focus indicators
- ARIA labels on interactive elements
- Semantic HTML

## Performance Optimizations

- Code splitting by route
- Lazy loading for heavy components
- Optimistic UI updates
- Query caching and invalidation
- Virtual scrolling (planned for large lists)

## Testing

### Unit Tests

Component tests are written with Vitest and Testing Library.

### Run Tests

```bash
npm test
```

## Troubleshooting

### Issue: Tailwind classes not working

```bash
# Clear Next.js cache
rm -rf .next

# Restart dev server
npm run dev
```

### Issue: API requests failing

- Check backend API is running on port 8000
- Verify `NEXT_PUBLIC_API_URL` in `.env.local`
- Check browser console for CORS errors
- Check API logs for errors

### Issue: Build errors

```bash
# Run TypeScript check
npx tsc --noEmit

# Run linter
npm run lint
```

## Future Enhancements

### Phase 2: Core Features (Weeks 3-5)

- [ ] Memory detail view
- [ ] Add/Edit memory functionality
- [ ] Advanced search with filters
- [ ] Session timeline view

### Phase 3: Visualization (Weeks 6-7)

- [ ] Timeline visualization with D3.js
- [ ] Knowledge graph with Cytoscape.js
- [ ] Charts with Recharts

### Phase 4: Analytics & Agents (Week 8)

- [ ] Analytics dashboard with metrics
- [ ] Agent management interface
- [ ] Performance monitoring

### Phase 5: Settings & Developer Tools (Week 9)

- [ ] Category management
- [ ] Data export/import
- [ ] API documentation viewer
- [ ] MCP tool tester

### Phase 6: Polish & Launch (Week 10)

- [ ] Cross-browser testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] Production deployment

## Contributing

This is part of the Enhanced Cognee project. Please follow the established coding patterns and conventions.

## License

Same as Enhanced Cognee project.

## Support

For issues or questions, please refer to the main Enhanced Cognee documentation or create an issue in the project repository.

---

**Built with:** Next.js 14, TypeScript, Tailwind CSS, TanStack Query, Zustand
**Status:** Phase 1 Foundation Complete
**Last Updated:** February 6, 2026
