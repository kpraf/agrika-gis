import React, { useEffect, useState } from "react";
import { onServerSlow } from "../../lib/api";

/**
 * Full-screen overlay shown while a backend request is taking unusually long —
 * i.e. the free-tier API is waking from sleep (cold start, ~30-60s). It appears
 * only when a request crosses the slow threshold and hides as soon as the
 * backend responds, so warm requests and backend-free public pages never see it.
 */
export default function ServerWakeOverlay() {
  const [waking, setWaking] = useState(false);

  useEffect(() => onServerSlow(setWaking), []);

  if (!waking) return null;

  return (
    <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-[#0B2005]/80 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-5 px-8 py-10 max-w-sm text-center">
        <img
          src="/images/agrika-gis-logo.png"
          alt="AgriKA-GIS"
          className="h-14 w-auto object-contain drop-shadow"
        />
        <span className="relative flex h-10 w-10">
          <span className="absolute inline-flex h-full w-full rounded-full border-4 border-white/25" />
          <span className="inline-flex h-10 w-10 rounded-full border-4 border-transparent border-t-white animate-spin" />
        </span>
        <div className="flex flex-col gap-1.5">
          <p className="text-base font-semibold text-white">Waking up the server…</p>
          <p className="text-sm leading-5 text-white/70">
            The server sleeps when idle on the free tier. This first load can take up to a
            minute. Hang tight, it'll continue automatically.
          </p>
        </div>
      </div>
    </div>
  );
}
