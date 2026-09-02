import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import DashboardSidebar from "../layout/DashboardSidebar";
import Navbar from "../layout/Navbar";
import LagunaMap from "./LagunaMap";
import { useAuth } from "../../context/AuthContext";
import { yieldApi } from "../../lib/api";

function ToggleSwitch({ checked, onChange, icon, label, disabled = false, hint }) {
  return (
    <div className={`flex items-center justify-between py-1 ${disabled ? "opacity-50" : ""}`}>
      <div className="flex items-center gap-3">
        <span className="text-[#74796F]">{icon}</span>
        <div className="flex flex-col">
          <span className="text-base text-[#191C1A]">{label}</span>
          {disabled && hint && <span className="text-[11px] text-[#9CA3AF]">{hint}</span>}
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={onChange}
        className={`relative w-11 h-6 rounded-full transition-colors ${
          disabled ? "bg-[#E1E3DE] cursor-not-allowed" : checked ? "bg-[#1B6D24]" : "bg-[#E1E3DE]"
        }`}
      >
        <span
          className={`absolute left-0 top-0.5 block w-5 h-5 rounded-full bg-white border transition-transform ${
            checked ? "translate-x-[22px] border-white" : "translate-x-0.5 border-[#D1D5DB]"
          }`}
        />
      </button>
    </div>
  );
}

function Card({ title, children }) {
  return (
    <div className="flex flex-col gap-3 p-6 bg-[#F8FAF5] border border-[#C3C8BD] rounded-xl w-full">
      <h4 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">{title}</h4>
      {children}
    </div>
  );
}

