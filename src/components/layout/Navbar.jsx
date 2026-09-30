import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useLocation } from "react-router-dom";

const NAV_LINKS = [
  { label: "Home", to: "/" },
  { label: "About", to: "/about" },
  { label: "Yield Map", to: "/yield-map" },
  { label: "FAQs", to: "/faq" },
  { label: "Contact", to: "/contact" },
];

const EASE = "cubic-bezier(.65,0,.35,1)";
const ORIGIN = "calc(100% - 48px) 48px";

export default function Navbar({ active = "Home" }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const onChange = (e) => e.matches && setOpen(false);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const bar = "absolute left-1/2 -ml-[10px] w-5 h-0.5 rounded bg-white";

  return (
    <nav className="relative z-30 flex items-center justify-between px-5 md:px-10 lg:px-12 py-5 lg:py-6">
      <Link to="/" className="relative z-30 flex items-center">
        <img src="/images/agrika-gis-logo.png" alt="AgriKA-GIS" className="h-16 md:h-16 lg:h-20 w-auto object-contain" />
      </Link>

      <div className="hidden lg:flex items-center gap-8">
        {NAV_LINKS.map((link) => (
          <Link
            key={link.label}
            to={link.to}
            className={`text-base font-medium ${
              link.label === active ? "text-[#FACC15]" : "text-white hover:text-[#FACC15]"
            } transition-colors`}
          >
            {link.label}
          </Link>
        ))}
      </div>

      <div className="relative z-30 flex items-center gap-2 md:gap-3">
        <Link
          to="/portal-access"
          className="flex items-center gap-2 px-4 py-2.5 md:px-6 md:py-3 rounded-full bg-[#286A11] text-white font-semibold text-sm md:text-base hover:bg-[#1F6306] transition-colors"
        >
          Portal Access
          <svg className="hidden md:block" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 8h12M9 4l4 4-4 4" stroke="white" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Link>

        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-menu"
          className="lg:hidden relative flex items-center justify-center w-11 h-11 md:w-12 md:h-12 rounded-full border border-white/25"
        >
          <span className={bar} style={{ transition: `transform 320ms ${EASE}`, transform: open ? "rotate(45deg)" : "translateY(-6px)" }} />
          <span className={bar} style={{ transition: "opacity 200ms ease", opacity: open ? 0 : 1 }} />
          <span className={bar} style={{ transition: `transform 320ms ${EASE}`, transform: open ? "rotate(-45deg)" : "translateY(6px)" }} />
        </button>
      </div>

      {createPortal(
        <div
          id="mobile-menu"
          aria-hidden={!open}
          className="lg:hidden fixed inset-0 z-[1000] flex flex-col bg-[#0E2207] px-5 md:px-10 pt-[104px] md:pt-[136px] pb-8"
          style={{
            transition: `clip-path 500ms ${EASE}`,
            clipPath: `circle(${open ? "150%" : "0%"} at ${ORIGIN})`,
            pointerEvents: open ? "auto" : "none",
          }}
        >
        {/* Top bar inside the overlay — the nav's own logo/button/hamburger sit
            behind this full-screen menu, so we mirror them here to keep the
            logo, Portal Access, and a close control visible while open. */}
        <div
          className="absolute top-0 left-0 right-0 flex items-center justify-between px-5 md:px-10 py-5 lg:py-6"
          style={{ transition: "opacity 200ms ease", transitionDelay: open ? "140ms" : "0ms", opacity: open ? 1 : 0 }}
        >
          <Link to="/" tabIndex={open ? 0 : -1} onClick={() => setOpen(false)} className="flex items-center">
            <img src="/images/agrika-gis-logo.png" alt="AgriKA-GIS" className="h-16 md:h-16 w-auto object-contain" />
          </Link>
          <div className="flex items-center gap-2 md:gap-3">
            <Link
              to="/portal-access"
              tabIndex={open ? 0 : -1}
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 px-4 py-2.5 md:px-6 md:py-3 rounded-full bg-[#286A11] text-white font-semibold text-sm md:text-base hover:bg-[#1F6306] transition-colors"
            >
              Portal Access
              <svg className="hidden md:block" width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M2 8h12M9 4l4 4-4 4" stroke="white" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Link>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close menu"
              className="lg:hidden relative flex items-center justify-center w-11 h-11 md:w-12 md:h-12 rounded-full border border-white/25"
            >
              <span className={bar} style={{ transform: "rotate(45deg)" }} />
              <span className={bar} style={{ opacity: 0 }} />
              <span className={bar} style={{ transform: "rotate(-45deg)" }} />
            </button>
          </div>
        </div>

        {NAV_LINKS.map((link, i) => (
          <Link
            key={link.label}
            to={link.to}
            tabIndex={open ? 0 : -1}
            onClick={() => setOpen(false)}
            className={`flex items-center justify-between px-1 py-[18px] md:py-6 border-b border-white/10 text-[22px] md:text-[32px] font-semibold ${
              link.label === active ? "text-[#FACC15]" : "text-white"
            }`}
            style={{
              transition: "opacity 360ms ease, transform 420ms cubic-bezier(.2,.8,.2,1)",
              transitionDelay: open ? `${180 + i * 40}ms` : "0ms",
              opacity: open ? 1 : 0,
              transform: open ? "translateY(0)" : "translateY(14px)",
            }}
          >
            {link.label}
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
              <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </Link>
        ))}
        </div>,
        document.body
      )}
    </nav>
  );
}
