"use client";

import { SearchInterface } from "@/components/organisms/SearchInterface";

export default function SearchPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Search</h1>
        <p className="text-muted-foreground">
          Search your memories using semantic and keyword search
        </p>
      </div>
      <SearchInterface />
    </div>
  );
}
