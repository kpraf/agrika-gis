import React, { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import MapControls from "../layout/MapControls";
import { boundariesApi } from "../../lib/api";

const DEFAULT_CENTER = [14.2117, 121.1653];
const DEFAULT_ZOOM = 11;

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

/**
 * Shared Laguna map used by both the Spatial GIS page and the Monitoring page.
 *
 * Props:
 *   boundariesVisible  - show/hide the boundary layer (default true)
 *   onSelectionChange  - called with the current selection whenever it changes:
 *       { level: "province", municipalityCount }  |
 *       { level: "municipality", id, name, barangayCount }
 */
export default function LagunaMap({
  boundariesVisible = true,
  onSelectionChange,
  focusMunicipalityId = null,
  onMunicipalitiesLoaded,
}) {
  const mapRef = useRef(null);
  const [basemap, setBasemap] = useState("map");
  const [muniGeo, setMuniGeo] = useState(null);
  const [provinceBounds, setProvinceBounds] = useState(null);
  const [selectedMuni, setSelectedMuni] = useState(null); // { id, name }
  const [barangayGeo, setBarangayGeo] = useState(null);

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
  const muniStyle = sat
    ? { color: "#FACC15", weight: 2, fillColor: "#FACC15", fillOpacity: 0 }
    : { color: "#1F6306", weight: 1.5, fillColor: "#3B9E1C", fillOpacity: 0.08 };
  const brgyStyle = sat
    ? { color: "#FDE047", weight: 1.2, fillColor: "#FDE047", fillOpacity: 0 }
    : { color: "#1B6D24", weight: 0.8, fillColor: "#3B9E1C", fillOpacity: 0.06 };

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
    setSelectedMuni({ id, name: feature.properties.name });
    setBarangayGeo(null);
    boundariesApi
      .barangays(id)
      .then((fc) => setBarangayGeo(fc))
      .catch(() => {});
    try {
      const b = L.geoJSON(feature).getBounds();
      if (b.isValid()) mapRef.current?.fitBounds(b, { padding: [24, 24] });
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

  return (
    <section className="relative flex-1 min-w-0 h-full bg-[#E5E7EB]">
      <MapContainer
        ref={mapRef}
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        zoomControl={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer key={basemap} attribution={BASEMAPS[basemap].attribution} url={BASEMAPS[basemap].url} />
        {boundariesVisible && !selectedMuni && muniGeo && (
          <GeoJSON key={`municipalities-${basemap}`} data={muniGeo} style={muniStyle} onEachFeature={onEachMunicipality} />
        )}
        {boundariesVisible && selectedMuni && barangayGeo && (
          <GeoJSON
            key={`barangays-${selectedMuni.id}-${basemap}`}
            data={barangayGeo}
            style={brgyStyle}
            onEachFeature={onEachBarangay}
          />
        )}
      </MapContainer>

      {/* Search overlay */}
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
  );
}
