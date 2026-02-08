# Enhanced Cognee Frontend Quick Start Guide

**Version:** 1.0.0
**Last Updated:** 2025-02-06
**Related Docs:** UX_UI_SPECIFICATION.md, UX_UI_WIREFRAMES.md

---

## Overview

This guide provides step-by-step instructions for setting up and implementing the Enhanced Cognee Memory Dashboard frontend using Next.js 14, TypeScript, and Tailwind CSS.

---

## Prerequisites

**Required:**
- Node.js 18+ and npm/yarn/pnpm
- Code editor (VS Code recommended)
- Git

**Recommended:**
- VS Code with these extensions:
  - ESLint
  - Prettier
  - Tailwind CSS IntelliSense
  - TypeScript Vue Plugin (if using Volar)
  - Error Lens (optional)

---

## Step 1: Project Setup

### 1.1 Create Next.js Project

```bash
# Navigate to frontend directory
cd enhanced-cognee/cognee-frontend

# Or create new project (if starting from scratch)
npx create-next-app@latest enhanced-cognee-dashboard --typescript --tailwind --eslint
cd enhanced-cognee-dashboard
```

**Interactive Prompts:**
```
Would you like to use App Router? (recommended) Yes
Would you like to use TypeScript? Yes
Would you like to use ESLint? Yes
Would you like to use Tailwind CSS? Yes
Would you like to use `src/` directory? Yes
Would you like to use App Router? Yes
Would you like to customize the default import alias (@/*)? Yes
```

### 1.2 Install Additional Dependencies

```bash
# UI component library (choose one)
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install lucide-react

# Or use shadcn/ui (recommended)
npx shadcn-ui@latest init

# Data visualization
npm install recharts
npm install cytoscape cytoscape-react-hook

# State management & data fetching
npm install @tanstack/react-query @tanstack/react-query-devtools
npm install zustand

# Form handling
npm install react-hook-form zod @hookform/resolvers

# Date handling
npm install date-fns

# Additional utilities
npm install clsx tailwind-merge
npm install axios
```

### 1.3 Setup Tailwind CSS

**tailwind.config.ts:**
```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
```

**src/app/globals.css:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 224.3 76.3% 48%;
    --radius: 0.5rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

---

## Step 2: Base Components

### 2.1 Button Component

**src/components/ui/button.tsx:**
```tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

### 2.2 Input Component

**src/components/ui/input.tsx:**
```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
```

### 2.3 Card Component

**src/components/ui/card.tsx:**
```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border bg-card text-card-foreground shadow-sm",
      className
    )}
    {...props}
  />
));
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
```

---

## Step 3: Layout Components

### 3.1 Header Component

**src/components/layout/header.tsx:**
```tsx
"use client";

import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, User, Settings } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        {/* Logo */}
        <Link href="/" className="mr-6 flex items-center space-x-2">
          <span className="hidden font-bold sm:inline-block">
            Enhanced Cognee
          </span>
        </Link>

        {/* Breadcrumbs - optional */}
        <nav className="flex items-center space-x-2 text-sm font-medium">
          <Link href="/dashboard">Dashboard</Link>
        </nav>

        {/* Spacer */}
        <div className="flex flex-1 items-center justify-end space-x-4">

          {/* Global Search */}
          <div className="w-full flex-1 md:w-auto md:flex-none">
            <button className="inline-flex items-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-input bg-transparent shadow-sm hover:bg-accent hover:text-accent-foreground h-9 px-4 py-2 relative w-full justify-start text-sm text-muted-foreground sm:pr-12 md:w-40 lg:w-64">
              <Search className="mr-2 h-4 w-4" />
              <span className="inline-flex">Search...</span>
              <kbd className="pointer-events-none absolute right-1.5 top-2 hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
                <span className="text-xs">⌘</span>K
              </kbd>
            </button>
          </div>

          {/* User Menu */}
          <nav className="flex items-center space-x-2">
            <Button variant="ghost" size="icon">
              <Settings className="h-5 w-5" />
            </Button>
            <Button variant="ghost" size="icon">
              <User className="h-5 w-5" />
            </Button>
          </nav>
        </div>
      </div>
    </header>
  );
}
```

### 3.2 Sidebar Component

**src/components/layout/sidebar.tsx:**
```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Home,
  Database,
  Search,
  Clock,
  BarChart3,
  Users,
  Settings,
  Code,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: Home },
  { name: "Memories", href: "/memories", icon: Database },
  { name: "Search", href: "/search", icon: Search },
  { name: "Sessions", href: "/sessions", icon: Clock },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Agents", href: "/agents", icon: Users },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Developer", href: "/developer", icon: Code },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-10 hidden w-64 flex-col border-r bg-background md:flex">
      <div className="flex h-16 items-center border-b px-6">
        <Link href="/" className="flex items-center space-x-2">
          <span className="font-bold text-lg">Enhanced Cognee</span>
        </Link>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
              )}
            >
              <item.icon className="mr-3 h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4">
        <div className="flex items-center space-x-3 rounded-lg border bg-card p-3">
          <div className="h-2 w-2 rounded-full bg-green-500" />
          <div className="flex-1 text-sm">
            <p className="font-medium">System Status</p>
            <p className="text-xs text-muted-foreground">All services operational</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
