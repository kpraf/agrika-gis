import React, { useEffect, useRef, useState } from "react";

// Compact "View" popover that replaces the Line / Bar / Average / Zoom button row.
// Sits at the right end of the Compare by / Season filter row.
export default function ViewMenu({ chartType, setChartType, showAverage, setShowAverage, zoomEnabled, setZoomEnabled }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const seg = (on) =>
    `flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm font-medium transition-[background-color,border-color,color,transform] duration-150 active:scale-[0.96] motion-reduce:active:scale-100 ${
      on ? "bg-[#F0FDFA] border-[#99F6E4] text-[#0F766E]" : "bg-white border-[#E5E7EB] text-[#374151] hover:bg-[#F9FAFB]"
    }`;

  const Toggle = ({ on, onClick, disabled, children }) => (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex items-center justify-between gap-3 w-full px-1 py-1 text-sm text-[#374151] disabled:opacity-40"
    >
      {children}
      <span className={`relative w-8 h-[18px] rounded-full transition-colors ${on ? "bg-[#3B9E1C]" : "bg-[#D1D5DB]"}`}>
        <span
          className="absolute top-[2px] left-[2px] w-[14px] h-[14px] rounded-full bg-white shadow transition-transform duration-200 ease-out motion-reduce:transition-none"
          style={{ transform: on ? "translateX(14px)" : "translateX(0)" }}
        />
      </span>
    </button>
  );

  return (
    <div ref={ref} className="relative ml-auto">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="true"
        aria-expanded={open}
        className={`group flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border text-[13px] font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-out hover:-translate-y-px hover:shadow-sm active:translate-y-0 active:scale-[0.97] active:shadow-none motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100 ${
          open
            ? "bg-[#F0FDF4] border-[#1F6306] text-[#1F6306]"
            : "bg-white border-[#E5E7EB] text-[#4B5563] hover:bg-[#F9FAFB] hover:border-[#C3C8BD]"
        }`}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          aria-hidden="true"
          className={`transition-transform duration-300 ease-out motion-reduce:transition-none ${
            open ? "rotate-180" : "group-hover:scale-110"
          }`}
        >
          <path d="M4 6h16M7 12h10M10 18h4" />
        </svg>
        View
      </button>

      {open && (
        <div className="anim-pop-in origin-top-right absolute right-0 top-[38px] z-20 flex flex-col gap-3 w-[240px] p-3 bg-white border border-[#E5E7EB] rounded-[10px] shadow-[0_12px_24px_rgba(0,0,0,0.1)]">
          <div className="flex flex-col gap-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#9CA3AF]">Chart type</span>
            <div className="flex gap-2">
              <button type="button" onClick={() => setChartType("line")} className={seg(chartType === "line")}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 17l5-6 4 4 9-11" /></svg>
                Line
              </button>
              <button type="button" onClick={() => setChartType("bar")} className={seg(chartType === "bar")}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 20V10M12 20V4M20 20v-7" /></svg>
                Bar
              </button>
            </div>
          </div>
          <div className="flex flex-col gap-1 pt-2 border-t border-[#F3F4F6]">
            <Toggle on={showAverage} onClick={() => setShowAverage((v) => !v)}>Show average</Toggle>
            <Toggle on={zoomEnabled && chartType === "line"} onClick={() => setZoomEnabled((v) => !v)} disabled={chartType !== "line"}>
              Zoom slider
            </Toggle>
          </div>
        </div>
      )}
    </div>
  );
}
