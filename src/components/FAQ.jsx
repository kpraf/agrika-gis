import React, { useState } from "react";
import Navbar from "./layout/Navbar";
import Footer from "./layout/Footer";
import ContactCTA from "./layout/ContactCTA";

const FAQS = [
  {
    q: "What is AgriKA-GIS?",
    a: "AgriKA-GIS is a web-based agricultural monitoring and rice yield visualization platform that uses satellite imagery, GIS mapping, and AI-based analytics to support data-driven agricultural decision-making.",
  },
  {
    q: "How does the system predict rice yield?",
    a: "The platform uses a CNN-LSTM deep learning model trained on Sentinel satellite imagery, historical weather data, and PSA/Ricelytics yield records to forecast municipal rice yields per season. The forecasts reduce reliance on manual field surveys, and recorded barangay-level yields are also shown for selected cities.",
  },
  {
    q: "Who can use AgriKA-GIS?",
    a: "AgriKA-GIS has three account roles: administrators, who have province-wide access and manage user accounts; agriculturists, who can use monitoring, analytics and comparison, and reporting for their assigned municipality; and rice technicians, who can use monitoring, the yield map, and reports for their assigned municipality. Accounts are created by an administrator. The public can view the Laguna yield map without logging in.",
  },
  {
    q: "What kind of data does the system display?",
    a: "The platform displays observed yields from 2018 onward, predicted yields, boundary layers, weather and vegetation indicators, municipality comparisons, and downloadable reports, all mapped across Laguna's municipalities.",
  },
  {
    q: "Does the system use satellite imagery?",
    a: "Yes. AgriKA-GIS uses monthly Sentinel-1 and Sentinel-2 composites from the Copernicus Data Space Ecosystem to track vegetation health through the season, together with publicly available weather data from Open-Meteo.",
  },
  {
    q: "Can users compare rice productivity between cities or municipalities?",
    a: "Yes. The Rice Yield Analytics & Comparison module lets agriculturists and administrators compare yield trends across municipalities side by side, filtered by year and season.",
  },
  {
    q: "How accurate are the predictions?",
    a: "Our optimized CNN-LSTM model has demonstrated a significant reduction in prediction error compared to traditional estimation methods, though accuracy can vary by municipality and data availability.",
  },
  {
    q: "Is AgriKA-GIS accessible on mobile devices?",
    a: "The public pages and portal are responsive and work on modern mobile browsers, though the data-dense monitoring and analytics dashboards are designed primarily for desktop use by agriculturists and technicians in the field office.",
  },
  {
    q: "What technologies are used in the platform?",
    a: "The frontend is built with React, Tailwind CSS, Leaflet for interactive mapping, and Recharts for analytics; the prediction engine is a CNN-LSTM model trained on satellite imagery and weather data.",
  },
  {
    q: "What is the main goal of AgriKA-GIS?",
    a: "To give Laguna's local government units and agriculturists a scalable, data-driven way to forecast rice yields and monitor agricultural conditions, reducing reliance on costly, labor-intensive manual field surveys.",
  },
];

function FAQItem({ q, a, open, onToggle, index }) {
  const id = `faq-${index}`;
  return (
    <div
      className={`anim-fade-up bg-white border rounded-xl shadow-sm transition-[border-color,box-shadow] duration-300 motion-safe-transition ${
        open ? "border-[#1F6306] shadow-md" : "border-[#E5E7EB] hover:border-[#1F6306]/40"
      }`}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <h3>
        <button
          type="button"
          id={`${id}-q`}
          aria-expanded={open}
          aria-controls={`${id}-a`}
          onClick={onToggle}
          className="w-full flex items-center justify-between gap-6 p-6 text-left cursor-pointer"
        >
          <span
            className={`text-lg transition-colors duration-300 motion-safe-transition ${
              open ? "text-[#1F6306] font-semibold" : "text-[#111827] font-medium"
            }`}
          >
            {q}
          </span>
          <span
            className={`flex items-center justify-center w-6 h-6 rounded-full border shrink-0 transition-colors duration-300 motion-safe-transition ${
              open ? "border-[#1F6306] bg-[#1F6306]" : "border-[#D1D5DB]"
            }`}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke={open ? "#FFFFFF" : "#9CA3AF"}
              className={`transition-transform duration-300 motion-safe-transition ${open ? "rotate-180" : ""}`}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </span>
        </button>
      </h3>
      {/* grid-rows 0fr -> 1fr animates to the content's natural height */}
      <div
        id={`${id}-a`}
        role="region"
        aria-labelledby={`${id}-q`}
        className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out motion-safe-transition ${
          open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="overflow-hidden" inert={!open}>
          <div className="px-6 pb-6 pt-4 border-t border-dashed border-[#1F6306]">
            <p className="text-base leading-6 text-[#4B5563]">{a}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function FAQ() {
  // One open at a time; the first answer starts expanded.
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <div className="w-full bg-white font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      {/* Hero + Nav */}
      <section className="relative bg-[#0B2005] overflow-hidden min-h-[500px] flex flex-col">
        <div className="absolute inset-0 bg-[url('/images/farmers2.png')] bg-cover bg-center" />
        <div className="absolute inset-0 bg-[#153321]/30" />

        <Navbar active="FAQs" />

        <div className="relative z-10 flex-1 flex flex-col items-start justify-center gap-4 px-6 md:px-12 pb-12 max-w-4xl">
          <h1 className="text-4xl md:text-6xl font-extrabold text-white leading-[1.05]">
            Frequently Asked Questions
          </h1>
          <p className="text-lg md:text-xl text-[#E5E7EB] max-w-2xl">
            Have questions about AgriKA-GIS? Explore answers about rice yield monitoring, GIS visualization,
            satellite data, and platform features.
          </p>
        </div>
      </section>

      {/* FAQ List */}
      <section className="bg-white py-20 px-6 md:px-16 flex justify-center">
        <div className="max-w-[1280px] w-full flex flex-col gap-4">
          {FAQS.map((item, i) => (
            <FAQItem
              key={item.q}
              q={item.q}
              a={item.a}
              index={i}
              open={openIndex === i}
              onToggle={() => setOpenIndex(openIndex === i ? null : i)}
            />
          ))}
        </div>
      </section>

      <ContactCTA />
      <Footer />
    </div>
  );
}