```

### 3.3 Root Layout

**src/app/layout.tsx:**
```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Enhanced Cognee Dashboard",
  description: "Enterprise-grade AI memory system dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="flex min-h-screen flex-col">
          <Header />
          <div className="flex flex-1">
            <Sidebar />
            <main className="flex-1 md:pl-64">
              <div className="container py-6">{children}</div>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
```

---

## Step 4: API Client Setup

### 4.1 API Client Configuration

**src/lib/api/client.ts:**
```typescript
import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
```

### 4.2 Memory API Endpoints

**src/lib/api/memories.ts:**
```typescript
import { apiClient } from "./client";

export interface Memory {
  id: string;
  content: string;
  category: string;
  agent_id: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

export interface MemoryFilters {
  category?: string;
  agent_id?: string;
  limit?: number;
  offset?: number;
}

export async function getMemories(filters?: MemoryFilters): Promise<Memory[]> {
  const response = await apiClient.get("/api/v1/memories", {
    params: filters,
  });
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
  const response = await apiClient.post("/api/v1/memories", data);
  return response.data;
}

export async function updateMemory(
  id: string,
  data: Partial<Memory>
): Promise<Memory> {
  const response = await apiClient.put(`/api/v1/memories/${id}`, data);
  return response.data;
}

export async function deleteMemory(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/memories/${id}`);
}
```

---

## Step 5: State Management

### 5.1 React Query Setup

**src/app/providers.tsx:**
```tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

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
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

**Update src/app/layout.tsx:**
```tsx
import { Providers } from "./providers";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="flex min-h-screen flex-col">
            {/* ... rest of layout */}
          </div>
        </Providers>
      </body>
    </html>
  );
}
```

### 5.2 Custom Hooks

**src/lib/hooks/useMemories.ts:**
```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMemories, createMemory, updateMemory, deleteMemory } from "@/lib/api/memories";
import type { Memory, MemoryFilters } from "@/lib/api/memories";

export function useMemories(filters?: MemoryFilters) {
  return useQuery({
    queryKey: ["memories", filters],
    queryFn: () => getMemories(filters),
  });
}

export function useMemory(id: string) {
  return useQuery({
    queryKey: ["memory", id],
    queryFn: () => getMemory(id),
    enabled: !!id,
  });
}

export function useCreateMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
    },
  });
}

export function useUpdateMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Memory> }) =>
      updateMemory(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["memory", variables.id] });
      queryClient.invalidateQueries({ queryKey: ["memories"] });
    },
  });
}

export function useDeleteMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
    },
  });
}
```

---

## Step 6: Example Page Implementation

### 6.1 Dashboard Page

**src/app/dashboard/page.tsx:**
```tsx
"use client";

