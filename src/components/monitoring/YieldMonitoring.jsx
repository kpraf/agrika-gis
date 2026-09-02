import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  PieChart,
  Pie,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";
import DashboardSidebar from "../layout/DashboardSidebar";
import LagunaMap from "../gis/LagunaMap";
import { yieldApi } from "../../lib/api";

// Green ramp shared with the map's choropleth.
const RAMP = ["#EDF8E9", "#C7E9C0", "#A1D99B", "#74C476", "#41AB5D", "#238B45", "#005A32"];

// Yield brackets (mt/ha) for the distribution pie.
const BRACKETS = [
  { label: "< 3.5", test: (y) => y < 3.5, color: "#C7E9C0" },
  { label: "3.5 – 4.0", test: (y) => y >= 3.5 && y < 4.0, color: "#A1D99B" },
  { label: "4.0 – 4.5", test: (y) => y >= 4.0 && y < 4.5, color: "#74C476" },
  { label: "4.5 – 5.0", test: (y) => y >= 4.5 && y < 5.0, color: "#41AB5D" },
  { label: "≥ 5.0", test: (y) => y >= 5.0, color: "#238B45" },
];

function yieldColor(value, min, max) {
  if (value == null || max <= min) return RAMP[3];
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  return RAMP[Math.round(t * (RAMP.length - 1))];
}

function SectionHeading({ title }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center justify-center w-8 h-8 rounded-full bg-[#3B9E1C]/20">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1B3315" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 12h4l3 8 4-16 3 8h4" />
        </svg>
      </span>
      <h2 className="text-xl font-bold text-[#1F2937]">{title}</h2>
    </div>
  );
}

function StatCard({ label, value, unit }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 h-24 bg-[#F9FAFB] border border-[#F3F4F6] rounded-lg">
      <span className="text-2xl font-bold text-[#1B3315]">
        {value}
        {unit && <span className="text-sm font-normal text-[#6B7280]"> {unit}</span>}
      </span>
      <span className="text-xs font-semibold text-[#6B7280] uppercase">{label}</span>
    </div>
  );
}

