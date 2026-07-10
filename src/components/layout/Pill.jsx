import React from "react";

export default function Pill({ children, variant = "gold" }) {
  const styles =
    variant === "gold"
      ? "border-[#FACC15] text-[#FACC15]"
      : "border-[#286A11] text-[#286A11]";
  return (
    <div
      className={`inline-flex items-center px-4 py-1.5 rounded-full border text-sm font-medium ${styles}`}
    >
      {children}
    </div>
  );
}
