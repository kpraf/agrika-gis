import React from "react";

// Right-panel card under the legend: what the map on screen says, in plain words
// (sentences from lib/mapInsights.js), plus the prediction disclaimer when the map
// shows a forecast or a residual.
export default function MapInsightsCard({ insights = [], disclaimer = false }) {
  if (!insights.length && !disclaimer) return null;
  return (
    <div className="flex flex-col gap-3 p-6 bg-[#F9FAFB] border border-[#C3C8BD] rounded-xl w-full">
      <h4 className="text-xs font-semibold tracking-[0.7px] text-[#434840] uppercase">Map Insights</h4>
      {insights.length > 0 && (
        <ul className="flex flex-col gap-2 m-0 p-0 list-none">
          {insights.map((s) => (
            <li key={s} className="flex gap-2 text-[13px] leading-5 text-[#191C1A]">
              <span className="mt-[7px] w-1.5 h-1.5 shrink-0 rounded-full bg-[#3B9E1C]" />
              <span>{s}</span>
            </li>
          ))}
        </ul>
      )}
      {disclaimer && (
        <p className="m-0 pt-3 border-t border-[#E1E3DE] text-[12px] leading-[18px] text-[#6B7280]">
          <b className="font-semibold text-[#434840]">Disclaimer.</b> Predicted yields are estimates from the
          trained CNN-LSTM model, made from satellite pictures and weather data. They are not official or reported
          figures, and the actual harvest can differ.
        </p>
      )}
    </div>
  );
}
