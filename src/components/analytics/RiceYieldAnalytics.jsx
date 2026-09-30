import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Brush,
  LabelList,
} from "recharts";
import DashboardSidebar from "../layout/DashboardSidebar";
import { yieldApi } from "../../lib/api";

// "Field" palette: lighter, softer series colours. Assigned by SELECTION order
// (not list position), so the chosen municipalities always get distinct colours.
const PALETTE = [
  "#74C476", "#F2C94C", "#7FB3D5", "#F0A080", "#B39DDB",
  "#80CBC4", "#F48FB1", "#C5D86D", "#FFB870", "#90A4AE",
];
const MAX_SELECTED = PALETTE.length;

function IconLine() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17l5-6 4 4 9-11" />
    </svg>
  );
}
function IconBar() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 20V10M12 20V4M20 20v-7" />
    </svg>
  );
}
function IconAverage() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12h18M3 12l4-4M3 12l4 4" />
    </svg>
  );
}
function IconZoom() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3M11 8v6M8 11h6" />
    </svg>
  );
}

function ControlButton({ active, onClick, disabled, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm font-medium shadow-sm transition-colors disabled:opacity-40 ${
        active
          ? "bg-[#F0FDFA] border-[#99F6E4] text-[#0F766E]"
          : "bg-white border-[#E5E7EB] text-[#374151] hover:bg-[#F9FAFB]"
      }`}
    >
      {children}
    </button>
  );
}

function QuickButton({ onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="px-2.5 py-1 rounded-full border border-[#E5E7EB] bg-white text-xs font-semibold text-[#374151] hover:bg-[#F9FAFB]"
    >
      {children}
    </button>
  );
}

// Pick the N highest-average series ids for a sensible default view.
function topByAverage(seriesById, ids, n) {
  const avg = (id) => {
    const vals = Object.values(seriesById[id] || {});
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : -Infinity;
  };
  return [...ids].sort((a, b) => avg(b) - avg(a)).slice(0, n);
}

export default function RiceYieldAnalytics() {
  const { city } = useParams();

  const [meta, setMeta] = useState({ years: [], seasons: [] });
  const [season, setSeason] = useState(null);
  const [level, setLevel] = useState("municipality"); // "municipality" | "barangay"
  const [chartType, setChartType] = useState("line");
  const [showAverage, setShowAverage] = useState(false);
  const [zoomEnabled, setZoomEnabled] = useState(true);
  const [loading, setLoading] = useState(false);

  // List controls
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState("name"); // "name" | "yield"
  const [hoverId, setHoverId] = useState(null);

  // Municipality comparison (province-wide).
  const [munis, setMunis] = useState([]); // [{ id, name, latest }]
  const [selectedMuni, setSelectedMuni] = useState([]); // ordered ids (order = colour)
  const [seriesByMuni, setSeriesByMuni] = useState({}); // { id: { year: yield } }

  // Predicted vs Recorded (municipality-level only).
  const [predMeta, setPredMeta] = useState({ has_predictions: false, years: [] });
  const [compareYear, setCompareYear] = useState(null);
  const [compareResp, setCompareResp] = useState(null);

  // Barangay comparison, always scoped to ONE municipality.
  const [brgyMunis, setBrgyMunis] = useState([]);
  const [brgyMuniId, setBrgyMuniId] = useState(null);
  const [brgys, setBrgys] = useState([]);
  const [selectedBrgy, setSelectedBrgy] = useState([]);
  const [brgySeries, setBrgySeries] = useState({});
  const [brgyYears, setBrgyYears] = useState([]);

  const cityLabel = useMemo(
    () => (city ? city.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Laguna Province"),
    [city],
  );
  const latestYear = meta.years?.[meta.years.length - 1];

  // Filter options, barangay availability, prediction availability.
  useEffect(() => {
    let active = true;
    yieldApi
      .meta()
      .then((m) => {
        if (!active) return;
        setMeta(m);
        setSeason(m.seasons?.[0] ?? "Dry");
      })
      .catch(() => {});
    yieldApi
      .barangayMunicipalities()
      .then((r) => {
        if (!active) return;
        const list = r.municipalities || [];
        setBrgyMunis(list);
        if (list.length) setBrgyMuniId(list[0].municipality_id);
      })
      .catch(() => {});
    yieldApi
      .predictionsMeta()
      .then((m) => {
        if (!active) return;
        setPredMeta(m);
        if (m.years?.length) setCompareYear(m.years[m.years.length - 1]);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  // Municipality list + latest-year value for the list column (re-fetched per season).
  // The first load also picks a default selection: the four research-locale
  // cities (Santa Rosa, Calamba, Cabuyao, Biñan), in that order.
  useEffect(() => {
    if (!latestYear || !season) return;
    let active = true;
    yieldApi
      .municipalities(latestYear, season)
      .then((r) => {
        if (!active) return;
        const list = (r.records || []).map((x) => ({ id: x.municipality_id, name: x.name, latest: x.yield }));
        list.sort((a, b) => a.name.localeCompare(b.name));
        setMunis(list);
        const fold = (s) => (s || "").toLowerCase().replace(/ñ/g, "n");
        const research = ["santa rosa", "calamba", "cabuyao", "binan"]
          .map((kw) => list.find((m) => fold(m.name).includes(kw))?.id)
          .filter((id) => id != null);
        setSelectedMuni((prev) => (prev.length ? prev : research));
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [latestYear, season]);

  // Observed vs predicted (+ MAE) for the chosen comparison year + season.
  useEffect(() => {
    if (!compareYear || !season) {
      setCompareResp(null);
      return;
    }
    let active = true;
    yieldApi
      .compare(compareYear, season)
      .then((r) => active && setCompareResp(r))
      .catch(() => active && setCompareResp(null));
    return () => {
      active = false;
    };
  }, [compareYear, season]);

  // Municipality series for each selected municipality.
  useEffect(() => {
    if (level !== "municipality" || !season) return;
    if (selectedMuni.length === 0) {
      setSeriesByMuni({});
      return;
    }
    let active = true;
    setLoading(true);
    Promise.all(selectedMuni.map((id) => yieldApi.trend(season, id).then((r) => [id, r.series || []])))
      .then((pairs) => {
        if (!active) return;
        const out = {};
        for (const [id, series] of pairs) {
          out[id] = {};
          for (const pt of series) out[id][pt.year] = pt.avg;
        }
        setSeriesByMuni(out);
      })
      .catch(() => active && setSeriesByMuni({}))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [level, season, selectedMuni]);

  // Barangay series: all barangays of the chosen municipality, for the season.
  useEffect(() => {
    if (level !== "barangay" || !season || !brgyMuniId) return;
    let active = true;
    setLoading(true);
    yieldApi
      .barangaySeries(brgyMuniId, season)
      .then((r) => {
        if (!active) return;
        const list = (r.barangays || []).map((b) => ({ id: b.barangay_id, name: b.name }));
        list.sort((a, b) => a.name.localeCompare(b.name));
        const series = {};
        for (const b of r.barangays || []) series[b.barangay_id] = b.series || {};
        setBrgys(list);
        setBrgySeries(series);
        setBrgyYears(r.years || []);
        setSelectedBrgy(topByAverage(series, list.map((b) => b.id), 6));
      })
      .catch(() => {
        if (!active) return;
        setBrgys([]);
        setBrgySeries({});
        setBrgyYears([]);
        setSelectedBrgy([]);
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [level, season, brgyMuniId]);

  // Generic view over whichever level is active.
  const isBarangay = level === "barangay";
  const entities = isBarangay ? brgys : munis;
  const selected = isBarangay ? selectedBrgy : selectedMuni;
  const setSelected = isBarangay ? setSelectedBrgy : setSelectedMuni;
  const seriesById = isBarangay ? brgySeries : seriesByMuni;
  const years = isBarangay ? brgyYears : meta.years;
  const entityWord = isBarangay ? "barangay" : "municipality";
  const entityWordPlural = isBarangay ? "barangays" : "municipalities";

  const colorFor = useMemo(() => {
    const map = {};
    selected.forEach((id, i) => {
      map[id] = PALETTE[i % PALETTE.length];
    });
    return map;
  }, [selected]);

  // Keep selection order (so colours stay stable) when building the chart series.
  const selectedEntities = selected.map((id) => entities.find((e) => e.id === id)).filter(Boolean);
  const hoverActive = hoverId != null && selected.includes(hoverId);
  const isFaded = (id) => hoverActive && id !== hoverId;

  const toggleEntity = (id) =>
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_SELECTED) return prev;
      return [...prev, id];
    });

  // Value shown next to each name in the list.
  const listValue = (e) => {
    if (isBarangay) {
      const vals = Object.values(brgySeries[e.id] || {}).filter((v) => v != null);
      return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    }
    return e.latest ?? null;
  };
  const listValueHeader = isBarangay ? `${season ?? ""} avg` : `${season ?? ""} ${latestYear ?? ""}`;

  const q = query.trim().toLowerCase();
  const listItems = entities
    .filter((e) => !q || e.name.toLowerCase().includes(q))
    .map((e) => ({ ...e, value: listValue(e) }))
    .sort((a, b) => (sortBy === "yield" ? (b.value ?? -1) - (a.value ?? -1) : a.name.localeCompare(b.name)));
  const byValueDesc = [...entities].map((e) => ({ id: e.id, v: listValue(e) ?? -1 })).sort((a, b) => b.v - a.v);
  const atCap = selected.length >= MAX_SELECTED;

  const barangayAvailable = brgyMunis.length > 0;
  const activeBrgyMuniName = brgyMunis.find((m) => m.municipality_id === brgyMuniId)?.name ?? "";

  // [{ year, e<id>: yield, ..., average }] across the active year range.
  const chartData = useMemo(() => {
    return years.map((year) => {
      const row = { year };
      const vals = [];
      for (const e of selectedEntities) {
        const v = seriesById[e.id]?.[year];
        if (v != null) {
          row[`e${e.id}`] = v;
          vals.push(v);
        }
      }
      row.average = vals.length ? Number((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(3)) : null;
      return row;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [years, selected, entities, seriesById]);

  const ChartComponent = chartType === "line" ? LineChart : BarChart;

  const compareChartData = useMemo(() => {
    if (isBarangay || !compareResp) return [];
    return (compareResp.records || [])
      .filter((r) => selectedMuni.includes(r.municipality_id))
      .map((r) => ({ name: r.name, observed: r.observed, predicted: r.predicted, residual: r.residual }));
  }, [compareResp, selectedMuni, isBarangay]);

  const hoverEntity = hoverActive ? selectedEntities.find((e) => e.id === hoverId) : null;
  const statsFor = (id) => {
    const vals = years.map((y) => seriesById[id]?.[y]).filter((v) => v != null);
    if (!vals.length) return null;
    return {
      avg: vals.reduce((a, b) => a + b, 0) / vals.length,
      min: Math.min(...vals),
      max: Math.max(...vals),
      latest: seriesById[id]?.[years[years.length - 1]],
    };
  };
  const hoverStats = hoverEntity ? statsFor(hoverEntity.id) : null;

  return (
    <div className="flex w-full h-screen bg-white font-sans pb-14 md:pb-0" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      <DashboardSidebar active="compare" city={city} />

      <div className="flex flex-col flex-1 min-w-0 anim-fade-in">
        <header className="flex items-center justify-between gap-3 px-4 md:px-10 h-14 md:h-20 shrink-0 bg-white border-b border-[#E5E7EB]">
          <h1 className="text-base md:text-2xl font-bold text-[#1F2937] tracking-[-0.6px] truncate">
            <span className="md:hidden">Analytics</span>
            <span className="hidden md:inline">Rice Yield Analytics and Comparison</span>
          </h1>
          <span className="text-xs md:text-sm font-medium text-[#6B7280] shrink-0">{cityLabel}</span>
        </header>

        <div className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-10">
          <div className="flex flex-col gap-6 p-6 bg-white border border-[#F3F4F6] shadow-sm rounded-2xl">
            {/* Level + Season filters (unchanged) */}
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-[#374151]">Compare by</span>
                <div className="flex p-1 gap-1 bg-[#F3F4F6] rounded-lg">
                  <button
                    type="button"
                    onClick={() => setLevel("municipality")}
                    className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                      level === "municipality" ? "bg-white text-[#1B3315] shadow-sm" : "text-[#4B5563]"
                    }`}
                  >
                    Municipality
                  </button>
                  <button
                    type="button"
                    onClick={() => barangayAvailable && setLevel("barangay")}
                    disabled={!barangayAvailable}
                    title={barangayAvailable ? "Compare barangays within one municipality" : "Barangay-level yield data not available yet"}
                    className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                      level === "barangay" ? "bg-white text-[#1B3315] shadow-sm" : "text-[#4B5563]"
                    } ${!barangayAvailable ? "opacity-40 cursor-not-allowed" : ""}`}
                  >
                    Barangay
                  </button>
                </div>
                {!barangayAvailable && <span className="text-[11px] text-[#9CA3AF]">Barangay: needs data</span>}
              </div>

              {isBarangay && (
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-[#374151]">Municipality</span>
                  <div className="relative">
                    <select
                      value={brgyMuniId ?? ""}
                      onChange={(e) => setBrgyMuniId(e.target.value ? Number(e.target.value) : null)}
                      className="appearance-none pl-3 pr-9 py-1.5 bg-white border border-[#C3C8BD] rounded-lg text-sm text-[#191C1A] outline-none focus:border-[#3B9E1C] cursor-pointer"
                    >
                      {brgyMunis.map((m) => (
                        <option key={m.municipality_id} value={m.municipality_id}>{m.name}</option>
                      ))}
                    </select>
                    <svg width="12" height="12" viewBox="0 0 14 14" fill="none" className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
                      <path d="M2 4l5 5 5-5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-[#374151]">Season</span>
                <div className="flex gap-1">
                  {(meta.seasons.length ? meta.seasons : ["Dry", "Wet"]).map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => setSeason(opt)}
                      className={`px-3 py-1.5 rounded-full border text-sm ${
                        season === opt ? "bg-[#3B9E1C] border-[#3B9E1C] text-white" : "bg-[#ECEFEA] border-[#C3C8BD] text-[#191C1A]"
                      }`}
                    >
                      {opt} Season
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* List (left) + chart (right). Stacks below lg. */}
            <div className="grid grid-cols-1 lg:grid-cols-[minmax(240px,280px)_minmax(0,1fr)] gap-6 items-start">
              {/* ---------- Left: entity list ---------- */}
              <div className="flex flex-col gap-3 min-w-0">
                <h3 className="text-sm font-semibold text-[#374151] capitalize">
                  {isBarangay ? <>Barangays in {activeBrgyMuniName}</> : entityWordPlural}{" "}
                  <span className="font-medium text-[#9CA3AF] normal-case">({selected.length} selected)</span>
                </h3>

                <div className="relative flex items-center">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="absolute left-3 text-[#9CA3AF]">
                    <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
                    <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={`Search ${entityWord}...`}
                    className="w-full pl-9 pr-3 py-2.5 border border-[#E5E7EB] rounded-lg text-sm text-[#374151] outline-none focus:border-[#3B9E1C] placeholder:text-[#9CA3AF]"
                  />
                </div>

                <div className="flex items-center justify-between gap-2">
                  <div className="flex gap-1.5">
                    <QuickButton onClick={() => setSelected(byValueDesc.slice(0, 5).map((x) => x.id))}>Top 5</QuickButton>
                    <QuickButton onClick={() => setSelected(byValueDesc.slice(0, MAX_SELECTED).map((x) => x.id))}>Top {MAX_SELECTED}</QuickButton>
                    <QuickButton onClick={() => setSelected([])}>Clear</QuickButton>
                  </div>
                  <div className="flex p-0.5 gap-0.5 bg-[#F3F4F6] rounded-md">
                    {[
                      { key: "name", label: "A–Z" },
                      { key: "yield", label: "Yield" },
                    ].map((s) => (
                      <button
                        key={s.key}
                        type="button"
                        onClick={() => setSortBy(s.key)}
                        className={`px-2 py-0.5 rounded text-[11px] font-semibold text-[#374151] ${sortBy === s.key ? "bg-white shadow-sm" : ""}`}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex justify-between px-2.5 text-[11px] font-semibold text-[#9CA3AF] uppercase tracking-[0.5px]">
                  <span>Name</span>
                  <span>{listValueHeader}</span>
                </div>

                <div className="flex flex-col gap-0.5 p-1.5 min-h-[420px] max-h-[560px] overflow-y-auto bg-[#F9FAFB]/80 border border-[#F3F4F6] rounded-lg">
                  {entities.length === 0 &&
                    (loading || !isBarangay ? (
                      <div className="flex flex-col gap-2 p-1 animate-pulse">
                        {Array.from({ length: 10 }).map((_, i) => (
                          <span key={i} className="h-8 rounded-md bg-[#E5E7EB]" />
                        ))}
                      </div>
                    ) : (
                      <span className="p-3 text-sm text-[#9CA3AF]">No barangay data for {activeBrgyMuniName}.</span>
                    ))}
                  {listItems.map((e) => {
                    const on = selected.includes(e.id);
                    const blocked = atCap && !on;
                    const hovered = hoverId === e.id;
                    return (
                      <button
                        key={e.id}
                        type="button"
                        onClick={() => !blocked && toggleEntity(e.id)}
                        onMouseEnter={() => setHoverId(e.id)}
                        onMouseLeave={() => setHoverId(null)}
                        className={`flex items-center gap-2.5 w-full px-2.5 py-2 rounded-md text-left transition-colors ${
                          hovered ? (on ? "bg-[#ECF5E8]" : "bg-[#F3F4F6]") : on ? "bg-white" : ""
                        } ${blocked ? "opacity-50 cursor-not-allowed" : ""}`}
                      >
                        <span
                          className={`flex items-center justify-center w-[18px] h-[18px] shrink-0 rounded border-[1.5px] transition-colors ${
                            on ? "bg-[#3B9E1C] border-[#3B9E1C]" : "bg-white border-[#C3C8BD]"
                          }`}
                        >
                          {on && (
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M5 12l5 5 9-11" />
                            </svg>
                          )}
                        </span>
                        <span className={`flex-1 min-w-0 truncate text-sm ${on ? "font-semibold text-[#191C1A]" : "text-[#4B5563]"}`}>{e.name}</span>
                        {on && <span className="w-2.5 h-2.5 shrink-0 rounded-full" style={{ background: colorFor[e.id] }} />}
                        <span className="text-xs font-semibold text-[#6B7280] tabular-nums">
                          {e.value != null ? Number(e.value).toFixed(2) : "N/A"}
                        </span>
                      </button>
                    );
                  })}
                </div>
                {atCap && <p className="text-[11px] text-[#9CA3AF]">You can compare up to {MAX_SELECTED} at a time.</p>}
              </div>

              {/* ---------- Right: chart + table ---------- */}
              <div className="flex flex-col gap-4 min-w-0">
                <div className="flex flex-wrap items-center gap-4 pb-4 border-b border-[#F3F4F6]">
                  <ControlButton active={chartType === "line"} onClick={() => setChartType("line")}><IconLine /> Line Chart</ControlButton>
                  <ControlButton active={chartType === "bar"} onClick={() => setChartType("bar")}><IconBar /> Bar Chart</ControlButton>
                  <ControlButton active={showAverage} onClick={() => setShowAverage((v) => !v)}><IconAverage /> Show Average</ControlButton>
                  <ControlButton active={zoomEnabled} onClick={() => setZoomEnabled((v) => !v)} disabled={chartType !== "line"}>
                    <IconZoom /> Toggle Zoom: {zoomEnabled ? "On" : "Off"}
                  </ControlButton>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 min-h-6">
                  <span className="text-sm text-[#374151]">
                    {hoverEntity && hoverStats
                      ? `${hoverEntity.name}: avg ${hoverStats.avg.toFixed(3)} · min ${hoverStats.min.toFixed(3)} · max ${hoverStats.max.toFixed(3)} mt/ha`
                      : `${selected.length} ${entityWordPlural} · ${season ?? ""} season`}
                  </span>
                  {!hoverEntity && <span className="text-xs text-[#9CA3AF]">Hover a name to isolate its line</span>}
                </div>

                <div className="relative w-full h-[380px]">
                  {selected.length === 0 ? (
                    <div className="absolute inset-0 flex items-center justify-center text-sm text-[#9CA3AF]">
                      Select {entityWordPlural} from the list to compare.
                    </div>
                  ) : loading && chartData.every((r) => r.average == null) ? (
                    <div className="w-full h-full flex flex-col justify-end gap-3 pb-8 animate-pulse">
                      <div className="flex-1 pt-6 rounded bg-[#F9FAFB]" />
                      <div className="h-2 w-full rounded bg-[#F3F4F6]" />
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <ChartComponent data={chartData} margin={{ top: 20, right: 16, left: 8, bottom: 0 }} onMouseLeave={() => setHoverId(null)}>
                        <CartesianGrid stroke="#F3F4F6" vertical={false} />
                        <XAxis dataKey="year" tick={{ fontSize: 12, fill: "#6B7280" }} axisLine={{ stroke: "#E5E7EB" }} tickLine={false} />
                        <YAxis
                          tick={{ fontSize: 12, fill: "#6B7280" }}
                          axisLine={false}
                          tickLine={false}
                          width={76}
                          domain={[(min) => Math.floor((min - 0.5) * 2) / 2, (max) => Math.ceil((max + 0.5) * 2) / 2]}
                          tickFormatter={(v) => `${Number(v).toFixed(1)} mt/ha`}
                        />
                        <Tooltip
                          contentStyle={{ borderRadius: 8, border: "1px solid #E5E7EB", fontSize: 13 }}
                          formatter={(v) => (v == null ? "N/A" : `${v} mt/ha`)}
                        />
                        {selectedEntities.map((e) => {
                          const focus = hoverActive && e.id === hoverId;
                          const faded = isFaded(e.id);
                          return chartType === "line" ? (
                            <Line
                              key={e.id}
                              type="monotone"
                              dataKey={`e${e.id}`}
                              name={e.name}
                              stroke={colorFor[e.id]}
                              strokeWidth={focus ? 3.5 : 2.5}
                              strokeOpacity={faded ? 0.25 : 1}
                              dot={{ r: focus ? 4 : 3, fill: colorFor[e.id], fillOpacity: faded ? 0.25 : 1, strokeOpacity: 0 }}
                              activeDot={{ r: 5 }}
                              connectNulls
                              isAnimationActive={false}
                              onMouseEnter={() => setHoverId(e.id)}
                            >
                              {focus && (
                                <LabelList dataKey={`e${e.id}`} position="top" fontSize={11} fontWeight={700} fill="#374151" formatter={(v) => (v == null ? "" : Number(v).toFixed(2))} />
                              )}
                            </Line>
                          ) : (
                            <Bar
                              key={e.id}
                              dataKey={`e${e.id}`}
                              name={e.name}
                              fill={colorFor[e.id]}
                              fillOpacity={faded ? 0.25 : 1}
                              radius={[4, 4, 0, 0]}
                              isAnimationActive={false}
                              onMouseEnter={() => setHoverId(e.id)}
                            >
                              {focus && (
                                <LabelList dataKey={`e${e.id}`} position="top" fontSize={11} fontWeight={700} fill="#374151" formatter={(v) => (v == null ? "" : Number(v).toFixed(2))} />
                              )}
                            </Bar>
                          );
                        })}
                        {showAverage && (
                          <Line type="monotone" dataKey="average" name="Average (selected)" stroke="#111827" strokeWidth={2} strokeDasharray="6 4" dot={false} connectNulls />
                        )}
                        {zoomEnabled && chartType === "line" && (
                          <Brush dataKey="year" height={24} stroke="#3B9E1C" travellerWidth={8} fill="#F8FAF5" />
                        )}
                      </ChartComponent>
                    </ResponsiveContainer>
                  )}
                </div>

                {showAverage && selected.length > 0 && (
                  <div className="flex items-center gap-2 text-xs text-[#374151]">
                    <span className="w-5 border-t-2 border-dashed border-[#111827]" /> Average of selected
                  </div>
                )}

                {/* Summary table. Hovering a row highlights the matching line. */}
                <div className="border border-[#F3F4F6] rounded-lg overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-[#F9FAFB] text-[#6B7280]">
                      <tr>
                        <th className="text-left font-semibold px-4 py-2 capitalize">{entityWord}</th>
                        <th className="text-right font-semibold px-4 py-2">Avg</th>
                        <th className="text-right font-semibold px-4 py-2">Min</th>
                        <th className="text-right font-semibold px-4 py-2">Max</th>
                        <th className="text-right font-semibold px-4 py-2">Latest</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedEntities
                        .map((e) => ({ e, s: statsFor(e.id) }))
                        .filter((x) => x.s)
                        .sort((a, b) => b.s.avg - a.s.avg)
                        .map(({ e, s }) => (
                          <tr
                            key={e.id}
                            onMouseEnter={() => setHoverId(e.id)}
                            onMouseLeave={() => setHoverId(null)}
                            className={`border-t border-[#F3F4F6] transition-colors ${hoverId === e.id ? "bg-[#F8FAF5]" : ""}`}
                          >
                            <td className="px-4 py-2 text-[#191C1A]">
                              <span className="inline-block w-2.5 h-2.5 rounded-full mr-2 align-middle" style={{ background: colorFor[e.id] }} />
                              {e.name}
                            </td>
                            <td className="px-4 py-2 text-right font-semibold text-[#1B3315]">{s.avg.toFixed(3)}</td>
                            <td className="px-4 py-2 text-right text-[#6B7280]">{s.min.toFixed(3)}</td>
                            <td className="px-4 py-2 text-right text-[#6B7280]">{s.max.toFixed(3)}</td>
                            <td className="px-4 py-2 text-right text-[#374151]">{s.latest != null ? s.latest : "N/A"}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Predicted vs Recorded Yield (unchanged, full width below) */}
            {!isBarangay && predMeta.has_predictions && (
              <div className="flex flex-col gap-3 pt-2 border-t border-[#F3F4F6]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-sm font-medium text-[#374151]">
                    Predicted vs Recorded Yield <span className="text-[#9CA3AF]">({season} season)</span>
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-[#6B7280]">Year</span>
                    <select
                      value={compareYear ?? ""}
                      onChange={(e) => setCompareYear(Number(e.target.value))}
                      className="px-2 py-1 text-sm text-[#1F2937] bg-white border border-[#E5E7EB] rounded-lg outline-none"
                    >
                      {(predMeta.years || []).map((y) => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {compareChartData.length === 0 ? (
                  <div className="text-sm text-[#9CA3AF] px-4 py-6 text-center bg-[#F9FAFB] rounded-lg">
                    No predictions for the selected municipalities in {compareYear} {season}.
                  </div>
                ) : (
                  <>
                    <div className="w-full h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={compareChartData} margin={{ top: 8, right: 16, left: 8, bottom: 40 }}>
                          <CartesianGrid stroke="#F3F4F6" vertical={false} />
                          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#6B7280" }} interval={0} angle={-35} textAnchor="end" height={56} />
                          <YAxis tick={{ fontSize: 12, fill: "#6B7280" }} width={70} tickFormatter={(v) => `${Number(v).toFixed(1)}`} />
                          <Tooltip formatter={(v) => (v == null ? "N/A" : `${v} mt/ha`)} />
                          <Bar dataKey="observed" name="Recorded" fill="#74C476" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="predicted" name="Predicted" fill="#F2C94C" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex flex-wrap gap-6 px-4 py-3 bg-[#F9FAFB] rounded-lg text-sm">
                      <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-sm bg-[#74C476]" />Recorded avg: <b className="text-[#1B3315]">{compareResp?.stats?.observed_avg ?? "N/A"} mt/ha</b></span>
                      <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-sm bg-[#F2C94C]" />Predicted avg: <b className="text-[#1B3315]">{compareResp?.stats?.predicted_avg ?? "N/A"} mt/ha</b></span>
                      <span>Model MAE: <b className="text-[#1B3315]">{compareResp?.stats?.mae ?? "N/A"} mt/ha</b></span>
                    </div>
                  </>
                )}
              </div>
            )}

            <p className="text-[11px] leading-4 text-[#9CA3AF]">
              {isBarangay ? (
                <>
                  Year-over-year observed average yield (mt/ha) per barangay in {activeBrgyMuniName}, {season} season. Source: City
                  Agriculture Office harvest reports. Barangays are compared only within their own municipality.
                </>
              ) : (
                <>
                  Year-over-year observed average yield (mt/ha) per municipality, {season} season. Source: PRiSM / Ricelytics
                  (2018 – 2026 Sem 1). Some municipalities have gaps in a few semesters.
                </>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
