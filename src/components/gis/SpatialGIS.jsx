import React, { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import DashboardSidebar from "../layout/DashboardSidebar";
import Navbar from "../layout/Navbar";
import LagunaMap from "./LagunaMap";
import { useAuth } from "../../context/AuthContext";

const CITY_FILTERS = ["All Cities", "Calamba", "Los Baños"];

function ToggleSwitch({ checked, onChange, icon, label }) {
  return (
    <div className="flex items-center justify-between py-1">
      <div className="flex items-center gap-3">
        <span className="text-[#74796F]">{icon}</span>
        <span className="text-base text-[#191C1A]">{label}</span>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={onChange}
        className={`relative w-11 h-6 rounded-full transition-colors ${checked ? "bg-[#1B6D24]" : "bg-[#E1E3DE]"}`}
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
  const [season, setSeason] = useState("wet");
  const [cityFilter, setCityFilter] = useState("All Cities");
  const [layers, setLayers] = useState({ yieldPoints: true, landUse: false, boundaries: true });
  const [selection, setSelection] = useState(null); // reported by <LagunaMap />

  const cityLabel = useMemo(
    () => (city ? city.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Laguna Province"),
    [city]
  );

  const toggleLayer = (key) => setLayers((prev) => ({ ...prev, [key]: !prev[key] }));

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
              {/* View Type */}
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
                  <button
                    type="button"
                    onClick={() => setViewType("parcels")}
                    className={`flex flex-col items-center gap-1 py-3 rounded-lg border text-sm font-semibold ${
                      viewType === "parcels"
                        ? "bg-[#3B9E1C] border-[#1B6D24] text-white"
                        : "bg-[#F8FAF5] border-[#C3C8BD] text-[#191C1A]"
                    }`}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 3h8v8H3zM13 3h8v8h-8zM3 13h8v8H3zM13 13h8v8h-8z" />
                    </svg>
                    Land Parcels
                  </button>
                </div>
              </div>

              {/* Filters */}
              <div className="flex flex-col gap-3">
                <h2 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Filters</h2>
                <div className="flex flex-col gap-6">
                  <div className="flex flex-col gap-1">
                    <label className="text-sm text-[#434840]">Season</label>
                    <div className="flex gap-1">
                      {[
                        { key: "dry", label: "Dry Season" },
                        { key: "wet", label: "Wet Season" },
                      ].map((opt) => (
                        <button
                          key={opt.key}
                          type="button"
                          onClick={() => setSeason(opt.key)}
                          className={`px-3 py-1.5 rounded-full border text-sm ${
                            season === opt.key
                              ? "bg-[#3B9E1C] border-[#3B9E1C] text-white"
                              : "bg-[#ECEFEA] border-[#C3C8BD] text-[#191C1A]"
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-sm text-[#434840]">City</label>
                    <div className="flex flex-wrap gap-1">
                      {CITY_FILTERS.map((option) => (
                        <button
                          key={option}
                          type="button"
                          onClick={() => setCityFilter(option)}
                          className={`px-3 py-1.5 rounded-full border text-sm ${
                            cityFilter === option
                              ? "bg-[#3B9E1C] border-[#3B9E1C] text-white"
                              : "bg-[#ECEFEA] border-[#C3C8BD] text-[#191C1A]"
                          }`}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-sm text-[#434840]">Year</label>
                    <button
                      type="button"
                      className="flex items-center justify-between px-3 py-3 bg-white border border-[#C3C8BD] rounded-lg text-base text-[#191C1A]"
                    >
                      2023 – 2024
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <path d="M2 4l5 5 5-5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <div className="border-t border-[#C3C8BD]" />

              {/* Map Layers */}
              <div className="flex flex-col gap-3">
                <h2 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Map Layers</h2>
                <div className="flex flex-col gap-3">
                  <ToggleSwitch
                    checked={layers.yieldPoints}
                    onChange={() => toggleLayer("yieldPoints")}
                    label="Yield Points"
                    icon={
                      <svg width="16" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 21s7-6.5 7-12a7 7 0 10-14 0c0 5.5 7 12 7 12z" />
                        <circle cx="12" cy="9" r="2.5" />
                      </svg>
                    }
                  />
                  <ToggleSwitch
                    checked={layers.landUse}
                    onChange={() => toggleLayer("landUse")}
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
          <LagunaMap boundariesVisible={layers.boundaries} onSelectionChange={setSelection} />

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
                  {[
                    ["yieldPoints", "Yield Points"],
                    ["landUse", "Land use"],
                    ["boundaries", "Boundaries"],
                  ]
                    .filter(([key]) => layers[key])
                    .map(([key, label]) => (
                      <div key={key} className="flex items-center gap-3">
                        <span className="w-2.5 h-2.5 rounded-sm bg-[#1B6D24]" />
                        <span className="text-sm text-[#191C1A]">{label}</span>
                      </div>
                    ))}
                  {!Object.values(layers).some(Boolean) && (
                    <span className="text-sm text-[#9CA3AF]">No layers active.</span>
                  )}
                </div>
              </Card>

              {/* Rice yield — honest pending state (no fabricated numbers) */}
              <Card title="Rice Yield">
                <p className="text-sm leading-5 text-[#6B7280]">
                  Rice yield metrics for the selected area will appear here once prediction data is available.
                </p>
              </Card>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
