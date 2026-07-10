import React from "react";

const CONTACT_ITEMS = [
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M6 2h12v20l-6-3-6 3V2z" stroke="#FACC15" strokeWidth="1.5" />
      </svg>
    ),
    title: "Call Us",
    lines: ["+63 917 000 0000"],
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M3 6h18v12H3V6z" stroke="#FACC15" strokeWidth="1.5" />
        <path d="M3 6l9 7 9-7" stroke="#FACC15" strokeWidth="1.5" />
      </svg>
    ),
    title: "Email Us",
    lines: ["agrika-gis.official@gmail.com", "help.agrika-gis@gmail.com"],
  },
  {
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M12 22s7-6.5 7-12a7 7 0 10-14 0c0 5.5 7 12 7 12z" stroke="#FACC15" strokeWidth="1.5" />
        <circle cx="12" cy="10" r="2.5" stroke="#FACC15" strokeWidth="1.5" />
      </svg>
    ),
    title: "Visit Us",
    lines: ["Pulo-Diezmo Road, Cabuyao,", "025 Laguna, Philippines"],
  },
];

export default function ContactCTA() {
  return (
    <section className="relative bg-[#FACC15] py-16 px-6 md:px-14 overflow-hidden">
      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-10 max-w-[1392px] mx-auto">
        {CONTACT_ITEMS.map((item) => (
          <div key={item.title} className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-[#1F6306] flex items-center justify-center shrink-0">
              {item.icon}
            </div>
            <div className="flex flex-col">
              <h4 className="text-lg font-bold text-[#0B2005]">{item.title}</h4>
              {item.lines.map((line) => (
                <p key={line} className="text-base font-medium text-[#1F6306] leading-6">
                  {line}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
