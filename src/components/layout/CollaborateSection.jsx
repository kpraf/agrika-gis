import React from "react";
import { Link } from "react-router-dom";
import Pill from "./Pill";

// Laguna LGUs with live barangay forecasts. Update as partners join.
const COVERED = ["Biñan", "Cabuyao", "Calamba", "Santa Rosa"];

const LAGUNA_LGUS = [
  "Alaminos", "Bay", "Biñan", "Cabuyao", "Calamba", "Calauan", "Cavinti", "Famy", "Kalayaan", "Liliw",
  "Los Baños", "Luisiana", "Lumban", "Mabitac", "Magdalena", "Majayjay", "Nagcarlan", "Paete", "Pagsanjan",
  "Pakil", "Pangil", "Pila", "Rizal", "San Pablo", "San Pedro", "Santa Cruz", "Santa Maria", "Santa Rosa",
  "Siniloan", "Victoria",
];

const NEEDS = [
  { num: "01", title: "Barangay boundaries & rice areas", desc: "Shapefiles or a list of rice-producing barangays." },
  { num: "02", title: "Past yield records", desc: "Harvest per season, so the model can learn your area." },
  { num: "03", title: "Planting calendar", desc: "Usual planting and harvest months per barangay." },
];

export default function CollaborateSection() {
  const open = LAGUNA_LGUS.filter((n) => !COVERED.includes(n));
  const total = LAGUNA_LGUS.length;

  return (
    <section className="bg-white py-24 px-6 md:px-16">
      <div className="max-w-[1280px] mx-auto grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-16 items-center">
        {/* Left: pitch + what we need */}
        <div className="flex flex-col items-start gap-5">
          <Pill variant="green">Collaborate With Us</Pill>
          <h2 className="text-3xl md:text-4xl font-bold text-[#1D211C] leading-tight">
            Is your municipality on the map yet?
          </h2>
          <p className="text-base leading-6 text-[#4B5563] max-w-[500px]">
            AgriKA-GIS forecasts rice yield for every barangay we have ground records for. We're looking for more
            Laguna agricultural offices to share barangay data, so your farmers get the same forecasts.
          </p>

          <div className="w-full max-w-[500px] flex flex-col mt-2">
            {NEEDS.map((n, i) => (
              <div
                key={n.num}
                className={`flex gap-5 py-4 ${i !== NEEDS.length - 1 ? "border-b border-[#F3F4F6]" : ""}`}
              >
                <span className="w-9 shrink-0 text-2xl font-bold text-[#286A11]">{n.num}</span>
                <div className="flex flex-col gap-0.5">
                  <h4 className="text-base font-bold text-[#1D211C]">{n.title}</h4>
                  <p className="text-sm text-[#6B7280]">{n.desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-2 flex flex-wrap gap-3">
            <Link
              to="/contact"
              className="group flex items-center gap-2 px-8 py-4 rounded-full bg-[#286A11] text-white font-semibold hover:bg-[#1F6306] transition-colors"
            >
              Partner With Us
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
                className="transition-transform duration-200 ease-out group-hover:translate-x-1 motion-reduce:transition-none"
              >
                <path d="M2 8h12M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Link>
            <a
              href="mailto:agrikagis.official@gmail.com"
              className="flex items-center px-6 py-4 rounded-full border border-[#D1D5DB] text-[#1D211C] font-semibold hover:border-[#286A11] transition-colors"
            >
              Email the team
            </a>
          </div>
        </div>

        {/* Right: coverage progress */}
        <div className="bg-[#F1F8E9] rounded-3xl p-6 md:p-8 flex flex-col gap-6">
          <div className="flex flex-col gap-1">
            <div className="flex items-baseline gap-1.5">
              <span className="text-5xl md:text-6xl font-bold text-[#286A11] leading-none">{COVERED.length}</span>
              <span className="text-2xl font-bold text-[#9CA3AF]">/ {total}</span>
            </div>
            <span className="text-base font-semibold text-[#1D211C]">Laguna LGUs with live forecasts</span>
          </div>

          <div
            className="grid gap-[3px]"
            style={{ gridTemplateColumns: `repeat(${total}, minmax(0, 1fr))` }}
            role="img"
            aria-label={`${COVERED.length} of ${total} Laguna LGUs covered`}
          >
            {Array.from({ length: total }, (_, i) => (
              <span
                key={i}
                className={`h-7 rounded-[3px] ${i < COVERED.length ? "bg-[#286A11]" : "bg-white border border-[#DCE3D5]"}`}
              />
            ))}
          </div>

          <div className="flex flex-col gap-2.5">
            <span className="text-xs font-bold tracking-wider uppercase text-[#286A11]">Live now</span>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              {COVERED.map((name) => (
                <span key={name} className="flex items-center gap-2 text-[15px] font-semibold text-[#1D211C]">
                  <span className="w-2 h-2 rounded-full bg-[#286A11]" />
                  {name}
                </span>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2 pt-5 border-t border-[#DCEBCB]">
            <span className="text-xs font-bold tracking-wider uppercase text-[#6B7280]">
              Open to partner · {open.length}
            </span>
            <p className="text-sm leading-[22px] text-[#4B5563]">{open.join(" · ")}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
