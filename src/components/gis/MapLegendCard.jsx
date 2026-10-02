import React, { useState } from "react";
import { YIELD_RAMP, RESIDUAL_RAMP, RAMPS } from "./LagunaMap"; // add `export` to those 3 consts (see README)

// Option 4c. Replaces the "Active Layers" card in SpatialGIS.jsx's right panel.
// Class boundaries match LagunaMap exactly: colours are picked with
// Math.round(t * (n - 1)), so each step spans one bucket and the two end steps span half.
//
// Props:
//   visible      - is a colour layer on the map right now?
//   scale        - { min, max } the map is using (barangay scale when drilled in)
//   colorMode    - "yield" | "residual"
//   rampKey      - "green" | "teal" | "blue" | "warm"
//   title        - e.g. "Avg yield (mt/ha)" or "Rainfall (mm/mo)"
//   badge        - e.g. "Observed yield", "Residual", "Environment · NDVI"
//   subtitle     - e.g. "Dry 2025"
//   avg          - optional; marks which class holds the average
//   boundariesOn - show the boundary key

const STORAGE_KEY = "agrika-gis:legend-list";

function decimalsFor(span) {
  if (span >= 50) return 0;
  if (span >= 5) return 1;
  return 2;
}

export default function MapLegendCard({
  visible, loading = false, emptyHint = null, scale, colorMode = "yield", rampKey = "green",
  title, badge, subtitle, avg, boundariesOn = true,
}) {
  const [listOn, setListOn] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) !== "off"; } catch { return true; }
  });
  const toggleList = () =>
    setListOn((v) => {
      const next = !v;
      try { localStorage.setItem(STORAGE_KEY, next ? "on" : "off"); } catch { /* ignore */ }
      return next;
    });

  const isResidual = colorMode === "residual";
  const ramp = isResidual ? RESIDUAL_RAMP : RAMPS[rampKey] || YIELD_RAMP;
  const n = ramp.length;
  const hasScale = visible && scale?.min != null && scale?.max != null && scale.max > scale.min;

  // Residual scale is symmetric around 0 (same as LagunaMap).
  const lo = hasScale ? (isResidual ? -Math.abs(scale.max) : scale.min) : 0;
  const hi = hasScale ? (isResidual ? Math.abs(scale.max) : scale.max) : 1;
  const span = hi - lo;
  const dp = decimalsFor(span);
  const fmt = (v) => {
    const s = v.toFixed(dp);
    return isResidual && v > 0 ? `+${s}` : s.replace("-", "−");
  };

  // Boundaries between classes, at t = (k + 0.5) / (n - 1)
  const cuts = Array.from({ length: n - 1 }, (_, k) => (k + 0.5) / (n - 1));
  const edges = [0, ...cuts, 1];
  const classes = ramp.map((color, i) => ({
    color,
    from: lo + edges[i] * span,
    to: lo + edges[i + 1] * span,
    width: (edges[i + 1] - edges[i]) * 100,
  }));
  const avgIdx =
    avg != null && hasScale ? classes.findIndex((c, i) => avg >= c.from && (avg < c.to || i === n - 1)) : -1;

  return (
    <div className="flex flex-col gap-3.5 p-6 bg-[#F9FAFB] border border-[#C3C8BD] rounded-xl w-full">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Map Legend</h4>
        {hasScale && badge && (
          <span className="px-2 py-[3px] rounded-full bg-[#ECEFEA] text-[#1F6306] text-[11px] font-semibold">{badge}</span>
        )}
      </div>

      {loading && !hasScale ? (
        <div className="flex flex-col gap-3 animate-pulse">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex h-4 w-4 rounded-full border-2 border-transparent border-t-[#1F6306] border-r-[#1F6306] animate-spin" />
            <span className="text-sm font-medium text-[#6B7280]">Loading layer data…</span>
          </div>
          <div className="h-3.5 w-full rounded bg-[#E1E3DE]" />
          <div className="flex gap-2">
            <span className="h-2.5 w-10 rounded bg-[#ECEFEA]" />
            <span className="h-2.5 flex-1 rounded bg-[#ECEFEA]" />
            <span className="h-2.5 w-10 rounded bg-[#ECEFEA]" />
          </div>
        </div>
      ) : hasScale ? (
        <>
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm font-semibold text-[#191C1A]">
              {isResidual ? "Residual (obs − pred), mt/ha" : title}
            </span>
            {subtitle && <span className="text-xs text-[#6B7280] shrink-0">{subtitle}</span>}
          </div>

          {/* Stepped bar + boundary ticks */}
          <div className="flex flex-col gap-1.5">
            <div className="flex h-3.5 gap-0.5 rounded overflow-hidden">
              {classes.map((c) => (
                <span key={c.color} style={{ width: `${c.width}%`, background: c.color }} />
              ))}
            </div>
            <div className="relative h-4 text-[11px] font-semibold text-[#434840]">
              {cuts.map((t) => (
                <span key={t} className="absolute -translate-x-1/2" style={{ left: `${t * 100}%` }}>
                  {fmt(lo + t * span)}
                </span>
              ))}
            </div>
            {isResidual && (
              <div className="flex justify-between text-[11px] text-[#6B7280]">
                <span>Over-predicts</span>
                <span>Under-predicts</span>
              </div>
            )}
          </div>

          {/* Range list toggle */}
          <button type="button" onClick={toggleList} className="flex items-center justify-between w-full">
            <span className="text-[13px] font-medium text-[#434840]">Show range list</span>
            <span
              role="switch"
              aria-checked={listOn}
              className={`relative block w-9 h-5 rounded-full transition-colors duration-200 ${listOn ? "bg-[#1B6D24]" : "bg-[#E1E3DE]"}`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-[0_1px_2px_rgba(0,0,0,0.2)] transition-transform duration-[240ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${listOn ? "translate-x-4" : "translate-x-0"}`}
              />
            </span>
          </button>

          <div
            className={`grid transition-[grid-template-rows,opacity,margin] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
              listOn ? "grid-rows-[1fr] opacity-100 mt-0" : "grid-rows-[0fr] opacity-0 -mt-3.5"
            }`}
          >
            <div className="overflow-hidden min-h-0">
              <div
                className={`flex flex-col gap-2 transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${listOn ? "translate-y-0" : "-translate-y-1.5"}`}
              >
                {classes.map((c, i) => (
                  <div key={c.color} className="flex items-center gap-2.5 text-[13px] text-[#191C1A]">
                    <span className="w-3 h-3 rounded-[3px] shadow-[inset_0_0_0_1px_rgba(0,0,0,0.08)]" style={{ background: c.color }} />
                    <span className="flex-1">{fmt(c.from)} to {fmt(c.to)}</span>
                    {i === avgIdx && (
                      <span className="text-[11px] font-semibold text-[#1F6306]">Avg {avg}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      ) : emptyHint ? (
        <div className="flex items-start gap-2.5 rounded-lg bg-[#FEF3C7]/50 border border-[#FDE68A] px-3 py-2.5">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#B45309" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 shrink-0">
            <circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" />
          </svg>
          <span className="text-[13px] leading-5 text-[#92400E]">{emptyHint}</span>
        </div>
      ) : (
        <p className="text-sm text-[#9CA3AF]">No colour layer on the map right now.</p>
      )}

      {(hasScale || boundariesOn) && (
        <div className={`flex flex-wrap gap-4 text-[13px] text-[#191C1A] ${hasScale ? "pt-3 border-t border-[#E1E3DE]" : ""}`}>
          {hasScale && (
            <span className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-[3px] bg-[#D1D5DB]" />No data
            </span>
          )}
          {boundariesOn && (
            <span className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-[3px] border-2 border-[#1F6306] box-border" />Boundary
            </span>
          )}
        </div>
      )}
    </div>
  );
}
