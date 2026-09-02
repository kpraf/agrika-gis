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
  Legend,
  Brush,
} from "recharts";
import DashboardSidebar from "../layout/DashboardSidebar";
import { yieldApi } from "../../lib/api";

// Distinct series colours, cycled if more municipalities are selected than colours.
const PALETTE = [
  "#0D9488", "#F97316", "#3B82F6", "#7C3AED", "#DB2777",
  "#16A34A", "#CA8A04", "#0EA5E9", "#DC2626", "#4B5563",
];

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

export default function RiceYieldAnalytics() {
  const { city } = useParams();

  const [meta, setMeta] = useState({ years: [], seasons: [] });
  const [season, setSeason] = useState(null);
  const [munis, setMunis] = useState([]); // [{ id, name }]
  const [selected, setSelected] = useState(new Set()); // municipality ids
  const [seriesByMuni, setSeriesByMuni] = useState({}); // { id: { year: yield } }
  const [chartType, setChartType] = useState("line");
  const [showAverage, setShowAverage] = useState(false);
  const [zoomEnabled, setZoomEnabled] = useState(true);
  const [loading, setLoading] = useState(false);
  const [level, setLevel] = useState("municipality"); // "municipality" | "barangay" (barangay pending data)

  const cityLabel = useMemo(
    () => (city ? city.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Laguna Province"),
    [city]
  );

  // Load filter options + the municipality list, and pick a sensible default set.
  useEffect(() => {
    let active = true;
    yieldApi.meta().then((m) => {
      if (!active) return;
      setMeta(m);
      const firstSeason = m.seasons?.[0] ?? "Dry";
      const latestYear = m.years?.[m.years.length - 1];
      setSeason(firstSeason);
      if (!latestYear) return;
      yieldApi.municipalities(latestYear, firstSeason).then((r) => {
        if (!active) return;
        const list = (r.records || []).map((x) => ({ id: x.municipality_id, name: x.name }));
        list.sort((a, b) => a.name.localeCompare(b.name));
        setMunis(list);
        // default: the 4 highest-yielding municipalities that year, for a useful first view
        const top = [...(r.records || [])].sort((a, b) => b.yield - a.yield).slice(0, 4);
        setSelected(new Set(top.map((x) => x.municipality_id)));
      });
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  // Fetch the year-over-year series for each selected municipality in the chosen season.
  useEffect(() => {
    if (!season || selected.size === 0) {
      setSeriesByMuni({});
      return;
    }
    let active = true;
    setLoading(true);
    const ids = [...selected];
    Promise.all(ids.map((id) => yieldApi.trend(season, id).then((r) => [id, r.series || []])))
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
    return () => { active = false; };
  }, [season, selected]);

  const colorFor = useMemo(() => {
    const map = {};
    munis.forEach((m, i) => { map[m.id] = PALETTE[i % PALETTE.length]; });
    return map;
  }, [munis]);

  const selectedMunis = munis.filter((m) => selected.has(m.id));

  const toggleMunicipality = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        if (next.size === 1) return prev; // keep at least one
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Build [{ year, m<id>: yield, ..., average }] across all years.
  const chartData = useMemo(() => {
    return meta.years.map((year) => {
      const row = { year };
      const vals = [];
      for (const m of selectedMunis) {
        const v = seriesByMuni[m.id]?.[year];
        if (v != null) {
          row[`m${m.id}`] = v;
          vals.push(v);
        }
      }
      row.average = vals.length ? Number((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(3)) : null;
      return row;
    });
  }, [meta.years, selectedMunis, seriesByMuni]);

  const ChartComponent = chartType === "line" ? LineChart : BarChart;

  return (
    <div className="flex w-full h-screen bg-white font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      <DashboardSidebar active="compare" city={city} />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Top Header */}
        <header className="flex items-center justify-between px-10 h-20 shrink-0 bg-white border-b border-[#E5E7EB]">
          <h1 className="text-2xl font-bold text-[#1F2937] tracking-[-0.6px]">
            Rice Yield Analytics and Comparison
          </h1>
          <span className="text-sm font-medium text-[#6B7280]">{cityLabel}</span>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-6 md:p-10">
          <div className="flex flex-col gap-6 p-6 bg-white border border-[#F3F4F6] shadow-sm rounded-2xl">
            {/* Level + Season filters */}
            <div className="flex flex-wrap items-center gap-6">
              {/* Compare level — Municipality is live; Barangay awaits barangay-level data. */}
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
                    disabled
                    title="Barangay-level yield data not available yet"
                    className="px-3 py-1.5 rounded text-sm font-medium text-[#4B5563] opacity-40 cursor-not-allowed"
                  >
                    Barangay
                  </button>
                </div>
                <span className="text-[11px] text-[#9CA3AF]">Barangay: needs data</span>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-[#374151]">Season</span>
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
            </div>

            {/* Municipality Selection */}
            <div className="flex flex-col gap-3">
              <h3 className="text-sm font-medium text-[#374151]">
                Compare municipalities <span className="text-[#9CA3AF]">({selected.size} selected)</span>
              </h3>
              <div className="flex flex-wrap gap-2 px-4 py-3 bg-[#F9FAFB]/80 border border-[#F3F4F6] rounded-lg max-h-[132px] overflow-y-auto">
                {munis.length === 0 && <span className="text-sm text-[#9CA3AF]">Loading municipalities…</span>}
                {munis.map((m) => {
                  const on = selected.has(m.id);
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => toggleMunicipality(m.id)}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-sm transition-colors ${
                        on ? "border-transparent text-white" : "bg-white border-[#E5E7EB] text-[#6B7280]"
                      }`}
                      style={on ? { background: colorFor[m.id] } : undefined}
                    >
                      <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ background: on ? "rgba(255,255,255,0.9)" : colorFor[m.id] }}
                      />
                      {m.name}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Chart Controls */}
            <div className="flex flex-wrap items-center gap-4 pt-2 pb-4 border-b border-[#F3F4F6]">
              <ControlButton active={chartType === "line"} onClick={() => setChartType("line")}>
                <IconLine /> Line Chart
              </ControlButton>
              <ControlButton active={chartType === "bar"} onClick={() => setChartType("bar")}>
                <IconBar /> Bar Chart
              </ControlButton>
              <ControlButton active={showAverage} onClick={() => setShowAverage((v) => !v)}>
                <IconAverage /> Show Average
              </ControlButton>
              <ControlButton active={zoomEnabled} onClick={() => setZoomEnabled((v) => !v)} disabled={chartType !== "line"}>
                <IconZoom /> Toggle Zoom: {zoomEnabled ? "On" : "Off"}
              </ControlButton>
            </div>

            {/* Chart Area */}
            <div className="w-full h-[360px] pt-2">
              {loading && chartData.every((r) => r.average == null) ? (
                <div className="w-full h-full flex items-center justify-center text-[#9CA3AF]">Loading yield series…</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <ChartComponent data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
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
                    <Legend wrapperStyle={{ fontSize: 13 }} />
                    {selectedMunis.map((m) =>
                      chartType === "line" ? (
                        <Line
                          key={m.id}
                          type="monotone"
                          dataKey={`m${m.id}`}
                          name={m.name}
                          stroke={colorFor[m.id]}
                          strokeWidth={2.5}
                          dot={{ r: 3 }}
                          activeDot={{ r: 5 }}
                          connectNulls
                        />
                      ) : (
                        <Bar key={m.id} dataKey={`m${m.id}`} name={m.name} fill={colorFor[m.id]} radius={[4, 4, 0, 0]} />
                      )
                    )}
                    {showAverage && (
                      <Line
                        type="monotone"
                        dataKey="average"
                        name="Average (selected)"
                        stroke="#111827"
                        strokeWidth={2}
                        strokeDasharray="6 4"
                        dot={false}
                        connectNulls
                      />
                    )}
                    {zoomEnabled && chartType === "line" && (
                      <Brush dataKey="year" height={24} stroke="#3B9E1C" travellerWidth={8} fill="#F8FAF5" />
                    )}
                  </ChartComponent>
                </ResponsiveContainer>
              )}
            </div>

            {/* Summary table — per selected municipality across the year range */}
            <div className="border border-[#F3F4F6] rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-[#F9FAFB] text-[#6B7280]">
                  <tr>
                    <th className="text-left font-semibold px-4 py-2">Municipality</th>
                    <th className="text-right font-semibold px-4 py-2">Avg</th>
                    <th className="text-right font-semibold px-4 py-2">Min</th>
                    <th className="text-right font-semibold px-4 py-2">Max</th>
                    <th className="text-right font-semibold px-4 py-2">Latest</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedMunis.map((m) => {
                    const vals = meta.years.map((y) => seriesByMuni[m.id]?.[y]).filter((v) => v != null);
                    if (!vals.length) return null;
                    const avg = (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(3);
                    const latest = seriesByMuni[m.id]?.[meta.years[meta.years.length - 1]];
                    return (
                      <tr key={m.id} className="border-t border-[#F3F4F6]">
                        <td className="px-4 py-2 text-[#191C1A]">
                          <span className="inline-block w-2.5 h-2.5 rounded-full mr-2 align-middle" style={{ background: colorFor[m.id] }} />
                          {m.name}
                        </td>
                        <td className="px-4 py-2 text-right font-semibold text-[#1B3315]">{avg}</td>
                        <td className="px-4 py-2 text-right text-[#6B7280]">{Math.min(...vals).toFixed(3)}</td>
                        <td className="px-4 py-2 text-right text-[#6B7280]">{Math.max(...vals).toFixed(3)}</td>
                        <td className="px-4 py-2 text-right text-[#374151]">{latest != null ? latest : "N/A"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <p className="text-[11px] leading-4 text-[#9CA3AF]">
              Year-over-year observed average yield (mt/ha) per municipality, {season} season.
              Source: PRiSM / Ricelytics (2018–2025). Some municipalities have gaps in a few semesters.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
