import React from "react";
import { useAuth } from "../context/AuthContext";
import { landingPathFor } from "../lib/cityScope";
import StatusPage from "./StatusPage";

export default function Unauthorized() {
  const { user } = useAuth();
  // Signed-in users go back to the dashboard their role can open; guests go home.
  const primary = user
    ? { label: "Back to Dashboard", to: landingPathFor(user) }
    : { label: "Back to Home", to: "/" };

  return (
    <StatusPage
      code="403"
      title="This field is fenced off."
      body="Your account doesn't have permission to view this page. If you think you should have access, ask your administrator."
      primary={primary}
      secondary={{ label: "Open Yield Map", to: "/yield-map" }}
      footerLink={{ label: "Request access", to: "/contact" }}
    />
  );
}
