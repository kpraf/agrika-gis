import React from "react";
import { Link } from "react-router-dom";

const NAV_LINKS = [
  { label: "Home", to: "/" },
  { label: "About", to: "/about" },
  { label: "Yield Map", to: "/yield-map" },
  { label: "FAQs", to: "/faq" },
  { label: "Contact", to: "/contact" },
];

export default function Navbar({ active = "Home" }) {
  return (
    <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-6">
      <Link to="/" className="flex items-center">
        <img src="/images/agrika-gis-logo.png" alt="AgriKA-GIS" className="h-14 w-auto object-contain" />
      </Link>
      <div className="hidden md:flex items-center gap-8">
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
      <Link
        to="/portal-access"
        className="flex items-center gap-2 px-6 py-3 rounded-full bg-[#286A11] text-white font-semibold text-base hover:bg-[#1F6306] transition-colors"
      >
        Portal Access
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M2 8h12M9 4l4 4-4 4" stroke="white" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </Link>
    </nav>
  );
}
