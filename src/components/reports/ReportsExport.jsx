import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import DashboardSidebar from "../layout/DashboardSidebar";

import * as XLSX from "xlsx";

// Green ramp so taller bars read darker — adds a second visual cue to height.
const REPORT_RAMP = ["#C7E9C0", "#A1D99B", "#74C476", "#41AB5D", "#238B45", "#005A32"];
function rampColor(value, min, max) {
  if (value == null || max <= min) return REPORT_RAMP[3];
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  return REPORT_RAMP[Math.round(t * (REPORT_RAMP.length - 1))];
}
import { yieldApi } from "../../lib/api";

function deriveStatus(yieldValue) {
  if (yieldValue >= 5) return "Good";
  if (yieldValue >= 4) return "Moderate";
  return "Low";
}

const STATUS_STYLES = {
  Good: "bg-[#DCFCE7] text-[#15803D]",
  Moderate: "bg-[#FEF9C3] text-[#A16207]",
  Low: "bg-[#FFEDD5] text-[#C2410C]",
};

const REPORT_TYPES = [
  { key: "summary", label: "Yield Summary" },
  { key: "comparison", label: "Comparison Report" },
  { key: "importLog", label: "Data Import History" },
];

const SEASONS = ["All", "Wet", "Dry"];

function toCSV(rows, columns) {
  const escape = (val) => {
    const str = String(val ?? "");
    return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
  };
  const header = columns.map((c) => c.label).join(",");
  const body = rows.map((row) => columns.map((c) => escape(row[c.key])).join(",")).join("\n");
  return `${header}\n${body}`;
}

function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// Real .xlsx workbook (SheetJS) — one sheet, auto-sized columns.
function downloadXLSX(title, rows, columns) {
  const sheetRows = rows.map((row) =>
    Object.fromEntries(
      columns.map((c) => [c.label, row[c.key] ?? ""])
    )
  );

  const ws = XLSX.utils.json_to_sheet(sheetRows, {
    header: columns.map((c) => c.label),
  });

  ws["!cols"] = columns.map((c) => ({
    wch:
      Math.max(
        c.label.length,
        ...rows.map((r) => String(r[c.key] ?? "").length)
      ) + 2,
  }));

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Report");

  XLSX.writeFile(
    wb,
    `${title.replace(/\s+/g, "-").toLowerCase()}.xlsx`
  );
}

function printAsPDF(title, rows, columns) {
  const win = window.open("", "_blank", "width=900,height=700");
  if (!win) return;
  const escapeHtml = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const headerHtml = columns.map((c) => `<th>${escapeHtml(c.label)}</th>`).join("");
  const rowsHtml = rows
    .map((row) => `<tr>${columns.map((c) => `<td>${escapeHtml(row[c.key])}</td>`).join("")}</tr>`)
    .join("");
  win.document.write(`<!doctype html><html><head><title>${escapeHtml(title)}</title>
    <style>
      body{font-family:Arial,sans-serif;padding:32px;color:#1F2937;}
      h1{font-size:20px;margin-bottom:4px;}
      p{color:#6B7280;font-size:12px;margin-top:0;}
      table{width:100%;border-collapse:collapse;margin-top:16px;}
      th,td{text-align:left;padding:8px 12px;border-bottom:1px solid #E5E7EB;font-size:13px;}
      th{background:#F9FAFB;text-transform:uppercase;font-size:11px;color:#6B7280;}
    </style></head><body>
    <h1>${escapeHtml(title)}</h1>
    <p>Generated ${new Date().toLocaleString()} &middot; ${rows.length} record(s)</p>
    <table><thead><tr>${headerHtml}</tr></thead><tbody>${rowsHtml}</tbody></table>
    </body></html>`);
  win.document.close();
  win.focus();
  win.print();
}

