// Overall Report (Reports module): one printable document for the province or a city,
// with the productivity indices, historical yields, predicted yields, charts, and
// plain-language insights written from the values by fixed sentence templates.
// Opened in a print window, like the other PDF exports (Save as PDF from there).

import { yieldApi } from "./api";
import { foldText } from "./text";

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const f2 = (v) => (v == null ? "N/A" : Number(v).toFixed(2));
const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
const signed = (d) => `${d > 0 ? "+" : d < 0 ? "−" : ""}${Math.abs(d).toFixed(2)}`;
const upDown = (d, unit = " mt/ha") =>
  Math.abs(d) < 0.005 ? "unchanged" : `${d > 0 ? "up" : "down"} ${Math.abs(d).toFixed(2)}${unit}`;
const SEASON_ORDER = { Dry: 0, Wet: 1 };

// ---------------------------------------------------------------- SVG charts
function lineChart({ labels, series, width = 680, height = 240, unit = "mt/ha" }) {
  const vals = series.flatMap((s) => s.values).filter((v) => v != null);
  if (!vals.length) return "";
  const lo = Math.floor((Math.min(...vals) - 0.2) * 2) / 2;
  const hi = Math.ceil((Math.max(...vals) + 0.2) * 2) / 2;
  const L = 56, R = 12, T = 12, B = 58;
  const W = width - L - R, H = height - T - B;
  const x = (i) => L + (labels.length === 1 ? W / 2 : (i * W) / (labels.length - 1));
  const y = (v) => T + H - ((v - lo) / (hi - lo)) * H;
  let out = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" font-family="Arial" font-size="10">`;
  for (let t = lo; t <= hi + 1e-9; t += 0.5) {
    out += `<line x1="${L}" x2="${L + W}" y1="${y(t)}" y2="${y(t)}" stroke="#E5E7EB"/>`;
    out += `<text x="${L - 6}" y="${y(t) + 3}" text-anchor="end" fill="#6B7280">${t.toFixed(1)}</text>`;
  }
  out += `<text x="12" y="${T + H / 2}" transform="rotate(-90 12 ${T + H / 2})" text-anchor="middle" fill="#6B7280">${esc(unit)}</text>`;
  labels.forEach((lab, i) => {
    out += `<text x="${x(i)}" y="${T + H + 12}" text-anchor="end" transform="rotate(-40 ${x(i)} ${T + H + 12})" fill="#6B7280">${esc(lab)}</text>`;
  });
  for (const s of series) {
    let d = "";
    let pen = false;
    s.values.forEach((v, i) => {
      if (v == null) {
        pen = false;
        return;
      }
      d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
      pen = true;
    });
    out += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2"${s.dash ? ` stroke-dasharray="${s.dash}"` : ""}/>`;
    s.values.forEach((v, i) => {
      if (v != null) out += `<circle cx="${x(i)}" cy="${y(v)}" r="2.6" fill="${s.color}"/>`;
    });
  }
  // legend
  let lx = L;
  for (const s of series) {
    out += `<line x1="${lx}" x2="${lx + 18}" y1="${height - 8}" y2="${height - 8}" stroke="${s.color}" stroke-width="2"${s.dash ? ` stroke-dasharray="${s.dash}"` : ""}/>`;
    out += `<text x="${lx + 22}" y="${height - 5}" fill="#374151">${esc(s.name)}</text>`;
    lx += 30 + s.name.length * 6;
  }
  return out + "</svg>";
}

function barChart({ rows, width = 680, unit = "" }) {
  // rows: [{ label, value }], horizontal bars, already sorted
  const rowH = 16, L = 150, R = 50;
  const height = rows.length * rowH + 10;
  const vals = rows.map((r) => r.value);
  const lo = Math.max(0, Math.floor(Math.min(...vals) - 0.5)), hi = Math.ceil(Math.max(...vals));
  const x = (v) => L + ((v - lo) / (hi - lo)) * (width - L - R);
  let out = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" font-family="Arial" font-size="10">`;
  rows.forEach((r, i) => {
    const yy = 4 + i * rowH;
    out += `<text x="${L - 6}" y="${yy + 10}" text-anchor="end" fill="#374151">${esc(r.label)}</text>`;
    out += `<rect x="${L}" y="${yy + 2}" width="${Math.max(1, x(r.value) - L)}" height="${rowH - 5}" fill="#74C476"/>`;
    out += `<text x="${x(r.value) + 4}" y="${yy + 10}" fill="#1B3315">${f2(r.value)}${esc(unit)}</text>`;
  });
  return out + "</svg>";
}

// ---------------------------------------------------------------- data
/**
 * scope: { name, municipalityId } — municipalityId null for the province.
 * records: observed yields in view [{ municipality, year, season, yield }] (already
 *          filtered by the page's city scope, years and season).
 * season: "All" | "Dry" | "Wet"; years: [from, to].
 */
