import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Home from "./components/Home";
import About from "./components/About";
import FAQ from "./components/FAQ";
import Contact from "./components/Contact";
import PortalAccess from "./components/PortalAccess";
import UserAccessManagement from "./components/admin/UserAccessManagement";

// Simple placeholder page (e.g. the unauthorized screen).
function Placeholder({ title }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F3F4F6]">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-[#1D211C]">{title}</h1>
      </div>
    </div>
  );
}

// Guards a route by role. Administrator always passes (province-wide access).
function RequireRole({ allowedRoles, children }) {
  const { isAuthenticated, role, loading } = useAuth();

  // While the session is being restored (token check on refresh), don't redirect yet.
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F3F4F6] text-[#6B7280]">
        Loading…
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/portal-access" replace />;
  }
  if (role !== "administrator" && !allowedRoles.includes(role)) {
    return <Navigate to="/unauthorized" replace />;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
        {/* Public */}
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/faq" element={<FAQ />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/portal-access" element={<PortalAccess />} />
        <Route path="/unauthorized" element={<Placeholder title="Unauthorized" />} />

        {/* Modules 2-5 (Monitoring, Spatial GIS, Analytics, Reports) are scheduled
            for the succeeding reporting periods and are not part of this build. */}

        {/* Module 6 — User Access Management and System Configuration (Admin only) */}
        <Route
          path="/admin/users"
          element={
            <RequireRole allowedRoles={[]}>
              <UserAccessManagement />
            </RequireRole>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}