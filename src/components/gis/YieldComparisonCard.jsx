import React from "react";

// Option 2c. Replaces the "Rice Yield" and "CNN-LSTM Prediction" <Card>s in SpatialGIS.jsx.
// Props come straight from existing SpatialGIS state:
//   season, year, yieldLoading, yieldResp, compareResp, predMeta,
//   selection, selectedYield, selectedCompare

const pct = (v, lo, hi) => `${((v - lo) / (hi - lo)) * 100}%`;
const fmtSigned = (v) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)}`;

function Shell({ season, year, showBadge, children }) {
  return (
    <div className="flex flex-col gap-5 p-6 bg-[#F8FAF5] border border-[#C3C8BD] rounded-xl w-full">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">
          {`Rice Yield: ${season ?? ""} ${year ?? ""}`.trim()}
        </h4>
        {showBadge && (
          <span className="px-2 py-[3px] rounded-full bg-[#0E2207] text-[#FACC15] text-[10px] font-bold tracking-[0.5px]">
            CNN-LSTM
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

function Tile({ value, label, tone }) {
  return (
    <div className="flex flex-col items-center justify-center gap-0.5 h-[72px] bg-white border border-[#E1E3DE] rounded-lg">
      <span className={`text-lg font-bold ${tone ?? "text-[#1B3315]"}`}>{value}</span>
      <span className="text-[10px] font-semibold text-[#6B7280] uppercase tracking-[0.5px] text-center">{label}</span>
    </div>
  );
}

export default function YieldComparisonCard({
  season, year, yieldLoading, yieldResp, compareResp, predMeta,
  selection, selectedYield, selectedCompare,
}) {
  const isMuni = selection?.level === "municipality";
  const stats = yieldResp?.stats;

  if (yieldLoading) {
    return <Shell season={season} year={year}><p className="text-sm text-[#6B7280]">Loading yield…</p></Shell>;
  }

  // Values for the current scope (province or clicked municipality)
  const observed = isMuni ? (selectedCompare?.observed ?? selectedYield?.yield) : (compareResp?.stats?.observed_avg ?? stats?.avg);
  const predicted = predMeta?.has_predictions
    ? (isMuni ? selectedCompare?.predicted : compareResp?.stats?.predicted_avg)
    : null;

  if (observed == null) {
    return (
      <Shell season={season} year={year}>
        <p className="text-sm text-[#6B7280]">
          {isMuni ? `No observed yield for ${selection.name} in ${season} ${year}.` : `No yield data for ${season} ${year}.`}
        </p>
      </Shell>
    );
  }

  const hasPred = predicted != null;
  const residual = hasPred ? +(observed - predicted).toFixed(3) : null; // obs − pred (same sign rule as before)
  const errPct = hasPred ? Math.abs(((predicted - observed) / observed) * 100).toFixed(1) : null;

  // Axis: province range, snapped out to 0.5 mt/ha
  const vals = [stats?.min, stats?.max, observed, predicted].filter((v) => v != null);
  const lo = Math.floor(Math.min(...vals) * 2) / 2;
  const hi = Math.ceil(Math.max(...vals) * 2) / 2 || lo + 0.5;
  const ticks = [];
  for (let t = lo; t <= hi + 1e-9; t += 0.5) ticks.push(+t.toFixed(1));

  const left = Math.min(observed, predicted ?? observed);
  const right = Math.max(observed, predicted ?? observed);

  return (
    <Shell season={season} year={year} showBadge={hasPred}>
      {/* Observed / Predicted values */}
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1 p-3.5 bg-white border border-[#E1E3DE] rounded-[10px]">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-[#434840]">
            <span className="w-2.5 h-2.5 rounded-full bg-[#1F6306]" />
            {isMuni ? "Observed" : "Observed avg"}
          </span>
          <span className="text-[26px] font-bold text-[#1B3315]">{observed}</span>
        </div>
        <div className={`flex flex-col gap-1 p-3.5 bg-white border border-dashed rounded-[10px] ${hasPred ? "border-[#EAB308]" : "border-[#E1E3DE]"}`}>
          <span className="flex items-center gap-1.5 text-xs font-semibold text-[#434840]">
            <span className="w-2.5 h-2.5 rounded-full border-[2.5px] border-[#EAB308] box-border" />
            {isMuni ? "Predicted" : "Predicted avg"}
          </span>
          <span className="text-[26px] font-bold text-[#1B3315]">{hasPred ? predicted : "N/A"}</span>
        </div>
      </div>

      {/* Dumbbell scale */}
      <div className="flex flex-col gap-1.5">
        <div className="relative h-7">
          <div className="absolute inset-x-0 top-[13px] h-0.5 bg-[#E1E3DE]" />
          {stats?.min != null && (
            <div
              className="absolute top-[9px] h-2.5 rounded-full bg-[#74C476]/25"
              style={{ left: pct(stats.min, lo, hi), width: `calc(${pct(stats.max, lo, hi)} - ${pct(stats.min, lo, hi)})` }}
            />
          )}
          {hasPred && (
            <div
              className="absolute top-3 h-1 bg-[#EAB308]"
              style={{ left: pct(left, lo, hi), width: `calc(${pct(right, lo, hi)} - ${pct(left, lo, hi)})` }}
            />
          )}
          <div
            className="absolute top-1.5 w-4 h-4 -ml-2 rounded-full bg-[#1F6306] border-2 border-[#F8FAF5] box-border"
            style={{ left: pct(observed, lo, hi) }}
            title={`Observed ${observed} mt/ha`}
          />
          {hasPred && (
            <div
              className="absolute top-1.5 w-4 h-4 -ml-2 rounded-full bg-[#F8FAF5] border-[3px] border-[#EAB308] box-border"
              style={{ left: pct(predicted, lo, hi) }}
              title={`Predicted ${predicted} mt/ha`}
            />
          )}
        </div>
        <div className="relative h-3.5 text-[11px] text-[#9CA3AF]">
          {ticks.map((t, i) => (
            <span
              key={t}
              className="absolute"
              style={
                i === 0 ? { left: 0 }
                : i === ticks.length - 1 ? { right: 0 }
                : { left: pct(t, lo, hi), transform: "translateX(-50%)" }
              }
            >
              {t.toFixed(1)}
            </span>
          ))}
        </div>
        {stats?.min != null && (
          <span className="text-[11px] text-[#6B7280]">
            mt/ha · Shaded: province range, {stats.min} to {stats.max}
          </span>
        )}
      </div>

      {/* Summary sentence */}
      {hasPred ? (
        <span className="text-sm leading-5 text-[#434840]">
          The model{" "}
          <b className="text-[#191C1A]">
            {residual < 0 ? "over-predicts" : residual > 0 ? "under-predicts" : "matches"}
            {residual !== 0 && ` by ${Math.abs(residual)} mt/ha`}
          </b>{" "}
          ({errPct}%) {isMuni ? `for ${selection.name}` : "at the province level"}.
        </span>
      ) : (
        <span className="text-sm leading-5 text-[#6B7280]">
          {predMeta?.has_predictions
            ? `No prediction for ${isMuni ? selection.name : "the province"} in ${season} ${year}.`
            : "No model predictions loaded yet. Once CNN-LSTM output is imported, the predicted yield will appear here."}
        </span>
      )}

      {/* Stat tiles */}
      {hasPred && (
        <div className="grid grid-cols-3 gap-2">
          <Tile
            value={compareResp?.stats?.mae ?? "N/A"}
            label={isMuni ? "Province MAE" : "MAE mt/ha"}
          />
          <Tile
            value={fmtSigned(residual)}
            label="Residual"
            tone={residual >= 0 ? "text-[#16A34A]" : "text-[#EF4444]"}
          />
          {isMuni ? (
            <Tile value={`${errPct}%`} label="Error" />
          ) : (
            <Tile value={compareResp?.stats?.count_predicted ?? stats?.count} label="Municipalities" />
          )}
        </div>
      )}

      <p className="text-xs text-[#9CA3AF]">
        {isMuni ? "Click “back to all” on the map for the province view." : "Switch to the Predicted layer or click a municipality."}
      </p>
    </Shell>
  );
}