export default function YieldMonitoring() {
  const { city } = useParams();

  const [meta, setMeta] = useState({ years: [], seasons: [] });
  const [season, setSeason] = useState(null);
  const [year, setYear] = useState(null);
  const [resp, setResp] = useState(null); // { stats, records } for year+season
  const [trend, setTrend] = useState([]); // yearly series
  const [selection, setSelection] = useState(null); // from the map
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("bar"); // "bar" | "pie" | "table"

  const cityLabel = useMemo(
    () => (city ? city.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Laguna Province"),
    [city]
  );

  // Filter options from the data.
  useEffect(() => {
    yieldApi.meta().then((m) => {
      setMeta(m);
      if (m.years?.length) setYear(m.years[m.years.length - 1]);
      if (m.seasons?.length) setSeason(m.seasons[0]);
    }).catch(() => {});
  }, []);

  // Snapshot for the selected year + season (drives bar, pie, table, map).
  useEffect(() => {
    if (!year || !season) return;
    let active = true;
    setLoading(true);
    yieldApi.municipalities(year, season)
      .then((r) => active && setResp(r))
      .catch(() => active && setResp(null))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [year, season]);

  // Year-over-year trend — province-wide, or for the selected municipality.
  useEffect(() => {
    if (!season) return;
    let active = true;
    const mid = selection?.level === "municipality" ? selection.id : undefined;
    yieldApi.trend(season, mid)
      .then((r) => active && setTrend(r.series || []))
      .catch(() => active && setTrend([]));
    return () => { active = false; };
  }, [season, selection]);

  const records = resp?.records ?? [];
  const stats = resp?.stats;

  const barData = useMemo(
    () => [...records].sort((a, b) => b.yield - a.yield).map((r) => ({ name: r.name, yield: r.yield, is_proxy: r.is_proxy })),
    [records]
  );

  const pieData = useMemo(
    () =>
      BRACKETS.map((b) => ({
        name: b.label,
        value: records.filter((r) => b.test(r.yield)).length,
        color: b.color,
      })).filter((d) => d.value > 0),
    [records]
  );

  const yieldByMuni = useMemo(() => {
    const out = {};
    for (const r of records) out[r.municipality_id] = { yield: r.yield, is_proxy: r.is_proxy };
    return out;
  }, [records]);

  const trendLabel = selection?.level === "municipality" ? selection.name : "Laguna Province";

  return (
    <div className="flex w-full h-screen bg-[#F8FAF5] font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      <DashboardSidebar active="monitoring" city={city} />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Top Header */}
        <header className="flex items-center justify-between px-10 h-20 shrink-0 bg-white border-b border-[#E5E7EB]">
          <h1 className="text-2xl font-bold text-[#1F2937] tracking-[-0.6px]">
            Real-Time and Historical Yield Monitoring
          </h1>
          <span className="text-sm font-medium text-[#6B7280]">{cityLabel}</span>
        </header>

        <div className="flex flex-1 min-h-0">
          {/* Left Panel — charts */}
          <section className="w-[440px] shrink-0 h-full overflow-y-auto [scrollbar-gutter:stable] bg-white border-r border-[#D8DBD6] shadow-sm">
            <div className="flex flex-col gap-6 p-6">
              <SectionHeading title="Yield Overview" />

              {/* Filters */}
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-[#6B7280] uppercase">Season</label>
                  <div className="flex gap-1">
                    {(meta.seasons.length ? meta.seasons : ["Dry", "Wet"]).map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => setSeason(opt)}
                        className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                          season === opt ? "bg-[#3B9E1C] text-white shadow-sm" : "bg-[#F3F4F6] text-[#4B5563]"
                        }`}
                      >
                        {opt} Season
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  <label htmlFor="mon-year" className="text-xs font-semibold text-[#6B7280] uppercase">Year</label>
                  <div className="relative">
                    <select
                      id="mon-year"
                      value={year ?? ""}
                      onChange={(e) => setYear(e.target.value ? Number(e.target.value) : null)}
                      disabled={!meta.years.length}
                      className="w-full appearance-none px-3 py-2.5 pr-9 bg-white border border-[#E5E7EB] rounded-lg text-sm text-[#374151] outline-none focus:border-[#3B9E1C] cursor-pointer disabled:opacity-50"
                    >
                      {meta.years.length ? meta.years.map((y) => <option key={y} value={y}>{y}</option>) : <option>Loading…</option>}
                    </select>
                    <svg width="12" height="12" viewBox="0 0 14 14" fill="none" className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
                      <path d="M2 4l5 5 5-5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                </div>
              </div>

              {/* Stat cards */}
              {stats && (
                <div className="grid grid-cols-3 gap-3">
                  <StatCard label="Average" value={stats.avg ?? "N/A"} unit="mt/ha" />
                  <StatCard label="Highest" value={stats.max ?? "N/A"} unit="mt/ha" />
                  <StatCard label="Lowest" value={stats.min ?? "N/A"} unit="mt/ha" />
                </div>
              )}

              {/* View switcher */}
              <div className="flex p-1 gap-1 bg-[#F3F4F6] rounded-lg">
                {[
                  { key: "bar", label: "Bar" },
                  { key: "pie", label: "Distribution" },
                  { key: "table", label: "Table" },
                ].map((t) => (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setTab(t.key)}
                    className={`flex-1 py-2 rounded text-sm font-medium transition-colors ${
                      tab === t.key ? "bg-white text-[#1B3315] shadow-sm" : "text-[#4B5563]"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {/* Bar chart — yield by municipality */}
              {tab === "bar" && (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-[#6B7280] uppercase">Yield by Municipality (mt/ha)</label>
                <div className="bg-[#F9FAFB] border border-[#F3F4F6] rounded-lg p-2">
                  {barData.length ? (
                    <ResponsiveContainer width="100%" height={Math.max(320, barData.length * 20)}>
                      <BarChart data={barData} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                        <XAxis type="number" domain={[0, "dataMax"]} tick={{ fontSize: 10, fill: "#9CA3AF" }} />
                        <YAxis type="category" dataKey="name" width={92} tick={{ fontSize: 10, fill: "#4B5563" }} interval={0} />
                        <Tooltip
                          formatter={(v, _n, p) => [`${v} mt/ha${p.payload.is_proxy ? " (est.)" : ""}`, "Yield"]}
                          contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        />
                        <Bar dataKey="yield" radius={[0, 3, 3, 0]}>
                          {barData.map((d, i) => (
                            <Cell key={i} fill={yieldColor(d.yield, stats?.min, stats?.max)} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-[#9CA3AF] p-4 text-center">{loading ? "Loading…" : "No data."}</p>
                  )}
                </div>
              </div>
              )}

              {/* Pie — distribution by yield bracket */}
              {tab === "pie" && (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-[#6B7280] uppercase">Distribution by Yield Range</label>
                <div className="flex items-center gap-3 bg-[#F9FAFB] border border-[#F3F4F6] rounded-lg p-3">
                  {pieData.length ? (
                    <>
                      <ResponsiveContainer width={130} height={130}>
                        <PieChart>
                          <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={30} outerRadius={58} paddingAngle={2}>
                            {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                          </Pie>
                          <Tooltip formatter={(v, n) => [`${v} municipalities`, n]} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="flex flex-col gap-1.5 flex-1">
                        {pieData.map((d) => (
                          <div key={d.name} className="flex items-center gap-2 text-xs text-[#374151]">
                            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: d.color }} />
                            <span className="flex-1">{d.name}</span>
                            <b>{d.value}</b>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-[#9CA3AF] p-2 text-center w-full">{loading ? "Loading…" : "No data."}</p>
                  )}
                </div>
              </div>
              )}

              {/* Table — ranked */}
              {tab === "table" && (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-[#6B7280] uppercase">Ranked Municipalities</label>
                <div className="border border-[#F3F4F6] rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-[#F3F4F6] text-[#6B7280]">
                      <tr>
                        <th className="text-left font-semibold px-3 py-2 w-8">#</th>
                        <th className="text-left font-semibold px-3 py-2">Municipality</th>
                        <th className="text-right font-semibold px-3 py-2">mt/ha</th>
                      </tr>
                    </thead>
                    <tbody>
                      {barData.map((d, i) => (
                        <tr key={d.name} className="border-t border-[#F3F4F6]">
                          <td className="px-3 py-1.5 text-[#9CA3AF]">{i + 1}</td>
                          <td className="px-3 py-1.5 text-[#191C1A]">
                            {d.name}
                            {d.is_proxy && <span className="ml-1 text-[10px] text-[#9CA3AF]">est.</span>}
                          </td>
                          <td className="px-3 py-1.5 text-right font-semibold text-[#1B3315]">{d.yield}</td>
                        </tr>
                      ))}
                      {!barData.length && (
                        <tr><td colSpan={3} className="px-3 py-4 text-center text-[#9CA3AF]">{loading ? "Loading…" : "No data."}</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              )}
            </div>
          </section>

          {/* Center — shared map (heatmap driven by the same filters) */}
          <LagunaMap
            heatmap
            yieldByMuni={yieldByMuni}
            colorScale={stats ? { min: stats.min, max: stats.max } : null}
            yieldKey={`${year}-${season}`}
            onSelectionChange={setSelection}
          />

          {/* Right Panel — historical trend */}
          <section className="w-[420px] shrink-0 h-full overflow-y-auto bg-white shadow-[-2px_0_10px_rgba(0,0,0,0.02)]">
            <div className="flex flex-col gap-6 p-6">
              <SectionHeading title="Historical Trends" />

              <p className="text-xs leading-5 text-[#6B7280]">
                Year-over-year average yield for <b>{trendLabel}</b> in the {season} season.
                {selection?.level === "municipality"
                  ? " Click “back to all” on the map for the province view."
                  : " Click a municipality on the map to focus its trend."}
              </p>

              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-[#6B7280] uppercase">
                  {season} Season Yield Trend (mt/ha)
                </label>
                <div className="bg-[#F9FAFB] border border-[#F3F4F6] rounded-lg p-3">
                  {trend.length ? (
                    <ResponsiveContainer width="100%" height={220}>
                      <LineChart data={trend} margin={{ left: 4, right: 8, top: 8, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#9CA3AF" }} />
                        <YAxis
                          width={58}
                          tick={{ fontSize: 10, fill: "#9CA3AF" }}
                          domain={[(min) => Math.floor((min - 0.5) * 2) / 2, (max) => Math.ceil((max + 0.5) * 2) / 2]}
                          tickFormatter={(v) => `${Number(v).toFixed(1)} mt/ha`}
                        />
                        <Tooltip formatter={(v) => [`${v} mt/ha`, "Avg yield"]} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                        <Line type="monotone" dataKey="avg" stroke="#1F6306" strokeWidth={2.5} dot={{ r: 3, fill: "#1F6306" }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-[#9CA3AF] p-4 text-center">Loading trend…</p>
                  )}
                </div>
              </div>

              {/* Min / max across the trend window */}
              {trend.length > 0 && (
                <div className="grid grid-cols-2 gap-4">
                  <StatCard
                    label="Best year"
                    value={trend.reduce((a, b) => (b.avg > a.avg ? b : a)).year}
                  />
                  <StatCard
                    label="Peak avg"
                    value={Math.max(...trend.map((t) => t.avg))}
                    unit="mt/ha"
                  />
                </div>
              )}

              <p className="text-[11px] leading-4 text-[#9CA3AF]">
                Source: PRiSM / Ricelytics observed municipality yields (2018–2025). Values marked
                “est.” are source proxy figures for low-rice cities. San Pedro has no palay data.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
