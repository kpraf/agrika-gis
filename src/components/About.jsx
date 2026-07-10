import React from "react";
import { Link } from "react-router-dom";
import Navbar from "./layout/Navbar";
import Footer from "./layout/Footer";
import ContactCTA from "./layout/ContactCTA";
import ServicesSection from "./layout/ServicesSection";
import Pill from "./layout/Pill";

const STATS = [
  {
    value: "29",
    suffix: "+",
    title: "Mapped Agricultural Zones",
    desc: "Spatially monitored rice-producing areas across Laguna using GIS and satellite imagery.",
  },
  {
    value: "15",
    suffix: "+",
    title: "Research & Data Sources",
    desc: "Integrated datasets including Sentinel-2 imagery, weather records, and agricultural yield data.",
  },
  {
    value: "41%",
    suffix: "+",
    title: "Improvement in Prediction Accuracy",
    desc: "Optimized CNN-LSTM modeling reduced prediction errors compared to traditional estimation methods.",
  },
];

const PROJECTS = ["/images/zero-hunger.png", "/images/industry.png", "/images/sustainable-cities.png", "/images/climate-action.png"];

export default function About() {
  return (
    <div className="w-full bg-[#FCFCFC] font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      {/* Hero + Nav */}
      <section className="relative bg-[#0B2005] overflow-hidden min-h-[500px] flex flex-col">
        <div className="absolute inset-0 bg-[url('/images/farmers.png')] bg-cover bg-center" />
        <div className="absolute inset-0 bg-[#153321]/30" />

        <Navbar active="About" />

        <div className="relative z-10 flex-1 flex flex-col items-start justify-center gap-4 px-6 md:px-12 pb-12 max-w-4xl">
          <h1 className="text-4xl md:text-6xl font-extrabold text-white leading-[1.05]">
            About Research &amp; Methodology
          </h1>
          <p className="text-lg md:text-xl text-[#E5E7EB] max-w-2xl">
            Pioneering precision agriculture through deep learning and spatial analytics to secure regional food
            systems.
          </p>
        </div>
      </section>

      {/* About History Section */}
      <section className="bg-white py-20 px-6 md:px-16 flex justify-center">
        <div className="max-w-[1280px] w-full flex flex-col gap-24">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-end">
            <div className="flex flex-col items-start justify-end gap-6">
              <Pill variant="green">About AgriKA-GIS</Pill>
              <h2 className="text-3xl md:text-5xl font-bold text-[#111827] leading-tight">
                Built From Research. Designed for Impact.
              </h2>
            </div>
            <div className="flex flex-col gap-6">
              <p className="text-lg leading-7 text-[#666666]">
                AgriKA-GIS was developed as a direct response to a critical gap in Philippine agriculture: the
                absence of scalable, data-driven tools for rice yield prediction at the local government level.
                Through years of research collaboration with PhilRice and city agriculturists across Laguna, our
                team developed and validated an optimized CNN-LSTM model capable of forecasting rice yields using
                only satellite imagery and publicly available weather data — significantly reducing the need for
                costly, labor-intensive field surveys.
              </p>
              <p className="text-lg leading-7 text-[#666666]">
                The result is a platform that translates complex deep learning outputs into clear, spatially
                referenced maps and dashboards that any agriculturist can use — no technical background required.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {STATS.map((stat) => (
              <div key={stat.title} className="bg-[#F1F8E9] rounded-2xl p-8 flex flex-col gap-2">
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl md:text-6xl font-bold text-[#286A11]">{stat.value}</span>
                  <span className="text-3xl md:text-4xl font-bold text-[#FFCA28]">{stat.suffix}</span>
                </div>
                <h3 className="pt-2 text-xl font-bold text-[#111827]">{stat.title}</h3>
                <p className="text-base leading-6 text-[#666666]">{stat.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Services Section */}
      <ServicesSection />

      {/* Promotional Banner Section */}
      <section className="relative min-h-[400px] md:min-h-[559px] flex items-center overflow-hidden">
        <div className="absolute inset-0 bg-[url('/images/farms-thing.png')] bg-cover bg-center" />
        <div className="absolute inset-0 bg-black/40" />
        <div className="relative z-10 w-full flex justify-center md:justify-end px-6 md:px-24 py-12">
          <div className="bg-[#FFCA28] rounded-3xl shadow-2xl p-10 md:p-12 max-w-[512px] flex flex-col gap-8">
            <h2 className="text-3xl md:text-4xl font-bold text-[#111827] leading-tight">
              Discover the Science Behind the Platform
            </h2>
            <Link
              to="#"
              className="self-start flex items-center gap-2 px-8 py-4 rounded-full bg-[#286A11] text-white font-bold hover:bg-[#1F6306] transition-colors"
            >
              Contact Now
              <span className="w-5 h-5 rounded-full bg-white flex items-center justify-center">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path d="M1 5h8M6 2l3 3-3 3" stroke="#286A11" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
            </Link>
          </div>
        </div>
      </section>

      {/* Projects / SDG Alignments Section */}
      <section className="bg-white py-20 px-6 md:px-16 flex justify-center">
        <div className="max-w-[1280px] w-full flex flex-col gap-12">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
            <div className="flex flex-col items-start gap-4">
              <Pill variant="green">Recently Completed</Pill>
              <h2 className="text-3xl md:text-4xl font-bold text-[#111827]">SDG Alignments</h2>
            </div>
            <p className="text-base leading-6 text-[#666666] md:pt-4">
              AgriKA-GIS supports sustainable agriculture, climate resilience, and data-driven food security
              initiatives through AI-powered spatial intelligence and precision farming technologies.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {PROJECTS.map((src, i) => (
              <div
                key={i}
                className="aspect-square rounded-2xl bg-cover bg-center bg-[#F1F8E9]"
                style={{ backgroundImage: `url('${src}')` }}
              />
            ))}
          </div>

          <div className="flex justify-center">
            <Link
              to="/yield-map"
              className="flex items-center gap-2 px-8 py-3 rounded-full bg-[#286A11] text-white font-medium hover:bg-[#1F6306] transition-colors"
            >
              View Our Yield Map
              <span className="w-4 h-4 rounded-full bg-[#FFCA28] flex items-center justify-center">
                <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                  <path d="M1 4h6M4 1l3 3-3 3" stroke="#286A11" strokeWidth="1" />
                </svg>
              </span>
            </Link>
          </div>
        </div>
      </section>

      <ContactCTA />
      <Footer />
    </div>
  );
}
