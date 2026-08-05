import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import DashboardSidebar from "../layout/DashboardSidebar";
import MapControls from "../layout/MapControls";
import Navbar from "../layout/Navbar";
import { useAuth } from "../../context/AuthContext";
import { boundariesApi } from "../../lib/api";

const DEFAULT_CENTER = [14.2117, 121.1653];
const DEFAULT_ZOOM = 12;

// Basemap options (both free, no API key). "map" = clean light map; "satellite" = aerial imagery.
const BASEMAPS = {
  map: {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri, Maxar, Earthstar Geographics",
  },
};

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
  const mapRef = useRef(null);
  const [viewType, setViewType] = useState("heatmap");
  const [season, setSeason] = useState("wet");
  const [cityFilter, setCityFilter] = useState("All Cities");
  const [layers, setLayers] = useState({ yieldPoints: true, landUse: false, boundaries: true });
  const [muniGeo, setMuniGeo] = useState(null);
  const [basemap, setBasemap] = useState("map");
  const [provinceBounds, setProvinceBounds] = useState(null);

  const [selectedMuni, setSelectedMuni] = useState(null); // { id, name } when drilled into a city
  const [barangayGeo, setBarangayGeo] = useState(null);

  // Fetch municipality boundaries (GeoJSON) from PostGIS once.
  useEffect(() => {
    let active = true;
    boundariesApi
      .municipalities()
      .then((fc) => {
        if (!active) return;
        setMuniGeo(fc);
        // Compute the whole-province extent and frame the map to it on first load.
        try {
          const b = L.geoJSON(fc).getBounds();
          if (b.isValid()) {
            setProvinceBounds(b);
            mapRef.current?.fitBounds(b, { padding: [20, 20] });
          }
        } catch {
          /* ignore */
        }
      })
      .catch(() => {
        /* boundaries just won't draw if the API is down */
      });
    return () => {
      active = false;
    };
  }, []);

  // Boundary colours adapt to the basemap: green on the light map, bright yellow
  // (outline only) on satellite so they stay visible over green farmland.
  const sat = basemap === "satellite";
  const muniStyle = sat
    ? { color: "#FACC15", weight: 2, fillColor: "#FACC15", fillOpacity: 0 }
    : { color: "#1F6306", weight: 1.5, fillColor: "#3B9E1C", fillOpacity: 0.08 };
  const brgyStyle = sat
    ? { color: "#FDE047", weight: 1.2, fillColor: "#FDE047", fillOpacity: 0 }
    : { color: "#1B6D24", weight: 0.8, fillColor: "#3B9E1C", fillOpacity: 0.06 };

  // Drill into a municipality: load its barangays and zoom to its bounds.
  const drillInto = (feature, layer) => {
    setSelectedMuni({ id: feature.properties.municipality_id, name: feature.properties.name });
    setBarangayGeo(null);
    boundariesApi
      .barangays(feature.properties.municipality_id)
      .then((fc) => setBarangayGeo(fc))
      .catch(() => {});
    if (mapRef.current && layer.getBounds) {
      mapRef.current.fitBounds(layer.getBounds(), { padding: [24, 24] });
    }
  };

  const backToProvince = () => {
    setSelectedMuni(null);
    setBarangayGeo(null);
    // Return to the whole-province view, not the default pin location.
    if (provinceBounds) {
      mapRef.current?.fitBounds(provinceBounds, { padding: [20, 20] });
    } else {
      mapRef.current?.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    }
  };

  const onEachMunicipality = (feature, layer) => {
    layer.on({
      click: () => drillInto(feature, layer),
      mouseover: () => layer.setStyle({ weight: muniStyle.weight + 1.5, fillOpacity: muniStyle.fillOpacity + 0.2 }),
      mouseout: () => layer.setStyle(muniStyle),
    });
    if (feature.properties?.name) layer.bindTooltip(feature.properties.name, { sticky: true });
  };

  const onEachBarangay = (feature, layer) => {
    layer.on({
      mouseover: () => layer.setStyle({ weight: brgyStyle.weight + 1, fillOpacity: brgyStyle.fillOpacity + 0.24 }),
      mouseout: () => layer.setStyle(brgyStyle),
    });
    if (feature.properties?.name) layer.bindTooltip(feature.properties.name, { sticky: true });
  };

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
      {!isPublic && <DashboardSidebar active="map" city={city} />}

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

          {/* Center — Map */}
          <section className="relative flex-1 min-w-0 h-full bg-[#E5E7EB]">
            <MapContainer
              ref={mapRef}
              center={DEFAULT_CENTER}
              zoom={DEFAULT_ZOOM}
              zoomControl={false}
              style={{ height: "100%", width: "100%" }}
            >
              <TileLayer key={basemap} attribution={BASEMAPS[basemap].attribution} url={BASEMAPS[basemap].url} />
              {/* Municipality outlines (click one to drill into its barangays) */}
              {layers.boundaries && !selectedMuni && muniGeo && (
                <GeoJSON
                  key={`municipalities-${basemap}`}
                  data={muniGeo}
                  style={muniStyle}
                  onEachFeature={onEachMunicipality}
                />
              )}
              {/* Barangay outlines for the selected municipality */}
              {layers.boundaries && selectedMuni && barangayGeo && (
                <GeoJSON
                  key={`barangays-${selectedMuni.id}-${basemap}`}
                  data={barangayGeo}
                  style={brgyStyle}
                  onEachFeature={onEachBarangay}
                />
              )}
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

            {/* Back-to-province button, shown when drilled into a municipality */}
            {selectedMuni && (
              <button
                type="button"
                onClick={backToProvince}
                className="absolute left-6 top-20 z-[600] flex items-center gap-2 px-4 py-2 rounded-lg bg-white shadow-md text-sm font-semibold text-[#1F6306] hover:bg-[#F0FDF4]"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {selectedMuni.name} — back to all
              </button>
            )}

            {/* Basemap switcher */}
            <div className="absolute left-6 bottom-6 z-[500] flex rounded-lg overflow-hidden shadow-md bg-white text-sm font-medium">
              {[
                { key: "map", label: "Map" },
                { key: "satellite", label: "Satellite" },
              ].map((b) => (
                <button
                  key={b.key}
                  type="button"
                  onClick={() => setBasemap(b.key)}
                  className={`px-3 py-1.5 transition-colors ${
                    basemap === b.key ? "bg-[#1F6306] text-white" : "text-[#374151] hover:bg-[#F3F4F6]"
                  }`}
                >
                  {b.label}
                </button>
              ))}
            </div>

            <MapControls
              onZoomIn={() => mapRef.current?.zoomIn()}
              onZoomOut={() => mapRef.current?.zoomOut()}
              onRecenter={() =>
                provinceBounds
                  ? mapRef.current?.fitBounds(provinceBounds, { padding: [20, 20] })
                  : mapRef.current?.setView(DEFAULT_CENTER, DEFAULT_ZOOM)
              }
            />
          </section>

          {/* Right Panel — Context */}
          <section className="w-[460px] shrink-0 h-full overflow-y-auto bg-white">
            <div className="flex flex-col gap-6 p-6">
              {/* Selected area (reflects the drill-down state) */}
              <div className="flex flex-col gap-2 p-6 bg-[#F8FAF5] border border-[#C3C8BD] rounded-xl w-full">
                <span className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Selected Area</span>
                {selectedMuni ? (
                  <>
                    <h3 className="text-lg font-bold text-[#061E04]">{selectedMuni.name}</h3>
                    <p className="text-sm leading-5 text-[#434840]">
                      {barangayGeo ? `${barangayGeo.features.length} barangays` : "Loading barangays…"}. Hover a
                      barangay on the map to see its name.
                    </p>
                  </>
                ) : (
                  <>
                    <h3 className="text-lg font-bold text-[#061E04]">Laguna Province</h3>
                    <p className="text-sm leading-5 text-[#434840]">
                      {muniGeo ? `${muniGeo.features.length} municipalities mapped.` : "Loading boundaries…"} Click a
                      municipality to explore its barangays.
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