export default function ReportsExport() {
  const { city } = useParams();
  const fileInputRef = useRef(null);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importLog, setImportLog] = useState([]);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null); // { inserted, updated, skipped, errors } | { error }
  const [importLevel, setImportLevel] = useState("municipality"); // "municipality" | "barangay"
  const [isDragging, setIsDragging] = useState(false);
  const [reportType, setReportType] = useState("summary");
  const [season, setSeason] = useState("All");
  const [fromYear, setFromYear] = useState(null);
  const [toYear, setToYear] = useState(null);
  const [exportFormat, setExportFormat] = useState("csv");
  const [chartGroupBy, setChartGroupBy] = useState("area"); // "area" (muni/brgy) | "year"

  // --- Report scope: the whole page (preview, records, export) is scoped by a
  // level and, optionally, a single municipality. Barangay level always targets
  // one municipality (that has barangay data) and shows its barangays.
  const [viewLevel, setViewLevel] = useState("municipality"); // "municipality" | "barangay"
  const [viewMuni, setViewMuni] = useState(""); // municipality level: "" = all, else a name
  const [viewBrgyMuni, setViewBrgyMuni] = useState(null); // barangay level: municipality_id
  const [barangayMunis, setBarangayMunis] = useState([]); // [{ municipality_id, name }] with barangay data
  const [barangayRows, setBarangayRows] = useState([]); // scoped barangay records (name = barangay)
  const [scopeLoading, setScopeLoading] = useState(false);

  // Map an API /yield/records payload into local rows and frame the year range.
  const applyRecords = (r) => {
    const mapped = (r.records || []).map((x) => ({
      municipality: x.municipality,
      year: x.year,
      season: x.season,
      yield: x.yield,
      status: deriveStatus(x.yield),
    }));
    setRecords(mapped);
    const ys = mapped.map((m) => m.year);
    if (ys.length) {
      setFromYear(Math.min(...ys));
      setToYear(Math.max(...ys));
    }
  };

  // Load the real observed-yield dataset and frame the year range around it.
  useEffect(() => {
    let active = true;
    yieldApi
      .records()
      .then((r) => active && applyRecords(r))
      .catch(() => active && setRecords([]))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  // Municipalities that actually have barangay yield data (barangay-level picker).
  useEffect(() => {
    yieldApi
      .barangayMunicipalities()
      .then((d) => setBarangayMunis(d.municipalities || []))
      .catch(() => {});
  }, []);

  // Default the barangay-level municipality once the list is known.
  useEffect(() => {
    if (viewLevel === "barangay" && viewBrgyMuni == null && barangayMunis.length) {
      setViewBrgyMuni(barangayMunis[0].municipality_id);
    }
  }, [viewLevel, barangayMunis, viewBrgyMuni]);

  // Fetch the selected municipality's barangay records for barangay level.
  useEffect(() => {
    if (viewLevel !== "barangay" || viewBrgyMuni == null) {
      setBarangayRows([]);
      return;
    }
    let active = true;
    setScopeLoading(true);
    yieldApi
      .barangayRecords(viewBrgyMuni)
      .then((d) => {
        if (!active) return;
        setBarangayRows(
          (d.records || []).map((x) => ({
            name: x.barangay,
            municipality: x.municipality,
            year: x.year,
            season: x.season,
            yield: x.yield,
            status: deriveStatus(x.yield),
          }))
        );
      })
      .catch(() => active && setBarangayRows([]))
      .finally(() => active && setScopeLoading(false));
    return () => {
      active = false;
    };
  }, [viewLevel, viewBrgyMuni]);

  const cityLabel = useMemo(
    () => (city ? city.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Laguna Province"),
    [city]
  );

  const isBarangay = viewLevel === "barangay";
  const areaLabel = isBarangay ? "barangays" : "municipalities";
  const areaColLabel = isBarangay ? "Barangay" : "Municipality";
  const areaCountLabel = (n) =>
    `${n} ${n === 1 ? (isBarangay ? "barangay" : "municipality") : areaLabel}`;

  // Base rows for the current scope, each carrying a generic `name` (municipality
  // name, or barangay name at barangay level).
  const scopedRecords = useMemo(() => {
    if (isBarangay) return barangayRows; // already scoped to one municipality, name = barangay
    const base = viewMuni ? records.filter((r) => r.municipality === viewMuni) : records;
    return base.map((r) => ({ ...r, name: r.municipality }));
  }, [isBarangay, barangayRows, records, viewMuni]);

  const yearOptions = useMemo(
    () => Array.from(new Set(scopedRecords.map((r) => r.year))).sort(),
    [scopedRecords]
  );

  // All municipality names (for the municipality-level scope dropdown).
  const muniOptions = useMemo(
    () => Array.from(new Set(records.map((r) => r.municipality))).sort(),
    [records]
  );

  // When the scope changes, reset the year window to the scoped data's range
  // (municipality years are 2018+, barangay years 2020+).
  useEffect(() => {
    const ys = Array.from(new Set(scopedRecords.map((r) => r.year)));
    if (ys.length) {
      setFromYear(Math.min(...ys));
      setToYear(Math.max(...ys));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewLevel, viewMuni, viewBrgyMuni, barangayRows]);

  const filtered = useMemo(
    () =>
      scopedRecords.filter(
        (r) =>
          (season === "All" || r.season === season) &&
          (fromYear == null || r.year >= fromYear) &&
          (toYear == null || r.year <= toYear)
      ),
    [scopedRecords, season, fromYear, toYear]
  );

  const stats = useMemo(() => {
    if (!filtered.length) {
      return { total: 0, areas: 0, highest: null, lowest: null, goodPct: 0 };
    }
    const areas = new Set(filtered.map((r) => r.name)).size;
    const highest = filtered.reduce((a, b) => (b.yield > a.yield ? b : a));
    const lowest = filtered.reduce((a, b) => (b.yield < a.yield ? b : a));
    const goodPct = Math.round((filtered.filter((r) => r.status === "Good").length / filtered.length) * 100);
    return { total: filtered.length, areas, highest, lowest, goodPct };
  }, [filtered]);

  const chartData = useMemo(() => {
    const groups = new Map();
    filtered.forEach((r) => {
      const key = chartGroupBy === "year" ? String(r.year) : r.name;
      const entry = groups.get(key) || { key, total: 0, count: 0 };
      entry.total += r.yield;
      entry.count += 1;
      groups.set(key, entry);
    });
    return Array.from(groups.values()).map((g) => ({ key: g.key, yield: Number((g.total / g.count).toFixed(2)) }));
  }, [filtered, chartGroupBy]);

  // Names the current scope for report titles ("Laguna Province", a municipality,
  // or a municipality's barangays).
  const scopeTitle = isBarangay
    ? `${barangayMunis.find((m) => m.municipality_id === viewBrgyMuni)?.name || "Barangays"} — Barangays`
    : viewMuni || "Laguna Province";

  const exportColumns = [
    { key: "name", label: areaColLabel },
    { key: "year", label: "Year" },
    { key: "season", label: "Season" },
    { key: "yield", label: "Yield (MT/ha)" },
    { key: "status", label: "Status" },
  ];

  const buildExportRows = () => {
    if (reportType === "importLog") {
      return {
        rows: importLog,
        columns: [
          { key: "fileName", label: "File Name" },
          { key: "rows", label: "Rows Imported" },
          { key: "importedAt", label: "Imported At" },
        ],
        title: "Data Import History",
      };
    }
    if (reportType === "comparison") {
      const groups = new Map();
      filtered.forEach((r) => {
        const entry = groups.get(r.name) || { name: r.name, total: 0, count: 0 };
        entry.total += r.yield;
        entry.count += 1;
        groups.set(r.name, entry);
      });
      const rows = Array.from(groups.values()).map((g) => ({
        name: g.name,
        avgYield: Number((g.total / g.count).toFixed(2)),
        records: g.count,
      }));
      return {
        rows,
        columns: [
          { key: "name", label: areaColLabel },
          { key: "avgYield", label: "Avg Yield (MT/ha)" },
          { key: "records", label: "Records" },
        ],
        title: `${areaColLabel} Comparison — ${scopeTitle}`,
      };
    }
    return { rows: filtered, columns: exportColumns, title: `Yield Summary — ${scopeTitle}` };
  };

  const handleGenerate = () => {
    const { rows, columns, title } = buildExportRows();
    if (!rows.length) return;
    if (exportFormat === "pdf") {
      printAsPDF(title, rows, columns);
    } else if (exportFormat === "excel") {
      downloadXLSX(title, rows, columns);
    } else {
      const csv = toCSV(rows, columns);
      downloadBlob(
        csv,
        `${title.replace(/\s+/g, "-").toLowerCase()}.csv`,
        "text/csv;charset=utf-8;"
      );
    }
  };

  const handleDownloadTemplate = () => {
    // Focused import template for the current level — the columns the server
    // expects, with new-season example rows (2026). Use a real municipality name
    // from the dataset so it imports as-is (must match the DB exactly, e.g.
    // "City of Calamba", not "Calamba"). For barangays, replace "Barangay 1" with
    // real barangay names of that municipality.
    const muniName =
      (records.length ? [...new Set(records.map((r) => r.municipality))][0] : null) || "City of Calamba";
    const q = (n) => (/[",\n]/.test(n) ? `"${n.replace(/"/g, '""')}"` : n);
    const template =
      importLevel === "barangay"
        ? "municipality,barangay,year,season,yield\n" +
          `${q(muniName)},Barangay 1,2026,Dry,5.2\n` +
          `${q(muniName)},Barangay 1,2026,Wet,4.8\n`
        : "municipality,year,season,yield\n" +
          `${q(muniName)},2026,Dry,5.2\n` +
          `${q(muniName)},2026,Wet,4.8\n`;
    downloadBlob(template, `agrika-gis-import-template-${importLevel}.csv`, "text/csv;charset=utf-8;");
  };

  // Send the CSV to the backend, which validates + upserts into the real
  // dataset, then refresh what this page shows. Other screens pick up the new
  // data on their next load.
  const ingestFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      const text = String(reader.result || "");
      if (!text.trim()) {
        setImportResult({ error: "That file looks empty." });
        return;
      }
      setImporting(true);
      setImportResult(null);
      try {
        const res = await yieldApi.importCsv(text, importLevel, `Manual import: ${file.name}`);
        setImportResult(res);
        const changed = (res.inserted || 0) + (res.updated || 0) > 0;
        // Municipality imports change this page's dataset; barangay imports feed
        // the Map/Analytics drill-down instead, so only refresh when relevant.
        if (changed && importLevel === "municipality") {
          applyRecords(await yieldApi.records());
        }
        if (changed) {
          setImportLog((prev) => [
            ...prev,
            {
              fileName: file.name,
              rows: (res.inserted || 0) + (res.updated || 0),
              importedAt: new Date().toLocaleString(),
            },
          ]);
        }
      } catch (e) {
        setImportResult({ error: e.message || "Import failed." });
      } finally {
        setImporting(false);
        if (fileInputRef.current) fileInputRef.current.value = ""; // allow re-selecting the same file
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="flex w-full h-screen bg-[#F3F4F6] font-sans pb-14 md:pb-0" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      <DashboardSidebar active="reports" city={city} />

      <div className="flex flex-col flex-1 min-w-0">
        <header className="flex items-center justify-between gap-3 px-4 md:px-10 h-14 md:h-20 shrink-0 bg-white border-b border-[#E5E7EB]">
          <h1 className="text-base md:text-2xl font-bold text-[#1F2937] tracking-[-0.6px] truncate">
            <span className="md:hidden">Reports</span>
            <span className="hidden md:inline">Reports Generation and Data Import/Export</span>
          </h1>
          <span className="text-xs md:text-sm font-medium text-[#6B7280] shrink-0">{cityLabel}</span>
        </header>

        <div className="flex-1 overflow-y-auto bg-[#F8FAFC] p-4 sm:p-6">
          {/* Top Stats Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard
              label="Total Records"
              value={String(stats.total)}
              caption={areaCountLabel(stats.areas)}
              captionColor="text-[#22C55E]"
              iconBg="bg-[#F9FAFB]"
              iconColor="#9CA3AF"
            />
            <StatCard
              label="Highest Yield"
              value={stats.highest ? `${stats.highest.yield.toFixed(1)} MT/ha` : "N/A"}
              caption={stats.highest?.name || "No data"}
              captionColor="text-[#9CA3AF]"
              iconBg="bg-[#F0FDF4]"
              iconColor="#22C55E"
            />
            <StatCard
              label="Lowest Yield"
              value={stats.lowest ? `${stats.lowest.yield.toFixed(1)} MT/ha` : "N/A"}
              caption={stats.lowest?.name || "No data"}
              captionColor="text-[#9CA3AF]"
              iconBg="bg-[#FFF7ED]"
              iconColor="#F97316"
            />
            <StatCard
              label="Yield Distribution"
              value={`${stats.goodPct}% Good`}
              caption={`${stats.total} records analyzed`}
              captionColor="text-[#9CA3AF]"
              iconBg="bg-[#EFF6FF]"
              iconColor="#3B82F6"
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
            {/* Left Column */}
            <div className="flex flex-col gap-6 min-w-0">
              {/* Data Import Zone */}
              <div className="bg-white border border-[#F3F4F6] shadow-sm rounded-xl p-6 flex flex-col gap-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-lg font-bold text-[#1F2937]">Import Data</h2>
                  <div className="flex items-center gap-3">
                    {/* Level toggle — decides the target table + template */}
                    <div className="flex p-0.5 bg-[#F3F4F6] rounded-lg text-xs font-medium">
                      {[
                        { key: "municipality", label: "Municipality" },
                        { key: "barangay", label: "Barangay" },
                      ].map((lvl) => (
                        <button
                          key={lvl.key}
                          type="button"
                          onClick={() => {
                            setImportLevel(lvl.key);
                            setImportResult(null);
                          }}
                          className={`px-3 py-1.5 rounded-md transition-colors ${
                            importLevel === lvl.key ? "bg-white text-[#1B3315] shadow-sm" : "text-[#6B7280]"
                          }`}
                        >
                          {lvl.label}
                        </button>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={handleDownloadTemplate}
                      className="flex items-center gap-2 text-sm font-semibold text-[#1F6306] hover:underline"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 3v12m0 0l-4-4m4 4l4-4M4 19h16" />
                      </svg>
                      Template
                    </button>
                  </div>
                </div>

                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setIsDragging(false);
                    ingestFile(e.dataTransfer.files?.[0]);
                  }}
                  className={`flex flex-col items-center justify-center gap-4 py-12 px-10 border-2 border-dashed rounded-xl transition-colors ${
                    isDragging ? "border-[#1F6306] bg-[#F0FDF4]" : "border-[#D1D5DB]"
                  }`}
                >
                  <span className="flex items-center justify-center w-16 h-16 rounded-full bg-[#F0FDF4]">
                    <svg width="30" height="21" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M7 16a4 4 0 01-.88-7.9A5.5 5.5 0 0117.5 9H18a3.5 3.5 0 010 7h-1M12 12v9m0-9l-3 3m3-3l3 3" />
                    </svg>
                  </span>
                  <h3 className="text-base font-semibold text-[#1F2937]">Drag & drop your CSV here</h3>
                  <p className="max-w-[340px] text-center text-sm text-[#6B7280]">
                    Importing <b>{importLevel === "barangay" ? "barangay" : "municipality"}</b> yields.
                    Columns:{" "}
                    <span className="font-mono text-xs">
                      {importLevel === "barangay"
                        ? "municipality, barangay, year, season, yield"
                        : "municipality, year, season, yield"}
                    </span>
                  </p>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="px-6 py-2 rounded-lg bg-[#1F6306] text-white text-sm font-medium shadow-sm hover:bg-[#286A11]"
                  >
                    Choose File
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,text/csv"
                    className="hidden"
                    onChange={(e) => ingestFile(e.target.files?.[0])}
                  />
                </div>

                {/* Import status / result */}
                {importing && (
                  <div className="flex items-center gap-2 text-sm text-[#6B7280]">
                    <span className="inline-flex h-4 w-4 rounded-full border-2 border-transparent border-t-[#1F6306] border-r-[#1F6306] animate-spin" />
                    Importing…
                  </div>
                )}
                {importResult?.error && (
                  <div className="rounded-lg bg-[#FEF2F2] border border-[#FECACA] px-4 py-3 text-sm text-[#B91C1C]">
                    {importResult.error}
                  </div>
                )}
                {importResult && !importResult.error && (
                  <div className="rounded-lg bg-[#F0FDF4] border border-[#BBF7D0] px-4 py-3 text-sm text-[#166534] flex flex-col gap-1">
                    <span>
                      <b>{importResult.inserted}</b> new, <b>{importResult.updated}</b> updated
                      {importResult.skipped ? (
                        <>
                          , <b>{importResult.skipped}</b> skipped
                        </>
                      ) : null}
                      .
                    </span>
                    {importResult.errors?.length > 0 && (
                      <details>
                        <summary className="cursor-pointer text-[#B45309]">
                          {importResult.skipped} row(s) skipped — see why
                        </summary>
                        <ul className="mt-1 list-disc pl-5 max-h-32 overflow-y-auto text-[#92400E]">
                          {importResult.errors.map((e, i) => (
                            <li key={i}>
                              Row {e.row}: {e.error}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                )}
              </div>

              {/* Report Preview Chart */}
              <div className="bg-white border border-[#F3F4F6] shadow-sm rounded-xl p-6 flex flex-col gap-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-lg font-bold text-[#1F2937]">Report Preview</h2>
                    <p className="text-xs text-[#6B7280]">{scopeTitle}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium uppercase text-[#9CA3AF]">Group by</span>
                    <select
                      value={chartGroupBy}
                      onChange={(e) => setChartGroupBy(e.target.value)}
                      className="px-2 py-1 text-xs text-[#4B5563] bg-white border border-[#E5E7EB] rounded-lg outline-none"
                    >
                      <option value="area">{areaColLabel}</option>
                      <option value="year">Year</option>
                    </select>
                  </div>
                </div>
                {/* Many categories (e.g. 29 cities) can't fit legibly on a phone —
                    let the chart scroll horizontally with room per bar. It still fits
                    without scrolling on wider screens and when grouped by Year. */}
                <div className="w-full overflow-x-auto">
                  <div
                    className="h-72"
                    style={{ width: "100%", minWidth: chartData.length > 12 ? `${chartData.length * 30}px` : "100%" }}
                  >
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={chartData}
                      margin={{ top: 8, right: 8, left: 6, bottom: chartData.length > 10 ? 64 : 8 }}
                      barCategoryGap="20%"
                    >
                      <CartesianGrid stroke="#F3F4F6" vertical={false} strokeDasharray="4 4" />
                      <XAxis
                        dataKey="key"
                        tick={{ fontSize: 11, fill: "#6B7280" }}
                        axisLine={{ stroke: "#E5E7EB" }}
                        tickLine={false}
                        interval={0}
                        angle={chartData.length > 10 ? -45 : 0}
                        textAnchor={chartData.length > 10 ? "end" : "middle"}
                        height={chartData.length > 10 ? 70 : 30}
                      />
                      <YAxis
                        tick={{ fontSize: 11, fill: "#9CA3AF" }}
                        axisLine={false}
                        tickLine={false}
                        width={52}
                        tickFormatter={(v) => `${v} mt/ha`}
                      />
                      <Tooltip
                        cursor={{ fill: "#F0FDF4" }}
                        contentStyle={{ borderRadius: 8, border: "1px solid #E5E7EB", fontSize: 13 }}
                        formatter={(v) => [`${v} mt/ha`, "Avg yield"]}
                      />
                      <Bar dataKey="yield" radius={[4, 4, 0, 0]}>
                        {(() => {
                          const vals = chartData.map((d) => d.yield);
                          const lo = vals.length ? Math.min(...vals) : 0;
                          const hi = vals.length ? Math.max(...vals) : 1;
                          return chartData.map((d, i) => <Cell key={i} fill={rampColor(d.yield, lo, hi)} />);
                        })()}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Detailed Records Table */}
              <div className="bg-white border border-[#F3F4F6] shadow-sm rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-[#F3F4F6]">
                  <div>
                    <h2 className="text-lg font-bold text-[#1F2937]">Detailed Records</h2>
                    <p className="text-xs text-[#6B7280]">
                      {scopeTitle} · {filtered.length} record(s) match current filters
                    </p>
                  </div>
                </div>
                <div className="max-h-[260px] overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-[#F9FAFB] sticky top-0">
                      <tr>
                        {[areaColLabel, "Year", "Season", "Yield (MT/ha)", "Status"].map((h) => (
                          <th key={h} className="px-6 py-3 text-left text-xs font-semibold tracking-wide uppercase text-[#6B7280]">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((r, i) => (
                        <tr key={i} className="border-t border-[#F3F4F6]">
                          <td className="px-6 py-3 font-medium text-[#1F2937]">{r.name}</td>
                          <td className="px-6 py-3 text-[#4B5563]">{r.year}</td>
                          <td className="px-6 py-3 text-[#4B5563]">{r.season}</td>
                          <td className="px-6 py-3 font-semibold text-[#1F2937]">{r.yield.toFixed(1)}</td>
                          <td className="px-6 py-3">
                            <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[r.status] || "bg-[#F3F4F6] text-[#4B5563]"}`}>
                              {r.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                      {!filtered.length && (
                        <tr>
                          <td colSpan={5} className="px-6 py-8 text-center text-sm text-[#9CA3AF]">
                            {loading || scopeLoading
                              ? "Loading records…"
                              : "No records match the current filters."}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Right Column — Report Settings */}
            <div className="bg-white border border-[#F3F4F6] shadow-sm rounded-xl p-6 flex flex-col gap-6 h-fit">
              <h2 className="text-xl font-bold text-[#1F2937]">Report Settings</h2>

              {/* Scope — drives the preview, records and export together */}
              <div className="flex flex-col gap-3">
                <h3 className="text-xs font-semibold tracking-wide uppercase text-[#9CA3AF]">Scope</h3>
                <div className="flex p-1 gap-1 bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg">
                  {[
                    { key: "municipality", label: "Municipality" },
                    { key: "barangay", label: "Barangay" },
                  ].map((l) => (
                    <button
                      key={l.key}
                      type="button"
                      onClick={() => {
                        setViewLevel(l.key);
                        setChartGroupBy("area");
                      }}
                      className={`flex-1 py-1.5 rounded-md text-xs font-medium transition-colors ${
                        viewLevel === l.key ? "bg-white text-[#1F6306] shadow-sm" : "text-[#6B7280]"
                      }`}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
                {viewLevel === "municipality" ? (
                  <select
                    value={viewMuni}
                    onChange={(e) => setViewMuni(e.target.value)}
                    className="px-3 py-2 text-sm text-[#1F2937] bg-white border border-[#E5E7EB] rounded-lg outline-none"
                  >
                    <option value="">All municipalities</option>
                    {muniOptions.map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                ) : barangayMunis.length ? (
                  <select
                    value={viewBrgyMuni ?? ""}
                    onChange={(e) => setViewBrgyMuni(Number(e.target.value))}
                    className="px-3 py-2 text-sm text-[#1F2937] bg-white border border-[#E5E7EB] rounded-lg outline-none"
                  >
                    {barangayMunis.map((m) => (
                      <option key={m.municipality_id} value={m.municipality_id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="text-xs text-[#9CA3AF]">No municipalities have barangay yield data yet.</p>
                )}
              </div>

              {/* Report Type */}
              <div className="flex flex-col gap-3">
                <h3 className="text-xs font-semibold tracking-wide uppercase text-[#9CA3AF]">Report Type</h3>
                <div className="flex flex-col gap-3">
                  {REPORT_TYPES.map((t) => (
                    <label key={t.key} className="flex items-center gap-3 text-sm font-medium text-[#4B5563] cursor-pointer">
                      <input
                        type="radio"
                        name="reportType"
                        value={t.key}
                        checked={reportType === t.key}
                        onChange={() => setReportType(t.key)}
                        className="w-4 h-4 accent-[#1F6306]"
                      />
                      {t.label}
                    </label>
                  ))}
                </div>
              </div>

              {/* Filters */}
              <div className="flex flex-col gap-4 pt-2">
                <h3 className="text-xs font-semibold tracking-wide uppercase text-[#9CA3AF]">Parameters</h3>

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-[#6B7280]">Time Period</label>
                  <div className="flex gap-2">
                    <select
                      value={fromYear ?? ""}
                      onChange={(e) => setFromYear(Number(e.target.value))}
                      className="flex-1 px-3 py-2 text-sm text-[#1F2937] bg-white border border-[#E5E7EB] rounded-lg outline-none"
                    >
                      {yearOptions.map((y) => (
                        <option key={y} value={y}>
                          From: {y}
                        </option>
                      ))}
                    </select>
                    <select
                      value={toYear ?? ""}
                      onChange={(e) => setToYear(Number(e.target.value))}
                      className="flex-1 px-3 py-2 text-sm text-[#1F2937] bg-white border border-[#E5E7EB] rounded-lg outline-none"
                    >
                      {yearOptions.map((y) => (
                        <option key={y} value={y}>
                          To: {y}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-[#6B7280]">Season</label>
                  <div className="flex p-1 gap-1 bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg">
                    {SEASONS.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setSeason(s)}
                        className={`flex-1 py-1.5 rounded-md text-xs font-medium transition-colors ${
                          season === s ? "bg-white text-[#1F6306] shadow-sm" : "text-[#6B7280]"
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Export */}
              <div className="flex flex-col gap-4 pt-4 border-t border-[#F3F4F6]">
                <h3 className="text-xs font-semibold tracking-wide uppercase text-[#9CA3AF]">Generate & Export</h3>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { key: "pdf", label: "PDF", color: "#EF4444" },
                    { key: "excel", label: "Excel", color: "#1F6306" },
                    { key: "csv", label: "CSV", color: "#6B7280" },
                  ].map((f) => (
                    <button
                      key={f.key}
                      type="button"
                      onClick={() => setExportFormat(f.key)}
                      className={`flex flex-col items-center gap-2 py-3 rounded-xl border text-xs font-bold uppercase transition-colors ${
                        exportFormat === f.key ? "border-[#1F6306] bg-[#F0FDF4]" : "border-[#E5E7EB]"
                      }`}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={f.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M6 2h9l5 5v15H6V2z" />
                        <path d="M15 2v5h5" />
                      </svg>
                      <span style={{ color: f.color }}>{f.label}</span>
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={handleGenerate}
                  className="flex items-center justify-center gap-2 py-3 rounded-xl bg-[#1F6306] text-white font-bold shadow-md hover:bg-[#286A11] transition-colors"
                >
                  <svg width="17" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 3v12m0 0l-4-4m4 4l4-4M4 19h16" />
                  </svg>
                  Generate Report
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, caption, captionColor, iconBg, iconColor }) {
  return (
    <div className="flex items-start justify-between p-5 bg-white border border-[#F3F4F6] shadow-sm rounded-xl">
      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-medium text-[#6B7280]">{label}</h3>
        <span className="text-[28px] leading-9 font-bold text-[#1F2937]">{value}</span>
        <p className={`text-xs ${captionColor}`}>{caption}</p>
      </div>
      <span className={`flex items-center justify-center w-10 h-10 rounded-lg shrink-0 ${iconBg}`}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={iconColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 12h4l3 8 4-16 3 8h4" />
        </svg>
      </span>
    </div>
  );
}
