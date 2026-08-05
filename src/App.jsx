import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Home from "./components/Home";
import About from "./components/About";
import FAQ from "./components/FAQ";
import Contact from "./components/Contact";
import PortalAccess from "./components/PortalAccess";
import YieldMonitoring from "./components/monitoring/YieldMonitoring";
import SpatialGIS from "./components/gis/SpatialGIS";
import RiceYieldAnalytics from "./components/analytics/RiceYieldAnalytics";
import ReportsExport from "./components/reports/ReportsExport";
import UserAccessManagement from "./components/admin/UserAccessManagement";

// Simple placeholder so routes are navigable before each module is built
function Placeholder({ title }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F3F4F6]">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-[#1D211C]">{title}</h1>
        <p className="text-[#6B7280] mt-2">Module not built yet.</p>
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

// Municipality-scoped dashboard wrapper (Agriculturist / Rice Technician only see their own city)
function MunicipalityDashboard({ moduleTitle }) {
  const { city } = useParams();
  return <Placeholder title={`${moduleTitle} — ${city}`} />;
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

        {/* Module 2 — Real-Time and Historical Yield Monitoring (Agriculturist, Rice Technician, Admin) */}
        <Route
          path="/monitoring/:city"
          element={
            <RequireRole allowedRoles={["agriculturist", "rice_technician"]}>
              <YieldMonitoring />
            </RequireRole>
          }
        />
        {/* Province-wide view (administrator only, no city scope) */}
        <Route
          path="/monitoring"
          element={
            <RequireRole allowedRoles={[]}>
              <YieldMonitoring />
            </RequireRole>
          }
        />

        {/* Module 3 — Spatial GIS Visualization and Analysis */}
        {/* Yield map. SpatialGIS itself decides chrome by auth state: logged in = side nav, public = top nav. */}
        <Route path="/yield-map" element={<SpatialGIS />} />
        <Route
          path="/yield-map/:city"
          element={
            <RequireRole allowedRoles={["agriculturist", "rice_technician"]}>
              <SpatialGIS />
            </RequireRole>
          }
        />

        {/* Module 4 — Rice Yield Analytics and Comparison (Agriculturist, Admin) */}
        <Route
          path="/analytics/:city"
          element={
            <RequireRole allowedRoles={["agriculturist"]}>
              <RiceYieldAnalytics />
            </RequireRole>
          }
        />
        <Route
          path="/analytics"
          element={
            <RequireRole allowedRoles={[]}>
              <RiceYieldAnalytics />
            </RequireRole>
          }
        />

        {/* Module 5 — Reports Generation and Data Import/Export (Agriculturist, Rice Technician, Admin) */}
        <Route
          path="/reports/:city"
          element={
            <RequireRole allowedRoles={["agriculturist", "rice_technician"]}>
              <ReportsExport />
            </RequireRole>
          }
        />
        <Route
          path="/reports"
          element={
            <RequireRole allowedRoles={[]}>
              <ReportsExport />
            </RequireRole>
          }
        />

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