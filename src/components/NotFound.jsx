import React from "react";
import StatusPage from "./StatusPage";

export default function NotFound() {
  return (
    <StatusPage
      code="404"
      title="Nothing planted on this plot."
      body="The page you're looking for doesn't exist or has been moved. Check the address, or head back to familiar ground."
      primary={{ label: "Back to Home", to: "/" }}
      secondary={{ label: "Open Yield Map", to: "/yield-map" }}
      footerLink={{ label: "Report a broken link", to: "/contact" }}
    />
  );
}
