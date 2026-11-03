// Plain-language insights for the yield map, written from the values on screen with
// fixed sentence templates (no AI model). Also the residual classes the paper uses:
// close within ±0.20 mt/ha, overestimated below −0.20, underestimated above +0.20.

export const RESIDUAL_CLOSE = 0.2; // mt/ha (200 kg/ha)

// Residual = observed − predicted. Negative: the model expected more than was harvested.
export function residualClass(r) {
  if (r == null) return null;
  if (r < -RESIDUAL_CLOSE) return "over";
  if (r > RESIDUAL_CLOSE) return "under";
  return "close";
}

const f2 = (v) => Number(v).toFixed(2);
const kg = (v) => Math.round(Math.abs(v) * 1000).toLocaleString("en-US");
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

function highLow(rows, key) {
  const sorted = [...rows].sort((a, b) => b[key] - a[key]);
  return { high: sorted[0], low: sorted[sorted.length - 1] };
}

/**
 * mode     "observed" | "predicted" | "residual"
 * records  [{ name, yield? , observed?, predicted?, residual? }]
 * period   e.g. "Wet 2026"
 * unit     ["barangay", "barangays"] or ["city or municipality", "cities and municipalities"]
 * place    "" or " in Calamba"
 * Returns a list of sentences (empty when there is nothing to say).
 */
export function mapInsights({ mode, records, period, unit, place = "" }) {
  const [one, many] = unit;
  if (mode === "observed") {
    const rows = (records ?? []).filter((r) => r.yield != null);
    if (!rows.length) return [];
    const { high, low } = highLow(rows, "yield");
    const out = [
      `Reported yields for ${period}${place} average ${f2(mean(rows.map((r) => r.yield)))} mt/ha across ${plural(rows.length, one, many)}.`,
    ];
    if (rows.length > 1)
      out.push(`Highest: ${high.name} (${f2(high.yield)} mt/ha). Lowest: ${low.name} (${f2(low.yield)} mt/ha).`);
    return out;
  }

  if (mode === "predicted") {
    const rows = (records ?? []).filter((r) => r.predicted != null);
    if (!rows.length) return [];
    const { high, low } = highLow(rows, "predicted");
    const out = [
      `The model forecasts an average of ${f2(mean(rows.map((r) => r.predicted)))} mt/ha for ${period}${place} across ${plural(rows.length, one, many)}.`,
    ];
    if (rows.length > 1)
      out.push(
        `Highest forecast: ${high.name} (${f2(high.predicted)} mt/ha). Lowest: ${low.name} (${f2(low.predicted)} mt/ha); areas forecast lowest may need field visits first.`
      );
    if (!rows.some((r) => r.observed != null))
      out.push("No harvest has been reported for this season yet, so the forecast cannot be checked against actual yields.");
    return out;
  }

  // Residual
  const rows = (records ?? []).filter((r) => r.residual != null);
  if (!rows.length) return [];
  const over = rows.filter((r) => residualClass(r.residual) === "over");
  const under = rows.filter((r) => residualClass(r.residual) === "under");
  const close = rows.length - over.length - under.length;
  const total = plural(rows.length, one, many);
  const out = [
    close === 0
      ? `None of the ${total} in ${period}${place} were within ±0.20 mt/ha of the forecast.`
      : close === rows.length
      ? `All ${total} in ${period}${place} were within ±0.20 mt/ha of the forecast.`
      : `${close} of ${total} in ${period}${place} were within ±0.20 mt/ha of the forecast.`,
  ];
  if (over.length) {
    const m = mean(over.map((r) => r.residual));
    const worst = over.reduce((a, b) => (b.residual < a.residual ? b : a));
    out.push(
      `${plural(over.length, one, many)} harvested less than forecast (overestimated) by ${f2(-m)} mt/ha (${kg(m)} kg/ha) on average, most in ${worst.name} (${f2(-worst.residual)} mt/ha). Check these for pests, flooding, late planting, or reporting errors before relying on the forecast there.`
    );
  }
  if (under.length) {
    const m = mean(under.map((r) => r.residual));
    const top = under.reduce((a, b) => (b.residual > a.residual ? b : a));
    out.push(
      `${plural(under.length, one, many)} harvested more than forecast (underestimated) by ${f2(m)} mt/ha (${kg(m)} kg/ha) on average, most in ${top.name} (${f2(top.residual)} mt/ha).`
    );
  }
  return out;
}
