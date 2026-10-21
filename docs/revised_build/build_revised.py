# -*- coding: utf-8 -*-
"""Build docs/AgriKA-GIS_Full_Thesis_Ch1-5_revised.html from the original (original is not modified)."""
import html as H
import re
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import rev_ch3_text as T

SRC = r"C:\Projects\PWW\agrika-gis\docs\AgriKA-GIS_Full_Thesis_Ch1-5.html"
OUT = r"C:\Projects\PWW\agrika-gis\docs\AgriKA-GIS_Full_Thesis_Ch1-5_revised.html"
s = open(SRC, encoding="utf-8").read()


def once(sub, where=None):
    n = s.count(sub)
    if n != 1:
        raise SystemExit(f"anchor found {n} times: {sub[:90]!r}")
    return s.index(sub)


def replace_once(old, new):
    global s
    once(old)
    s = s.replace(old, new)


def para_bounds(snippet):
    i = once(snippet)
    a = s.rfind("<p", 0, i)
    b = s.index("</p>", i) + 4
    return a, b


def replace_para(snippet, new_html):
    global s
    a, b = para_bounds(snippet)
    s = s[:a] + new_html + s[b:]


def replace_region(start_anchor, end_anchor, new_html):
    """Replace from start_anchor (inclusive) up to end_anchor (exclusive)."""
    global s
    a = once(start_anchor)
    b = s.index(end_anchor, a)
    s = s[:a] + new_html + s[b:]


def B(rid, h):
    """Mark a changed block with the green side bar; rid is the jump-link target."""
    return f'<div class="rev" id="{rid}">{h}</div>' if rid else f'<div class="rev">{h}</div>'


def S(rid, t):
    """Mark a changed sentence with the green highlight."""
    return f'<span class="revs" id="{rid}">{t}</span>' if rid else f'<span class="revs">{t}</span>'


# ---------------------------------------------------------------- 1. clean revision marks
s = re.sub(r'<div class="revbanner">.*?</div>', "", s, flags=re.S)
s = re.sub(r'<span class="revs"[^>]*>(.*?)</span>', r"\1", s, flags=re.S)
# unwrap <div class="rev" ...> ... </div> (nested divs counted)
out, pos = [], 0
for m in re.finditer(r'<div class="rev"[^>]*>', s):
    if m.start() < pos:
        continue
    depth, j = 1, m.end()
    while depth:
        nxt_open = s.find("<div", j)
        nxt_close = s.find("</div>", j)
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            j = nxt_open + 4
        else:
            depth -= 1
            j = nxt_close + 6
    out.append(s[pos:m.start()])
    out.append(s[m.end():j - 6])
    pos = j
out.append(s[pos:])
s = "".join(out)

# ---------------------------------------------------------------- 2. Chapter 1
replace_once(
    "From these satellite images, vegetation indices such as the Normalized Difference Vegetation Index (NDVI), Enhanced Vegetation Index (EVI), and Green Ratio are extracted because these indicators have been widely used in previous studies to describe vegetation health and crop vigor.",
    S("r21-framework", "From these images, three vegetation indices are computed, the Normalized Difference Vegetation Index (NDVI), the Enhanced Vegetation Index (EVI), and the Normalized Difference Water Index (NDWI), because these indicators have been widely used in previous studies to describe vegetation health, crop vigor, and surface water."))
replace_once(
    "Sentinel-1 provides soil moisture indicators that complement the vegetation indices by capturing information related to ground conditions regardless of weather conditions.",
    S(None, "Sentinel-1 provides VV and VH backscatter, which describes crop structure and surface moisture and complements the vegetation indices because it is available regardless of cloud cover."))
replace_once("satellite imagery is processed to derive vegetation indices and soil moisture indicators",
             S(None, "satellite imagery is processed to derive vegetation indices and radar backscatter values"))