export async function openOverallReport({ scope, records, season, years }) {
  const win = window.open("", "_blank", "width=1000,height=800");
  if (!win) return;
  win.document.write("<p style='font-family:Arial;padding:24px'>Preparing the report…</p>");
  const mid = scope.municipalityId;
  const [prodAll, avp] = await Promise.all([
    yieldApi.productivity(mid).catch(() => ({ records: [] })),
    yieldApi.actualVsPredicted(mid).catch(() => ({ series: [] })),
  ]);
  const seasonsWanted = season === "All" ? ["Dry", "Wet"] : [season];
  const inYears = (y) => y >= years[0] && y <= years[1];
  const series = (avp.series || []).filter((p) => seasonsWanted.includes(p.season) && (inYears(p.year) || p.actual == null));
  const next = [...(avp.series || [])].reverse().find((p) => p.actual == null && seasonsWanted.includes(p.season));
  const ctx = next
    ? await yieldApi
        .forecastContext({ season: next.season, year: next.year, municipalityId: mid })
        .catch(() => null)
    : null;
  win.document.open();
  win.document.write(buildHtml({ scope, records, season, years, prod: prodAll.records || [], series, next, ctx }));
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 300);
}

// ---------------------------------------------------------------- document
function buildHtml({ scope, records, season, years, prod, series, next, ctx }) {
  const isCity = scope.municipalityId != null;
  const seasons = season === "All" ? ["Dry", "Wet"] : [season];
  const yrs = [...new Set(records.map((r) => r.year))].sort((a, b) => a - b);

  // Historical yields: per year and season, the city's value or the province mean.
  const hist = {};
  for (const r of records) {
    const k = `${r.year}|${r.season}`;
    (hist[k] ??= []).push(r.yield);
  }
  const histVal = (y, s) => (hist[`${y}|${s}`] ? mean(hist[`${y}|${s}`]) : null);
  const seasonAvg = (s) => mean(yrs.map((y) => histVal(y, s)).filter((v) => v != null));
  const allPts = yrs.flatMap((y) => seasons.map((s) => ({ y, s, v: histVal(y, s) }))).filter((p) => p.v != null);
  const best = allPts.reduce((a, b) => (!a || b.v > a.v ? b : a), null);
  const worst = allPts.reduce((a, b) => (!a || b.v < a.v ? b : a), null);

  // Indices
  const city = isCity ? prod.find((r) => r.municipality_id === scope.municipalityId) : null;
  const rpiLatest = (r) => r.rpi?.series?.[r.rpi.series.length - 1];
  const rpiPrev = (r) => r.rpi?.series?.[r.rpi.series.length - 2];
  const provinceRpi = prod
    .filter((r) => rpiLatest(r))
    .map((r) => ({ label: r.name.replace(/^City of /, ""), value: rpiLatest(r).rpi, year: rpiLatest(r).year, prev: rpiPrev(r)?.rpi }))
    .sort((a, b) => b.value - a.value);
  const spiRows = (isCity ? [city].filter(Boolean) : prod).filter((r) => r.spi);

  // Predicted vs actual
  const scored = series.filter((p) => p.actual != null);
  const over = scored.filter((p) => p.predicted > p.actual).length;
  const mad = scored.length ? mean(scored.map((p) => Math.abs(p.actual - p.predicted))) : null;
  const mae = ctx?.typical_error?.mae;

  // ---- insights (fixed templates)
  const where = isCity ? scope.name : "the province (mean of its cities and municipalities)";
  const ins = [];
  if (yrs.length) {
    const parts = seasons.map((s) => `the ${s.toLowerCase()} season averaged ${f2(seasonAvg(s))} mt/ha`);
    ins.push(`From ${yrs[0]} to ${yrs[yrs.length - 1]}, ${parts.join(" and ")} in ${where}.`);
  }
  if (best && worst && best !== worst)
    ins.push(`The best season was ${best.s} ${best.y} (${f2(best.v)} mt/ha) and the weakest ${worst.s} ${worst.y} (${f2(worst.v)} mt/ha).`);
  if (isCity && city?.rpi && rpiLatest(city)) {
    const a = rpiLatest(city), b = rpiPrev(city);
    ins.push(
      `The Rice Productivity Index for ${a.year} was ${f2(a.rpi)} mt/ha${b ? `, ${upDown(a.rpi - b.rpi)} from ${b.year}` : ""}.`
    );
  } else if (!isCity && provinceRpi.length > 1) {
    const top = provinceRpi[0], low = provinceRpi[provinceRpi.length - 1];
    const falling = provinceRpi.filter((r) => r.prev != null && r.value < r.prev).length;
    ins.push(
      `In ${top.year}, the Rice Productivity Index was highest in ${top.label} (${f2(top.value)}) and lowest in ${low.label} (${f2(low.value)}); it fell from the year before in ${falling} of ${provinceRpi.length} cities and municipalities.`
    );
  }
  for (const r of spiRows) {
    const s = r.spi.series[r.spi.series.length - 1];
    ins.push(
      `${r.name}: ${s.rice_ha.toLocaleString("en-US")} ha of rice were harvested in ${s.season} ${s.year}, ${f2(s.spi)}% of the city's land area (Spatial Productivity Index).`
    );
  }
  if (scored.length)
    ins.push(
      `Over ${scored.length} reported seasons, predictions differed from actual yields by ${f2(mad)} mt/ha on average and were higher than actual in ${over}.`
    );
  if (next) {
    const u = ctx?.usual;
    ins.push(
      `For ${next.season} ${next.year}, not yet reported, the model forecasts ${f2(next.predicted)} mt/ha${mae != null ? ` (± ${f2(mae)}, ${f2(next.predicted - mae)} to ${f2(next.predicted + mae)})` : ""}${
        u ? `, ${upDown(next.predicted - u.avg)} against the usual ${next.season.toLowerCase()} yield of ${f2(u.avg)} mt/ha (${u.from} to ${u.to})` : ""
      }.`
    );
  }

  // ---- tables
  const histTable = `<table><thead><tr><th>Year</th>${seasons.map((s) => `<th class="n">${s} (mt/ha)</th>`).join("")}${
    !isCity ? `<th class="n">Cities reporting</th>` : ""
  }</tr></thead><tbody>${yrs
    .map(
      (y) =>
        `<tr><td>${y}</td>${seasons.map((s) => `<td class="n">${f2(histVal(y, s))}</td>`).join("")}${
          !isCity ? `<td class="n">${Math.max(...seasons.map((s) => hist[`${y}|${s}`]?.length ?? 0))}</td>` : ""
        }</tr>`
    )
    .join("")}</tbody></table>`;

  const rpiTable = isCity
    ? city?.rpi
      ? `<table><thead><tr><th>Year</th><th class="n">Dry</th><th class="n">Wet</th><th class="n">RPI</th></tr></thead><tbody>${city.rpi.series
          .map((p) => `<tr><td>${p.year}</td><td class="n">${f2(p.dry)}</td><td class="n">${f2(p.wet)}</td><td class="n"><b>${f2(p.rpi)}</b></td></tr>`)
          .join("")}</tbody></table><p class="note">Weights: dry ${f2(city.rpi.w_dry)}, wet ${f2(city.rpi.w_wet)} (CV: dry ${(city.rpi.cv_dry * 100).toFixed(1)}%, wet ${(city.rpi.cv_wet * 100).toFixed(1)}%).</p>`
      : `<p class="note">No year with both seasons reported.</p>`
    : provinceRpi.length
    ? barChart({ rows: provinceRpi, unit: "" }) +
      `<p class="note">Rice Productivity Index of each city and municipality, ${provinceRpi[0].year}, mt/ha.</p>`
    : "";

  const spiTable = spiRows.length
    ? `<table><thead><tr><th>City</th><th>Season</th><th class="n">Harvested rice area (ha)</th><th class="n">City land area (ha)</th><th class="n">SPI (%)</th></tr></thead><tbody>${spiRows
        .flatMap((r) =>
          (isCity ? r.spi.series : r.spi.series.slice(-2)).map(
            (s) =>
              `<tr><td>${esc(r.name)}</td><td>${s.season} ${s.year}</td><td class="n">${s.rice_ha.toLocaleString("en-US")}</td><td class="n">${r.spi.land_ha.toLocaleString("en-US")}</td><td class="n"><b>${f2(s.spi)}</b></td></tr>`
          )
        )
        .join("")}</tbody></table>${!isCity ? `<p class="note">Latest two seasons of each city with barangay harvest records.</p>` : ""}`
    : `<p class="note">No barangay harvested-area records${isCity ? ` for ${esc(scope.name)}` : ""}, so no Spatial Productivity Index.</p>`;

  const avpChart = lineChart({
    labels: series.map((p) => `${p.season} ${p.year}`),
    series: [
      { name: "Actual", color: "#1F6306", values: series.map((p) => p.actual) },
      { name: "Predicted", color: "#C98500", dash: "5 4", values: series.map((p) => p.predicted) },
    ],
  });
  const avpTable = `<table><thead><tr><th>Season</th><th class="n">Actual</th><th class="n">Predicted</th><th class="n">Difference (actual − predicted)</th></tr></thead><tbody>${series
    .map(
      (p) =>
        `<tr><td>${p.season} ${p.year}</td><td class="n">${p.actual == null ? "not yet reported" : f2(p.actual)}</td><td class="n">${f2(p.predicted)}${
          p.actual == null && mae != null && next && p.year === next.year && p.season === next.season ? ` ± ${f2(mae)}` : ""
        }</td><td class="n">${p.actual == null ? "" : signed(p.actual - p.predicted)}</td></tr>`
    )
    .join("")}</tbody></table>`;

  const histChart = lineChart({
    labels: yrs.map(String),
    series: seasons.map((s) => ({
      name: `${s} season`,
      color: s === "Dry" ? "#C98500" : "#2A78D6",
      values: yrs.map((y) => histVal(y, s)),
    })),
  });

  const title = `Overall Rice Yield Report: ${scope.name}`;
  const period = `${years[0]} to ${years[1]}, ${season === "All" ? "dry and wet seasons" : `${season.toLowerCase()} season`}`;
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(title)}</title><style>
    @page{size:A4;margin:16mm}
    body{font-family:Arial,sans-serif;color:#1F2937;font-size:12px;line-height:1.45;margin:0 auto;max-width:720px;padding:16px}
    h1{font-size:20px;margin:0 0 2px;color:#1B3315}
    h2{font-size:14px;margin:22px 0 6px;padding-bottom:4px;border-bottom:2px solid #1F6306;color:#1B3315;break-after:avoid}
    .meta{color:#6B7280;font-size:11px;margin:0 0 10px}
    ul{margin:4px 0 0;padding-left:18px} li{margin:3px 0}
    table{width:100%;border-collapse:collapse;margin-top:6px;break-inside:auto}
    th,td{text-align:left;padding:4px 8px;border-bottom:1px solid #E5E7EB;font-size:11px}
    th{background:#F3F4F6;font-size:10px;text-transform:uppercase;color:#4B5563}
    td.n,th.n{text-align:right} tr{break-inside:avoid;page-break-inside:avoid}
    thead{display:table-header-group}
    /* Each block (heading + chart, a table, the summary box) prints whole: if it does
       not fit on what is left of a page, it moves to the next page. */
    .keep{break-inside:avoid;page-break-inside:avoid}
    .note{color:#6B7280;font-size:10px;margin:4px 0 0}
    svg{display:block;margin-top:6px;max-width:100%;height:auto}
    .box{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:6px;padding:10px 12px}
    footer{margin-top:22px;padding-top:8px;border-top:1px solid #E5E7EB;color:#6B7280;font-size:10px}
    footer p{margin:0 0 3px}
  </style></head><body>
  <h1>${esc(title)}</h1>
  <p class="meta">AgriKA-GIS · ${esc(period)} · generated ${esc(new Date().toLocaleString())}</p>

  <div class="keep"><h2>Summary</h2>
  <div class="box"><ul>${ins.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div></div>

  <div class="keep"><h2>Productivity Indices</h2>
  <p><b>Rice Productivity Index (RPI)</b>: the dry- and wet-season yields of a year in one value, RPI = dry yield × W<sub>dry</sub> + wet yield × W<sub>wet</sub>, where each season's weight is its coefficient of variation (CV) over the years divided by the sum of both.</p>
  ${rpiTable}</div>
  <div class="keep"><p style="margin-top:12px"><b>Spatial Productivity Index (SPI)</b>: harvested rice area divided by the city's land area, × 100.</p>
  ${spiTable}</div>

  <div class="keep"><h2>Historical Yield</h2>
  ${histChart}</div>
  <div class="keep">${histTable}
  <p class="note">${isCity ? "Observed yield of the city." : "Mean observed yield of the cities and municipalities reporting that season."}</p></div>

  <div class="keep"><h2>Predicted Versus Actual Yield</h2>
  ${avpChart}</div>
  <div class="keep">${avpTable}
  <p class="note">One row per season; years are not averaged together.${!isCity ? " Province rows average the cities with both values that season." : ""}${
    mae != null ? ` ± is the model's average error on past seasons (${ctx.typical_error.n} city-seasons).` : ""
  }</p></div>

  <footer class="keep">
    <p>Sources: PRiSM / Ricelytics (PhilRice) city and municipality yields; City Agriculture Office barangay harvest reports (harvested area for the SPI); CNN-LSTM predictions of AgriKA-GIS; city land areas from the PSA boundaries.</p>
    <p>Disclaimer: predicted yields are estimates from the trained model, made from satellite pictures and weather data. They are not official or reported figures, and the actual harvest can differ.</p>
  </footer>
  </body></html>`;
}

// Resolve a city name in the records to its municipality_id (for the APIs).
export async function municipalityIdFor(name) {
  if (!name) return null;
  const r = await yieldApi.productivity().catch(() => ({ records: [] }));
  const k = foldText(name);
  return (r.records || []).find((x) => foldText(x.name) === k)?.municipality_id ?? null;
}