export default function SpatialGIS() {
  const { city } = useParams();
  const { isAuthenticated, loading } = useAuth();
  // Chrome is decided by WHO is viewing, not the URL:
  //   logged in  -> portal side nav
  //   public     -> top nav only
  const isPublic = !isAuthenticated;

  const [viewType, setViewType] = useState("heatmap");
  const [layers, setLayers] = useState({ boundaries: true });
  const [selection, setSelection] = useState(null); // reported by <LagunaMap />
  const [municipalities, setMunicipalities] = useState([]); // [{ id, name }] from the map
  const [activeCityId, setActiveCityId] = useState(null); // null = whole province

  // Filters, backed by the real data available in the DB.
  const [meta, setMeta] = useState({ years: [], seasons: [] });
  const [season, setSeason] = useState(null);
  const [year, setYear] = useState(null);
  const [yieldResp, setYieldResp] = useState(null); // { stats, records }
  const [yieldLoading, setYieldLoading] = useState(false);
  // SYNTHETIC per-barangay yields for the drilled-in municipality (sample data).
  const [barangayResp, setBarangayResp] = useState(null); // { synthetic, stats, records }

  // CNN-LSTM predictions overlay (empty until model output is loaded).
  const [dataSource, setDataSource] = useState("observed"); // "observed" | "predicted"
  const [predMeta, setPredMeta] = useState({ has_predictions: false });
  const [compareResp, setCompareResp] = useState(null); // { stats, records } observed vs predicted

  const cityLabel = useMemo(
    () => (city ? city.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Laguna Province"),
    [city]
  );

  const toggleLayer = (key) => setLayers((prev) => ({ ...prev, [key]: !prev[key] }));

  // Which years/seasons actually have data -> populate the filters, default to
  // the most recent year and the first available season.
  useEffect(() => {
    yieldApi
      .meta()
      .then((m) => {
        setMeta(m);
        if (m.years?.length) setYear(m.years[m.years.length - 1]);
        if (m.seasons?.length) setSeason(m.seasons[0]);
      })
      .catch(() => {});
  }, []);

  // Fetch observed yields whenever the year/season selection changes.
  useEffect(() => {
    if (!year || !season) return;
    let active = true;
    setYieldLoading(true);
    yieldApi
      .municipalities(year, season)
      .then((resp) => active && setYieldResp(resp))
      .catch(() => active && setYieldResp(null))
      .finally(() => active && setYieldLoading(false));
    return () => {
      active = false;
    };
  }, [year, season]);

  // Fetch synthetic per-barangay yields when a municipality is drilled into.
  // Cleared when back at the province view.
  useEffect(() => {
    if (!activeCityId || !year || !season) {
      setBarangayResp(null);
      return;
    }
    let active = true;
    yieldApi
      .barangays(activeCityId, year, season)
      .then((resp) => active && setBarangayResp(resp))
      .catch(() => active && setBarangayResp(null));
    return () => {
      active = false;
    };
  }, [activeCityId, year, season]);

  // Are there any CNN-LSTM predictions loaded at all? (gates the Predicted view)
  useEffect(() => {
    yieldApi.predictionsMeta().then(setPredMeta).catch(() => {});
  }, []);

  // Observed vs predicted (+ residual) for the current year/season.
  useEffect(() => {
    if (!year || !season) return;
    let active = true;
    yieldApi
      .compare(year, season)
      .then((r) => active && setCompareResp(r))
      .catch(() => active && setCompareResp(null));
    return () => {
      active = false;
    };
  }, [year, season]);

  // Shape the records for the map (id -> { yield, is_proxy }) and the panels.
  const yieldByMuni = useMemo(() => {
    const out = {};
    for (const r of yieldResp?.records ?? []) out[r.municipality_id] = { yield: r.yield, is_proxy: r.is_proxy };
    return out;
  }, [yieldResp]);

  // Predicted values shaped for the map, plus a colour scale over predictions.
  const predByMuni = useMemo(() => {
    const out = {};
    for (const r of compareResp?.records ?? []) {
      if (r.predicted != null) out[r.municipality_id] = { yield: r.predicted, is_proxy: false };
    }
    return out;
  }, [compareResp]);
  const predScale = useMemo(() => {
    const vals = Object.values(predByMuni).map((x) => x.yield);
    return vals.length ? { min: Math.min(...vals), max: Math.max(...vals) } : null;
  }, [predByMuni]);

  // Synthetic barangay yields shaped for the map, with a per-municipality colour
  // scale (local min/max) so intra-municipality variation is visible on drill-in.
  const yieldByBarangay = useMemo(() => {
    const out = {};
    for (const r of barangayResp?.records ?? []) out[r.barangay_id] = { yield: r.yield };
    return out;
  }, [barangayResp]);
  const barangayScale = useMemo(
    () =>
      barangayResp?.stats?.min != null
        ? { min: barangayResp.stats.min, max: barangayResp.stats.max }
        : null,
    [barangayResp]
  );

  const showingPredicted = dataSource === "predicted" && predMeta.has_predictions;
  const mapYieldByMuni = showingPredicted ? predByMuni : yieldByMuni;
  const mapColorScale = showingPredicted
    ? predScale
    : yieldResp?.stats
    ? { min: yieldResp.stats.min, max: yieldResp.stats.max }
    : null;
  const heatmapOn =
    viewType === "heatmap" && layers.boundaries && (showingPredicted ? !!predScale : !!yieldResp);
  // Barangay choropleth (synthetic) only in the observed heatmap view.
  const barangayHeatmapOn = heatmapOn && !showingPredicted && !!barangayScale;
  const mapYieldByBarangay = barangayHeatmapOn ? yieldByBarangay : null;
  const selectedYield = selection?.level === "municipality" ? yieldByMuni[selection.id] : null;
  const selectedCompare =
    selection?.level === "municipality"
      ? (compareResp?.records ?? []).find((r) => r.municipality_id === selection.id)
      : null;

  // When the map's drill state changes (e.g. the user clicked a municipality),
  // mirror it into the City filter so the two never disagree.
  const handleSelection = (sel) => {
    setSelection(sel);
    setActiveCityId(sel.level === "municipality" ? sel.id : null);
  };

  // While the session is being restored, don't render either chrome (avoids a
  // public->portal flash for a logged-in user refreshing on /yield-map).
  if (loading) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-[#F8FAF5] text-[#6B7280]">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex w-full h-screen bg-[#F8FAF5] font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      {!isPublic && <DashboardSidebar active="map" />}

      <div className="flex flex-col flex-1 min-w-0">
        {isPublic ? (
          /* Public view: use the public site navigation bar (dark band keeps its white text legible) */
          <div className="shrink-0 bg-[#0B2005]">
            <Navbar active="Yield Map" />
          </div>
        ) : (
          /* Portal view: dashboard header */
          <header className="flex items-center justify-between px-10 h-20 shrink-0 bg-white border-b border-[#E5E7EB]">
            <h1 className="text-2xl font-bold text-[#1F2937] tracking-[-0.6px]">
              Spatial GIS Visualization and Analysis
            </h1>
            <span className="text-sm font-medium text-[#6B7280]">{cityLabel}</span>
          </header>
        )}

        <div className="flex flex-1 min-h-0">
          {/* Left Panel — Map Controls */}
          <section className="w-[400px] shrink-0 h-full overflow-y-auto bg-white border-r border-[#C3C8BD]">
            <div className="flex flex-col gap-12 p-6">
              {/* View Type — Yield Heatmap is live (real observed data). Land Parcels
                  needs parcel geometry we don't have, so it stays disabled. */}
              <div className="flex flex-col gap-3">
                <h2 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">View Type</h2>
                <div className="grid grid-cols-2 gap-1">
                  <button
                    type="button"
                    onClick={() => setViewType("heatmap")}
                    className={`flex flex-col items-center gap-1 py-3 rounded-lg border text-sm font-semibold ${
                      viewType === "heatmap"
                        ? "bg-[#3B9E1C] border-[#1B6D24] text-white"
                        : "bg-[#F8FAF5] border-[#C3C8BD] text-[#191C1A]"
                    }`}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 12h4l3 8 4-16 3 8h4" />
                    </svg>
                    Yield Heatmap
                  </button>
                  <div
                    title="Needs land-parcel data"
                    className="flex flex-col items-center gap-1 py-3 rounded-lg border bg-[#F8FAF5] border-[#C3C8BD] text-[#191C1A] text-sm font-semibold opacity-50 cursor-not-allowed"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 3h8v8H3zM13 3h8v8h-8zM3 13h8v8H3zM13 13h8v8h-8z" />
                    </svg>
                    Land Parcels
                  </div>
                </div>
              </div>

              {/* Data source — Observed is live; Predicted lights up once CNN-LSTM
                  model output is loaded (municipality_predictions). */}
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Data Source</h2>
                  {!predMeta.has_predictions && (
                    <span className="text-[10px] font-medium text-[#9CA3AF]">Predicted: needs model output</span>
                  )}
                </div>
                <div className="flex p-1 gap-1 bg-[#ECEFEA] rounded-lg">
                  <button
                    type="button"
                    onClick={() => setDataSource("observed")}
                    className={`flex-1 py-2 rounded text-sm font-medium transition-colors ${
                      dataSource === "observed" ? "bg-[#3B9E1C] text-white shadow-sm" : "text-[#4B5563]"
                    }`}
                  >
                    Observed
                  </button>
                  <button
                    type="button"
                    onClick={() => predMeta.has_predictions && setDataSource("predicted")}
                    disabled={!predMeta.has_predictions}
                    className={`flex-1 py-2 rounded text-sm font-medium transition-colors ${
                      dataSource === "predicted" && predMeta.has_predictions
                        ? "bg-[#3B9E1C] text-white shadow-sm"
                        : "text-[#4B5563]"
                    } ${!predMeta.has_predictions ? "opacity-40 cursor-not-allowed" : ""}`}
                  >
                    Predicted
                  </button>
                </div>
              </div>

              {/* Filters */}
              <div className="flex flex-col gap-3">
                <h2 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Filters</h2>
                <div className="flex flex-col gap-6">
                  {/* Season — live: filters the observed-yield choropleth. */}
                  <div className="flex flex-col gap-1">
                    <label className="text-sm text-[#434840]">Season</label>
                    <div className="flex gap-1">
                      {(meta.seasons.length ? meta.seasons : ["Dry", "Wet"]).map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => setSeason(opt)}
                          className={`px-3 py-1.5 rounded-full border text-sm ${
                            season === opt
                              ? "bg-[#3B9E1C] border-[#3B9E1C] text-white"
                              : "bg-[#ECEFEA] border-[#C3C8BD] text-[#191C1A]"
                          }`}
                        >
                          {opt} Season
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* City — fully functional: drives the map's drill-down. */}
                  <div className="flex flex-col gap-1">
                    <label htmlFor="city-filter" className="text-sm text-[#434840]">
                      City / Municipality
                    </label>
                    <div className="relative">
                      <select
                        id="city-filter"
                        value={activeCityId ?? ""}
                        onChange={(e) => setActiveCityId(e.target.value ? Number(e.target.value) : null)}
                        className="w-full appearance-none px-3 py-3 pr-9 bg-white border border-[#C3C8BD] rounded-lg text-base text-[#191C1A] outline-none focus:border-[#3B9E1C] cursor-pointer"
                      >
                        <option value="">All Cities</option>
                        {municipalities.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name}
                          </option>
                        ))}
                      </select>
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 14 14"
                        fill="none"
                        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2"
                      >
                        <path d="M2 4l5 5 5-5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                    {municipalities.length === 0 && (
                      <span className="text-[11px] text-[#9CA3AF]">Loading municipalities…</span>
                    )}
                  </div>

                  {/* Year — live: from the years that actually have data. */}
                  <div className="flex flex-col gap-1">
                    <label htmlFor="year-filter" className="text-sm text-[#434840]">Year</label>
                    <div className="relative">
                      <select
                        id="year-filter"
                        value={year ?? ""}
                        onChange={(e) => setYear(e.target.value ? Number(e.target.value) : null)}
                        disabled={!meta.years.length}
                        className="w-full appearance-none px-3 py-3 pr-9 bg-white border border-[#C3C8BD] rounded-lg text-base text-[#191C1A] outline-none focus:border-[#3B9E1C] cursor-pointer disabled:opacity-50"
                      >
                        {meta.years.length ? (
                          meta.years.map((y) => (
                            <option key={y} value={y}>
                              {y}
                            </option>
                          ))
                        ) : (
                          <option>Loading…</option>
                        )}
                      </select>
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 14 14"
                        fill="none"
                        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2"
                      >
                        <path d="M2 4l5 5 5-5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </div>
                </div>
              </div>

              <div className="border-t border-[#C3C8BD]" />

              {/* Map Layers — Boundaries is live; land-use still needs its data layer. */}
              <div className="flex flex-col gap-3">
                <h2 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Map Layers</h2>
                <div className="flex flex-col gap-3">
                  <ToggleSwitch
                    checked={false}
                    disabled
                    hint="Needs land-use data"
                    label="Land use"
                    icon={
                      <svg width="22" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M2 17l10 5 10-5M2 12l10 5 10-5M12 2L2 7l10 5 10-5-10-5z" />
                      </svg>
                    }
                  />
                  <ToggleSwitch
                    checked={layers.boundaries}
                    onChange={() => toggleLayer("boundaries")}
                    label="Boundaries"
                    icon={
                      <svg width="20" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 17l6-12 6 8 6-10" strokeDasharray="3 3" />
                      </svg>
                    }
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Center — shared map */}
          <LagunaMap
            boundariesVisible={layers.boundaries}
            onSelectionChange={handleSelection}
            focusMunicipalityId={activeCityId}
            onMunicipalitiesLoaded={setMunicipalities}
            heatmap={heatmapOn}
            yieldByMuni={mapYieldByMuni}
            colorScale={mapColorScale}
            yieldByBarangay={mapYieldByBarangay}
            barangayColorScale={barangayScale}
            yieldKey={`${showingPredicted ? "pred" : "obs"}-${year}-${season}`}
            barangayKey={`brgy-${activeCityId}-${year}-${season}-${barangayResp?.stats?.count ?? 0}`}
          />

          {/* Right Panel — Context */}
          <section className="w-[460px] shrink-0 h-full overflow-y-auto bg-white">
            <div className="flex flex-col gap-6 p-6">
              {/* Selected area (reflects the drill-down state from the map) */}
              <div className="flex flex-col gap-2 p-6 bg-[#F8FAF5] border border-[#C3C8BD] rounded-xl w-full">
                <span className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Selected Area</span>
                {selection?.level === "municipality" ? (
                  <>
                    <h3 className="text-lg font-bold text-[#061E04]">{selection.name}</h3>
                    <p className="text-sm leading-5 text-[#434840]">
                      {selection.barangayCount != null ? `${selection.barangayCount} barangays` : "Loading barangays…"}.
                      Hover a barangay on the map to see its name.
                    </p>
                  </>
                ) : (
                  <>
                    <h3 className="text-lg font-bold text-[#061E04]">Laguna Province</h3>
                    <p className="text-sm leading-5 text-[#434840]">
                      {selection?.municipalityCount != null
                        ? `${selection.municipalityCount} municipalities mapped.`
                        : "Loading boundaries…"}{" "}
                      Click a municipality to explore its barangays.
                    </p>
                  </>
                )}
              </div>

              {/* Active layers — reflects the real toggles */}
              <Card title="Active Layers">
                <div className="flex flex-col gap-1.5">
                  {heatmapOn && (
                    <div className="flex items-center gap-3">
                      <span className="w-2.5 h-2.5 rounded-sm bg-[#41AB5D]" />
                      <span className="text-sm text-[#191C1A]">Yield Heatmap</span>
                    </div>
                  )}
                  {layers.boundaries && (
                    <div className="flex items-center gap-3">
                      <span className="w-2.5 h-2.5 rounded-sm bg-[#1B6D24]" />
                      <span className="text-sm text-[#191C1A]">Boundaries</span>
                    </div>
                  )}
                  {!heatmapOn && !layers.boundaries && (
                    <span className="text-sm text-[#9CA3AF]">No layers active.</span>
                  )}
                </div>
              </Card>

              {/* Rice yield — real observed data (mt/ha) for the current filters */}
              <Card title={`Rice Yield — ${season ?? ""} ${year ?? ""}`.trim()}>
                {yieldLoading ? (
                  <p className="text-sm text-[#6B7280]">Loading yield…</p>
                ) : selection?.level === "municipality" ? (
                  selectedYield?.yield != null ? (
                    <div className="flex flex-col gap-1">
                      <span className="text-3xl font-bold text-[#1B3315]">
                        {selectedYield.yield}
                        <span className="text-base font-normal text-[#6B7280]"> mt/ha</span>
                      </span>
                      <span className="text-sm text-[#434840]">
                        Observed average yield for {selection.name}.
                        {selectedYield.is_proxy && " (Estimated — source proxy value.)"}
                      </span>
                      {barangayHeatmapOn && barangayResp?.stats?.count > 0 && (
                        <div className="mt-1 flex items-start gap-2 rounded-lg bg-[#FEF3C7] border border-[#FDE68A] px-3 py-2">
                          <span className="mt-0.5 inline-flex shrink-0 items-center rounded-full bg-[#F59E0B] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                            Sample
                          </span>
                          <span className="text-xs leading-4 text-[#92400E]">
                            The per-barangay colours are <b>sample data</b>, estimated from this
                            municipality's yield (not measured). Only the municipality value above is real.
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-[#6B7280]">
                      No observed yield for {selection.name} in {season} {year}.
                    </p>
                  )
                ) : yieldResp?.stats?.avg != null ? (
                  <div className="flex flex-col gap-3">
                    <div className="flex flex-col gap-1">
                      <span className="text-3xl font-bold text-[#1B3315]">
                        {yieldResp.stats.avg}
                        <span className="text-base font-normal text-[#6B7280]"> mt/ha</span>
                      </span>
                      <span className="text-sm text-[#434840]">
                        Province average across {yieldResp.stats.count} municipalities.
                      </span>
                    </div>
                    <div className="flex gap-4 text-sm text-[#434840]">
                      <span>Low <b className="text-[#191C1A]">{yieldResp.stats.min}</b></span>
                      <span>High <b className="text-[#191C1A]">{yieldResp.stats.max}</b></span>
                    </div>
                    <p className="text-xs text-[#9CA3AF]">Click a municipality for its value.</p>
                  </div>
                ) : (
                  <p className="text-sm text-[#6B7280]">No yield data for {season} {year}.</p>
                )}
              </Card>

              {/* CNN-LSTM prediction — observed vs predicted (+ residual). Empty
                  until model output is loaded into municipality_predictions. */}
              <Card title="CNN-LSTM Prediction">
                {!predMeta.has_predictions ? (
                  <p className="text-sm leading-5 text-[#6B7280]">
                    No model predictions loaded yet. Once CNN-LSTM output is imported, predicted yield
                    and the observed-vs-predicted residual will appear here and as a “Predicted” map layer.
                  </p>
                ) : selection?.level === "municipality" ? (
                  selectedCompare?.predicted != null ? (
                    <div className="flex flex-col gap-2">
                      <div className="flex gap-6">
                        <div className="flex flex-col">
                          <span className="text-xs text-[#6B7280]">Predicted</span>
                          <span className="text-2xl font-bold text-[#1B3315]">{selectedCompare.predicted}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-xs text-[#6B7280]">Observed</span>
                          <span className="text-2xl font-bold text-[#1B3315]">
                            {selectedCompare.observed ?? "—"}
                          </span>
                        </div>
                      </div>
                      {selectedCompare.residual != null && (
                        <span className="text-sm text-[#434840]">
                          Residual (obs − pred):{" "}
                          <b className={selectedCompare.residual >= 0 ? "text-[#16A34A]" : "text-[#EF4444]"}>
                            {selectedCompare.residual > 0 ? "+" : ""}
                            {selectedCompare.residual} mt/ha
                          </b>
                        </span>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-[#6B7280]">No prediction for {selection.name} in {season} {year}.</p>
                  )
                ) : compareResp?.stats?.predicted_avg != null ? (
                  <div className="flex flex-col gap-2">
                    <div className="flex gap-6">
                      <div className="flex flex-col">
                        <span className="text-xs text-[#6B7280]">Predicted avg</span>
                        <span className="text-2xl font-bold text-[#1B3315]">{compareResp.stats.predicted_avg}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs text-[#6B7280]">Observed avg</span>
                        <span className="text-2xl font-bold text-[#1B3315]">{compareResp.stats.observed_avg}</span>
                      </div>
                    </div>
                    {compareResp.stats.mae != null && (
                      <span className="text-sm text-[#434840]">
                        Model MAE: <b className="text-[#191C1A]">{compareResp.stats.mae} mt/ha</b>{" "}
                        over {compareResp.stats.count_predicted} municipalities
                      </span>
                    )}
                    <p className="text-xs text-[#9CA3AF]">Switch to the Predicted layer or click a municipality.</p>
                  </div>
                ) : (
                  <p className="text-sm text-[#6B7280]">No predictions for {season} {year}.</p>
                )}
              </Card>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