replace_once(
    "Within the model, the CNN extracts spatial characteristics from the satellite-derived features, while the LSTM network captures temporal relationships among historical rice yield records and weather variables.",
    S(None, "Within the model, the convolutional layers learn short-term patterns across the monthly sequence of satellite and weather features, while the LSTM layers capture how these conditions develop over the cropping season."))
replace_once("By incorporating Sentinel-1 soil moisture indicators alongside", S(None, "By incorporating Sentinel-1 backscatter alongside"))
replace_once("namely functional suitability, usability, performance efficiency, and reliability.",
             S(None, "namely functional suitability, performance efficiency, usability, reliability, security, and maintainability."))
replace_once("City Agriculturists and Rice Technicians from the participating Local Government Units will serve as respondents to determine",
             S(None, "Agricultural personnel of the participating LGU agriculture offices serve as respondents to determine"))

# Rationale: institutional mission (Mapua MCL Student Handbook AY 2025-2026)
a, b = para_bounds("Beyond its immediate operational benefits, this study is aligned with several Sustainable Development Goals")
s = s[:b] + B("r21-rationale", "<p>The study is also aligned with the mission of Mapúa Malayan Colleges Laguna, which commits the institution to help solve "
             "industry's and society's problems by the expert application of existing knowledge (Mapúa Malayan Colleges Laguna, 2025). "
             "AgriKA-GIS applies remote sensing, machine learning, and geospatial technology to a problem faced by the agriculture offices of "
             "Laguna, the province in which the institution is located, and in doing so reflects its motto of Excellence and Virtue: the "
             "pursuit of technical excellence in service of the local community.</p>") + s[b:]

# Scope: the model learns from all municipalities
replace_once("Laguna also represents an appropriate study area because of its significant contribution to regional rice production and its continuing transition toward increasingly urbanized agricultural landscapes.",
             S("r21-scope", "Laguna also represents an appropriate study area because of its significant contribution to regional rice production and its continuing transition toward increasingly urbanized agricultural landscapes. The prediction model itself is trained on the seasonal yield records of all rice-producing cities and municipalities of Laguna, so that it learns from enough seasons; barangay-level outputs are limited to the four selected cities."))
replace_once("whose start times may be delayed by several minutes and which",
             S("r21-delim", "whose start times may be delayed, by as much as a few hours in the runs recorded, and which"))

# ---------------------------------------------------------------- 3. Chapter 2 synthesis for 2.3
i = once('<div class="chapdiv" id="ch3">')
s = s[:i] + B("r21-synthesis", T.SYNTH_23) + s[i:]

# ---------------------------------------------------------------- 4. Chapter 3 methodology
replace_region('<h2 id="research-design">', '<p>Figure 2 presents the research design', B("r21-design", T.DESIGN))
a = once('<p>Figure 2 presents the research design')
b = s.index('<p class="cap">Figure 2.', a)
s = s[:a] + B("r21-design-fig", s[a:b]) + s[b:]
a, b = para_bounds("Collectively, these research sites provided the necessary operational environment")
s = s[:b] + B("r21-locale", T.LOCALE_ADD) + s[b:]
replace_region("<h2>Population of the Study</h2>", '<h3 id="data-gathering-tools">', B("r21-population", T.POPULATION))
replace_region('<h3 id="data-gathering-tools">', "<p>Figure 3 summarizes the workflow", B("r21-tools", T.TOOLS_AND_PROCEDURE))
replace_region("<h3>Image Pre-processing</h3>", "<h4>Data Collection</h4>", B("r21-model", T.MODEL))
# feature engineering: heading + paragraph, keep Figure 6 that follows
a = once("<h4>Feature Engineering and Data Preparation</h4>")
b = s.index("</p>", a) + 4
s = s[:a] + B("r21-features", T.FEATURE_ENG) + s[b:]
replace_region("<h4>CNN-LSTM Architecture</h4>", '<h1 id="data-analysis">', B("r21-training", T.ARCH_TO_ANALYSIS))
for k, (snip, new) in enumerate(T.ANALYSIS):
    rid = {0: "r21-analysis", 3: "r21-ncai", 7: "r21-paired", 9: "r21-uat-analysis", 15: "r21-pipeline-analysis"}.get(k)
    replace_para(snip, B(rid, new))
