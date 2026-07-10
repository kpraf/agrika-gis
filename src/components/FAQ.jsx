import React, { useCallback } from "react";
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
    a: "The platform uses an optimized CNN-LSTM deep learning model trained on Sentinel satellite imagery and historical weather data to forecast rice yields at the barangay and municipality level, without requiring manual field surveys.",
  },
  {
    q: "Who can use AgriKA-GIS?",
    a: "AgriKA-GIS supports four user types: administrators with province-wide access, agriculturists and rice technicians with municipality-scoped access to monitoring, analytics, and reporting tools, and guests who can view the public yield map.",
  },
  {
    q: "What kind of data does the system display?",
    a: "The platform displays real-time and historical yield estimates, land use and boundary layers, weather and vegetation indicators, municipality comparisons, and downloadable reports — all mapped spatially across Laguna's municipalities.",
  },
  {
    q: "Does the system use real-time satellite imagery?",
    a: "Yes. AgriKA-GIS pulls Sentinel-1 and Sentinel-2 imagery to monitor vegetation health and crop growth stages throughout the season, combined with publicly available weather data.",
  },
  {
    q: "Can users compare rice productivity between cities or municipalities?",
    a: "Yes — the Rice Yield Analytics & Comparison module lets agriculturists and administrators compare yield trends across multiple municipalities side by side, filtered by season and growth stage.",
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
    a: "To give Laguna's local government units and agriculturists a scalable, data-driven way to forecast rice yields and monitor agricultural conditions — reducing reliance on costly, labor-intensive manual field surveys.",
  },
];

function FAQItem({ q, a, defaultOpen = false }) {
  const detailsRef = useCallback(
    (node) => {
      if (node) node.open = defaultOpen;
    },
    [defaultOpen]
  );

  return (
    <details
      ref={detailsRef}
      className="group bg-white border border-[#E5E7EB] open:border-[#1F6306] rounded-xl shadow-sm transition-colors"
    >
      <summary className="flex items-center justify-between gap-6 p-6 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
        <span className="text-lg font-medium text-[#111827] group-open:text-[#1F6306] group-open:font-semibold">
          {q}
        </span>
        <span className="flex items-center justify-center w-6 h-6 rounded-full border border-[#D1D5DB] group-open:border-[#1F6306] shrink-0">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#9CA3AF"
            className="group-open:stroke-[#1F6306] group-open:rotate-180 transition-transform"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </span>
      </summary>
      <div className="px-6 pb-6 pt-4 border-t border-dashed border-[#1F6306]">
        <p className="text-base leading-6 text-[#4B5563]">{a}</p>
      </div>
    </details>
  );
}

export default function FAQ() {
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
            <FAQItem key={item.q} q={item.q} a={item.a} defaultOpen={i === 0} />
          ))}
        </div>
      </section>

      <ContactCTA />
      <Footer />
    </div>
  );
}
