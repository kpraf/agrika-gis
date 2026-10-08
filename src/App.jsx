import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useParams, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { useCityScope } from "./lib/cityScope";
import Home from "./components/Home";
import About from "./components/About";
import FAQ from "./components/FAQ";
import Contact from "./components/Contact";
import PrivacyPolicy from "./components/PrivacyPolicy";
import TermsOfService from "./components/TermsOfService";
import PortalAccess from "./components/PortalAccess";
import NotFound from "./components/NotFound";
import Unauthorized from "./components/Unauthorized";
import YieldMonitoring from "./components/monitoring/YieldMonitoring";
import SpatialGIS from "./components/gis/SpatialGIS";
import RiceYieldAnalytics from "./components/analytics/RiceYieldAnalytics";
import ReportsExport from "./components/reports/ReportsExport";
import UserAccessManagement from "./components/admin/UserAccessManagement";

// Reset scroll to the top on every navigation. Without this, react-router keeps
// the previous scroll offset, so following a link while scrolled down lands you
// mid-page on the new route instead of at its header.
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
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

// Keeps a scoped role (agriculturist / rice technician) on their assigned city.
// `base` is the module path, e.g. "/monitoring". Any other city in the address —
// or none, on the public map — is replaced with their own. Administrators and
// guests pass straight through.
function OwnCityOnly({ base, children }) {
  const { city } = useParams();
  const { loading } = useAuth();
  const scope = useCityScope();
  if (loading || !scope.locked) return children;
  if (!scope.slug) {
    // No city on the account: nothing to scope to. The public map stays viewable.
    return base === "/yield-map" && !city ? children : <Navigate to="/unauthorized" replace />;
  }
  if (city !== scope.slug) return <Navigate to={`${base}/${scope.slug}`} replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ScrollToTop />
        <Routes>
        {/* Public */}
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/faq" element={<FAQ />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/privacy" element={<PrivacyPolicy />} />
        <Route path="/terms" element={<TermsOfService />} />
        <Route path="/portal-access" element={<PortalAccess />} />
        <Route path="/unauthorized" element={<Unauthorized />} />

        {/* Module 2 — Real-Time and Historical Yield Monitoring (Agriculturist, Rice Technician, Admin) */}
        <Route
          path="/monitoring/:city"
          element={
            <RequireRole allowedRoles={["agriculturist", "rice_technician"]}>
              <OwnCityOnly base="/monitoring">
                <YieldMonitoring />
              </OwnCityOnly>
            </RequireRole>
          }
        />
        {/* Province-wide view (administrator only, no city scope). A scoped role that
            opens it is sent to its own city by OwnCityOnly, here and on Modules 4-5. */}
        <Route
          path="/monitoring"
          element={
            <OwnCityOnly base="/monitoring">
              <RequireRole allowedRoles={[]}>
                <YieldMonitoring />
              </RequireRole>
            </OwnCityOnly>
          }
        />

        {/* Module 3 — Spatial GIS Visualization and Analysis */}
        {/* Yield map. SpatialGIS itself decides chrome by auth state: logged in = side nav, public = top nav. */}
        <Route
          path="/yield-map"
          element={
            <OwnCityOnly base="/yield-map">
              <SpatialGIS />
            </OwnCityOnly>
          }
        />
        <Route
          path="/yield-map/:city"
          element={
            <RequireRole allowedRoles={["agriculturist", "rice_technician"]}>
              <OwnCityOnly base="/yield-map">
                <SpatialGIS />
              </OwnCityOnly>
            </RequireRole>
          }
        />

        {/* Module 4 — Rice Yield Analytics and Comparison (Agriculturist, Admin) */}
        <Route
          path="/analytics/:city"
          element={
            <RequireRole allowedRoles={["agriculturist"]}>
              <OwnCityOnly base="/analytics">
                <RiceYieldAnalytics />
              </OwnCityOnly>
            </RequireRole>
          }
        />
        <Route
          path="/analytics"
          element={
            <OwnCityOnly base="/analytics">
              <RequireRole allowedRoles={[]}>
                <RiceYieldAnalytics />
              </RequireRole>
            </OwnCityOnly>
          }
        />

        {/* Module 5 — Reports Generation and Data Import/Export (Agriculturist, Rice Technician, Admin) */}
        <Route
          path="/reports/:city"
          element={
            <RequireRole allowedRoles={["agriculturist", "rice_technician"]}>
              <OwnCityOnly base="/reports">
                <ReportsExport />
              </OwnCityOnly>
            </RequireRole>
          }
        />
        <Route
          path="/reports"
          element={
            <OwnCityOnly base="/reports">
              <RequireRole allowedRoles={[]}>
                <ReportsExport />
              </RequireRole>
            </OwnCityOnly>
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
        <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}