import { useMemories } from "@/lib/hooks/useMemories";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  const { data: memories, isLoading, error } = useMemories({ limit: 10 });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
        <p className="text-destructive">Error loading dashboard: {error.message}</p>
      </div>
    );
  }

  const totalMemories = memories?.length || 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your Enhanced Cognee memory system
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Memories
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalMemories}</div>
            <p className="text-xs text-muted-foreground">
              +12% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Agents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">3 currently active</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Storage Used
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2.4 GB</div>
            <p className="text-xs text-muted-foreground">+8% this week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Avg Query Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">42ms</div>
            <p className="text-xs text-muted-foreground">-15% optimized</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {memories?.slice(0, 5).map((memory) => (
              <div key={memory.id} className="flex items-center space-x-4">
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {memory.content.slice(0, 80)}...
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Agent: {memory.agent_id} • {new Date(memory.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

### 6.2 Memories List Page

**src/app/memories/page.tsx:**
```tsx
"use client";

import { useState } from "react";
import { useMemories, useDeleteMemory } from "@/lib/hooks/useMemories";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function MemoriesListPage() {
  const [filters, setFilters] = useState({
    category: "",
    agent_id: "",
    limit: 50,
  });

  const { data: memories, isLoading, error } = useMemories(filters);
  const deleteMutation = useDeleteMemory();

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this memory?")) {
      await deleteMutation.mutateAsync(id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Memories</h1>
          <p className="text-muted-foreground">
            Browse and manage your AI memories
          </p>
        </div>
        <Button>Add Memory</Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <Input
          placeholder="Search memories..."
          className="max-w-sm"
        />
        <Select value={filters.category} onValueChange={(value) =>
          setFilters({ ...filters, category: value })
        }>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="trading">Trading</SelectItem>
            <SelectItem value="development">Development</SelectItem>
            <SelectItem value="testing">Testing</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.agent_id} onValueChange={(value) =>
          setFilters({ ...filters, agent_id: value })
        }>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Agent" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Agents</SelectItem>
            <SelectItem value="bot-1">Trading Bot</SelectItem>
            <SelectItem value="agent-2">SDLC Manager</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Memories List */}
      {isLoading ? (
        <div className="text-center py-12">Loading...</div>
      ) : error ? (
        <div className="text-destructive py-12">Error: {error.message}</div>
      ) : (
        <div className="space-y-4">
          {memories?.map((memory) => (
            <Card key={memory.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge>{memory.category}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {new Date(memory.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm mb-2">{memory.content}</p>
                    <p className="text-xs text-muted-foreground">
                      Agent: {memory.agent_id}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm">
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(memory.id)}
                      disabled={deleteMutation.isPending}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Step 7: Utility Functions

### 7.1 cn Utility (className merge)

**src/lib/utils.ts:**
```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(date));
}

export function formatRelativeTime(date: string | Date): string {
  const now = new Date();
  const past = new Date(date);
  const seconds = Math.floor((now.getTime() - past.getTime()) / 1000);

  const intervals = {
    year: 31536000,
    month: 2592000,
    week: 604800,
    day: 86400,
    hour: 3600,
    minute: 60,
  };

  for (const [unit, secondsInUnit] of Object.entries(intervals)) {
    const interval = Math.floor(seconds / secondsInUnit);
    if (interval >= 1) {
      return `${interval} ${unit}${interval > 1 ? "s" : ""} ago`;
    }
  }

  return "just now";
}
```

---

## Step 8: Environment Variables

**.env.local:**
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Analytics
NEXT_PUBLIC_GA_ID=your-google-analytics-id

# Optional: Feature Flags
NEXT_PUBLIC_ENABLE_GRAPH=true
NEXT_PUBLIC_ENABLE_TIMELINE=true
```

---

## Step 9: Running the Development Server

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Open browser
# Navigate to http://localhost:3000
```

---

## Step 10: Building for Production

```bash
# Type check
npm run type-check

# Lint
npm run lint

# Build
npm run build

# Start production server
npm start
```

---

## Common Patterns

### Data Fetching with Loading State

```tsx
const { data, isLoading, error } = useMemories();

if (isLoading) return <LoadingSkeleton />;
if (error) return <ErrorMessage error={error} />;
if (!data) return <EmptyState />;

// Render data
```

### Form Handling

```tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

const memorySchema = z.object({
  content: z.string().min(10, "Content must be at least 10 characters"),
  category: z.string().optional(),
});

export function AddMemoryForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(memorySchema),
  });

  const createMutation = useCreateMemory();

  const onSubmit = (data: z.infer<typeof memorySchema>) => {
    createMutation.mutate(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <textarea {...register("content")} />
      {errors.content && <span>{errors.content.message}</span>}
      <button type="submit" disabled={createMutation.isPending}>
        Add Memory
      </button>
    </form>
  );
}
```

### Error Handling

```tsx
"use client";

import { useEffect } from "react";

export function ErrorBoundary({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h2 className="text-2xl font-bold mb-4">Something went wrong!</h2>
      <p className="text-muted-foreground mb-4">{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

---

## Next Steps

1. **Implement remaining pages:** Search, Analytics, Agents, Sessions
2. **Add data visualizations:** Integrate Recharts for analytics
3. **Implement graph view:** Use Cytoscape.js for knowledge graph
4. **Add authentication:** Implement login/logout flow
5. **Add testing:** Write unit and E2E tests
6. **Optimize performance:** Code splitting, lazy loading, image optimization
7. **Deploy:** Set up CI/CD and deployment pipeline

---

## Troubleshooting

**Issue: Tailwind classes not working**
- Clear `.next` cache: `rm -rf .next`
- Restart dev server

**Issue: API requests failing**
- Check API URL in `.env.local`
- Verify backend is running
- Check browser console for CORS errors

**Issue: Build errors**
- Run `npm run type-check` to identify TypeScript errors
- Check all imports are correct
- Verify all dependencies are installed

---

**Document Version:** 1.0.0
**Last Updated:** 2025-02-06
**Related:** UX_UI_SPECIFICATION.md, UX_UI_WIREFRAMES.md

For detailed design specifications, refer to the UX/UI Specification document. For visual wireframes, refer to the Wireframes document.
