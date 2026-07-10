import React, { useMemo, useState } from "react";
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
  ReferenceLine,
  Brush,
} from "recharts";
import DashboardSidebar from "../layout/DashboardSidebar";

const MUNICIPALITIES = [
  { key: "calamba", label: "Calamba", color: "#F97316" },
  { key: "sanPablo", label: "San Pablo", color: "#0D9488" },
  { key: "malolos", label: "Malolos", color: "#FACC15" },
  { key: "cabuyao", label: "Cabuyao", color: "#3B82F6" },
];

// Mock weekly yield (MT/ha, cumulative) across a 12-week rice growing season.
const WEEKLY_DATA = [
  { week: "Wk 1", stage: "vegetative", calamba: 0.8, sanPablo: 0.6, malolos: 0.7, cabuyao: 0.9 },
  { week: "Wk 2", stage: "vegetative", calamba: 1.3, sanPablo: 1.0, malolos: 1.1, cabuyao: 1.4 },
  { week: "Wk 3", stage: "vegetative", calamba: 1.9, sanPablo: 1.5, malolos: 1.6, cabuyao: 2.0 },
  { week: "Wk 4", stage: "vegetative", calamba: 2.4, sanPablo: 2.0, malolos: 2.1, cabuyao: 2.6 },
  { week: "Wk 5", stage: "vegetative", calamba: 2.9, sanPablo: 2.4, malolos: 2.5, cabuyao: 3.1 },
  { week: "Wk 6", stage: "vegetative", calamba: 3.3, sanPablo: 2.8, malolos: 2.9, cabuyao: 3.5 },
  { week: "Wk 7", stage: "reproductive", calamba: 3.8, sanPablo: 3.3, malolos: 3.4, cabuyao: 4.0 },
  { week: "Wk 8", stage: "reproductive", calamba: 4.2, sanPablo: 3.7, malolos: 3.8, cabuyao: 4.4 },
  { week: "Wk 9", stage: "reproductive", calamba: 4.5, sanPablo: 4.0, malolos: 4.1, cabuyao: 4.7 },
  { week: "Wk 10", stage: "reproductive", calamba: 4.7, sanPablo: 4.2, malolos: 4.3, cabuyao: 4.9 },
  { week: "Wk 11", stage: "reproductive", calamba: 4.9, sanPablo: 4.4, malolos: 4.5, cabuyao: 5.1 },
  { week: "Wk 12", stage: "reproductive", calamba: 5.1, sanPablo: 4.6, malolos: 4.7, cabuyao: 5.4 },
];

const STAGES = [
  { key: "vegetative", label: "Vegetative Stage" },
  { key: "reproductive", label: "Reproductive Stage" },
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
function IconPlay() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="white" stroke="none">
      <path d="M6 4l14 8-14 8V4z" />
    </svg>
  );
}

function ControlButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm font-medium shadow-sm transition-colors ${
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
  const [variety, setVariety] = useState("All Crops");
  const [year, setYear] = useState("2024");
  const [selected, setSelected] = useState(() => new Set(MUNICIPALITIES.map((m) => m.key)));
  const [chartType, setChartType] = useState("line");
  const [showAverage, setShowAverage] = useState(false);
  const [zoomEnabled, setZoomEnabled] = useState(true);
  const [stage, setStage] = useState(null); // null = all stages

  const cityLabel = useMemo(
    () => (city ? city.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Laguna Province"),
    [city]
  );

  const toggleMunicipality = (key) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size === 1) return prev; // keep at least one series visible
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const activeMunicipalities = MUNICIPALITIES.filter((m) => selected.has(m.key));

  const chartData = useMemo(() => {
    const rows = stage ? WEEKLY_DATA.filter((row) => row.stage === stage) : WEEKLY_DATA;
    return rows.map((row) => {
      const values = activeMunicipalities.map((m) => row[m.key]);
      const average = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
      return { ...row, average: Number(average.toFixed(2)) };
    });
  }, [stage, activeMunicipalities]);

  const ChartComponent = chartType === "line" ? LineChart : BarChart;
  const SeriesComponent = chartType === "line" ? Line : Bar;

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
            {/* Dropdown Filters */}
            <div className="flex flex-wrap gap-3">
              <select
                value={variety}
                onChange={(e) => setVariety(e.target.value)}
                className="min-w-[140px] px-3 py-2 text-sm text-[#4B5563] bg-white border border-[#E5E7EB] rounded-lg outline-none focus:border-[#3B9E1C]"
              >
                <option>All Crops</option>
                <option>Inbred Rice</option>
                <option>Hybrid Rice</option>
              </select>
              <select
                value={year}
                onChange={(e) => setYear(e.target.value)}
                className="min-w-[100px] px-3 py-2 text-sm text-[#4B5563] bg-white border border-[#E5E7EB] rounded-lg outline-none focus:border-[#3B9E1C]"
              >
                <option>2024</option>
                <option>2023</option>
                <option>2022</option>
              </select>
            </div>

            {/* Municipality Selection */}
            <div className="flex flex-col gap-3">
              <h3 className="text-sm font-medium text-[#374151]">Select municipalities in Laguna</h3>
              <div className="flex flex-wrap items-center gap-4 px-4 py-3 bg-[#F9FAFB]/80 border border-[#F3F4F6] rounded-lg">
                {MUNICIPALITIES.map((m, i) => (
                  <React.Fragment key={m.key}>
                    {i > 0 && <div className="w-px h-4 bg-[#D1D5DB]" />}
                    <label className="flex items-center gap-1.5 text-sm text-[#374151] cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={selected.has(m.key)}
                        onChange={() => toggleMunicipality(m.key)}
                        className="sr-only peer"
                      />
                      <span
                        className="w-[18px] h-[18px] rounded flex items-center justify-center transition-opacity peer-focus-visible:ring-2"
                        style={{ background: m.color, opacity: selected.has(m.key) ? 1 : 0.3 }}
                      >
                        {selected.has(m.key) && (
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                            <path d="M2 6l3 3 5-6" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </span>
                      {m.label}
                    </label>
                  </React.Fragment>
                ))}
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
              <ControlButton active={zoomEnabled} onClick={() => setZoomEnabled((v) => !v)}>
                <IconZoom /> Toggle Zoom: {zoomEnabled ? "On" : "Off"}
              </ControlButton>
            </div>

            {/* Chart Area */}
            <div className="w-full h-[350px] pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <ChartComponent data={chartData} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
                  <CartesianGrid stroke="#F3F4F6" vertical={false} />
                  <XAxis dataKey="week" tick={{ fontSize: 12, fill: "#6B7280" }} axisLine={{ stroke: "#E5E7EB" }} tickLine={false} />
                  <YAxis
                    tick={{ fontSize: 12, fill: "#6B7280" }}
                    axisLine={false}
                    tickLine={false}
                    unit=" MT/ha"
                    width={80}
                  />
                  <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #E5E7EB", fontSize: 13 }} />
                  <Legend wrapperStyle={{ fontSize: 13 }} />
                  {activeMunicipalities.map((m) =>
                    chartType === "line" ? (
                      <Line
                        key={m.key}
                        type="monotone"
                        dataKey={m.key}
                        name={m.label}
                        stroke={m.color}
                        strokeWidth={2.5}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                    ) : (
                      <Bar key={m.key} dataKey={m.key} name={m.label} fill={m.color} radius={[4, 4, 0, 0]} />
                    )
                  )}
                  {showAverage && (
                    <Line
                      type="monotone"
                      dataKey="average"
                      name="Average"
                      stroke="#111827"
                      strokeWidth={2}
                      strokeDasharray="6 4"
                      dot={false}
                    />
                  )}
                  {zoomEnabled && (
                    <Brush dataKey="week" height={24} stroke="#3B9E1C" travellerWidth={8} fill="#F8FAF5" />
                  )}
                </ChartComponent>
              </ResponsiveContainer>
            </div>

            {/* Bottom Control Bar — Plant Growth Stages */}
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => setStage(null)}
                aria-label="Show all growth stages"
                title="Show all growth stages"
                className="flex items-center justify-center w-10 h-10 rounded-lg bg-[#0F766E] shadow-sm shrink-0"
              >
                <IconPlay />
              </button>
              <div className="flex flex-1 gap-2">
                {STAGES.map((s) => (
                  <button
                    key={s.key}
                    type="button"
                    onClick={() => setStage((prev) => (prev === s.key ? null : s.key))}
                    className={`flex-1 h-10 rounded-lg border text-sm font-medium transition-colors ${
                      stage === s.key
                        ? "bg-[#0F766E] border-[#0F766E] text-white"
                        : "bg-[#F0FDFA] border-[#CCFBF1] text-[#0F766E] hover:bg-[#CCFBF1]/60"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
