import React, { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import DashboardSidebar from "../layout/DashboardSidebar";
import LagunaMap from "../gis/LagunaMap";

const HARVEST_BARS = [
  { label: "Calamba", value: 80, color: "#3B9E1C" },
  { label: "Cabuyao", value: 100, color: "#0E2207" },
  { label: "Sta. Rosa", value: 40, color: "#1F6306" },
  { label: "Los Baños", value: 60, color: "#3B9E1C" },
  { label: "Biñan", value: 30, color: "#FACC15" },
];

const TREND_YEARS = ["2022", "2023", "2024", "2025", "2026"];
const YIELD_TREND_POINTS = "0,32 92,20 184,26 276,8 368,4";
const RAINFALL_TREND_POINTS = "0,64 92,72 184,50 276,58 368,44";

const FILTERS = ["Weekly", "Monthly", "Yearly", "Quarterly", "Custom Range"];

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

export default function YieldMonitoring() {
  const { city } = useParams();
  const [scope, setScope] = useState("province");
  const [activeFilter, setActiveFilter] = useState("Monthly");
  const maxBar = Math.max(...HARVEST_BARS.map((b) => b.value));

  const cityLabel = useMemo(
    () => (city ? city.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Laguna Province"),
    [city]
  );

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

        {/* Dashboard Layout */}
        <div className="flex flex-1 min-h-0">
          {/* Left Panel — Real-Time Yield View */}
          <section className="w-[400px] shrink-0 h-full overflow-y-auto bg-white border-r border-[#D8DBD6] shadow-sm">
            <div className="flex flex-col gap-6 p-6">
              <SectionHeading title="Live Overview" />

              <div className="flex p-1 gap-1 bg-[#F3F4F6] rounded-lg">
                <button
                  type="button"
                  onClick={() => setScope("province")}
                  className={`flex-1 py-2 rounded text-sm font-medium transition-colors ${
                    scope === "province" ? "bg-[#3B9E1C] text-white shadow-sm" : "text-[#4B5563]"
                  }`}
                >
                  Province-wide
                </button>
                <button
                  type="button"
                  onClick={() => setScope("barangay")}
                  className={`flex-1 py-2 rounded text-sm font-medium transition-colors ${
                    scope === "barangay" ? "bg-[#3B9E1C] text-white shadow-sm" : "text-[#4B5563]"
                  }`}
                >
                  By Barangay
                </button>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-[#6B7280]">MUNICIPALITY SEARCH</label>
                <div className="relative">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]">
                    <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
                    <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                  <input
                    type="text"
                    placeholder="e.g., San Jose"
                    className="w-full pl-9 pr-3 py-2.5 text-sm text-[#374151] bg-white border border-[#E5E7EB] rounded-lg outline-none focus:border-[#3B9E1C]"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-[#6B7280]">SORT BY YIELD</label>
                <button
                  type="button"
                  className="flex items-center justify-between px-3 py-2.5 text-sm text-[#374151] bg-white border border-[#E5E7EB] rounded-lg"
                >
                  Highest to Lowest
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path d="M1.5 3.5L5 7l3.5-3.5" stroke="#6B7280" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>

              <div className="border-t border-[#F3F4F6]" />

              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-[#6B7280] uppercase">Current Harvest Volume (MT)</label>
                <div className="flex items-end justify-center gap-2 h-[192px] bg-[#F9FAFB] border border-[#F3F4F6] rounded-lg px-4">
                  {HARVEST_BARS.map((bar) => (
                    <div key={bar.label} className="flex flex-col items-center gap-1.5 flex-1">
                      <div
                        className="w-full rounded-t-sm"
                        style={{ height: `${(bar.value / maxBar) * 128}px`, background: bar.color }}
                        title={`${bar.label}: ${bar.value} MT`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* Center — shared map */}
          <LagunaMap />

          {/* Right Panel — Historical Yield View */}
          <section className="w-[450px] shrink-0 h-full overflow-y-auto bg-white shadow-[-2px_0_10px_rgba(0,0,0,0.02)]">
            <div className="flex flex-col gap-6 p-6">
              <SectionHeading title="Historical Trends" />

              <p className="text-xs leading-5 text-[#6B7280]">
                Analyze past agricultural performance to identify trends, seasonal variations, and make
                data-driven decisions for future planting cycles.
              </p>

              <div className="flex flex-wrap gap-2">
                {FILTERS.map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    onClick={() => setActiveFilter(filter)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      activeFilter === filter ? "bg-[#3B9E1C] text-white" : "bg-[#F3F4F6] text-[#374151]"
                    }`}
                  >
                    {filter}
                  </button>
                ))}
              </div>

              <button
                type="button"
                className="flex flex-col gap-1 p-4 text-left border border-[#E5E7EB] rounded-lg"
              >
                <span className="text-xs text-[#9CA3AF]">MUNICIPALITY FILTER</span>
                <span className="flex items-center justify-between text-sm font-semibold text-[#1F2937]">
                  All Municipalities
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 4l4 4 4-4" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              </button>

              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-[#6B7280] uppercase">5-Year Trend Analysis</label>
                <div className="flex flex-col items-center justify-center gap-2 p-4 bg-[#F9FAFB] border border-[#F3F4F6] rounded-lg">
                  <svg viewBox="0 0 368 80" className="w-full h-[110px]" preserveAspectRatio="none">
                    <polyline points={YIELD_TREND_POINTS} fill="none" stroke="#0E2207" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                    <polyline points={RAINFALL_TREND_POINTS} fill="none" stroke="#FACC15" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <div className="flex justify-between w-full px-1">
                    {TREND_YEARS.map((year) => (
                      <span key={year} className="text-[10px] text-[#9CA3AF]">
                        {year}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[#6B7280] uppercase">Avg Yield/Ha</label>
                  <div className="flex flex-col items-center justify-center gap-1 h-24 bg-[#F9FAFB] border border-[#F3F4F6] rounded-lg">
                    <span className="text-2xl font-bold text-[#1B3315]">
                      4.2 <span className="text-sm font-normal text-[#6B7280]">MT</span>
                    </span>
                    <span className="flex items-center gap-1 text-xs text-[#16A34A]">
                      <svg width="9" height="10" viewBox="0 0 9 10" fill="none">
                        <path d="M4.5 9V1M1 4.5L4.5 1l3.5 3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      +12.5%
                    </span>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-[#6B7280] uppercase">Total Area Harvested</label>
                  <div className="flex flex-col items-center justify-center gap-1 h-24 bg-[#F9FAFB] border border-[#F3F4F6] rounded-lg">
                    <span className="text-2xl font-bold text-[#374151]">
                      3.8 <span className="text-sm font-normal text-[#6B7280]">K ha</span>
                    </span>
                    <span className="flex items-center gap-1 text-xs text-[#EF4444]">
                      <svg width="9" height="10" viewBox="0 0 9 10" fill="none">
                        <path d="M4.5 1v8M1 5.5L4.5 9l3.5-3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      -3.2%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
