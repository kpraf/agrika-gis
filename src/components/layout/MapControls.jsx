import React from "react";

export default function MapControls({ onZoomIn, onZoomOut, onRecenter }) {
  return (
    <div className="absolute right-6 bottom-6 z-[500] flex flex-col items-stretch gap-2 p-1 bg-white rounded-lg shadow-[0_4px_6px_-1px_rgba(0,0,0,0.1),0_2px_4px_-2px_rgba(0,0,0,0.1)]">
      <button
        type="button"
        onClick={onZoomIn}
        aria-label="Zoom in"
        className="w-8 h-8 flex items-center justify-center rounded text-[#4B5563] hover:bg-[#F3F4F6]"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
      <div className="h-px bg-[#E5E7EB] mx-1" />
      <button
        type="button"
        onClick={onRecenter}
        aria-label="Recenter map"
        className="w-8 h-8 flex items-center justify-center rounded text-[#4B5563] hover:bg-[#F3F4F6]"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="2" fill="currentColor" />
          <path d="M8 1v2.5M8 12.5V15M1 8h2.5M12.5 8H15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
      <div className="h-px bg-[#E5E7EB] mx-1" />
      <button
        type="button"
        onClick={onZoomOut}
        aria-label="Zoom out"
        className="w-8 h-8 flex items-center justify-center rounded text-[#4B5563] hover:bg-[#F3F4F6]"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M2 8h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}