# Chapter 3 table captions: metrics 4 -> 5, interpretation 5 -> 6, summary 6 -> 7
replace_once('<p class="tcap"><b>Table 4</b></p><p>Model Evaluation Metrics', '<p class="tcap"><b>Table 5</b></p><p>Model Evaluation Metrics')
replace_once('<h3 id="table-6">Table 6</h3>', '<h3 id="table-7">Table 7</h3>')
replace_once('<h3 id="table-5">Table 5</h3>', '<h3 id="table-6">Table 6</h3>')
for k, (snip, new) in enumerate(T.SOFTWARE):
    rid = {1: "r21-agile", 10: "r21-security"}.get(k)
    replace_para(snip, B(rid, new))

# Data Flow Design: mark the redrawn DFD section (text and Figures 9 and 10 come from the original)
a = once('<h1 id="data-flow-design">Data Flow Design</h1>') + len('<h1 id="data-flow-design">Data Flow Design</h1>')
b = s.index('<h1 id="database-design">', a)
s = s[:a] + B("r21-dfd", s[a:b]) + s[b:]

# Module 6 roles (Major System Modules) and End Users
replace_once("Users are assigned one of three roles, administrator, agriculturist, rice technician, or guest, and access",
             S("r21-module6", "Users are assigned one of three roles, Administrator, Agriculturist, or Rice Technician, while visitors who are not signed in can view only the home pages and the public map; access"))
replace_once("AgriKA-GIS is designed to support three categories of users with varying levels of system access.",
             S("r21-endusers", "AgriKA-GIS is designed to support three categories of signed-in users with varying levels of system access, in addition to public visitors who can view the home pages and the public map without signing in."))
replace_once("The system is designed for three primary user groups: Administrator, Agriculturists, and Rice Technicians,",
             S("r21-userprofile", "The system is designed for three signed-in user groups, Administrator, Agriculturists, and Rice Technicians, and for Public Visitors who do not sign in,"))
a, b = para_bounds("Their core operational responsibilities include encoding and submitting barangay yield reports")
s = s[:b] + B(None, "<p>4. Public Visitors: Members of the public who do not sign in. As shown in Figure 12, they can view the home and system information "
             "pages and the public yield map, but cannot open the portal modules or change any record.</p>") + s[b:]
replace_once("Users are assigned one of three roles, Administrator, City Agriculturist, or Rice Technician with access",
             S(None, "Users are assigned one of three roles, Administrator, Agriculturist, or Rice Technician, with access"))

# Database design: entities that match the ERD (Figure 11)
a = once("<li><b>Yield Records, Predictions, and Residuals</b>")
b = s.index("</li>", a) + 5
s = s[:a] + ('<li id="r21-database"><span class="revs">' "<b>Barangay Predictions</b>: the CNN-LSTM predicted yield per barangay per season, from which the residual (observed minus "
             "predicted) is computed when an observed barangay yield exists.</span></li>") + s[b:]
a = once("<li><b>Satellite Monthly</b>")
b = s.index("</li>", a) + 5
s = s[:b] + ('<li><span class="revs">' "<b>Weather Monthly Barangay</b> and <b>Satellite Monthly Barangay</b>: the same monthly features for each barangay with a "
             "reported yield.</span></li></ul><p><b>Audit records (not shown in Figure 11).</b></p><ul>"
             "<li><b>Pipeline Runs</b>: one record per pipeline run with its trigger, start and end time, stage outcomes, records added and "
             "refreshed, and integrity violations.</li>"
             "<li><b>Yield Import Log</b>: one record per upload of yield records, with the uploading account, its role and assigned city, "
             "and the number of rows inserted, updated, and skipped.</li>") + s[b:]
