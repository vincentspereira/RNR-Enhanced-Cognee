"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/atoms";
import { Badge } from "@/components/atoms";
import { Button } from "@/components/atoms";
import { Checkbox } from "@/components/atoms";
import {
  MoreVertical,
  Edit,
  Trash2,
  Eye,
  Clock,
  User,
  FileText
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/atoms";
import { formatRelativeTime } from "@/lib/utils";

interface MemoryCardProps {
  memory: {
    id: string;
    content: string;
    summary?: string;
    memory_type?: string;
    memory_concept?: string;
    data_type?: string;
    created_at: string;
    updated_at?: string;
    char_count?: number;
    estimated_tokens?: number;
    metadata?: Record<string, unknown>;
  };
  isSelected?: boolean;
  onSelect?: (id: string) => void;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onView?: (id: string) => void;
  variant?: "default" | "compact" | "detailed";
}

const MEMORY_TYPE_COLORS: Record<string, string> = {
  bugfix: "bg-red-500/10 text-red-500 border-red-500/20 hover:bg-red-500/20",
  feature: "bg-blue-500/10 text-blue-500 border-blue-500/20 hover:bg-blue-500/20",
  decision: "bg-purple-500/10 text-purple-500 border-purple-500/20 hover:bg-purple-500/20",
  refactor: "bg-orange-500/10 text-orange-500 border-orange-500/20 hover:bg-orange-500/20",
  discovery: "bg-green-500/10 text-green-500 border-green-500/20 hover:bg-green-500/20",
  general: "bg-gray-500/10 text-gray-500 border-gray-500/20 hover:bg-gray-500/20",
};

const MEMORY_CONCEPT_COLORS: Record<string, string> = {
  "how-it-works": "bg-cyan-500/10 text-cyan-500 border-cyan-500/20 hover:bg-cyan-500/20",
  gotcha: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20 hover:bg-yellow-500/20",
  "trade-off": "bg-pink-500/10 text-pink-500 border-pink-500/20 hover:bg-pink-500/20",
  pattern: "bg-indigo-500/10 text-indigo-500 border-indigo-500/20 hover:bg-indigo-500/20",
  general: "bg-gray-500/10 text-gray-500 border-gray-500/20 hover:bg-gray-500/20",
};

export function MemoryCard({
  memory,
  isSelected = false,
  onSelect,
  onEdit,
  onDelete,
  onView,
  variant = "default"
}: MemoryCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const displayContent = memory.summary || memory.content;
  const isTruncated = !memory.summary && memory.content.length > 200;

  const getTypeColor = (type?: string) => {
    return type && MEMORY_TYPE_COLORS[type]
      ? MEMORY_TYPE_COLORS[type]
      : MEMORY_TYPE_COLORS.general;
  };

  const getConceptColor = (concept?: string) => {
    return concept && MEMORY_CONCEPT_COLORS[concept]
      ? MEMORY_CONCEPT_COLORS[concept]
      : MEMORY_CONCEPT_COLORS.general;
  };

  const handleCardClick = () => {
    onView?.(memory.id);
  };

  const handleEditClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(memory.id);
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(memory.id);
  };

  const handleViewClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onView?.(memory.id);
  };

  return (
    <Card
      className={`
        group relative transition-all duration-200 cursor-pointer
        ${isSelected ? "ring-2 ring-primary" : ""}
        ${isHovered ? "shadow-lg" : "shadow-sm hover:shadow-md"}
      `}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleCardClick}
    >
      <CardContent className="p-4">
        {/* Selection Checkbox */}
        <div className="absolute top-4 left-4 z-10">
          <Checkbox
            checked={isSelected}
            onCheckedChange={(checked) => {
              onSelect?.(memory.id);
            }}
            onClick={(e) => e.stopPropagation()}
            aria-label={`Select memory ${memory.id}`}
          />
        </div>

        {/* Badges and Timestamp */}
        <div className="flex items-start justify-between gap-2 mb-3 pl-8">
          <div className="flex items-center gap-2 flex-wrap">
            {memory.memory_type && (
              <Badge
                variant="outline"
                className={getTypeColor(memory.memory_type)}
              >
                {memory.memory_type}
              </Badge>
            )}
            {memory.memory_concept && (
              <Badge
                variant="outline"
                className={getConceptColor(memory.memory_concept)}
              >
                {memory.memory_concept}
              </Badge>
            )}
          </div>
          <div
            className="flex items-center gap-1 text-xs text-muted-foreground"
            title={new Date(memory.created_at).toLocaleString()}
          >
            <Clock className="h-3 w-3" />
            <span>{formatRelativeTime(memory.created_at)}</span>
          </div>
        </div>

        {/* Content */}
        <div className="mb-3 pl-8">
          <p className="text-sm leading-relaxed">
            {displayContent.slice(0, variant === "compact" ? 150 : 200)}
            {(displayContent.length > (variant === "compact" ? 150 : 200) ||
              isTruncated) && (
              <span className="text-primary hover:underline ml-1">
                Read more
              </span>
            )}
          </p>
        </div>

        {/* Metadata */}
        <div className="flex items-center justify-between pl-8">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1" title="Agent ID">
              <User className="h-3 w-3" />
              <span>{memory.data_type || "default"}</span>
            </div>
            {memory.estimated_tokens && (
              <div className="flex items-center gap-1" title="Estimated tokens">
                <FileText className="h-3 w-3" />
                <span>{memory.estimated_tokens.toLocaleString()} tokens</span>
              </div>
            )}
            {memory.char_count && !memory.estimated_tokens && (
              <div className="flex items-center gap-1" title="Character count">
                <FileText className="h-3 w-3" />
                <span>{memory.char_count.toLocaleString()} chars</span>
              </div>
            )}
          </div>

          {/* Actions Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleViewClick}>
                <Eye className="mr-2 h-4 w-4" />
                View Details
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleEditClick}>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={handleDeleteClick}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Selection indicator */}
        {isSelected && (
          <div className="absolute top-0 left-0 w-1 h-full bg-primary rounded-l" />
        )}
      </CardContent>
    </Card>
  );
}
