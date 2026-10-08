import React from "react";
import { Link } from "react-router-dom";

const LINKS = [
  { label: "About AgriKA-GIS", to: "/about" },
  { label: "Yield Map", to: "/yield-map" },
  { label: "FAQs", to: "/faq" },
  { label: "Contact", to: "/contact" },
];

const Arrow = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M2 8h12M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const Chevron = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// Full-screen status page (404, 403). `primary`, `secondary` and `footerLink`
// are each { label, to }.
export default function StatusPage({ code, title, body, primary, secondary, footerLink }) {
  return (
    <div className="flex flex-col min-h-screen bg-[#1B3315] text-white font-['Plus_Jakarta_Sans',sans-serif]">
      <nav className="flex items-center justify-between gap-4 px-5 md:px-10 lg:px-12 py-5 md:py-6">
        <Link to="/" className="flex shrink-0">
          <img src="/images/agrika-gis-logo.png" alt="AgriKA-GIS" className="h-11 md:h-14 w-auto object-contain" />
        </Link>
        <Link
          to="/portal-access"
          className="flex items-center px-4 py-2.5 md:px-6 md:py-3 rounded-full bg-[#286A11] hover:bg-[#1F6306] text-white text-sm md:text-[15px] font-semibold transition-colors whitespace-nowrap"
        >
          Portal Access
        </Link>
      </nav>

      <main className="flex-1 flex items-center px-5 md:px-10 lg:px-12 pt-6 pb-12 md:py-12 lg:pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 md:gap-14 lg:gap-20 items-center w-full max-w-[1200px] mx-auto">
          {/* Numeral: top on mobile/tablet, right column on desktop */}
          <div
            aria-hidden="true"
            className="order-first lg:order-last lg:hidden text-[110px] sm:text-[150px] md:text-[180px] leading-[0.85] font-extrabold tracking-[-0.05em] text-[#286A11]"
          >
            {code}
          </div>

          <div className="flex flex-col gap-5 md:gap-6">
            <span className="text-xs md:text-[13px] font-bold tracking-[0.12em] uppercase text-[#FACC15]">Error {code}</span>
            <h1 className="m-0 text-[36px] sm:text-[44px] md:text-[56px] lg:text-[64px] leading-[1.05] font-extrabold tracking-[-0.02em] [text-wrap:balance]">
              {title}
            </h1>
            <p className="m-0 max-w-[480px] text-base md:text-[17px] leading-relaxed text-[#D1D5DB] [text-wrap:pretty]">
              {body}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <Link
                to={primary.to}
                className="flex items-center justify-center gap-2 min-h-[48px] px-6 rounded-full bg-[#FACC15] hover:bg-[#FDE047] text-[#0E2207] text-[15px] font-bold transition-colors"
              >
                {primary.label} <Arrow />
              </Link>
              <Link
                to={secondary.to}
                className="flex items-center justify-center min-h-[48px] px-6 rounded-full border border-white/30 hover:border-white text-white text-[15px] font-semibold transition-colors"
              >
                {secondary.label}
              </Link>
            </div>
          </div>

          <div className="flex flex-col gap-5">
            <div aria-hidden="true" className="hidden lg:block text-[220px] xl:text-[240px] leading-[0.85] font-extrabold tracking-[-0.05em] text-[#286A11]">
              {code}
            </div>
            <div className="flex flex-col border-t border-white/10">
              <span className="pt-4 pb-2 text-xs font-semibold tracking-[0.08em] uppercase text-[#9CA3AF]">Or try</span>
              {LINKS.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className="flex items-center justify-between gap-3 min-h-[52px] border-b border-white/10 text-white hover:text-[#FACC15] text-base md:text-[17px] font-semibold transition-colors"
                >
                  {l.label} <Chevron />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </main>

      <footer className="flex flex-col sm:flex-row sm:justify-between gap-2 px-5 md:px-10 lg:px-12 py-5 bg-[#0E2207] text-[13px] text-[#9CA3AF]">
        <span>© {new Date().getFullYear()} AgriKA-GIS · Laguna Province</span>
        <Link to={footerLink.to} className="hover:text-white transition-colors">{footerLink.label}</Link>
      </footer>
    </div>
  );
}
