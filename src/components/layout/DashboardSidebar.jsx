import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const ICONS = {
  monitoring: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12h4l3 8 4-16 3 8h4" />
    </svg>
  ),
  map: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 20l-6-3V4l6 3 6-3 6 3v13l-6-3-6 3z" />
      <path d="M9 7v13M15 4v13" />
    </svg>
  ),
  compare: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 20V10M12 20V4M17 20v-7" />
    </svg>
  ),
  reports: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 2h9l5 5v15H6V2z" />
      <path d="M15 2v5h5M9 13h6M9 17h6" />
    </svg>
  ),
  settings: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  ),
  logout: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
    </svg>
  ),
};

function NavItem({ to, icon, label, active }) {
  return (
    <Link to={to} className="flex flex-col items-center gap-1 pt-6 w-10">
      <span
        className={`flex items-center justify-center w-10 h-10 rounded-lg ${
          active ? "bg-white/10 text-white" : "text-white/50 hover:text-white/80"
        }`}
      >
        {ICONS[icon]}
      </span>
      <span className={`text-[10px] font-medium leading-[15px] ${active ? "text-white" : "text-white/50"}`}>
        {label}
      </span>
    </Link>
  );
}

// Which modules each role may open (matches the route guards in App.jsx).
const NAV_BY_ROLE = {
  administrator: ["monitoring", "map", "compare", "reports", "settings"],
  agriculturist: ["monitoring", "map", "compare", "reports"],
  rice_technician: ["monitoring", "map", "reports"],
};

export default function DashboardSidebar({ active }) {
  const { role, municipality, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/portal-access", { replace: true });
  };

  // Admin is province-wide (no city in the path); scoped roles use their municipality slug.
  const slug = (municipality || "").toLowerCase().trim().replace(/\s+/g, "-");
  const base = role === "administrator" || !slug ? "" : `/${slug}`;

  const ITEMS = {
    monitoring: { label: "Monitor", to: `/monitoring${base}` },
    map: { label: "Map", to: `/yield-map${base}` },
    compare: { label: "Compare", to: `/analytics${base}` },
    reports: { label: "Reports", to: `/reports${base}` },
    settings: { label: "Settings", to: "/admin/users" },
  };

  const keys = NAV_BY_ROLE[role] || ["monitoring", "map", "compare", "reports"];
  const NAV = keys.map((key) => ({ key, ...ITEMS[key] }));

  return (
    <aside className="flex flex-col items-center justify-between py-6 w-[70px] shrink-0 h-full bg-[#1F6306] shadow-[0_20px_25px_-5px_rgba(0,0,0,0.1),0_8px_10px_-6px_rgba(0,0,0,0.1)] z-10">
      <div className="flex flex-col items-center w-full pb-8">
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-[#D1D5DB] text-[#1F6306] font-extrabold shadow-sm">
          A
        </div>
      </div>

      <nav className="flex flex-col items-center flex-1 w-full px-2">
        {NAV.map((item) => (
          <NavItem key={item.key} to={item.to} icon={item.key} label={item.label} active={active === item.key} />
        ))}
      </nav>

      <div className="flex flex-col items-center gap-6 w-full pb-4">
        <div className="w-10 h-10 rounded-full border-2 border-white/20 shadow-sm flex items-center justify-center">
          <span className="w-9 h-9 rounded-full bg-[#D1D5DB]" />
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="flex flex-col items-center gap-1 w-10 text-white/50 hover:text-white/80"
        >
          {ICONS.logout}
          <span className="text-[10px] font-medium leading-[15px]">Exit</span>
        </button>
      </div>
    </aside>
  );
}