replace_once("<p><b>Public inquiries.</b></p>", "<p><b>Public inquiries (not shown in Figure 11).</b></p>")

# ---------------------------------------------------------------- 5. Chapter 4 deviation section
a = once("<h3>Deviation from the Stated Methodology</h3>")
b = s.index('<div class="chapdiv"', a)
s = s[:a] + B("r21-changes", T.DEVIATION) + s[b:]

# ---------------------------------------------------------------- 6. renumber tables from Chapter 4 on
MAP = {"X5": "19", "19": "20", "20": "21", "21": "22", "22": "23", "23": "24", "24": "25", "30": "26", "25": "27",
       "31": "28", "28": "29", "29": "30", "26": "31", "X1": "32", "X2": "33", "X3": "34", "27": "35"}
ch4 = once('<div class="chapdiv" id="ch4">')
body = s[ch4:]
tok = r"(?:\d+|X\d+)"


def fix(m):
    nums = re.sub(tok, lambda t: MAP.get(t.group(0), t.group(0)), m.group(2))
    return m.group(1) + nums


body = re.sub(r"(\bTables?\s+)(" + tok + r"(?:\s*(?:,|and|to|–|-)\s*" + tok + r")*)", fix, body)
s = s[:ch4] + body

# ---------------------------------------------------------------- 7. rebuild List of Tables
caps = []
for m in re.finditer(r'<h3[^>]*>Table (\d+)</h3>\s*<(?:h3|p)[^>]*>(.*?)</(?:h3|p)>', s):
    caps.append((int(m.group(1)), m.start(), H.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()))
for m in re.finditer(r'<p class="tcap"[^>]*><b>Table (\d+)</b>(.*?)</p>(\s*<p[^>]*>(.*?)</p>)?', s, re.S):
    title = H.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip() or H.unescape(re.sub(r"<[^>]+>", "", m.group(4) or "")).strip()
    caps.append((int(m.group(1)), m.start(), title))
caps.sort(key=lambda c: c[1])
nums = [c[0] for c in caps]
assert nums == list(range(1, len(nums) + 1)), nums
rows = "".join(f'<div class="fmrow"><span class="fmk">Table {n}</span><span class="fmd">{H.escape(t)}</span></div>' for n, _, t in caps)
a = once('<section class="fm" id="fm-lot">') if '<section class="fm" id="fm-lot">' in s else None
if a is None:
    hi = once(">List of Tables</h1>")
    a = s.rfind("<section", 0, hi)
hend = s.index("</h1>", a) + 5
send = s.index("</section>", a)
s = s[:hend] + rows + s[send:]

# ---------------------------------------------------------------- 7b. Figure X -> Figure 28 (+ List of Figures)
assert s.count("Figure X") == 2
s = s.replace("Figure X.", '<span class="revs" id="r21-fig28">Figure 28.</span>', 1).replace("Figure X", "Figure 28")
lof = once('id="fm-lof"')
k = s.index('<span class="fmk">Figure 27</span>', lof)
k = s.index("</div>", k) + 6
s = s[:k] + '<div class="fmrow"><span class="fmk">Figure 28</span><span class="fmd">Weekly Scheduled Run of the Data Pipeline</span></div>' + s[k:]

# ---------------------------------------------------------------- 8. reference entry
a, b = para_bounds("Mabalay, M. R., Raviz, J.")
s = s[:b] + ('<p id="r21-reference"><span class="revs">' "Mapúa Malayan Colleges Laguna. (2025). <i>Student handbook, academic year 2025–2026</i>. "
             "https://mcl.edu.ph/wp-content/uploads/2026/02/Mapua-MCL-Student-Handbook-AY-2025-2026.pdf</span></p>") + s[b:]

