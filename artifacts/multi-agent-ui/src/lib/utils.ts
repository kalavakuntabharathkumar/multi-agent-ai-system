// Utility: merges Tailwind CSS class names, resolving conflicts with tailwind-merge.
// All UI components use cn() instead of plain string concatenation for class names.

import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

// Combine clsx (conditional classes) with twMerge (conflict resolution) in one call
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
