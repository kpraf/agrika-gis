import React, { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import MapControls from "../layout/MapControls";
import { boundariesApi, onServerSlow } from "../../lib/api";

const DEFAULT_CENTER = [14.2117, 121.1653];
const DEFAULT_ZOOM = 11;

// Minimum time the "loading barangays" highlight stays up, so it's always
// perceptible even when the backend responds in a few hundred ms.
const MIN_LOADING_MS = 550;

// Drill-in fit options. `maxZoom` stops tiny municipalities (e.g. Victoria) from
// zooming in so far that the basemap goes white/blurry while high-zoom tiles load.
// The zoom stays animated; the loading highlight is deferred until it settles (see
// fitAndSignal / highlightReady) so its stroke is never caught in the zoom-stretch.
const FIT_OPTS = { padding: [24, 24], maxZoom: 13 };

// Basemap options. "map" = clean light map (CARTO); "satellite" = aerial imagery (Esri).
// CARTO raster tiles now require an API key to drop the "API key required" watermark.
// The key is read at build time from VITE_CARTO_API_KEY (see .env / DEPLOY.md). It is
// public by nature (sent from the browser with every tile request), so this is expected.
const CARTO_KEY = import.meta.env.VITE_CARTO_API_KEY;
const CARTO_KEY_PARAM = CARTO_KEY ? `?key=${CARTO_KEY}` : "";

const BASEMAPS = {
  map: {
    url: `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png${CARTO_KEY_PARAM}`,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri, Maxar, Earthstar Geographics",
  },
};

/**
 * Shared Laguna map used by both the Spatial GIS page and the Monitoring page.
 *
 * Props:
 *   boundariesVisible  - show/hide the boundary layer (default true)
 *   onSelectionChange  - called with the current selection whenever it changes:
 *       { level: "province", municipalityCount }  |
 *       { level: "municipality", id, name, barangayCount }
 */
// Sequential green ramp for the yield heatmap: light (low yield) -> dark (high).
const YIELD_RAMP = ["#EDF8E9", "#C7E9C0", "#A1D99B", "#74C476", "#41AB5D", "#238B45", "#005A32"];

function yieldColor(value, min, max) {
  if (value == null || min == null || max == null || max <= min) return YIELD_RAMP[3];
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  return YIELD_RAMP[Math.round(t * (YIELD_RAMP.length - 1))];
}

export default function LagunaMap({
  boundariesVisible = true,
  onSelectionChange,
  focusMunicipalityId = null,
  onMunicipalitiesLoaded,
  heatmap = false,
  yieldByMuni = null, // { [municipality_id]: { yield, is_proxy } }
  colorScale = null, // { min, max }
  yieldByBarangay = null, // { [barangay_id]: { yield } } — SYNTHETIC sample data
  barangayColorScale = null, // { min, max } local to the drilled-in municipality
  yieldKey = "", // changes (e.g. "2024-Dry") force the choropleth to restyle
  barangayKey = "", // changes force the barangay choropleth to restyle
}) {
  const mapRef = useRef(null);
  // Monotonic id of the latest drill-in, so a slower earlier fetch can't override
  // the barangays of a municipality the user has since clicked.
  const drillReqRef = useRef(0);
  // Token for the latest fit-to-bounds, so only its "settled" signal counts.
  const fitTokenRef = useRef(0);
  const [basemap, setBasemap] = useState("map");
  const [muniGeo, setMuniGeo] = useState(null);
  const [provinceBounds, setProvinceBounds] = useState(null);
  const [selectedMuni, setSelectedMuni] = useState(null); // { id, name }
  const [barangayGeo, setBarangayGeo] = useState(null);
  const [barangaysLoading, setBarangaysLoading] = useState(false);
  // GeoJSON feature of the municipality being drilled into. While its barangays load,
  // its own polygon shows a steady "loading" highlight instead of blanking the map.
  const [loadingFeature, setLoadingFeature] = useState(null);
  // True once the drill-in zoom has settled, so the highlight polygon is only drawn
  // at its final scale — never mid-animation, where Leaflet's zoom-stretch would
  // balloon its stroke into a thick border.
  const [highlightReady, setHighlightReady] = useState(false);

  // Search: query + barangay index (names only) + a pending barangay to zoom to
  // once its municipality's boundaries finish loading.
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [barangayIndex, setBarangayIndex] = useState([]);
  const [pendingBarangay, setPendingBarangay] = useState(null);

  // "server waking up" signal (free-tier cold start), scoped to the map overlay.
  const [serverSlow, setServerSlow] = useState(false);
  useEffect(() => onServerSlow(setServerSlow), []);

  // Keep the loading overlay up until the base tiles have actually painted, so
  // there's no blank-grey "frozen" gap. Safety timeout in case tiles never fire.
  const [tilesReady, setTilesReady] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setTilesReady(true), 6000);
    return () => clearTimeout(t);
  }, []);

  // Report the loaded municipality list to the parent (for the City filter),
  // via a ref so an inline callback doesn't retrigger the fetch effect.
  const muniListCbRef = useRef(onMunicipalitiesLoaded);
  muniListCbRef.current = onMunicipalitiesLoaded;

  // Fetch municipality boundaries once, and frame the whole province.
  useEffect(() => {
    let active = true;
    boundariesApi
      .municipalities()
      .then((fc) => {
        if (!active) return;
        setMuniGeo(fc);
        muniListCbRef.current?.(
          fc.features
            .map((f) => ({ id: f.properties.municipality_id, name: f.properties.name }))
            .sort((a, b) => a.name.localeCompare(b.name))
        );
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

  // Fetch the lightweight barangay index once (for the search box).
  useEffect(() => {
    let active = true;
    boundariesApi
      .barangayIndex()
      .then((list) => active && setBarangayIndex(list))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  // Report the current selection to the parent (via a ref so an inline callback
  // doesn't retrigger the effect).
  const cbRef = useRef(onSelectionChange);
  cbRef.current = onSelectionChange;
  useEffect(() => {
    if (!cbRef.current) return;
    if (selectedMuni) {
      cbRef.current({
        level: "municipality",
        id: selectedMuni.id,
        name: selectedMuni.name,
        barangayCount: barangayGeo?.features?.length ?? null,
      });
    } else {
      cbRef.current({ level: "province", municipalityCount: muniGeo?.features?.length ?? null });
    }
  }, [selectedMuni, barangayGeo, muniGeo]);

  // Boundary colours adapt to the basemap: green on the light map, bright yellow
  // (outline only) on satellite so they stay visible over green farmland.
  const sat = basemap === "satellite";
  const heatmapActive = heatmap && yieldByMuni;
  const baseMuniStyle = sat
    ? { color: "#FACC15", weight: 2, fillColor: "#FACC15", fillOpacity: 0 }
    : { color: "#1F6306", weight: 1.5, fillColor: "#3B9E1C", fillOpacity: 0.08 };
  const brgyStyle = sat
    ? { color: "#FDE047", weight: 1.2, fillColor: "#FDE047", fillOpacity: 0 }
    : { color: "#1B6D24", weight: 0.8, fillColor: "#3B9E1C", fillOpacity: 0.06 };

  // Synthetic per-barangay choropleth: colour each barangay by its (sample) yield
  // on a local scale, grey where there's no value. Falls back to the flat outline
  // style when no barangay data is provided.
  const brgyHeatmapActive = !!yieldByBarangay && !!barangayColorScale;
  const brgyStyleFor = (feature) => {
    if (!brgyHeatmapActive) return brgyStyle;
    const rec = yieldByBarangay[feature.properties.barangay_id];
    if (!rec || rec.yield == null) {
      return { color: sat ? "#FFFFFF" : "#9CA3AF", weight: 0.8, fillColor: "#D1D5DB", fillOpacity: sat ? 0.3 : 0.45 };
    }
    return {
      color: sat ? "#FFFFFF" : "#0E2207",
      weight: 0.8,
      fillColor: yieldColor(rec.yield, barangayColorScale.min, barangayColorScale.max),
      fillOpacity: sat ? 0.6 : 0.8,
    };
  };
  const brgyTooltip = (feature) => {
    const name = feature.properties?.name ?? "";
    if (!brgyHeatmapActive) return name;
    const rec = yieldByBarangay[feature.properties.barangay_id];
    if (!rec || rec.yield == null) return `${name}: no data`;
    return `${name}: ${rec.yield} mt/ha (sample)`;
  };

  // react-leaflet applies `style`/`onEachFeature` (incl. bound tooltips) only at
  // mount, so the layer must remount whenever the yield data itself changes —
  // not just when year/season changes. Fold the record count + scale into the
  // signature so the choropleth and its tooltips refresh once data arrives.
  const yieldSig = heatmapActive
    ? `heat-${Object.keys(yieldByMuni).length}-${colorScale?.min}-${colorScale?.max}-${yieldKey}`
    : "plain";

  // Per-feature municipality style. In heatmap mode, fill by observed yield;
  // municipalities with no data (e.g. San Pedro) render a neutral grey.
  const muniStyleFor = (feature) => {
    if (!heatmapActive) return baseMuniStyle;
    const rec = yieldByMuni[feature.properties.municipality_id];
    if (!rec || rec.yield == null) {
      return { color: sat ? "#FFFFFF" : "#9CA3AF", weight: 1, fillColor: "#D1D5DB", fillOpacity: sat ? 0.35 : 0.5 };
    }
    return {
      color: sat ? "#FFFFFF" : "#0E2207",
      weight: 1,
      fillColor: yieldColor(rec.yield, colorScale?.min, colorScale?.max),
      fillOpacity: sat ? 0.6 : 0.85,
    };
  };

  const muniTooltip = (feature) => {
    const name = feature.properties?.name ?? "";
    if (!heatmapActive) return name;
    const rec = yieldByMuni[feature.properties.municipality_id];
    if (!rec || rec.yield == null) return `${name}: no data`;
    return `${name}: ${rec.yield} mt/ha${rec.is_proxy ? " (est.)" : ""}`;
  };

  // Select a municipality and load its barangays, keeping the "loading" highlight up
  // for at least MIN_LOADING_MS so the municipality -> loading -> barangays sequence
  // is always visible (even on a fast backend). Stale fetches are ignored.
  const loadBarangays = (id, name, feature) => {
    setSelectedMuni({ id, name });
    setBarangayGeo(null);
    setBarangaysLoading(true);
    setLoadingFeature(feature);
    const reqId = ++drillReqRef.current;
    const startedAt = performance.now();
    boundariesApi
      .barangays(id)
      .then((fc) => {
        if (drillReqRef.current !== reqId) return; // superseded by a newer click
        const wait = Math.max(0, MIN_LOADING_MS - (performance.now() - startedAt));
        setTimeout(() => {
          if (drillReqRef.current !== reqId) return;
          setBarangayGeo(fc);
          setBarangaysLoading(false);
        }, wait);
      })
      .catch(() => {
        if (drillReqRef.current === reqId) setBarangaysLoading(false);
      });
  };

  // Animate to `bounds`, then flag the highlight ready once the zoom settles. A
  // timeout fallback covers the case where the view doesn't change (no moveend).
  const fitAndSignal = (bounds) => {
    const map = mapRef.current;
    if (!map) {
      setHighlightReady(true);
      return;
    }
    setHighlightReady(false);
    const token = ++fitTokenRef.current;
    const finish = () => {
      map.off("moveend", finish);
      if (fitTokenRef.current === token) setHighlightReady(true);
    };
    map.once("moveend", finish);
    setTimeout(finish, 800);
    map.fitBounds(bounds, FIT_OPTS);
  };

  const drillInto = (feature, layer) => {
    loadBarangays(feature.properties.municipality_id, feature.properties.name, feature);
    if (mapRef.current && layer.getBounds) {
      fitAndSignal(layer.getBounds());
    }
  };

  const backToProvince = () => {
    drillReqRef.current += 1; // cancel any in-flight barangay load
    fitTokenRef.current += 1; // invalidate any pending highlight-ready signal
    setSelectedMuni(null);
    setBarangayGeo(null);
    setBarangaysLoading(false);
    setLoadingFeature(null);
    setHighlightReady(false);
    if (provinceBounds) {
      mapRef.current?.fitBounds(provinceBounds, { padding: [20, 20] });
    } else {
      mapRef.current?.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    }
  };

  // Drill into a municipality by id (used by the parent's City filter — we may
  // not have a Leaflet layer handle here, so derive bounds from the geometry).
  const focusMunicipality = (id) => {
    if (!muniGeo) return;
    const feature = muniGeo.features.find((f) => f.properties.municipality_id === id);
    if (!feature) return;
    loadBarangays(id, feature.properties.name, feature);
    try {
      const b = L.geoJSON(feature).getBounds();
      if (b.isValid()) fitAndSignal(b);
    } catch {
      /* ignore */
    }
  };

  // Keep the map in sync with the parent's City filter. Guard against the value
  // we're already showing so map clicks (which the parent echoes back) don't
  // re-drill or bounce us to the province view.
  useEffect(() => {
    const currentId = selectedMuni?.id ?? null;
    if (focusMunicipalityId === currentId) return;
    if (focusMunicipalityId == null) backToProvince();
    else focusMunicipality(focusMunicipalityId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusMunicipalityId, muniGeo]);

  // Once a searched barangay's municipality has loaded, zoom to that barangay.
  useEffect(() => {
    if (pendingBarangay == null || !barangayGeo) return;
    const f = barangayGeo.features.find((x) => x.properties.barangay_id === pendingBarangay);
    if (f) {
      try {
        const b = L.geoJSON(f).getBounds();
        if (b.isValid()) mapRef.current?.fitBounds(b, { padding: [40, 40], maxZoom: 14 });
      } catch {
        /* ignore */
      }
    }
    setPendingBarangay(null);
  }, [barangayGeo, pendingBarangay]);

  // Search matches: municipalities + barangays, capped for a tidy dropdown.
  const q = query.trim().toLowerCase();
  const searchResults = q
    ? [
        ...(muniGeo?.features ?? [])
          .filter((f) => f.properties.name?.toLowerCase().includes(q))
          .map((f) => ({ type: "municipality", id: f.properties.municipality_id, name: f.properties.name })),
        ...barangayIndex
          .filter((b) => b.name?.toLowerCase().includes(q))
          .map((b) => ({
            type: "barangay",
            id: b.barangay_id,
            name: b.name,
            municipality_id: b.municipality_id,
            municipality_name: b.municipality_name,
          })),
      ].slice(0, 8)
    : [];

  const selectResult = (r) => {
    setQuery("");
    setSearchOpen(false);
    if (r.type === "municipality") {
      focusMunicipality(r.id);
    } else {
      // Drill into the barangay's municipality, then zoom to the barangay.
      if (selectedMuni?.id !== r.municipality_id) {
        focusMunicipality(r.municipality_id);
      }
      setPendingBarangay(r.id);
    }
  };

  const onEachMunicipality = (feature, layer) => {
    const base = muniStyleFor(feature);
    layer.on({
      click: () => drillInto(feature, layer),
      mouseover: () => layer.setStyle({ weight: base.weight + 1.5, fillOpacity: Math.min(1, base.fillOpacity + 0.2) }),
      mouseout: () => layer.setStyle(base),
    });
    layer.bindTooltip(muniTooltip(feature), { sticky: true });
  };

  const onEachBarangay = (feature, layer) => {
    const base = brgyStyleFor(feature);
    layer.on({
      mouseover: () => layer.setStyle({ weight: base.weight + 1, fillOpacity: Math.min(1, base.fillOpacity + 0.24) }),
      mouseout: () => layer.setStyle(base),
    });
    layer.bindTooltip(brgyTooltip(feature), { sticky: true });
  };

  return (
    <section className="relative flex-1 min-w-0 h-full bg-[#E5E7EB]">
      <MapContainer
        ref={mapRef}
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        zoomControl={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          key={basemap}
          attribution={BASEMAPS[basemap].attribution}
          url={BASEMAPS[basemap].url}
          eventHandlers={{ load: () => setTilesReady(true) }}
        />
        {boundariesVisible && !selectedMuni && muniGeo && (
          <GeoJSON
            key={`municipalities-${basemap}-${yieldSig}`}
            data={muniGeo}
            style={muniStyleFor}
            onEachFeature={onEachMunicipality}
          />
        )}
        {boundariesVisible && selectedMuni && barangayGeo && (
          <GeoJSON
            key={`barangays-${selectedMuni.id}-${basemap}-${barangayKey}`}
            data={barangayGeo}
            style={brgyStyleFor}
            onEachFeature={onEachBarangay}
          />
        )}
        {/* Steady "loading" highlight of the clicked municipality, shown only while
            its barangays are being fetched — and only after the drill-in zoom has
            settled, so its stroke is never caught in the zoom-stretch. */}
        {selectedMuni && barangaysLoading && loadingFeature && highlightReady && (
          <GeoJSON
            key={`loading-${selectedMuni.id}`}
            data={loadingFeature}
            interactive={false}
            style={{
              color: sat ? "#FDE047" : "#1F6306",
              weight: 2.5,
              fillColor: sat ? "#FACC15" : "#3B9E1C",
              fillOpacity: 0.35,
            }}
          />
        )}
      </MapContainer>

      {/* Full-screen loading overlay — ONLY for the initial map/province load
          (blank tiles, or the API waking up before the province is drawn). Once a
          municipality is selected, a slow barangay fetch shows the localized highlight
          on that municipality instead, so drilling in never blanks the whole map. */}
      {(!tilesReady || !muniGeo || (serverSlow && !selectedMuni)) && (
        <div className="absolute inset-0 z-[650] flex items-center justify-center bg-[#E5E7EB]/80 backdrop-blur-[2px]">
          <div className="flex flex-col items-center gap-3 px-8 text-center">
            <span className="relative flex h-9 w-9">
              <span className="absolute inline-flex h-full w-full rounded-full border-4 border-[#1F6306]/20" />
              <span className="inline-flex h-9 w-9 rounded-full border-4 border-transparent border-t-[#1F6306] animate-spin" />
            </span>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-semibold text-[#1F2937]">
                {serverSlow ? "Waking up the server…" : "Loading map…"}
              </p>
              {serverSlow && (
                <p className="text-xs leading-4 text-[#6B7280] max-w-[240px]">
                  The server sleeps when idle on the free tier. This can take up to a minute.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Barangay loading indicator — a spinner + label centered over the map. Since
          drilling in fits the map to the clicked municipality, this sits on that
          municipality (whose polygon is highlighted underneath). Non-blocking. */}
      {selectedMuni && barangaysLoading && (
        <div className="absolute inset-0 z-[600] flex items-center justify-center pointer-events-none">
          <div className="flex items-center gap-2.5 rounded-full bg-white/95 px-4 py-2.5 shadow-[0_4px_6px_-1px_rgba(0,0,0,0.1),0_2px_4px_-2px_rgba(0,0,0,0.1)] backdrop-blur-sm">
            <span className="inline-flex h-4 w-4 rounded-full border-2 border-transparent border-t-[#1F6306] border-r-[#1F6306] animate-spin" />
            <span className="text-sm font-medium text-[#374151] whitespace-nowrap">
              Loading barangays…
            </span>
          </div>
        </div>
      )}

      {/* Search overlay — municipalities + barangays, click a result to fly there */}
      <div className="absolute left-6 right-6 top-6 z-[500] flex justify-center pointer-events-none">
        <div className="w-full max-w-[473px] pointer-events-auto">
          <div className="bg-white/95 backdrop-blur-sm shadow-[0_10px_15px_-3px_rgba(0,0,0,0.1),0_4px_6px_-4px_rgba(0,0,0,0.1)] rounded-lg">
            <div className="relative flex items-center">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="absolute left-4 text-[#9CA3AF]">
                <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
                <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              <input
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSearchOpen(true);
                }}
                onFocus={() => setSearchOpen(true)}
                onBlur={() => setTimeout(() => setSearchOpen(false), 150)}
                placeholder="Search a municipality or barangay..."
                className="w-full pl-11 pr-4 py-3.5 text-sm text-[#374151] bg-transparent outline-none placeholder:text-[#6B7280]"
              />
            </div>
          </div>

          {searchOpen && q && (
            <div className="mt-1 bg-white rounded-lg shadow-lg max-h-72 overflow-y-auto border border-[#E5E7EB]">
              {searchResults.length ? (
                searchResults.map((r) => (
                  <button
                    key={`${r.type}-${r.id}`}
                    type="button"
                    onMouseDown={(e) => e.preventDefault()} // keep input from blurring first
                    onClick={() => selectResult(r)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-[#F0FDF4]"
                  >
                    <span
                      className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${
                        r.type === "municipality" ? "bg-[#DCFCE7] text-[#15803D]" : "bg-[#EFF6FF] text-[#1D4ED8]"
                      }`}
                    >
                      {r.type === "municipality" ? "City" : "Brgy"}
                    </span>
                    <span className="flex flex-col">
                      <span className="text-sm text-[#191C1A]">{r.name}</span>
                      {r.type === "barangay" && (
                        <span className="text-xs text-[#9CA3AF]">{r.municipality_name}</span>
                      )}
                    </span>
                  </button>
                ))
              ) : (
                <div className="px-4 py-3 text-sm text-[#9CA3AF]">No matches for “{query}”.</div>
              )}
            </div>
          )}
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
          {selectedMuni.name} · back to all
        </button>
      )}

      {/* Yield heatmap legend — centred along the bottom of the map. */}
      {heatmapActive && !selectedMuni && colorScale?.min != null && (
        <div className="absolute left-1/2 -translate-x-1/2 bottom-6 z-[500] bg-white/95 backdrop-blur-sm shadow-md rounded-lg px-5 py-3">
          <div className="flex items-center gap-4">
            <span className="text-sm font-semibold text-[#374151] whitespace-nowrap">Avg yield (mt/ha)</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#6B7280]">{colorScale.min}</span>
              <div className="flex h-3.5 w-52 rounded-full overflow-hidden">
                {YIELD_RAMP.map((c) => (
                  <span key={c} className="flex-1" style={{ background: c }} />
                ))}
              </div>
              <span className="text-xs text-[#6B7280]">{colorScale.max}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm bg-[#D1D5DB]" />
              <span className="text-xs text-[#6B7280] whitespace-nowrap">No data</span>
            </div>
          </div>
        </div>
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
  );
}
