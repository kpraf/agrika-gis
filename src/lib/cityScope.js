import { useAuth } from "../context/AuthContext";

// "City of Calamba" -> "city-of-calamba" (the :city segment of the dashboard routes).
export const slugify = (name) => (name || "").toLowerCase().trim().replace(/\s+/g, "-");

// Where each role lands right after signing in — everyone starts on Monitoring.
// Admin sees the province-wide view; scoped roles see their own municipality.
export function landingPathFor(user) {
  if (user.role === "administrator") return "/monitoring";
  const city = slugify(user.municipality);
  return city ? `/monitoring/${city}` : "/yield-map";
}

/**
 * The city a signed-in user is limited to (Table 19: "Assigned city only").
 *
 * Administrators and guests are not locked. An agriculturist or rice technician
 * is locked to the municipality on their account: every dashboard shows that
 * city's data only, and the routes send them back to it.
 *
 * Returns { locked, municipalityId, municipalityName, slug }. A locked account
 * with no city assigned has municipalityId === null.
 */
export function useCityScope() {
  const { user, role } = useAuth();
  const locked = !!user && role !== "administrator";
  return {
    locked,
    municipalityId: locked ? user.municipality_id ?? null : null,
    municipalityName: locked ? user.municipality ?? "" : "",
    slug: locked ? slugify(user.municipality) : "",
  };
}
