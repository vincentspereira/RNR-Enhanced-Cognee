"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { X, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/atoms/Button";
import { Input } from "@/components/atoms/Input";
import { Textarea } from "@/components/atoms/Textarea";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query/queryKeys";
import { createMemory } from "@/lib/api/memories";
import { toast } from "sonner";

const memorySchema = z.object({
  content: z
    .string()
    .min(1, "Content is required")
    .max(10000, "Content must be less than 10,000 characters"),
  agent_id: z.string().min(1, "Agent ID is required").default("default"),
  memory_type: z.string().optional(),
  memory_concept: z.string().optional(),
  before_state: z.string().optional(),
  after_state: z.string().optional(),
  files: z.string().optional(),
  facts: z.string().optional(),
});

type MemoryFormData = z.infer<typeof memorySchema>;

interface AddMemoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const MEMORY_TYPES = [
  "observation",
  "bugfix",
  "feature",
  "decision",
  "refactor",
  "discovery",
  "general",
];

const MEMORY_CONCEPTS = [
  "code",
  "architecture",
  "testing",
  "documentation",
  "performance",
  "security",
  "deployment",
  "monitoring",
  "general",
];

export function AddMemoryModal({ isOpen, onClose }: AddMemoryModalProps) {
  const [isAutoCategorizing, setIsAutoCategorizing] = useState(false);
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<MemoryFormData>({
    resolver: zodResolver(memorySchema),
    defaultValues: {
      agent_id: "default",
    },
  });

  const content = watch("content") || "";
  const contentLength = content.length;

  const onSubmit = async (data: MemoryFormData) => {
    try {
      // Parse files and facts
      const files = data.files
        ? data.files.split(",").map((f) => f.trim()).filter(Boolean)
        : undefined;

      const facts = data.facts
        ? data.facts.split("\n").map((f) => f.trim()).filter(Boolean)
        : undefined;

      await createMemory({
        content: data.content,
        agent_id: data.agent_id,
        memory_type: data.memory_type,
        memory_concept: data.memory_concept,
      });

      toast.success("Memory added successfully", {
        description: "Your memory has been stored.",
      });

      // Invalidate queries
      queryClient.invalidateQueries({
        queryKey: queryKeys.memories.lists(),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.analytics.systemStats(),
      });

      reset();
      onClose();
    } catch (error) {
      console.error("Failed to add memory:", error);
      toast.error("Failed to add memory", {
        description:
          error instanceof Error ? error.message : "An unknown error occurred",
      });
    }
  };

  const handleAutoCategorize = async () => {
    if (!content) {
      toast.error("Content required", {
        description: "Please enter content before auto-categorizing.",
      });
      return;
    }

    setIsAutoCategorizing(true);

    try {
      // Simulate auto-categorization
      // In production, this would call an LLM endpoint
      await new Promise((resolve) => setTimeout(resolve, 1500));

      // Mock categorization
      setValue("memory_type", "observation");
      setValue("memory_concept", "code");

      toast.success("Auto-categorized", {
        description: "Type and concept have been detected.",
      });
    } catch (error) {
      console.error("Auto-categorization failed:", error);
      toast.error("Auto-categorization failed", {
        description: "Please select type and concept manually.",
      });
    } finally {
      setIsAutoCategorizing(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4 animate-in fade-in zoom-in duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2
            id="modal-title"
            className="text-xl font-semibold text-gray-900"
          >
            Add New Memory
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
          {/* Content */}
          <div>
            <label
              htmlFor="content"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Content <span className="text-red-500">*</span>
            </label>
            <Textarea
              id="content"
              {...register("content")}
              placeholder="Enter the memory content..."
              rows={6}
              className={errors.content ? "border-red-500" : ""}
              aria-invalid={errors.content ? "true" : "false"}
              aria-describedby={
                errors.content ? "content-error" : "content-description"
              }
            />
            <div className="mt-1 flex items-center justify-between">
              {errors.content ? (
                <p id="content-error" className="text-sm text-red-600">
                  {errors.content.message}
                </p>
              ) : (
                <p id="content-description" className="text-sm text-gray-500">
                  Enter detailed information for this memory
                </p>
              )}
              <span className="text-sm text-gray-500">
                {contentLength} / 10,000
              </span>
            </div>
          </div>

          {/* Type and Concept */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Memory Type */}
            <div>
              <label
                htmlFor="memory_type"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Memory Type
              </label>
              <select
                id="memory_type"
                {...register("memory_type")}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select type...</option>
                {MEMORY_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {/* Memory Concept */}
            <div>
              <label
                htmlFor="memory_concept"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Memory Concept
              </label>
              <select
                id="memory_concept"
                {...register("memory_concept")}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select concept...</option>
                {MEMORY_CONCEPTS.map((concept) => (
                  <option key={concept} value={concept}>
                    {concept.charAt(0).toUpperCase() + concept.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Auto-categorize button */}
          <div>
            <button
              type="button"
              onClick={handleAutoCategorize}
              disabled={isAutoCategorizing || !content}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAutoCategorizing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              Auto-categorize
            </button>
          </div>

          {/* Agent ID */}
          <div>
            <label
              htmlFor="agent_id"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Agent ID <span className="text-red-500">*</span>
            </label>
            <Input
              id="agent_id"
              {...register("agent_id")}
              placeholder="default"
              error={errors.agent_id?.message}
              aria-invalid={errors.agent_id ? "true" : "false"}
              aria-describedby={errors.agent_id ? "agent_id-error" : undefined}
            />
            {errors.agent_id && (
              <p id="agent_id-error" className="mt-1 text-sm text-red-600">
                {errors.agent_id.message}
              </p>
            )}
          </div>

          {/* Before State */}
          <div>
            <label
              htmlFor="before_state"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Before State (Optional)
            </label>
            <Textarea
              id="before_state"
              {...register("before_state")}
              placeholder="Describe the state before this memory..."
              rows={3}
            />
          </div>

          {/* After State */}
          <div>
            <label
              htmlFor="after_state"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              After State (Optional)
            </label>
            <Textarea
              id="after_state"
              {...register("after_state")}
              placeholder="Describe the state after this memory..."
              rows={3}
            />
          </div>

          {/* Files */}
          <div>
            <label
              htmlFor="files"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Related Files (Optional)
            </label>
            <Input
              id="files"
              {...register("files")}
              placeholder="file1.ts, file2.ts, file3.ts (comma-separated)"
            />
            <p className="mt-1 text-sm text-gray-500">
              Enter file paths separated by commas
            </p>
          </div>

          {/* Facts */}
          <div>
            <label
              htmlFor="facts"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Key Facts (Optional)
            </label>
            <Textarea
              id="facts"
              {...register("facts")}
              placeholder="Fact 1&#10;Fact 2&#10;Fact 3 (one per line)"
              rows={4}
            />
            <p className="mt-1 text-sm text-gray-500">
              Enter each fact on a new line
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                "Add Memory"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
