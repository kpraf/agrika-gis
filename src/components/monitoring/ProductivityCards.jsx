import React, { useEffect, useState } from "react";
import { yieldApi } from "../../lib/api";

// Two dashboard cards for the city in focus (Chapter 3, Data Analysis):
//   RPI: the dry- and wet-season yields of a year in one value, each season weighted
//        by how much its yields vary across the years (coefficient of variation).
//   SPI: harvested rice area as a share of the city's land area, in percent.
// Province view (no city in focus): a prompt to pick one.

const f2 = (v) => Number(v).toFixed(2);

function Change({ now, before, unit, digits = 2 }) {
  if (before == null) return null;
  const d = now - before;
  if (Math.abs(d) < 10 ** -digits / 2) return <span className="text-[11px] text-[#6B7280]">no change</span>;
  const up = d > 0;
  return (
    <span className={`text-[11px] font-semibold ${up ? "text-[#16A34A]" : "text-[#DC2626]"}`}>
      {up ? "▲" : "▼"} {Math.abs(d).toFixed(digits)}
      {unit}
    </span>
  );
}

function Card({ title, value, unit, change, lines }) {
  return (
    <div className="flex flex-col gap-1.5 p-4 bg-[#F9FAFB] border border-[#F3F4F6] rounded-lg">
      <span className="text-[10px] sm:text-xs font-semibold text-[#6B7280] uppercase tracking-wide">{title}</span>
      <div className="flex items-baseline gap-1.5 flex-wrap">
        <span className="text-2xl font-bold text-[#1B3315] leading-tight">{value}</span>
        {unit && <span className="text-[11px] text-[#6B7280]">{unit}</span>}
        {change}
      </div>
      {lines.map((l) => (
        <span key={l} className="text-[11px] leading-4 text-[#6B7280]">
          {l}
        </span>
      ))}
    </div>
  );
}

export default function ProductivityCards({ municipalityId, cityName }) {
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!municipalityId) {
      setRec(null);
      return;
    }
    let active = true;
    setLoading(true);
    yieldApi
      .productivity(municipalityId)
      .then((r) => active && setRec(r.records?.[0] ?? null))
      .catch(() => active && setRec(null))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [municipalityId]);

  if (!municipalityId) {
    return (
      <p className="text-xs leading-5 text-[#6B7280]">
        Click a city or municipality on the map to see its Rice Productivity Index and Spatial Productivity Index.
      </p>
    );
  }
  if (loading && !rec) return <p className="text-xs text-[#9CA3AF]">Loading indices…</p>;

  const rpiSeries = rec?.rpi?.series ?? [];
  const rpiNow = rpiSeries[rpiSeries.length - 1];
  const rpiBefore = rpiSeries[rpiSeries.length - 2];
  const spiSeries = rec?.spi?.series ?? [];
  const spiNow = spiSeries[spiSeries.length - 1];
  // Same season a year earlier, so dry is compared with dry and wet with wet.
  const spiBefore = spiNow
    ? spiSeries.find((s) => s.season === spiNow.season && s.year === spiNow.year - 1)
    : null;

  return (
    <div className="grid grid-cols-1 gap-3">
      {rpiNow ? (
        <Card
          title={`Rice Productivity Index, ${rpiNow.year}`}
          value={f2(rpiNow.rpi)}
          unit="mt/ha"
          change={<Change now={rpiNow.rpi} before={rpiBefore?.rpi} unit={` vs ${rpiBefore?.year}`} />}
          lines={[
            `Dry ${f2(rpiNow.dry)} × ${f2(rec.rpi.w_dry)} + Wet ${f2(rpiNow.wet)} × ${f2(rec.rpi.w_wet)}`,
            `Weights from how much each season's yield varies across the years (CV: dry ${(rec.rpi.cv_dry * 100).toFixed(1)}%, wet ${(rec.rpi.cv_wet * 100).toFixed(1)}%).`,
          ]}
        />
      ) : (
        <Card title="Rice Productivity Index" value="N/A" lines={[`No year with both seasons reported for ${cityName}.`]} />
      )}
      {spiNow ? (
        <Card
          title={`Spatial Productivity Index, ${spiNow.season} ${spiNow.year}`}
          value={f2(spiNow.spi)}
          unit="%"
          change={<Change now={spiNow.spi} before={spiBefore?.spi} unit={` pts vs ${spiNow.season} ${spiNow.year - 1}`} />}
          lines={[
            `${spiNow.rice_ha.toLocaleString("en-US")} ha harvested of ${rec.spi.land_ha.toLocaleString("en-US")} ha city land area.`,
          ]}
        />
      ) : (
        <Card
          title="Spatial Productivity Index"
          value="N/A"
          lines={[`Needs barangay harvested-area records from the City Agriculture Office of ${cityName}.`]}
        />
      )}
    </div>
  );
}
