import React from "react";

// Thin moving bar along the bottom edge of a page header: "something on this page
// is loading". Give the parent `relative`.
export function LoadingBar({ active }) {
  if (!active) return null;
  return (
    <div
      role="progressbar"
      aria-label="Loading data"
      aria-busy="true"
      className="absolute inset-x-0 bottom-0 h-[3px] overflow-hidden bg-[#DCFCE7]"
    >
      <span className="anim-indeterminate absolute inset-y-0 left-0 w-2/5 rounded-full bg-[#3B9E1C]" />
    </div>
  );
}

// Spinner + label floating over the thing being reloaded (a chart, a table).
// Give the parent `relative`; the old content underneath should be dimmed with
// loadingDim() so it reads as out of date.
export function LoadingPill({ active, label = "Loading…" }) {
  if (!active) return null;
  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none anim-fade-in">
      <div
        role="status"
        aria-live="polite"
        className="flex items-center gap-2.5 px-4 py-2.5 rounded-full bg-white/95 border border-[#E5E7EB] shadow-[0_4px_12px_rgba(0,0,0,0.12)]"
      >
        <span className="inline-flex h-4 w-4 rounded-full border-2 border-transparent border-t-[#1F6306] border-r-[#1F6306] animate-spin" />
        <span className="text-sm font-medium text-[#374151] whitespace-nowrap">{label}</span>
      </div>
    </div>
  );
}

// Classes that fade content while its replacement loads.
export const loadingDim = (active) =>
  `transition-opacity duration-200 ${active ? "opacity-40 pointer-events-none" : "opacity-100"}`;
