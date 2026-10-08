import React from "react";

// Phone-only (<640px) filter block: no labels, full-width controls, 44px targets.
// Desktop/tablet keeps the existing labeled row.
export default function MobileFilters({
  level,
  setLevel,
  barangayAvailable,
  brgyMunis,
  brgyMuniId,
  setBrgyMuniId,
  seasons,
  season,
  setSeason,
  viewMenu,
}) {
  const levelBtn = (on) =>
    `h-9 rounded-[7px] text-sm font-semibold transition-colors ${
      on ? "bg-white text-[#1B3315] shadow-[0_1px_2px_rgba(0,0,0,0.08)]" : "text-[#4B5563]"
    }`;
  const seasonBtn = (on) =>
    `h-9 rounded-full text-sm font-semibold transition-colors ${on ? "bg-[#3B9E1C] text-white" : "text-[#191C1A]"}`;

  return (
    <div className="sm:hidden flex flex-col gap-2.5">
      <div className="grid grid-cols-2 gap-1 p-1 bg-[#F3F4F6] rounded-[10px]" role="group" aria-label="Compare by">
        <button type="button" onClick={() => setLevel("municipality")} aria-pressed={level === "municipality"} className={levelBtn(level === "municipality")}>
          Municipality
        </button>
        <button
          type="button"
          onClick={() => barangayAvailable && setLevel("barangay")}
          disabled={!barangayAvailable}
          aria-pressed={level === "barangay"}
          className={`${levelBtn(level === "barangay")} disabled:opacity-40`}
        >
          Barangay
        </button>
      </div>

      {level === "barangay" && (
        <label className="relative flex items-center">
          <span className="absolute left-3 text-xs font-medium text-[#6B7280]">In</span>
          <select
            value={brgyMuniId ?? ""}
            onChange={(e) => setBrgyMuniId(e.target.value ? Number(e.target.value) : null)}
            aria-label="Municipality"
            className="w-full h-11 pl-[34px] pr-9 appearance-none bg-white border border-[#C3C8BD] rounded-[10px] text-sm font-semibold text-[#191C1A] outline-none focus:border-[#3B9E1C]"
          >
            {brgyMunis.map((m) => (
              <option key={m.municipality_id} value={m.municipality_id}>{m.name}</option>
            ))}
          </select>
          <svg width="12" height="12" viewBox="0 0 14 14" fill="none" className="pointer-events-none absolute right-3.5">
            <path d="M2 4l5 5 5-5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </label>
      )}

      <div className="flex gap-2">
        <div
          className="flex-1 grid gap-1 p-1 bg-[#ECEFEA] rounded-full"
          style={{ gridTemplateColumns: `repeat(${seasons.length}, minmax(0, 1fr))` }}
          role="group"
          aria-label="Season"
        >
          {seasons.map((opt) => (
            <button key={opt} type="button" onClick={() => setSeason(opt)} aria-pressed={season === opt} className={seasonBtn(season === opt)}>
              {opt} season
            </button>
          ))}
        </div>
        {viewMenu}
      </div>
    </div>
  );
}
