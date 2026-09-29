import React from "react";

// Option 5c. Replaces the "Selected Area" card in SpatialGIS.jsx's right panel.
// It sits edge-to-edge at the very top of the panel, above the padded card stack.
//
// Props (all existing SpatialGIS state):
//   selection  - from <LagunaMap onSelectionChange>
//   yieldResp  - { stats, records } observed municipality yields (for the rank)
//   season, year
//   onBack     - () => setActiveCityId(null)   // LagunaMap then flies back to the province

export default function SelectedAreaHeader({ selection, yieldResp, season, year, onBack }) {
  const isMuni = selection?.level === "municipality";

  // Rank of the selected municipality by observed yield (1 = highest).
  let rank = null;
  let ranked = 0;
  if (isMuni && yieldResp?.records?.length) {
    const sorted = yieldResp.records
      .filter((r) => r.yield != null)
      .sort((a, b) => b.yield - a.yield);
    ranked = sorted.length;
    const i = sorted.findIndex((r) => r.municipality_id === selection.id);
    rank = i >= 0 ? i + 1 : null;
  }

  if (!isMuni) {
    const muniCount = selection?.municipalityCount;
    const withData = yieldResp?.stats?.count;
    return (
      <div className="flex flex-col gap-1 px-6 pt-6 pb-5 border-b border-[#E1E3DE]">
        <span className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Selected Area</span>
        <h3 className="text-2xl font-bold text-[#061E04] tracking-[-0.6px]">Laguna Province</h3>
        <span className="text-[13px] text-[#6B7280]">
          {muniCount != null ? `${muniCount} municipalities` : "Loading boundaries…"}
          {withData != null && ` · ${withData} with yield data`}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 px-6 pt-6 pb-5 border-b border-[#E1E3DE] anim-fade-in">
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        <div className="flex items-center gap-1.5 text-xs font-semibold">
          <button type="button" onClick={onBack} className="text-[#1F6306] hover:underline">
            Laguna Province
          </button>
          <span className="text-[#9CA3AF]">/</span>
        </div>
        <h3 className="text-2xl font-bold text-[#061E04] tracking-[-0.6px] truncate">{selection.name}</h3>
        <span className="text-[13px] text-[#6B7280]">
          {selection.barangayCount != null ? `${selection.barangayCount} barangays` : "Loading barangays…"}
          {rank != null && ` · Rank ${rank} of ${ranked}, ${season} ${year}`}
        </span>
      </div>
      <button
        type="button"
        onClick={onBack}
        aria-label="Back to province"
        className="flex items-center justify-center w-9 h-9 shrink-0 rounded-full border border-[#C3C8BD] bg-white text-[#434840] hover:bg-[#F3F4F6] transition-colors"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
