import React from "react";
import { Link } from "react-router-dom";
import Navbar from "./layout/Navbar";
import Footer from "./layout/Footer";
import ContactCTA from "./layout/ContactCTA";
import ServicesSection from "./layout/ServicesSection";
import Pill from "./layout/Pill";

const STEPS = [
  {
    num: "01",
    title: "Satellite Data Acquisition",
    desc: "Sentinel-1 and Sentinel-2 imagery is pulled for every target barangay.",
  },
  {
    num: "02",
    title: "Vegetation Analysis",
    desc: "NDVI and SAR features are extracted to gauge crop health and growth stage.",
  },
  {
    num: "03",
    title: "AI-Powered Prediction",
    desc: "A CNN-LSTM model turns spatial and temporal features into yield forecasts.",
  },
  {
    num: "04",
    title: "Interactive Visualization",
    desc: "Results are mapped barangay-by-barangay for agriculturists and technicians.",
  },
];

const PARTNERS = [
  { name: "PhilRice", logo: "/images/philrice.png", w: "w-40" },
  { name: "ASEAN University Network", logo: "/images/asean.png", w: "w-36" },
  { name: "MAPUA MMCL", logo: "/images/MMCL_Logo.png", w: "w-20" },
  { name: "Calamba City Agricultural Services Dept.", logo: "/images/agric-calamba.png", w: "w-24" },
  { name: "Cabuyao City Agricultural Services Dept.", logo: "/images/agric-cabuyao.png", w: "w-24" },
  { name: "Santa Rosa City Agricultural Services Dept.", logo: "/images/agric-sta-rosa.png", w: "w-24" },

];

const TEAM = [
  { name: "Jonalyn G. Ebron", role: "Research Adviser", photo: null },
  { name: "Ashlie C. Argana", role: "Frontend Developer", photo: null },
  { name: "Kester Praferosa", role: "Machine Learning Engineer", photo: null },
  { name: "Joshua Ilagan", role: "Backend Developer", photo: "/images/josh.jpg" },
  { name: "Jean C. Madolora", role: "Data Engineering", photo: null },
];

export default function Home() {
  return (
    <div className="w-full bg-[#F3F4F6] font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      {/* Hero + Nav */}
      <section className="relative bg-[#0B2005] overflow-hidden min-h-[100vh] flex flex-col">
        <div className="absolute inset-0 bg-[url('/images/farmer-1.png')] bg-cover bg-center opacity-80" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#0B2005]/65 via-[#0B2005]/35 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0B2005]/20 to-transparent" />

        <Navbar active="Home" />

        {/* Hero content */}
        <div className="relative z-10 flex-1 flex flex-col items-start justify-center px-6 md:px-12 max-w-4xl">
          <Pill variant="gold">Regional Stewardship</Pill>
          <h1 className="mt-6 text-4xl md:text-6xl lg:text-7xl font-extrabold text-white leading-[1.05]">
            Mapping the Future of Rice in Laguna
          </h1>
          <p className="mt-6 text-lg md:text-xl text-[#D1D5DB] max-w-xl">
            AI-powered yield forecasting for smarter agricultural decisions across the CALABARZON region.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              to="/about"
              className="flex items-center gap-2 px-8 py-4 rounded-full bg-[#286A11] text-white font-semibold hover:bg-[#1F6306] transition-colors"
            >
              Discover More
              <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center">
                <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                  <path d="M1 4h6M4 1l3 3-3 3" stroke="white" strokeWidth="1" />
                </svg>
              </span>
            </Link>
            <Link
              to="/yield-map"
              className="flex items-center gap-2 px-8 py-4 rounded-full border border-[#FACC15] text-[#FACC15] font-semibold hover:bg-[#FACC15]/10 transition-colors"
            >
              See Yield Map
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M2 8h12M9 4l4 4-4 4" stroke="#FACC15" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Link>
          </div>
        </div>
      </section>

      {/* Partners Strip Section */}
      <section className="relative bg-[#FACC15] py-14 px-6 overflow-hidden">
        {/* subtle decorative pattern layer - swap for the real Figma pattern asset if available */}
        <div className="absolute inset-0 bg-repeat opacity-10 bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2280%22 height=%2280%22><circle cx=%2210%22 cy=%2210%22 r=%223%22 fill=%22%23000%22/></svg>')]" />
        <div className="relative z-10 flex flex-wrap items-center justify-center gap-16">
          {PARTNERS.map((partner) => (
            <img
              key={partner.name}
              src={partner.logo}
              alt={partner.name}
              className={`${partner.w} h-24 object-contain`}
            />
          ))}
        </div>
      </section>

      {/* Services Section */}
      <ServicesSection />

      {/* How We Work Section */}
      <section className="bg-white py-24 px-6 md:px-16">
        <div className="max-w-[1280px] mx-auto grid grid-cols-1 md:grid-cols-2 gap-16 items-start">
          <div className="flex flex-col items-start gap-4">
            <Pill variant="green">How It Works</Pill>
            <h2 className="text-3xl md:text-4xl font-bold text-[#1D211C]">
              How AgriKA-GIS Works
            </h2>
            <img
              src="/images/satellite.png"
              alt="AgriKA-GIS satellite monitoring visual"
              className="mt-4 w-full h-[420px] rounded-3xl object-cover"
            />
          </div>

          <div className="flex flex-col gap-8">
            <p className="text-base leading-6 text-[#4B5563]">
              Traditional yield estimation is slow, labor-intensive, and often inaccurate. AgriKA-GIS automates
              the entire pipeline — from satellite data collection to real-time prediction — so decision-makers
              always have the insights they need, when they need them.
            </p>
            <div className="flex flex-col">
              {STEPS.map((step, i) => (
                <div
                  key={step.num}
                  className={`flex gap-6 py-8 ${
                    i !== STEPS.length - 1 ? "border-b border-[#F3F4F6]" : ""
                  }`}
                >
                  <span className="text-5xl font-bold text-[#286A11]/80 shrink-0">
                    {step.num}
                  </span>
                  <div className="flex flex-col gap-1">
                    <h4 className="text-xl font-bold text-[#1D211C]">{step.title}</h4>
                    <p className="text-sm text-[#6B7280]">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="bg-[#0E2207] py-24 px-6 md:px-12 flex flex-col items-center">
        <div className="max-w-[1280px] w-full flex flex-col items-center gap-4">
          <Pill variant="gold">Our Partners</Pill>
          <h2 className="text-3xl md:text-5xl font-bold text-white text-center">
            Meet the Research Team
          </h2>
          <div className="mt-8 w-full grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
            {TEAM.map((member) => (
              <div
                key={member.name}
                className="bg-[#1F6306] rounded-2xl p-2 pb-7 flex flex-col gap-4"
              >
                {member.photo ? (
                  <img
                    src={member.photo}
                    alt={member.name}
                    className="w-full aspect-square rounded-xl object-cover"
                  />
                ) : (
                  <div className="w-full aspect-square rounded-xl bg-[#E1E3DF]/20" />
                )}
                <div className="px-2 flex flex-col gap-1">
                  <h4 className="text-lg font-bold text-white leading-tight">{member.name}</h4>
                  <p className="text-sm text-[#F3B700]">{member.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <ContactCTA />
      <Footer />
    </div>
  );
}
