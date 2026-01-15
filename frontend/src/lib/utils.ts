/**
 * Utility functions for the Fund Extraction application
 */

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Utility function to merge class names with Tailwind CSS
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Generate a UUID v4 compatible string that works in all browsers
 * Falls back to a timestamp-based approach if crypto.randomUUID is not available
 */
export function generateUUID(): string {
  // Try to use the native crypto.randomUUID if available (modern browsers, HTTPS)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    try {
      return crypto.randomUUID();
    } catch {
      // Fall through to fallback method
    }
  }

  // Fallback UUID v4 generator for older browsers or HTTP contexts
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Generate a simple session ID for extraction requests
 */
export function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Format currency values for display
 */
export function formatCurrency(value: number | undefined): string {
  if (!value) return "N/A";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 2
  }).format(value);
}

/**
 * Format percentage values for display
 */
export function formatPercentage(value: number | undefined): string {
  if (!value) return "N/A";
  return `${value.toFixed(2)}%`;
}