# ---------------------------------------------------------------- 9. summary box at the top, with jump links
LINKS = [
    ("Chapter 1", [("r21-rationale", "Rationale: new paragraph on the Mapúa MCL mission and motto (rubric: values of the institution)"),
                   ("r21-scope", "Scope: the model is trained on all rice-producing municipalities of Laguna"),
                   ("r21-delim", "Delimitations: the scheduled run can start a few hours late"),
                   ("r21-framework", "Conceptual Framework: real inputs (NDVI, EVI, NDWI; Sentinel-1 VV/VH), six UAT characteristics")]),
    ("Chapter 2", [("r21-synthesis", "New Synthesis for section 2.3 (models)")]),
    ("Chapter 3 (rewritten in past tense: what was actually done)", [
        ("r21-design", "Research Design"),
        ("r21-design-fig", "Research Design figure (Figure 2): same eight phases, activities updated to match the system"),
        ("r21-locale", "Research Locale: UAT extended to Victoria, Nagcarlan, and Calauan"),
        ("r21-population", "Population and Sampling: 26 identified, 19 respondents from eight offices"),
        ("r21-tools", "Data Gathering Tools and Procedure: monthly satellite statistics instead of growth-stage images"),
        ("r21-model", "Model development: actual configuration (Table 3), feature ablation, data dictionary (Table 4)"),
        ("r21-features", "Feature Engineering: six-month seasons, fold-wise standardization"),
        ("r21-training", "Model training: leave-one-year-out validation; Phases 4 and 5"),
        ("r21-analysis", "Data Analysis (past tense)"),
        ("r21-ncai", "NCAI formulas written out"),
        ("r21-paired", "Paired statistical analysis (Wilcoxon, t-test, Cohen's d)"),
        ("r21-uat-analysis", "UAT analysis and the weighted-mean formula"),
        ("r21-pipeline-analysis", "Pipeline evaluation (past tense)"),
        ("r21-agile", "Software Development Life Cycle: the two iterations"),
        ("r21-module6", "Major System Modules, Module 6: roles corrected, public visitors"),
        ("r21-endusers", "End Users: public visitors added"),
        ("r21-dfd", "Data Flow Diagram redrawn: Context Diagram (Figure 9) and Level 1 diagram (Figure 10), with a description of each process; later figures renumbered"),
        ("r21-database", "Database Design: entities now match the ERD, audit tables added"),
        ("r21-userprofile", "User Profile: four user types (Public Visitor added)"),
        ("r21-security", "Security Design (past tense)")]),
    ("Chapter 4", [("r21-changes", "\"Deviation from the Stated Methodology\" is now \"Changes from the Approved Proposal\" (seven changes with reasons)"),
                   ("r21-fig28", "Figure X is now Figure 28")]),
    ("Whole paper", [("fm-lot", "Tables renumbered 1 to 35 in order of appearance; all references and the List of Tables updated"),
                     ("r21-reference", "References: Mapúa MCL Student Handbook added")]),
]
for _, items in LINKS:
    for rid, _ in items:
        assert f'id="{rid}"' in s, rid
groups = "".join(
    f"<p style=\"margin:8px 0 2px\"><b>{H.escape(g)}</b></p><ul style=\"margin:0 0 4px 18px;padding:0\">"
    + "".join(f'<li><a href="#{rid}">{H.escape(t)}</a></li>' for rid, t in items) + "</ul>"
    for g, items in LINKS)
banner = ('<div class="revbanner"><b>Revised copy, October 21, 2026.</b> This copy fixes the items found when the paper was checked '
          'against the CCIS defense rubric. Changed text has a green bar on the left or a green highlight. Click a line to jump to it. '
          'The original file, AgriKA-GIS_Full_Thesis_Ch1-5.html, is unchanged.' + groups + "</div>")
k = once("<div id='page'>") + len("<div id='page'>")
s = s[:k] + banner + s[k:]

open(OUT, "w", encoding="utf-8").write(s)
print("written", OUT, len(s))
print("tables:", len(caps))
