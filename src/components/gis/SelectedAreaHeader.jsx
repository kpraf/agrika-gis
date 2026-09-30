import React from "react";

// Edge-to-edge header at the top of the map's right panel. Handles three levels:
// province, a clicked municipality, and a clicked barangay (breadcrumb back up).
//
// Props (SpatialGIS state):
//   selection    - from <LagunaMap onSelectionChange>
//   yieldResp    - { stats, records } observed municipality yields (for the rank)
//   season, year
//   onProvince   - () => back to the whole province
//   onBackToMuni - () => deselect a barangay, back to its municipality

export default function SelectedAreaHeader({ selection, yieldResp, season, year, onProvince, onBackToMuni }) {
  const level = selection?.level;

  // Province view
  if (level !== "municipality" && level !== "barangay") {
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

  const isBarangay = level === "barangay";

  // Rank of the selected municipality by observed yield (1 = highest).
  let rank = null;
  let ranked = 0;
  if (!isBarangay && yieldResp?.records?.length) {
    const sorted = yieldResp.records.filter((r) => r.yield != null).sort((a, b) => b.yield - a.yield);
    ranked = sorted.length;
    const i = sorted.findIndex((r) => r.municipality_id === selection.id);
    rank = i >= 0 ? i + 1 : null;
  }

  const onBack = isBarangay ? onBackToMuni : onProvince;

  return (
    <div className="flex items-start gap-3 px-6 pt-6 pb-5 border-b border-[#E1E3DE] anim-fade-in">
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        <div className="flex items-center gap-1.5 text-xs font-semibold flex-wrap">
          <button type="button" onClick={onProvince} className="text-[#1F6306] hover:underline">
            Laguna Province
          </button>
          <span className="text-[#9CA3AF]">/</span>
          {isBarangay && (
            <>
              <button
                type="button"
                onClick={onBackToMuni}
                className="text-[#1F6306] hover:underline truncate max-w-[150px]"
              >
                {selection.municipalityName}
              </button>
              <span className="text-[#9CA3AF]">/</span>
            </>
          )}
        </div>
        <h3 className="text-2xl font-bold text-[#061E04] tracking-[-0.6px] truncate">{selection.name}</h3>
        <span className="text-[13px] text-[#6B7280] truncate">
          {isBarangay ? (
            `Barangay · ${selection.municipalityName}`
          ) : (
            <>
              {selection.barangayCount != null ? `${selection.barangayCount} barangays` : "Loading barangays…"}
              {rank != null && ` · Rank ${rank} of ${ranked}, ${season} ${year}`}
            </>
          )}
        </span>
      </div>
      <button
        type="button"
        onClick={onBack}
        title={isBarangay ? `Back to ${selection.municipalityName}` : "Back to Laguna Province"}
        aria-label={isBarangay ? `Back to ${selection.municipalityName}` : "Back to Laguna Province"}
        className="flex items-center justify-center w-9 h-9 shrink-0 rounded-full border border-[#C3C8BD] bg-white text-[#434840] hover:bg-[#F3F4F6] transition-colors"
      >
        {/* Back one level (barangay -> municipality, municipality -> province) */}
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </button>
    </div>
  );
}
