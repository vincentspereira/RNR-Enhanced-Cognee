"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useStoredPreference, writeStoredPreference } from "@/lib/hooks/useStoredPreference";
import { useQuery } from "@tanstack/react-query";
import { Input, Badge } from "@/components/atoms";
import { MemoryCard } from "@/components/molecules";
import { MemoryListSkeleton } from "@/components/organisms/MemoryListSkeleton";
import { Search, X, Clock } from "lucide-react";
import { useRouter } from "next/navigation";
import { searchMemories } from "@/lib/api/memories";

interface SearchInterfaceProps {
  onResultsFound?: (count: number) => void;
}

export function SearchInterface({ onResultsFound }: SearchInterfaceProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const savedSearches = useStoredPreference("recent-searches");
  const recentSearches = useMemo((): string[] => {
    try {
      const saved: unknown = JSON.parse(savedSearches || "[]");
      return Array.isArray(saved) ? saved.filter((item): item is string => typeof item === "string").slice(0, 5) : [];
    } catch { return []; }
  }, [savedSearches]);

  // Debounced search (300ms delay)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Search query
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["search", debouncedQuery],
    queryFn: async () => {
      return searchMemories({ query: debouncedQuery, limit: 20 });
    },
    enabled: debouncedQuery.length > 0,
  });

  // Notify parent of results count
  useEffect(() => {
    if (data && onResultsFound) {
      onResultsFound(data.result_count || data.results?.length || 0);
    }
  }, [data, onResultsFound]);

  // Save search to history
  const handleSearch = useCallback((searchQuery: string) => {
    if (searchQuery.trim()) {
      const newRecent = [searchQuery, ...recentSearches.filter((s) => s !== searchQuery)].slice(0, 5);
      writeStoredPreference("recent-searches", JSON.stringify(newRecent));
      setQuery(searchQuery);
    }
  }, [recentSearches]);

  // Handle result click
  const handleResultClick = (id: string) => {
    router.push(`/memories/${id}`);
  };

  // Normalize results: backend returns memory_id, MemoryCard expects id
  const rawResults = data?.results || [];
  const results = rawResults.map((m) => ({
    ...m,
    summary: m.summary ?? undefined,
    memory_type: m.memory_type ?? undefined,
    memory_concept: m.memory_concept ?? undefined,
    char_count: m.char_count ?? undefined,
    estimated_tokens: m.estimated_tokens ?? undefined,
  }));
  const resultCount = data?.result_count ?? results.length;

  return (
    <div className="space-y-6">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search memories..."
          className="pl-10 pr-10"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSearch(query);
            }
          }}
          autoFocus
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2"
            aria-label="Clear search"
          >
            <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
          </button>
        )}
      </div>

      {/* Recent Searches */}
      {query === "" && recentSearches.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Recent Searches
          </h3>
          <div className="flex flex-wrap gap-2">
            {recentSearches.map((search) => (
              <Badge
                key={search}
                variant="outline"
                className="cursor-pointer hover:bg-accent"
                onClick={() => handleSearch(search)}
              >
                {search}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Search Results */}
      {query !== "" && (
        <>
          {isLoading ? (
            <MemoryListSkeleton count={5} />
          ) : isError ? (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
              <p className="text-destructive">Error: {error.message}</p>
            </div>
          ) : results.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                No results found for &quot;{query}&quot;
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-sm text-muted-foreground">
                Found {resultCount} result{resultCount !== 1 ? "s" : ""} for &quot;{query}&quot;
              </div>
              {results.map((memory) => (
                <MemoryCard
                  key={memory.id}
                  memory={memory}
                  onView={handleResultClick}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Suggested Searches (when empty) */}
      {query === "" && (
        <div>
          <h3 className="text-sm font-medium mb-3">Suggested Searches</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {[
              "TypeScript",
              "React",
              "authentication",
              "API design",
              "testing",
              "deployment",
            ].map((suggestion) => (
              <Badge
                key={suggestion}
                variant="outline"
                className="cursor-pointer hover:bg-accent justify-start"
                onClick={() => handleSearch(suggestion)}
              >
                {suggestion}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
