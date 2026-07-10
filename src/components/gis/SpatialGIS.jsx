import React, { useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import DashboardSidebar from "../layout/DashboardSidebar";
import MapControls from "../layout/MapControls";

const DEFAULT_CENTER = [14.2117, 121.1653];
const DEFAULT_ZOOM = 12;

const ZONE_MARKER = { name: "Brgy. San Isidro, Calamba", position: DEFAULT_CENTER, status: "Above Expected" };

const markerIcon = L.divIcon({
  className: "",
  html: `
    <span class="relative flex items-center justify-center w-8 h-8 -translate-x-1/2 -translate-y-1/2">
      <span class="absolute w-8 h-8 rounded-full bg-[#1B3315]/20"></span>
      <span class="w-4 h-4 rounded-full bg-[#1B3315] border-2 border-white shadow-[0_1px_2px_rgba(0,0,0,0.05)]"></span>
    </span>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const CITY_FILTERS = ["All Cities", "Calamba", "Los Baños"];

const EFFICIENCY_BADGES = [
  { label: "Moderate", bg: "bg-[#FACC15]/50", text: "text-[#241A00]" },
  { label: "High Yield", bg: "bg-[#3B9E1C]/50", text: "text-[#002204]" },
  { label: "Underused", bg: "bg-[#E1E3DE]", text: "text-[#434840]" },
];

const YIELD_VS_EXPECTED = [
  { label: "Corn", percent: 85, value: "85%", color: "#1B6D24" },
  { label: "Rice", percent: 65, value: "65%", color: "#CDA722" },
];

const LEGEND_LABELS = ["Low Yield", "Expected", "High Yield"];

const ACTIVE_LAYERS = ["Yield Points", "Boundaries"];

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
  const mapRef = useRef(null);
  const [viewType, setViewType] = useState("heatmap");
  const [season, setSeason] = useState("wet");
  const [cityFilter, setCityFilter] = useState("All Cities");
  const [layers, setLayers] = useState({ yieldPoints: true, landUse: false, boundaries: true });

  const cityLabel = useMemo(
    () => (city ? city.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Laguna Province"),
    [city]
  );

  const toggleLayer = (key) => setLayers((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="flex w-full h-screen bg-[#F8FAF5] font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      <DashboardSidebar active="map" city={city} />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Top Header */}
        <header className="flex items-center justify-between px-10 h-20 shrink-0 bg-white border-b border-[#E5E7EB]">
          <h1 className="text-2xl font-bold text-[#1F2937] tracking-[-0.6px]">
            Spatial GIS Visualization and Analysis
          </h1>
          <span className="text-sm font-medium text-[#6B7280]">{cityLabel}</span>
        </header>

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

          {/* Center — Map */}
          <section className="relative flex-1 min-w-0 h-full bg-[#E5E7EB]">
            <MapContainer
              ref={mapRef}
              center={DEFAULT_CENTER}
              zoom={DEFAULT_ZOOM}
              zoomControl={false}
              style={{ height: "100%", width: "100%" }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <Marker position={ZONE_MARKER.position} icon={markerIcon}>
                <Popup>
                  <strong>{ZONE_MARKER.name}</strong>
                  <br />
                  Yield status: {ZONE_MARKER.status}
                </Popup>
              </Marker>
            </MapContainer>

            <div className="absolute left-6 right-6 top-6 z-[500] flex justify-center pointer-events-none">
              <div className="w-full max-w-[473px] bg-white/90 backdrop-blur-sm shadow-[0_10px_15px_-3px_rgba(0,0,0,0.1),0_4px_6px_-4px_rgba(0,0,0,0.1)] rounded-lg pointer-events-auto">
                <div className="relative flex items-center">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="absolute left-4 text-[#9CA3AF]">
                    <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
                    <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                  <input
                    type="text"
                    placeholder="Search municipalities, crops, or indicators..."
                    className="w-full pl-11 pr-4 py-3.5 text-sm text-[#374151] bg-transparent outline-none placeholder:text-[#6B7280]"
                  />
                </div>
              </div>
            </div>

            <MapControls
              onZoomIn={() => mapRef.current?.zoomIn()}
              onZoomOut={() => mapRef.current?.zoomOut()}
              onRecenter={() => mapRef.current?.setView(DEFAULT_CENTER, DEFAULT_ZOOM)}
            />
          </section>

          {/* Right Panel — Context Cards */}
          <section className="w-[460px] shrink-0 h-full overflow-y-auto bg-white">
            <div className="flex flex-col gap-6 p-6">
              {/* 1. Selected Zone Detail */}
              <div className="flex flex-col gap-3 p-6 bg-[#F8FAF5] border border-[#C3C8BD] rounded-xl w-full">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg text-[#061E04]">{ZONE_MARKER.name}</h3>
                  <svg width="16" height="20" viewBox="0 0 24 24" fill="none" stroke="#74796F" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </div>
                <p className="text-sm leading-5 text-[#434840]">
                  Primary agricultural zone focusing on organic rice and corn production. Current soil health is
                  optimal.
                </p>
              </div>

              {/* 2. City Status Badges */}
              <Card title="Efficiency Ratings">
                <div className="flex flex-wrap gap-2">
                  {EFFICIENCY_BADGES.map((badge) => (
                    <span
                      key={badge.label}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs ${badge.bg} ${badge.text}`}
                    >
                      <span className="w-2 h-2 rounded-full bg-current" />
                      {badge.label}
                    </span>
                  ))}
                </div>
              </Card>

              {/* 3. Yield vs Expected */}
              <Card title="Yield vs Expected">
                <div className="flex flex-col gap-3">
                  {YIELD_VS_EXPECTED.map((row) => (
                    <div key={row.label} className="flex flex-col gap-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[#191C1A]">{row.label}</span>
                        <span className="text-[#061E04]">{row.value}</span>
                      </div>
                      <div className="relative h-2 bg-[#E1E3DE] rounded-full overflow-hidden">
                        <div
                          className="absolute inset-y-0 left-0 rounded-full"
                          style={{ width: `${row.percent}%`, background: row.color }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* 4. Yield Heatmap Legend */}
              <Card title="Yield Heatmap Legend">
                <div className="flex flex-col gap-1">
                  <div className="h-4 rounded-full bg-gradient-to-r from-[#FECACA] via-[#FDE047] to-[#16A34A]" />
                  <div className="flex justify-between text-xs text-[#434840]">
                    {LEGEND_LABELS.map((label) => (
                      <span key={label}>{label}</span>
                    ))}
                  </div>
                </div>
              </Card>

              {/* 5. Active Layers Summary */}
              <Card title="Active Layers">
                <div className="flex flex-col gap-1.5">
                  {ACTIVE_LAYERS.map((layer) => (
                    <div key={layer} className="flex items-center gap-3">
                      <span className="w-2.5 h-2.5 rounded-sm bg-[#1B6D24]" />
                      <span className="text-sm text-[#191C1A]">{layer}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
