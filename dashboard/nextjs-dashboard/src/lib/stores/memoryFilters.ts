/**
 * memoryFilters store - re-exports useFilterStore as useMemoryFilters
 * for backward compatibility with legacy page imports
 */

import { useFilterStore } from "./filterStore";
import type { MemoryFilters } from "./filterStore";

export { useFilterStore as useMemoryFilters };
export type { MemoryFilters };
