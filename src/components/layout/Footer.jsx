import React from "react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="bg-[#0E2207] pt-20 px-6 md:px-14 pb-8">
      <div className="max-w-[1280px] mx-auto flex flex-col gap-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
          <div className="flex flex-col gap-6">
            <Link to="/" className="flex items-center">
              <img src="/images/agrika-gis-logo.png" alt="AgriKA-GIS" className="h-14 w-auto object-contain" />
            </Link>
            <p className="text-sm text-[#D1D5DB] leading-[23px] max-w-[284px]">
              Empowering local agriculture with satellite intelligence and AI-powered precision
              farming tools across Laguna and beyond.
            </p>
          </div>

          <div className="flex flex-col gap-6">
            <h4 className="text-xl font-bold text-white">Useful Info</h4>
            <div className="flex flex-col gap-4">
              {[
                { label: "Home", to: "/" },
                { label: "About", to: "/about" },
                { label: "FAQs", to: "/faq" },
              ].map((item) => (
                <Link key={item.label} to={item.to} className="text-base font-medium text-[#D1D5DB] hover:text-white">
                  {item.label}
                </Link>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-6">
            <h4 className="text-xl font-bold text-white">Explore More</h4>
            <div className="flex flex-col gap-4">
              {[
                { label: "Yield Map", to: "/yield-map" },
                { label: "Portal Access", to: "/portal-access" },
                { label: "Contact", to: "/contact" },
              ].map((item) => (
                <Link key={item.label} to={item.to} className="text-base font-medium text-[#D1D5DB] hover:text-white">
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8 border-t border-white/10">
          <p className="text-sm text-[#9CA3AF]">© 2026 AgriKa-GIS. All Rights Reserved.</p>
          <div className="flex gap-6">
            <a href="#" className="text-sm text-[#9CA3AF] hover:text-white">Privacy Policy</a>
            <a href="#" className="text-sm text-[#9CA3AF] hover:text-white">Terms of Service</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
