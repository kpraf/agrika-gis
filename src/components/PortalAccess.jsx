import React, { useState } from "react";

export default function PortalAccess() {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="relative w-full min-h-screen flex items-center justify-center bg-white px-8 py-24 overflow-hidden">
      {/* Background image layer */}
      <div className="absolute inset-0 bg-[url('/images/farms.png')] bg-cover bg-center opacity-80" />

      {/* Back to Home - sits on the page background, outside the card */}
      <a
        href="/"
        className="absolute top-8 left-8 z-20 flex items-center gap-2 px-6 py-3 rounded-full bg-[#1F6306] text-white text-base font-semibold hover:bg-[#286A11] transition-colors"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M8 1L2 6l6 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Back to Home
      </a>

      {/* Main card */}
      <div className="relative z-10 w-full max-w-[1024px] min-h-[600px] flex flex-col md:flex-row bg-white rounded-[32px] shadow-[0px_20px_40px_-10px_rgba(27,51,21,0.1)] overflow-hidden">
        {/* Left image section */}
        <div className="relative flex w-full md:w-[46%] min-h-[300px] md:min-h-0 p-4">
          <div className="relative w-full rounded-3xl overflow-hidden">
            <div className="absolute inset-0 bg-[url('/images/male-farmer.png')] bg-cover bg-center" />
            <div className="absolute inset-0 bg-gradient-to-t from-[#1B3315]/80 via-[#1B3315]/20 to-transparent" />

            {/* Content overlay */}
            <div className="absolute inset-0 flex flex-col justify-between p-8">
              <img
                src="/images/agrika-gis-logo.png"
                alt="AgriKA-GIS"
                className="h-12 w-auto self-start object-contain"
              />

              <div className="flex flex-col gap-2">
                <span className="text-xs font-medium uppercase tracking-wider text-white/80">
                  AgriKA-GIS Spatial Intelligence
                </span>
                <h2 className="text-2xl md:text-3xl font-bold text-white leading-snug">
                  Access spatial analytics and real-time rice yield insights.
                </h2>
              </div>
            </div>
          </div>
        </div>

        {/* Right form section */}
        <div className="relative w-full md:w-[54%] flex flex-col px-8 md:px-16 py-12">
          {/* Header */}
          <div className="flex flex-col gap-3 mb-8">
            <div className="w-8 h-8 rounded-full bg-[#2D5A27]/10 flex items-center justify-center">
              <svg width="15" height="14" viewBox="0 0 15 14" fill="none">
                <path d="M7.5 1L1 5v8h13V5L7.5 1z" stroke="#1F6306" strokeWidth="1.2" />
              </svg>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-[#1B3315]">Portal Access</h1>
            <p className="text-sm leading-[23px] text-[#6B7280] max-w-[380px]">
              Access the AgriKA-GIS platform to explore spatial yield analytics, GIS
              visualizations, and agricultural monitoring tools.
            </p>
          </div>

          {/* Form */}
          <form className="flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-[#1B3315]">Your email</label>
              <input
                type="email"
                placeholder="example@agrika-gis.com"
                className="w-full px-4 py-3.5 border border-[#E5E7EB] rounded-xl text-sm text-[#1B3315] placeholder-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1F6306]/30"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-[#1B3315]">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  className="w-full px-4 py-3.5 border border-[#E5E7EB] rounded-xl text-sm text-[#1B3315] placeholder-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1F6306]/30"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#9CA3AF]"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path
                      d="M1 10s3-6 9-6 9 6 9 6-3 6-9 6-9-6-9-6z"
                      stroke="currentColor"
                      strokeWidth="1.25"
                    />
                    <circle cx="10" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.25" />
                  </svg>
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-3.5 rounded-xl bg-[#1F6306] text-white font-semibold text-base shadow-[0px_10px_20px_-5px_rgba(45,90,39,0.3)] hover:bg-[#286A11] transition-colors"
            >
              Sign In
            </button>
          </form>

          {/* Request access link */}
          <p className="mt-8 text-center text-sm text-[#6B7280]">
            Don't have portal access yet?{" "}
            <a href="#" className="font-semibold text-[#1F6306] hover:underline">
              Request Access
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}