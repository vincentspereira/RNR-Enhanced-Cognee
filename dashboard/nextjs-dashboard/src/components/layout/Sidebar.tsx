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
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/atoms";
import { useUIStore } from "@/lib/stores";

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
  const { sidebarCollapsed, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-10 flex-col border-r bg-background transition-all duration-300",
        sidebarCollapsed ? "w-16" : "w-64",
        "hidden md:flex"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b px-6">
        {!sidebarCollapsed && (
          <Link href="/" className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">E</span>
            </div>
            <span className="font-bold text-lg">Enhanced Cognee</span>
          </Link>
        )}
        {sidebarCollapsed && (
          <Link href="/" className="flex items-center justify-center w-full">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">E</span>
            </div>
          </Link>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto">
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
                  : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground",
                sidebarCollapsed && "justify-center"
              )}
              title={sidebarCollapsed ? item.name : undefined}
            >
              <item.icon className="h-5 w-5" />
              {!sidebarCollapsed && (
                <span className="ml-3">{item.name}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Collapse Toggle */}
      <div className="border-t p-4">
        <Button
          variant="ghost"
          size="sm"
          className="w-full"
          onClick={toggleSidebar}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4 mr-2" />
              Collapse
            </>
          )}
        </Button>
      </div>

      {/* System Status */}
      {!sidebarCollapsed && (
        <div className="border-t p-4">
          <div className="flex items-center space-x-3 rounded-lg border bg-card p-3">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            <div className="flex-1 text-sm">
              <p className="font-medium">System Status</p>
              <p className="text-xs text-muted-foreground">All services operational</p>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
