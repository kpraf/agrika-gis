import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { foldText } from "../../lib/text";

// Right-panel card on the map: the growth-phase pictures the model used for the
// selected city or barangay and season, Sentinel-2 NDVI and Sentinel-1 radar, one per
// phase. Files and index come from backend/scripts/build_phase_pictures.py
// (public/phase-pictures). Keys are folded names, so they match in any database.

const BASE = "/phase-pictures";
const PHASES = ["Vegetative", "Reproductive", "Ripening"];
const ROWS = [
  { kind: "n", col: 1, label: "NDVI", sub: "Sentinel-2" },
  { kind: "r", col: 2, label: "Radar", sub: "Sentinel-1" },
];

let indexPromise = null; // fetched once per page load
const loadIndex = () =>
  (indexPromise ??= fetch(`${BASE}/index.json`)
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null));

const key = (name) => foldText(name).replace(/^city of /, "");
const slug = (k) => k.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

function fmtDate(d) {
  return new Date(`${d}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

// The six pictures, in a grid of phases (columns) by sensor (rows). `size` is the
// image width class; the card uses the panel width, the enlarged view a fixed size.
function PictureGrid({ phases, src, name, imgClass }) {
  return (
    <div className="grid grid-cols-[auto_1fr_1fr_1fr] gap-x-2 gap-y-1.5 items-center">
      <span />
      {PHASES.map((p, i) => (
        <span key={p} className="text-center text-[11px] leading-tight font-semibold text-[#374151]">
          Phase {i + 1}
          <br />
          <span className="font-normal text-[#6B7280]">{p}</span>
        </span>
      ))}
      {ROWS.map((row) => (
        <React.Fragment key={row.kind}>
          <span className="text-[11px] leading-tight font-semibold text-[#374151] pr-1">
            {row.label}
            <br />
            <span className="font-normal text-[#6B7280]">{row.sub}</span>
          </span>
          {[1, 2, 3].map((ph) => {
            const date = phases.find((e) => e[0] === ph)?.[row.col];
            return (
              <figure key={ph} className="m-0 flex flex-col items-center gap-1">
                {date ? (
                  <img
                    src={src(ph, row.kind)}
                    alt={`${row.label}, phase ${ph}, ${name}, ${fmtDate(date)}`}
                    loading="lazy"
                    className={`${imgClass} aspect-square object-contain bg-white border border-[#E1E3DE] rounded-md`}
                  />
                ) : (
                  <div className={`${imgClass} aspect-square flex items-center justify-center p-1 bg-white border border-dashed border-[#D1D5DB] rounded-md text-center text-[10px] leading-tight text-[#9CA3AF]`}>
                    {row.kind === "n" ? "No cloud-free picture" : "No picture"}
                  </div>
                )}
                <figcaption className="text-[10px] text-[#6B7280] whitespace-nowrap">{date ? fmtDate(date) : " "}</figcaption>
              </figure>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
}

export default function PhasePicturesCard({ selection, year, season }) {
  const [index, setIndex] = useState(null);
  const [enlarged, setEnlarged] = useState(false);
  useEffect(() => {
    if (!enlarged) return;
    const onKey = (e) => e.key === "Escape" && setEnlarged(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enlarged]);
  useEffect(() => {
    let active = true;
    loadIndex().then((i) => active && setIndex(i));
    return () => {
      active = false;
    };
  }, []);

  if (!selection || (selection.level !== "municipality" && selection.level !== "barangay") || !year || !season)
    return null;
  const isBrgy = selection.level === "barangay";
  const level = isBrgy ? "b" : "m";
  const k = isBrgy ? `${key(selection.municipalityName)}|${key(selection.name)}` : key(selection.name);
  const place = isBrgy ? `${slug(key(selection.municipalityName))}/${slug(key(selection.name))}` : slug(k);
  const phases = index?.[level]?.[k]?.[`${year} ${season}`];
  const src = (phase, kind) => `${BASE}/${level}/${place}/${year}${season[0]}${phase}-${kind}.webp`;

  return (
    <div className="flex flex-col gap-3 p-6 bg-[#F9FAFB] border border-[#C3C8BD] rounded-xl w-full">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Growth-Phase Pictures</h4>
        <span className="text-xs text-[#6B7280]">{season} {year}</span>
      </div>

      {!index ? (
        <p className="m-0 text-sm text-[#9CA3AF]">Loading pictures…</p>
      ) : !phases ? (
        <p className="m-0 text-[13px] leading-5 text-[#6B7280]">
          No growth-phase pictures for {selection.name} in {season} {year}.
        </p>
      ) : (
        <>
          <button
            type="button"
            onClick={() => setEnlarged(true)}
            title="View larger"
            className="block w-full p-0 bg-transparent border-0 text-left cursor-zoom-in"
          >
            <PictureGrid phases={phases} src={src} name={selection.name} imgClass="w-full" />
          </button>
          <button
            type="button"
            onClick={() => setEnlarged(true)}
            className="self-start text-xs font-semibold text-[#1F6306] hover:underline"
          >
            View larger
          </button>
          <p className="m-0 text-[11px] leading-4 text-[#6B7280]">
            {isBrgy
              ? "The pictures cover the whole barangay, including land that is not rice."
              : "The pictures show the city's rice fields only."}{" "}
            These are the pictures the model reads for this season; greener NDVI means denser green vegetation.
          </p>
        </>
      )}

      {/* Portal: the side panel is a transformed drawer, which would trap a fixed overlay. */}
      {enlarged && phases && createPortal(
        <div
          className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-black/60"
          onClick={() => setEnlarged(false)}
          role="dialog"
          aria-modal="true"
          aria-label={`Growth-phase pictures, ${selection.name}, ${season} ${year}`}
        >
          <div
            className="flex flex-col gap-4 max-w-full max-h-full overflow-auto p-5 sm:p-6 bg-white rounded-2xl shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="m-0 text-base font-bold text-[#1F2937]">Growth-Phase Pictures, {selection.name}</h3>
                <p className="m-0 text-sm text-[#6B7280]">{season} {year}</p>
              </div>
              <button
                type="button"
                onClick={() => setEnlarged(false)}
                aria-label="Close"
                className="p-1.5 -mr-1.5 text-[#6B7280] hover:text-[#1F2937]"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
              </button>
            </div>
            <PictureGrid phases={phases} src={src} name={selection.name} imgClass="w-[min(26vw,260px)]" />
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
