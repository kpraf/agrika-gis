import React, { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import MapControls from "../layout/MapControls";
import { boundariesApi, onServerSlow } from "../../lib/api";
import { foldText, matchesQuery } from "../../lib/text";

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
 *   lockedMunicipalityId - when set, the map is pinned to that municipality: it
 *       opens on the whole city as one shape, a click shows its barangays, only
 *       that city can be searched, and there is no way back to the province (used
 *       for the roles limited to their assigned city)
 *   lockedBarangays    - on a locked map, lets the parent show (true) or hide
 *       (false) the barangays; null leaves it to the map
 *   onSelectionChange  - called with the current selection whenever it changes:
 *       { level: "province", municipalityCount }  |
 *       { level: "municipality", id, name, barangayCount, barangaysShown }
 */
// Sequential green ramp for the yield heatmap: light (low yield) -> dark (high).
export const YIELD_RAMP = ["#EDF8E9", "#C7E9C0", "#A1D99B", "#74C476", "#41AB5D", "#238B45", "#005A32"];

function yieldColor(value, min, max, ramp = YIELD_RAMP) {
  if (value == null || min == null || max == null || max <= min) return ramp[3];
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  return ramp[Math.round(t * (ramp.length - 1))];
}

// Diverging ramp for residuals (observed - predicted): over-prediction (negative)
// -> red, near-zero -> neutral, under-prediction (positive) -> blue.
export const RESIDUAL_RAMP = ["#B2182B", "#EF8A62", "#FDDBC7", "#F7F7F7", "#D1E5F0", "#67A9CF", "#2166AC"];

// Sequential ramps for the Environment (remote-sensing) layers, keyed by family.
export const RAMPS = {
  green: YIELD_RAMP, // NDVI / EVI (vegetation)
  teal: ["#F7FCFD", "#E5F5F9", "#CCECE6", "#99D8C9", "#66C2A4", "#2CA25F", "#006D2C"], // NDWI (moisture)
  blue: ["#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6", "#3182BD", "#08519C"], // rainfall / humidity
  warm: ["#FFF5EB", "#FEE6CE", "#FDD0A2", "#FDAE6B", "#FD8D3C", "#E6550D", "#A63603"], // temperature
  purple: ["#FCFBFD", "#EFEDF5", "#DADAEB", "#BCBDDC", "#9E9AC8", "#756BB1", "#54278F"], // radar backscatter
};

function residualColor(value, absMax) {
  if (value == null || !absMax) return RESIDUAL_RAMP[3];
  const t = Math.max(-1, Math.min(1, value / absMax)); // [-1, 1]
  return RESIDUAL_RAMP[Math.round(((t + 1) / 2) * (RESIDUAL_RAMP.length - 1))];
}

export default function LagunaMap({
  boundariesVisible = true,
  detailedTooltips = false, // hover shows name + year + season + value (vs value only)
  year = null,
  season = "",
  onSelectionChange,
  focusMunicipalityId = null,
  lockedMunicipalityId = null,
  lockedBarangays = null,
  clearBrgyToken = 0, // bump to clear the clicked-barangay selection from the parent
  onMunicipalitiesLoaded,
  heatmap = false,
  yieldByMuni = null, // { [municipality_id]: { yield, is_proxy } }
  colorScale = null, // { min, max }
  colorMode = "yield", // "yield" (sequential) | "residual" (diverging, symmetric scale)
  rampKey = "green", // sequential palette family for the Environment layers
  legendLabel = "Avg yield (mt/ha)", // legend title (sequential modes)
  valueUnit = "mt/ha", // unit shown in tooltips ("" for unitless indices like NDVI)
  yieldByBarangay = null, // { [barangay_id]: { yield } } — real observed barangay_yield
  barangayColorScale = null, // { min, max } local to the drilled-in municipality
  barangayHeatmap = false, // yield mode on drill-in: colour barangays by yield, grey the no-data ones
  yieldKey = "", // changes (e.g. "2024-Dry") force the choropleth to restyle
  barangayKey = "", // changes force the barangay choropleth to restyle
  overlayLoading = false, // show a non-blocking "loading data" pill over the map
  overlayLabel = "Loading…", // label for that pill
  notice = null, // { title?, text, status?, actionLabel?, onAction?, onDismiss? } - a note about the layer on show; status is the short version on the layer chip
  layerChip = null, // { label, sub, kind: "observed" | "predicted" | "residual" } - names the layer on show
  forecastOutline = false, // dashed outlines on areas with data (the Predicted layer)
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
  const [selectedBrgy, setSelectedBrgy] = useState(null); // { id, name } clicked barangay
  // Leaflet layer of the currently highlighted barangay, so a new click can reset it.
  const barangayGeoRef = useRef(null); // latest barangay geo, for zooming back out on deselect
  const [barangayGeo, setBarangayGeo] = useState(null);
  const [barangaysLoading, setBarangaysLoading] = useState(false);
  // GeoJSON feature of the municipality being drilled into. While its barangays load,
  // its own polygon shows a steady "loading" highlight instead of blanking the map.
  const [loadingFeature, setLoadingFeature] = useState(null);
  // True once the drill-in zoom has settled, so the highlight polygon is only drawn
  // at its final scale — never mid-animation, where Leaflet's zoom-stretch would
  // balloon its stroke into a thick border.
  const [highlightReady, setHighlightReady] = useState(false);
  // A locked map first shows its city as one shape (the city total); a click on
  // it, or the parent, reveals the barangays.
  const [cityOverview, setCityOverview] = useState(true);
  const overview = lockedMunicipalityId != null && cityOverview;
  useEffect(() => {
    if (lockedBarangays != null) setCityOverview(!lockedBarangays);
  }, [lockedBarangays]);

  // Search: query + barangay index (names only) + a pending barangay to zoom to
  // once its municipality's boundaries finish loading.
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [activeResult, setActiveResult] = useState(0); // keyboard-highlighted search result
  const [barangayIndex, setBarangayIndex] = useState([]);
  const [pendingBarangay, setPendingBarangay] = useState(null);
  const searchInputRef = useRef(null);
  const [noteOpen, setNoteOpen] = useState(false); // layer chip expanded to show the note
  // Collapse the note whenever the layer or its message changes.
  useEffect(() => setNoteOpen(false), [layerChip?.kind, notice?.text]);

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

  // The city the map opens on, if any (pinned account or City filter). Read by the
  // one-time boundary fetch below.
  const openCityRef = useRef(null);
  openCityRef.current = lockedMunicipalityId ?? focusMunicipalityId;

  // Fetch municipality boundaries once, and frame the whole province (unless a
  // city is wanted: its own fit follows right after, and Leaflet ignores a fit
  // that starts while another zoom is still animating).
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
            if (openCityRef.current == null) mapRef.current?.fitBounds(b, { padding: [20, 20] });
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
    if (selectedMuni && selectedBrgy) {
      cbRef.current({
        level: "barangay",
        id: selectedBrgy.id,
        name: selectedBrgy.name,
        municipalityId: selectedMuni.id,
        municipalityName: selectedMuni.name,
      });
    } else if (selectedMuni) {
      cbRef.current({
        level: "municipality",
        id: selectedMuni.id,
        name: selectedMuni.name,
        barangayCount: barangayGeo?.features?.length ?? null,
        barangaysShown: !overview,
      });
    } else {
      cbRef.current({ level: "province", municipalityCount: muniGeo?.features?.length ?? null });
    }
  }, [selectedMuni, selectedBrgy, barangayGeo, muniGeo, overview]);

  // Parent asked to deselect the barangay (e.g. the panel's back button):
  // restore all barangays and zoom back out to the whole municipality.
  useEffect(() => {
    if (!clearBrgyToken) return;
    setSelectedBrgy(null); // brgyStyleFor drops the isolate on the next render
    try {
      const geo = barangayGeoRef.current;
      if (geo && mapRef.current) {
        const b = L.geoJSON(geo).getBounds();
        if (b.isValid()) mapRef.current.fitBounds(b, FIT_OPTS);
      }
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearBrgyToken]);

  // Boundary colours stay green on both basemaps for a consistent look. On
  // satellite we drop the fill (outline only, so the imagery shows through) and
  // use a slightly heavier stroke so the green lines stay legible over farmland.
  const sat = basemap === "satellite";
  const heatmapActive = heatmap && yieldByMuni;
  const baseMuniStyle = sat
    ? { color: "#1F6306", weight: 2, fillColor: "#3B9E1C", fillOpacity: 0 }
    : { color: "#1F6306", weight: 1.5, fillColor: "#3B9E1C", fillOpacity: 0.08 };
  const brgyStyle = sat
    ? { color: "#1B6D24", weight: 1.2, fillColor: "#3B9E1C", fillOpacity: 0 }
    : { color: "#1B6D24", weight: 0.8, fillColor: "#3B9E1C", fillOpacity: 0.06 };

  // The "back to ..." pill: shown when drilled into a municipality; on a locked map
  // only to step back from the barangays to the whole pinned city.
  const backPillShown = !!selectedMuni && !overview;

  // Predicted layer: dash the outline of every area that has a value, so a
  // forecast never looks like reported data even though it shares the green ramp.
  const dash = forecastOutline ? { dashArray: "5 4", lineCap: "butt" } : { dashArray: null };

  // Per-barangay choropleth: in barangayHeatmap mode, colour each barangay on the
  // local scale using the SAME palette/mode as the municipality layer (yield green,
  // Environment ramp, or the diverging residual ramp), and grey the ones with no
  // value. Outside that mode, fall back to the flat outline style.
  const brgyHeatmapActive = barangayHeatmap;
  const brgyFill = (v) =>
    colorMode === "residual"
      ? residualColor(v, barangayColorScale?.max)
      : yieldColor(v, barangayColorScale?.min, barangayColorScale?.max, RAMPS[rampKey] || YIELD_RAMP);
  const brgyBaseStyleFor = (feature) => {
    if (!brgyHeatmapActive) return brgyStyle;
    const rec = yieldByBarangay?.[feature.properties.barangay_id];
    if (!rec || rec.yield == null || !barangayColorScale) {
      return { color: sat ? "#FFFFFF" : "#9CA3AF", weight: 0.8, fillColor: "#D1D5DB", fillOpacity: sat ? 0.3 : 0.45 };
    }
    return {
      color: sat ? "#FFFFFF" : "#0E2207",
      weight: forecastOutline ? 1.4 : 0.8,
      fillColor: brgyFill(rec.yield),
      fillOpacity: sat ? 0.6 : 0.8,
      ...dash,
    };
  };
  // Isolate a clicked barangay: highlight it, dim the rest. Declarative (folded
  // into the style prop) so react-leaflet doesn't wipe it on the next render.
  const brgyHighlightStyle = (base) => ({
    color: sat ? "#FDE047" : "#0B3D0B",
    weight: 3.5,
    opacity: 1,
    fillColor: base.fillColor,
    fillOpacity: Math.min(1, (base.fillOpacity ?? 0) + 0.15),
  });
  const brgyDimStyle = (base) => ({ ...base, opacity: 0.2, fillOpacity: (base.fillOpacity ?? 0) * 0.3 });
  const brgyStyleFor = (feature) => {
    const base = brgyBaseStyleFor(feature);
    if (!selectedBrgy) return base;
    return feature.properties.barangay_id === selectedBrgy.id ? brgyHighlightStyle(base) : brgyDimStyle(base);
  };
  // Value label + formatting shared by the municipality and barangay tooltips.
  const valueLabel =
    colorMode === "residual" ? "Residual" : valueUnit === "mt/ha" ? "Yield" : legendLabel || "Value";
  const formatValue = (rec) => {
    if (!rec || rec.yield == null) return "no data";
    const unit = valueUnit ? ` ${valueUnit}` : "";
    if (colorMode === "residual") return `${rec.yield > 0 ? "+" : ""}${rec.yield}${unit}`;
    return `${rec.yield}${unit}${rec.is_proxy ? " (est.)" : ""}`;
  };
  // Detailed OFF: "Name: value". Detailed ON: name + year + season + value.
  const tooltipFor = (name, rec) => {
    const value = formatValue(rec);
    if (!detailedTooltips) return `${name}: ${value}`;
    return (
      `<div class="agrika-tt"><b>${name}</b>` +
      (year != null ? `<br/>Year: ${year}` : "") +
      (season ? `<br/>Season: ${season}` : "") +
      `<br/>${valueLabel}: ${value}</div>`
    );
  };

  const brgyTooltip = (feature) => {
    const name = feature.properties?.name ?? "";
    if (!brgyHeatmapActive) return name;
    return tooltipFor(name, yieldByBarangay?.[feature.properties.barangay_id]);
  };

  // The colour-scale legend follows what the map is showing: the municipality
  // choropleth at the province view, or the barangay choropleth (its own local
  // scale) once drilled into a municipality.
  // The one-city overview of a locked map needs no scale (the panel shows its value).
  const legendScale = selectedMuni ? barangayColorScale : colorScale;
  const legendVisible = !overview && (selectedMuni ? brgyHeatmapActive : heatmapActive) && legendScale?.min != null;

  // react-leaflet applies `style`/`onEachFeature` (incl. bound tooltips) only at
  // mount, so the layer must remount whenever the yield data itself changes —
  // not just when year/season changes. Fold the record count + scale into the
  // signature so the choropleth and its tooltips refresh once data arrives.
  const yieldSig =
    (heatmapActive
      ? `heat-${Object.keys(yieldByMuni).length}-${colorScale?.min}-${colorScale?.max}-${yieldKey}`
      : "plain") + `-${detailedTooltips ? "d" : "s"}`;

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
      weight: forecastOutline ? 1.8 : 1,
      fillColor:
        colorMode === "residual"
          ? residualColor(rec.yield, colorScale?.max)
          : yieldColor(rec.yield, colorScale?.min, colorScale?.max, RAMPS[rampKey] || YIELD_RAMP),
      fillOpacity: sat ? 0.6 : 0.85,
      ...dash,
    };
  };

  const muniTooltip = (feature) => {
    const name = feature.properties?.name ?? "";
    if (!heatmapActive) return name;
    return tooltipFor(name, yieldByMuni[feature.properties.municipality_id]);
  };

  // Select a municipality and load its barangays, keeping the "loading" highlight up
  // for at least MIN_LOADING_MS so the municipality -> loading -> barangays sequence
  // is always visible (even on a fast backend). Stale fetches are ignored.
  const loadBarangays = (id, name, feature) => {
    setSelectedMuni({ id, name });
    setSelectedBrgy(null); // dropping into a (different) city clears any clicked barangay
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
    // Leaflet drops a fit requested mid-zoom-animation, so wait for it to end.
    if (map._animatingZoom) {
      map.once("zoomend", () => fitAndSignal(bounds));
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
    if (lockedMunicipalityId != null) return; // pinned to one city: no province view
    drillReqRef.current += 1; // cancel any in-flight barangay load
    fitTokenRef.current += 1; // invalidate any pending highlight-ready signal
    setSelectedMuni(null);
    setSelectedBrgy(null);
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

  // The map's "back" button steps back ONE level: a selected barangay -> its
  // municipality (deselect + zoom out to the city), otherwise the municipality
  // -> the whole province.
  const backOneLevel = () => {
    if (selectedBrgy) {
      setSelectedBrgy(null); // reporting effect then reports the municipality
      try {
        const geo = barangayGeoRef.current;
        if (geo && mapRef.current) {
          const b = L.geoJSON(geo).getBounds();
          if (b.isValid()) mapRef.current.fitBounds(b, FIT_OPTS);
        }
      } catch {
        /* ignore */
      }
    } else if (lockedMunicipalityId != null) {
      setCityOverview(true); // pinned city: back to the whole city as one shape
      if (cityFeature) fitAndSignal(L.geoJSON(cityFeature).getBounds());
    } else {
      backToProvince();
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
  // A locked map always follows its pinned city, whatever the parent's filter says.
  const wantedMuniId = lockedMunicipalityId ?? focusMunicipalityId;
  useEffect(() => {
    const currentId = selectedMuni?.id ?? null;
    if (wantedMuniId === currentId) return;
    if (wantedMuniId == null) backToProvince();
    else focusMunicipality(wantedMuniId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wantedMuniId, muniGeo]);

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
  // Accents and case are ignored, so "Binan" finds "Biñan".
  const q = foldText(query);
  // On a locked map only the pinned city's barangays are searchable.
  const searchResults = q
    ? [
        ...(lockedMunicipalityId != null ? [] : muniGeo?.features ?? [])
          .filter((f) => matchesQuery(f.properties.name, q))
          .map((f) => ({ type: "municipality", id: f.properties.municipality_id, name: f.properties.name })),
        ...barangayIndex
          .filter((b) => lockedMunicipalityId == null || b.municipality_id === lockedMunicipalityId)
          .filter((b) => matchesQuery(b.name, q))
          .map((b) => ({
            type: "barangay",
            id: b.barangay_id,
            name: b.name,
            municipality_id: b.municipality_id,
            municipality_name: b.municipality_name,
          })),
      ].slice(0, 8)
    : [];

  // Keyboard on the search box: Up/Down move through the results (wrapping),
  // Enter opens the highlighted one, Escape closes the list.
  const onSearchKeyDown = (e) => {
    if (e.key === "Escape") {
      setSearchOpen(false);
      return;
    }
    if (!searchResults.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); // keep the text cursor where it is
      const step = e.key === "ArrowDown" ? 1 : -1;
      setSearchOpen(true);
      setActiveResult((i) => (searchOpen ? (i + step + searchResults.length) % searchResults.length : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      selectResult(searchResults[Math.min(activeResult, searchResults.length - 1)]);
    }
  };
  // Keep the highlighted result in view when the list scrolls.
  useEffect(() => {
    if (!searchOpen) return;
    document.getElementById(`map-search-opt-${activeResult}`)?.scrollIntoView({ block: "nearest" });
  }, [activeResult, searchOpen]);

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
      setCityOverview(false);
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

  // The pinned city's own polygon, for the one-shape overview of a locked map.
  const cityFeature =
    lockedMunicipalityId != null
      ? muniGeo?.features.find((f) => f.properties.municipality_id === lockedMunicipalityId) ?? null
      : null;

  const onEachCity = (feature, layer) => {
    const base = muniStyleFor(feature);
    layer.on({
      click: () => setCityOverview(false), // already framed on the city; show its barangays
      mouseover: () => layer.setStyle({ weight: base.weight + 1.5, fillOpacity: Math.min(1, base.fillOpacity + 0.2) }),
      mouseout: () => layer.setStyle(base),
    });
    layer.bindTooltip(muniTooltip(feature), { sticky: true });
  };

  barangayGeoRef.current = barangayGeo; // keep the latest geo for zoom-back-out

  const onEachBarangay = (feature, layer) => {
    const isSel = () => selectedBrgy?.id === feature.properties.barangay_id;
    layer.on({
      click: () => {
        // Zoom into the clicked barangay (municipality -> barangay), like the
        // province -> municipality drill-in. Isolate is handled by brgyStyleFor.
        try {
          const b = layer.getBounds();
          if (b.isValid()) mapRef.current?.fitBounds(b, { padding: [40, 40], maxZoom: 16 });
        } catch {
          /* ignore */
        }
        setSelectedBrgy({ id: feature.properties.barangay_id, name: feature.properties.name });
      },
      mouseover: () => {
        const base = brgyStyleFor(feature);
        layer.setStyle({ weight: (base.weight ?? 0.8) + 1, opacity: 1, fillOpacity: Math.min(1, (base.fillOpacity ?? 0) + 0.24) });
      },
      mouseout: () => layer.setStyle(brgyStyleFor(feature)),
    });
    layer.bindTooltip(brgyTooltip(feature), { sticky: true });
  };

  return (
    <section className="relative flex-1 min-w-0 h-full bg-[#E5E7EB]">
      <MapContainer
        ref={mapRef}
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        zoomSnap={0.25} // lets a fit fill the panel instead of stopping a whole level short
        zoomControl={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          key={basemap}
          attribution={BASEMAPS[basemap].attribution}
          url={BASEMAPS[basemap].url}
          eventHandlers={{ load: () => setTilesReady(true) }}
        />
        {/* Province view. Never drawn on a locked map: it would show the other
            cities for a moment before the pinned one loads. */}
        {boundariesVisible && !selectedMuni && muniGeo && lockedMunicipalityId == null && (
          <GeoJSON
            key={`municipalities-${basemap}-${yieldSig}`}
            data={muniGeo}
            style={muniStyleFor}
            onEachFeature={onEachMunicipality}
          />
        )}
        {boundariesVisible && overview && cityFeature && (
          <GeoJSON
            key={`city-${lockedMunicipalityId}-${basemap}-${yieldSig}`}
            data={cityFeature}
            style={muniStyleFor}
            onEachFeature={onEachCity}
          />
        )}
        {boundariesVisible && selectedMuni && barangayGeo && !overview && (
          <GeoJSON
            key={`barangays-${selectedMuni.id}-${basemap}-${barangayKey}-${selectedBrgy?.id ?? "none"}`}
            data={barangayGeo}
            style={brgyStyleFor}
            onEachFeature={onEachBarangay}
          />
        )}
        {/* Steady "loading" highlight of the clicked municipality, shown only while
            its barangays are being fetched — and only after the drill-in zoom has
            settled, so its stroke is never caught in the zoom-stretch. */}
        {selectedMuni && barangaysLoading && loadingFeature && highlightReady && !overview && (
          <GeoJSON
            key={`loading-${selectedMuni.id}`}
            data={loadingFeature}
            interactive={false}
            style={{
              color: "#1F6306",
              weight: 2.5,
              fillColor: "#3B9E1C",
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
              <p className="text-sm font-semibold text-[#1F2937]">Loading map…</p>
              {serverSlow && (
                <p className="text-xs leading-4 text-[#6B7280] max-w-[240px]">
                  This can take a moment.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Barangay loading indicator — a spinner + label centered over the map. Since
          drilling in fits the map to the clicked municipality, this sits on that
          municipality (whose polygon is highlighted underneath). Non-blocking. */}
      {selectedMuni && barangaysLoading && !overview && (
        <div className="absolute inset-0 z-[600] flex items-center justify-center pointer-events-none">
          <div className="flex items-center gap-2.5 rounded-full bg-white/95 px-4 py-2.5 shadow-[0_4px_6px_-1px_rgba(0,0,0,0.1),0_2px_4px_-2px_rgba(0,0,0,0.1)] backdrop-blur-sm">
            <span className="inline-flex h-4 w-4 rounded-full border-2 border-transparent border-t-[#1F6306] border-r-[#1F6306] animate-spin" />
            <span className="text-sm font-medium text-[#374151] whitespace-nowrap">
              Loading barangays…
            </span>
          </div>
        </div>
      )}

      {/* Environment (or other data) loading pill — non-blocking, shown while the
          selected layer's values are being fetched so the map isn't silently blank
          until they arrive. Hidden while the barangay-drill pill is up. */}
      {overlayLoading && !barangaysLoading && (
        <div className="absolute inset-0 z-[600] flex items-center justify-center pointer-events-none">
          <div className="flex items-center gap-2.5 rounded-full bg-white/95 px-4 py-2.5 shadow-[0_4px_6px_-1px_rgba(0,0,0,0.1),0_2px_4px_-2px_rgba(0,0,0,0.1)] backdrop-blur-sm">
            <span className="inline-flex h-4 w-4 rounded-full border-2 border-transparent border-t-[#1F6306] border-r-[#1F6306] animate-spin" />
            <span className="text-sm font-medium text-[#374151] whitespace-nowrap">{overlayLabel}</span>
          </div>
        </div>
      )}

      {/* Location bar: back arrow + where you are + search, in one bar. */}
      <div className="absolute left-4 right-4 sm:left-6 sm:right-6 top-4 sm:top-6 z-[500] flex justify-center pointer-events-none">
        <div className="w-full max-w-[473px] pointer-events-auto">
          <div className="bg-white/95 backdrop-blur-sm shadow-[0_10px_15px_-3px_rgba(0,0,0,0.1),0_4px_6px_-4px_rgba(0,0,0,0.1)] rounded-lg">
            <div className="relative flex items-center h-12">
              {backPillShown ? (
                <button
                  type="button"
                  onClick={backOneLevel}
                  aria-label={
                    selectedBrgy || lockedMunicipalityId != null ? `Back to ${selectedMuni.name}` : "Back to all of Laguna"
                  }
                  className="shrink-0 flex items-center justify-center w-12 h-12 border-r border-[#E5E7EB] text-[#1F6306] rounded-l-lg hover:bg-[#F0FDF4]"
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="absolute left-4 text-[#9CA3AF]" aria-hidden="true">
                  <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              )}

              <div className="relative flex-1 min-w-0 h-full">
                <input
                  ref={searchInputRef}
                  type="text"
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setSearchOpen(true);
                    setActiveResult(0); // new results: start from the top
                  }}
                  onKeyDown={onSearchKeyDown}
                  onFocus={() => setSearchOpen(true)}
                  onBlur={() => setTimeout(() => setSearchOpen(false), 150)}
                  role="combobox"
                  aria-expanded={searchOpen && !!q}
                  aria-controls="map-search-results"
                  aria-autocomplete="list"
                  aria-activedescendant={
                    searchOpen && q && searchResults.length ? `map-search-opt-${activeResult}` : undefined
                  }
                  placeholder={
                    backPillShown || lockedMunicipalityId != null
                      ? "Search a barangay..."
                      : "Search a municipality or barangay..."
                  }
                  className={`w-full h-full ${backPillShown ? "pl-3 pr-10" : "pl-11 pr-4"} text-sm text-[#374151] bg-transparent outline-none placeholder:text-[#6B7280]`}
                />
                {/* Drilled in and idle: show where you are. Tapping it starts a search. */}
                {backPillShown && !searchOpen && !query && (
                  <button
                    type="button"
                    onClick={() => searchInputRef.current?.focus()}
                    className="absolute inset-0 flex flex-col justify-center pl-3 pr-10 text-left bg-white rounded-r-lg"
                  >
                    <span className="text-sm font-semibold text-[#1F2937] truncate">
                      {selectedBrgy ? selectedBrgy.name : selectedMuni.name}
                    </span>
                    <span className="text-[11px] text-[#6B7280] truncate">
                      {selectedBrgy ? `${selectedMuni.name} · Search a barangay` : "Search a barangay"}
                    </span>
                  </button>
                )}
              </div>

              {backPillShown && (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="absolute right-4 text-[#6B7280] pointer-events-none" aria-hidden="true">
                  <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              )}
            </div>
          </div>

          {searchOpen && q && (
            <div
              id="map-search-results"
              role="listbox"
              className="mt-1 bg-white rounded-lg shadow-lg max-h-72 overflow-y-auto border border-[#E5E7EB]"
            >
              {searchResults.length ? (
                searchResults.map((r, i) => (
                  <button
                    key={`${r.type}-${r.id}`}
                    id={`map-search-opt-${i}`}
                    role="option"
                    aria-selected={i === activeResult}
                    tabIndex={-1}
                    type="button"
                    onMouseDown={(e) => e.preventDefault()} // keep input from blurring first
                    onMouseEnter={() => setActiveResult(i)}
                    onClick={() => selectResult(r)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left ${
                      i === activeResult ? "bg-[#F0FDF4]" : "hover:bg-[#F0FDF4]"
                    }`}
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

      {/* One chip: names the layer and, when there is a note, its status. Tap to read
          the note. Keyed by kind so it replays anim-fade-up on every switch. */}
      {(layerChip || notice) && (
        <div className="absolute left-4 right-4 sm:left-6 sm:right-6 top-[76px] sm:top-[84px] z-[450] flex justify-center pointer-events-none">
          <div className="w-full max-w-[473px] flex">
            <div
              key={layerChip?.kind ?? "note"}
              className={`anim-fade-up pointer-events-auto max-w-full bg-white shadow-[0_4px_12px_rgba(0,0,0,0.15)] transition-[border-radius] ${
                noteOpen ? "rounded-xl" : "rounded-[20px]"
              }`}
            >
              <button
                type="button"
                onClick={() => notice && setNoteOpen((o) => !o)}
                aria-expanded={notice ? noteOpen : undefined}
                aria-controls={notice ? "map-layer-note" : undefined}
                className={`flex items-center gap-2 pl-3 pr-3 py-2 text-left ${notice ? "cursor-pointer" : "cursor-default"}`}
              >
                <span
                  className={`shrink-0 w-3 h-3 rounded-full box-border ${
                    layerChip?.kind === "predicted"
                      ? "bg-white border-2 border-dashed border-[#1B3315]"
                      : layerChip?.kind === "residual"
                      ? "bg-[#2166AC]"
                      : "bg-[#3B9E1C]"
                  }`}
                />
                <span className="text-[13px] font-bold text-[#191C1A] whitespace-nowrap">
                  {layerChip?.label ?? notice.title}
                </span>
                {notice?.status ? (
                  <span className="text-xs font-semibold text-[#B45309] truncate">· {notice.status}</span>
                ) : (
                  layerChip?.sub && <span className="hidden sm:inline text-xs text-[#6B7280] whitespace-nowrap">· {layerChip.sub}</span>
                )}
                {notice && (
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"
                    className={`shrink-0 transition-transform duration-200 ${noteOpen ? "rotate-180" : ""}`}>
                    <path d="M4 6l4 4 4-4" stroke="#6B7280" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>

              {notice && noteOpen && (
                <div id="map-layer-note" role="status" className="anim-fade-up flex flex-col gap-2.5 pl-8 pr-3 pb-3 -mt-0.5">
                  <p className="text-[13px] leading-[18px] text-[#4B5563] text-pretty">
                    {notice.title && <b className="font-semibold text-[#1F2937]">{notice.title} </b>}
                    {notice.text}
                  </p>
                  {(notice.actionLabel || notice.onDismiss) && (
                    <div className="flex items-center gap-2">
                      {notice.actionLabel && (
                        <button type="button" onClick={notice.onAction}
                          className="px-3 py-[7px] rounded-lg bg-[#191C1A] text-white text-xs font-semibold whitespace-nowrap hover:bg-black active:scale-95 transition">
                          {notice.actionLabel}
                        </button>
                      )}
                      {notice.onDismiss && (
                        <button type="button" onClick={notice.onDismiss}
                          className="px-2.5 py-[7px] rounded-lg text-xs font-medium text-[#6B7280] hover:bg-[#F3F4F6]">
                          Hide note
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Colour-scale legend — centred along the bottom of the map. Shows for the
          municipality choropleth (province view) or the barangay one (drilled in). */}
      {legendVisible && (
        <div className="absolute left-3 bottom-20 min-[1770px]:left-1/2 min-[1770px]:-translate-x-1/2 min-[1770px]:bottom-6 z-[500] bg-white/95 backdrop-blur-sm shadow-md rounded-lg px-3 py-2 min-[1770px]:px-5 min-[1770px]:py-3 max-w-[calc(100vw-5rem)] min-[1770px]:max-w-none">
          <div className="flex items-center gap-2 min-[1770px]:gap-4">
            <span className="text-xs min-[1770px]:text-sm font-semibold text-[#374151] whitespace-nowrap">
              {colorMode === "residual" ? "Residual (obs − pred), mt/ha" : legendLabel}
            </span>
            <div className="flex items-center gap-1.5 min-[1770px]:gap-2">
              <span className="text-[10px] min-[1770px]:text-xs text-[#6B7280]">
                {colorMode === "residual" ? "over-predicts" : legendScale.min}
              </span>
              <div className="flex h-3 min-[1770px]:h-3.5 w-24 min-[1770px]:w-52 rounded-full overflow-hidden">
                {(colorMode === "residual" ? RESIDUAL_RAMP : RAMPS[rampKey] || YIELD_RAMP).map((c) => (
                  <span key={c} className="flex-1" style={{ background: c }} />
                ))}
              </div>
              <span className="text-[10px] min-[1770px]:text-xs text-[#6B7280]">
                {colorMode === "residual" ? "under-predicts" : legendScale.max}
              </span>
            </div>
            {/* "No data" key hidden below 1770px to keep the legend from colliding with
                the basemap toggle / zoom; the grey polygons read clearly enough. */}
            <div className="hidden min-[1770px]:flex items-center gap-1.5">
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
