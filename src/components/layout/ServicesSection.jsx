import React from "react";
import Pill from "./Pill";

const SERVICES = [
  {
    title: "What We Do",
    desc: "We utilize high-resolution satellite imagery and advanced machine learning algorithms to map rice cultivated areas, forecast yields, and monitor crop health continuously throughout the growing season.",
    image: "/images/what.png",
  },
  {
    title: "Who We Serve",
    desc: "Our platform empowers local government units, agricultural extension workers, researchers, and policymakers with actionable, spatial data to support food security initiatives.",
    image: "/images/who.png",
  },
  {
    title: "Why It Matters",
    desc: "Accurate, timely data is critical for mitigating climate risks, optimizing resource allocation, and ensuring a resilient agricultural sector in the face of changing environmental conditions.",
    image: "/images/why.png",
  },
];

export default function ServicesSection({
  pill = "Our Services",
  heading = "We Offer Precision Agriculture Intelligence",
  services = SERVICES,
}) {
  return (
    <section className="bg-white py-24 px-6 md:px-16">
      <div className="max-w-[1280px] mx-auto">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-12">
          <div className="flex flex-col items-start gap-4">
            <Pill variant="green">{pill}</Pill>
            <h2 className="text-3xl md:text-4xl font-bold text-[#111827] max-w-2xl">
              {heading}
            </h2>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {services.map((s) => (
            <div
              key={s.title}
              className="bg-[#286A11] rounded-2xl pt-4 flex flex-col overflow-hidden"
            >
              <img
                src={s.image}
                alt={s.title}
                className="mx-4 h-48 rounded-2xl object-cover"
                style={{ width: "calc(100% - 2rem)" }}
              />
              <div className="p-6 flex flex-col gap-3">
                <h3 className="text-2xl font-bold text-[#F6F8F3]">{s.title}</h3>
                <p className="text-sm leading-5 text-[#E5E7EB]">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
