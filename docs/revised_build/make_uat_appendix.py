"""Build docs/UAT_Appendix_Draft.html: paste-ready appendix pages for the UAT and
functional testing evidence (Appendices MM to SS, after the existing A to LL).

Data sources (copied here on 2026-10-21):
  - "UAT Results" Google Sheet (id 1wiZOrTkhgtQYMS-2EcoAHe4sri_6RhLZY4ae_csdjHk),
    sheet "Raw Responses", R01 to R19
  - "AgriKA-GIS - User Acceptance Testing (UAT) Form" Google Doc
    (id 1Q_0vCINPGu_10nN6o3N7olck9g1ZOajgNaju3wMuinw)
  - docs/Functional_Test_Tracker.xlsx

Every statistic is recomputed from the raw responses and checked against the
values already reported in Chapter 4 (Tables 29 and 30) before the file is written.

    python docs/revised_build/make_uat_appendix.py
"""
import os
import statistics as st
from html import escape

OUT = os.path.join(os.path.dirname(__file__), "..", "UAT_Appendix_Draft.html")

ITEMS = [
    ("FS1", "Functional Suitability", "The system correctly displays rice yield data and rankings for the year and season I select."),
    ("FS2", "Functional Suitability", "The map accurately shows Laguna municipalities and drills down to the barangays."),
    ("FS3", "Functional Suitability", "The system produces the reports and data exports I need for my work."),
    ("PE1", "Performance Efficiency", "Pages and maps load within an acceptable amount of time."),
    ("PE2", "Performance Efficiency", "The system responds quickly when I change filters or move between modules."),
    ("US1", "Usability", "The system is easy to navigate and understand."),
    ("US2", "Usability", "Labels, menus, maps, and legends are clear and readable."),
    ("US3", "Usability", "I can complete my tasks with little or no assistance."),
    ("RE1", "Reliability", "The system works consistently without crashing or showing errors."),
    ("RE2", "Reliability", "My session and data are restored correctly after I refresh or log in again."),
    ("SE1", "Security", "The system requires proper login and limits what I can access based on my role."),
    ("SE2", "Security", "I am confident that the system keeps its data and user access secure."),
    ("MA1", "Maintainability", "Yield records and data can be updated or imported without difficulty."),
    ("MA2", "Maintainability", "Keeping the system current with new data seems manageable."),
]
CHAR_DESC = {
    "Functional Suitability": "the system does what it is supposed to do",
    "Performance Efficiency": "the system responds within a reasonable time",
    "Usability": "the system is easy to learn and use",
    "Reliability": "the system works consistently",
    "Security": "access and data are protected",
    "Maintainability": "the system is easy to keep up to date",
}
CHARS = list(CHAR_DESC)

# Raw Responses sheet, columns FS1..MA2
RAW = [
    ("R01", "Biñan", "44444444444444"),
    ("R02", "Santa Rosa", "44444444444444"),
    ("R03", "Santa Rosa", "44444444444444"),
    ("R04", "Santa Rosa", "44444444444444"),
    ("R05", "Santa Rosa", "44444444444444"),
    ("R06", "Calamba", "34444444444444"),
    ("R07", "Calamba", "34444444444444"),
    ("R08", "Calamba", "44444444444443"),
    ("R09", "Victoria", "44444444444444"),
    ("R10", "Santa Cruz Provincial", "44333444334444"),
    ("R11", "Nagcarlan", "34344343443343"),
    ("R12", "Santa Cruz Provincial", "33333334443443"),
    ("R13", "Santa Cruz Provincial", "44444444444444"),
    ("R14", "Nagcarlan", "44444444444444"),
    ("R15", "Nagcarlan", "44444443444444"),
    ("R16", "Calauan", "44344444444444"),
    ("R17", "Santa Cruz Provincial", "33433333333333"),
    ("R18", "Santa Cruz Provincial", "44444444444444"),
    ("R19", "Cabuyao", "44443444444444"),
]
RESP = [(r, o, [int(c) for c in s]) for r, o, s in RAW]
assert all(len(v) == 14 for _, _, v in RESP)

OFFICE_NAME = {
    "Biñan": "City Agriculture Office of Biñan",
    "Santa Rosa": "City Agriculture Office of Santa Rosa",
    "Calamba": "City Agriculture Office of Calamba",
    "Cabuyao": "City Agriculture Office of Cabuyao",
    "Victoria": "Municipal Agriculture Office of Victoria",
    "Nagcarlan": "Municipal Agriculture Office of Nagcarlan",
    "Calauan": "Municipal Agriculture Office of Calauan",
    "Santa Cruz Provincial": "Provincial Agriculture Office, Santa Cruz",
}
OFFICES = list(OFFICE_NAME)


def interp(m):
    if m >= 3.26:
        return "Strongly Agree"
    if m >= 2.51:
        return "Agree"
    if m >= 1.76:
        return "Disagree"
    return "Strongly Disagree"


def summarize(values):
    n = len(values)
    f = {k: values.count(k) for k in (4, 3, 2, 1)}
    return n, f, st.mean(values), st.stdev(values)


# ---- statistics ---------------------------------------------------------
item_rows = []
for j, (code, char, text) in enumerate(ITEMS):
    vals = [v[j] for _, _, v in RESP]
    item_rows.append((code, char, text) + summarize(vals) + (st.variance(vals),))

char_rows = []
for c in CHARS:
    idx = [j for j, it in enumerate(ITEMS) if it[1] == c]
    vals = [v[j] for _, _, v in RESP for j in idx]
    char_rows.append((c, len(idx)) + summarize(vals))
all_vals = [x for _, _, v in RESP for x in v]
overall = ("Overall", 14) + summarize(all_vals)

office_rows = []
for o in OFFICES:
    vals = [x for _, oo, v in RESP if oo == o for x in v]
    office_rows.append((o, sum(1 for _, oo, _ in RESP if oo == o), st.mean(vals)))
assert sum(r[1] for r in office_rows) == 19

totals = [sum(v) for _, _, v in RESP]
k = 14
sum_item_var = sum(r[-1] for r in item_rows)
var_total = st.variance(totals)
alpha = k / (k - 1) * (1 - sum_item_var / var_total)

# checks against Chapter 4 Tables 29 and 30 (revised copy)
REPORTED = {"Functional Suitability": (80.7, 3.81, 0.40), "Performance Efficiency": (81.6, 3.82, 0.39),
            "Usability": (86.0, 3.86, 0.35), "Reliability": (89.5, 3.89, 0.31),
            "Security": (86.8, 3.87, 0.34), "Maintainability": (86.8, 3.87, 0.34),
            "Overall": (85.0, 3.85, 0.36)}
for name, nitems, n, f, m, sd in char_rows + [overall]:
    pct, rm, rsd = REPORTED[name]
    assert round(100 * f[4] / n, 1) == pct and round(m, 2) == rm and round(sd, 2) == rsd, name
assert round(sum_item_var, 3) == 1.842 and round(var_total, 3) == 13.655 and round(alpha, 3) == 0.932

# ---- functional testing (docs/Functional_Test_Tracker.xlsx) --------------
FT = [("Modules 1 and 2, Home and Monitoring", "Table 22", 11, 11),
      ("Module 3, Spatial GIS", "Table 23", 13, 13),
      ("Modules 4 and 5, Analytics and Reports", "Table 24", 11, 11),
      ("Module 6 and Access Control", "Table 25", 12, 12)]
assert sum(r[2] for r in FT) == 47

# ---- html ---------------------------------------------------------------
CSS = """
body{font-family:Georgia,'Times New Roman',serif;line-height:1.55;color:#1a202c;max-width:900px;margin:32px auto;padding:0 24px}
h1{font-size:24px;border-bottom:2px solid #d7dde3;padding-bottom:6px}
h2{font-size:19px;margin-top:44px;color:#20344a;text-align:center}
h2 small{display:block;font-size:16px;font-weight:normal;margin-top:2px}
h3{font-size:15px;color:#20344a;margin-top:22px}
p{text-align:justify;margin:0 0 12px}
table{border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:12px;margin:8px 0}
th,td{border:1px solid #c9d1d9;padding:5px 7px;vertical-align:top;text-align:left}
th{background:#eef2f6}
td.c,th.c{text-align:center}
.tcap{text-align:left;margin:16px 0 0}
.note{font-size:12.5px}
.where{font-family:Arial,sans-serif;font-size:13px;background:#e8f0fb;border-left:4px solid #2f5597;padding:8px 12px;margin:22px 0 12px}
.todo{background:#fff3cd;border:1px solid #e0b100;padding:8px 10px;font-family:Arial,sans-serif;font-size:12.5px;text-align:left;margin:10px 0}
.plain{text-align:left;font-family:Arial,sans-serif;font-size:13.5px}
.slot{border:2px dashed #9aa8b6;background:#f6f8fa;min-height:190px;display:flex;align-items:center;justify-content:center;font-family:Arial,sans-serif;font-size:13px;color:#56636f;text-align:center;padding:12px;margin:10px 0 4px}
.slot.tall{min-height:420px}
.wide{overflow-x:auto;margin:8px 0}.wide table{min-width:720px}
.cap{text-align:center;font-style:italic;margin:4px 0 18px}
.form{border:1px solid #c9d1d9;padding:14px 18px;margin:8px 0}
.form h4{font-family:Arial,sans-serif;font-size:13.5px;margin:16px 0 6px}
.lines{border-bottom:1px solid #9aa8b6;height:26px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:640px){.grid2{grid-template-columns:1fr}}
"""


def todo(text):
    return f'<div class="todo"><b>To do:</b> {text}</div>'


def where(text):
    return f'<div class="where">{text}</div>'


def heading(letter, title):
    return f'<h2>Appendix {letter}<small>{escape(title)}</small></h2>'


def photo_slot(fig, caption, tall=False):
    cls = "slot tall" if tall else "slot"
    return (f'<div class="{cls}">Insert photo here</div>'
            f'<p class="cap">Figure {fig}. {caption}</p>')


h = []
h.append(f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>UAT Appendix Draft</title><style>{CSS}</style></head><body>")
h.append("<h1>AgriKA-GIS: UAT and testing appendices (draft)</h1>")
h.append("<p class='plain'>Prepared October 21, 2026. These pages add the missing evidence for User Acceptance Testing "
         "and functional testing. They continue the official paper's appendices, which end at <b>Appendix LL</b>, so they "
         "start at <b>MM</b>. Blue boxes say where things go. Black text is ready to paste. <b>Yellow boxes are things only "
         "your team can supply</b> (photos, letters, scans, comments). Every number below was recomputed from the 19 raw "
         "responses in the <i>UAT Results</i> sheet and matches Chapter 4, Tables 29 and 30. Nothing in the paper has been "
         "changed.</p>")

# List of Appendices rows
h.append(where("<b>List of Appendices:</b> add these rows after Appendix LL, with page numbers once pasted."))
LETTERS = [("MM", "Letters of Request for User Acceptance Testing"),
           ("NN", "User Acceptance Testing Form"),
           ("OO", "Documentation of User Acceptance Testing Sessions"),
           ("PP", "Summary of User Acceptance Testing Responses"),
           ("QQ", "Sample Accomplished User Acceptance Testing Forms"),
           ("RR", "Comments and Suggestions from User Acceptance Testing"),
           ("SS", "Summary of Functional Testing")]
h.append("<table><tr><th>Appendix</th><th>Title</th><th>Page</th></tr>"
         + "".join(f"<tr><td>{l}</td><td>{escape(t)}</td><td></td></tr>" for l, t in LETTERS) + "</table>")
h.append(todo("Inside Appendix LL, the first section and its table are labelled <i>QQ.1</i> and <i>Table QQ.1</i>. Rename them "
              "to <i>LL.1</i> and <i>Table LL.1</i> so they do not clash with Appendix QQ below."))

# MM letters
h.append(heading("MM", "Letters of Request for User Acceptance Testing"))
h.append("<p>The letters below were sent to the participating agriculture offices to request permission to conduct the "
         "User Acceptance Testing of AgriKA-GIS with their personnel.</p>")
h.append(todo("Scan or screenshot the signed or received letter for each office and place one per page. If one letter "
              "covered several offices, one copy is enough; say which offices it covered in the caption. If no letter was "
              "sent for the UAT, delete this appendix rather than leave it empty, and tell the adviser how access was "
              "arranged (for example, during the visit for harvest records)."))
h.append("<div class='grid2'>")
for i, o in enumerate(OFFICES, 1):
    h.append("<div>" + photo_slot(f"MM.{i}", f"Letter of request for User Acceptance Testing, {OFFICE_NAME[o]}") + "</div>")
h.append("</div>")

# NN form
h.append(heading("NN", "User Acceptance Testing Form"))
h.append("<p>The instrument used for the User Acceptance Testing is reproduced below. It is based on the ISO/IEC 25010 "
         "software quality model and adapted from Ebron et al. (2025). Respondents first performed the tasks in Part 2 and "
         "then rated the fourteen statements in Part 3.</p>")
h.append(todo("If the printed form you actually used differs from this version (for example, an office list that includes "
              "Victoria, Nagcarlan, and Calauan), paste a scan of the printed blank form here instead."))
f = ["<div class='form'>",
     "<p style='text-align:center'><b>AgriKA-GIS: User Acceptance Testing (UAT) Form</b><br><i>A Spatial-Temporal Framework "
     "for High-Resolution Rice Productivity Mapping and Yield Forecasting in Laguna</i></p>",
     "<p>Thank you for evaluating <b>AgriKA-GIS</b>. This form measures how well the system meets your needs as an "
     "agricultural officer, based on the <b>ISO/IEC 25010 Software Quality Model</b>. Please try the system using the short "
     "task list below, then rate each statement honestly. Your answers are confidential and will be used only for this study.</p>",
     "<h4>Part 1. Respondent Information</h4>",
     "<table><tr><th style='width:28%'>Name (optional)</th><td></td></tr>"
     "<tr><th>Office (encircle one)</th><td>Biñan CAO &bull; Cabuyao CAO &bull; Calamba CAO &bull; Santa Rosa CAO &bull; "
     "Provincial Agriculture Office (Santa Cruz)</td></tr><tr><th>Position / Role</th><td></td></tr>"
     "<tr><th>Date evaluated</th><td></td></tr></table>",
     "<h4>Part 2. Tasks to Try Before Rating</h4>",
     "<p>Please perform these tasks in the system. Tick when done and note any problem you encounter.</p>",
     "<table><tr><th class='c'>#</th><th>Task</th><th class='c'>Done (&#10003;)</th><th>Remarks</th></tr>"]
TASKS = ["Log in to the portal with your assigned credentials.",
         "View the ranked municipality yields for a selected year and season (Monitoring).",
         "Open the map and drill down from Laguna to a municipality and then a barangay (Spatial GIS).",
         "Compare rice yields across municipalities or across years (Analytics).",
         "Generate or export a report (Reports / Data Export).",
         "(Administrator only) Manage a user account or a system setting.",
         "Log out of the system."]
f += [f"<tr><td class='c'>{i}</td><td>{escape(t)}</td><td></td><td></td></tr>" for i, t in enumerate(TASKS, 1)]
f += ["</table>", "<h4>Part 3. System Evaluation (ISO/IEC 25010)</h4>",
      "<p><b>Rating scale:</b> 4 = Strongly Agree, 3 = Agree, 2 = Disagree, 1 = Strongly Disagree. Please put a check "
      "(&#10003;) under the number that matches your experience.</p>",
      "<table><tr><th class='c'>#</th><th>Statement</th><th class='c'>4</th><th class='c'>3</th><th class='c'>2</th><th class='c'>1</th></tr>"]
n = 0
for c in CHARS:
    letter = "ABCDEF"[CHARS.index(c)]
    f.append(f"<tr><th colspan='6'>{letter}. {c}: {CHAR_DESC[c]}</th></tr>")
    for code, cc, text in ITEMS:
        if cc == c:
            n += 1
            f.append(f"<tr><td class='c'>{n}</td><td>{escape(text)}</td><td></td><td></td><td></td><td></td></tr>")
f += ["</table>", "<h4>Part 4. Comments and Suggestions</h4>", "<p>What did you like most about AgriKA-GIS?</p>",
      "<div class='lines'></div><div class='lines'></div><div class='lines'></div>",
      "<p style='margin-top:12px'>What could be improved?</p>",
      "<div class='lines'></div><div class='lines'></div><div class='lines'></div>",
      "<p style='margin-top:30px;text-align:right'>______________________________<br>Signature over Printed Name</p>",
      "<p class='note'><i>For researcher use only.</i> Responses are scored per statement and per characteristic using "
      "frequency, percentage, weighted mean, and standard deviation. Weighted-mean interpretation: 3.26 to 4.00 = Strongly "
      "Agree; 2.51 to 3.25 = Agree; 1.76 to 2.50 = Disagree; 1.00 to 1.75 = Strongly Disagree. Internal consistency is "
      "assessed using Cronbach's alpha (0.70 or higher acceptable; previous AgriKA study = 0.8442). Instrument adapted from "
      "Ebron et al. (2025).</p>", "</div>"]
h += f

# OO photos
h.append(heading("OO", "Documentation of User Acceptance Testing Sessions"))
h.append("<p>The photographs below were taken during the User Acceptance Testing sessions, in which agricultural personnel "
         "used AgriKA-GIS to perform the tasks in Part 2 of the evaluation form before rating the system.</p>")
h.append(todo("One or two photos per office: the respondent using the system on screen, with the researchers present. "
              "Fill in the date and names (with titles) in each caption, as the interview appendices do. Ask permission "
              "before using a photo of a respondent; if someone declined, use a photo where they cannot be identified. "
              "Delete the slots for any office you have no photo of, and do not reuse one photo for two offices."))
counts = {o: c for o, c, _ in office_rows}
for i, o in enumerate(OFFICES, 1):
    h.append(photo_slot(f"OO.{i}", f"User Acceptance Testing at the {OFFICE_NAME[o]} ({counts[o]} "
                        f"respondent{'s' if counts[o] > 1 else ''}), [date]. From left to right: [names and positions]"))

# PP results
h.append(heading("PP", "Summary of User Acceptance Testing Responses"))
h.append("<p>This appendix presents the complete responses of the 19 agricultural personnel and the computations behind "
         "Tables 29 and 30 of Chapter 4. Respondents are identified by code only, to keep individual answers confidential "
         "as promised on the form.</p>")
h.append("<p class='tcap'><b>Table PP.1</b><br><i>Individual Responses to the Fourteen Evaluation Items (n = 19)</i></p>")
h.append("<div class='wide'><table><tr><th>Code</th><th>Office</th>" + "".join(f"<th class='c'>{c}</th>" for c, _, _ in ITEMS)
         + "<th class='c'>Total</th></tr>")
for (r, o, v), t in zip(RESP, totals):
    h.append(f"<tr><td>{r}</td><td>{escape(o)}</td>" + "".join(f"<td class='c'>{x}</td>" for x in v)
             + f"<td class='c'>{t}</td></tr>")
h.append("</table></div><p class='note'>Note. 4 = Strongly Agree, 3 = Agree, 2 = Disagree, 1 = Strongly Disagree. Item codes "
         "follow Table PP.2. The highest possible total is 56.</p>")

h.append("<p class='tcap'><b>Table PP.2</b><br><i>Frequency, Percentage, Weighted Mean, and Standard Deviation per Item</i></p>")
h.append("<div class='wide'><table><tr><th>Code</th><th>Statement</th><th class='c'>SA (4)</th><th class='c'>A (3)</th><th class='c'>D (2)</th>"
         "<th class='c'>SD (1)</th><th class='c'>% SA</th><th class='c'>Weighted Mean</th><th class='c'>SD</th>"
         "<th>Interpretation</th></tr>")
for code, char, text, n_, fr, m, sd, _ in item_rows:
    h.append(f"<tr><td>{code}</td><td>{escape(text)}</td><td class='c'>{fr[4]}</td><td class='c'>{fr[3]}</td>"
             f"<td class='c'>{fr[2]}</td><td class='c'>{fr[1]}</td><td class='c'>{100 * fr[4] / n_:.1f}%</td>"
             f"<td class='c'>{m:.2f}</td><td class='c'>{sd:.2f}</td><td>{interp(m)}</td></tr>")
h.append("</table></div><p class='note'>Note. n = 19 for every item. FS = Functional Suitability, PE = Performance Efficiency, "
         "US = Usability, RE = Reliability, SE = Security, MA = Maintainability. Weighted means interpreted using Table 6.</p>")

h.append("<p class='tcap'><b>Table PP.3</b><br><i>Frequency of Responses per Quality Characteristic</i></p>")
h.append("<div class='wide'><table><tr><th>Quality Characteristic</th><th class='c'>Items</th><th class='c'>Responses</th><th class='c'>SA (4)</th>"
         "<th class='c'>A (3)</th><th class='c'>D (2)</th><th class='c'>SD (1)</th><th class='c'>Weighted Mean</th>"
         "<th class='c'>SD</th></tr>")
for name, ni, n_, fr, m, sd in char_rows + [overall]:
    b = ("<b>", "</b>") if name == "Overall" else ("", "")
    h.append(f"<tr><td>{b[0]}{name}{b[1]}</td><td class='c'>{ni}</td><td class='c'>{n_}</td><td class='c'>{fr[4]}</td>"
             f"<td class='c'>{fr[3]}</td><td class='c'>{fr[2]}</td><td class='c'>{fr[1]}</td>"
             f"<td class='c'>{b[0]}{m:.2f}{b[1]}</td><td class='c'>{sd:.2f}</td></tr>")
h.append("</table></div><p class='note'>Note. Responses = items &times; 19 respondents. These counts are the basis of the "
         "percentages and means in Table 29.</p>")

h.append("<p class='tcap'><b>Table PP.4</b><br><i>Overall Weighted Mean by Office</i></p>")
h.append("<table><tr><th>Office</th><th class='c'>Respondents</th><th class='c'>Weighted Mean</th><th>Interpretation</th></tr>")
for o, c, m in office_rows:
    h.append(f"<tr><td>{OFFICE_NAME[o]}</td><td class='c'>{c}</td><td class='c'>{m:.2f}</td><td>{interp(m)}</td></tr>")
h.append(f"<tr><td><b>All offices</b></td><td class='c'><b>19</b></td><td class='c'><b>{overall[4]:.2f}</b></td>"
         f"<td>{interp(overall[4])}</td></tr></table>")
h.append("<p class='note'>Note. Offices with one respondent reflect a single person's ratings and are shown for "
         "completeness, not for comparison between offices.</p>")

h.append("<p class='tcap'><b>Table PP.5</b><br><i>Computation of Cronbach's Alpha</i></p>")
h.append("<div class='wide'><table><tr><th>Item</th>" + "".join(f"<th class='c'>{c}</th>" for c, _, _ in ITEMS) + "</tr><tr><td>Variance</td>"
         + "".join(f"<td class='c'>{r[-1]:.4f}</td>" for r in item_rows) + "</tr></table></div>")
h.append(f"<p>With k = 14 items, a sum of item variances of {sum_item_var:.4f}, and a variance of the respondents' total "
         f"scores of {var_total:.4f}:</p>")
h.append(f"<p style='text-align:center'>&alpha; = (k / (k &minus; 1)) &times; (1 &minus; &Sigma;&sigma;<sub>i</sub>&sup2; / "
         f"&sigma;<sub>T</sub>&sup2;) = (14 / 13) &times; (1 &minus; {sum_item_var:.4f} / {var_total:.4f}) = <b>{alpha:.3f}</b></p>")
h.append("<p class='note'>Note. Sample variances (n &minus; 1 denominator) are used throughout, as in Table 30.</p>")

# QQ sample forms
h.append(heading("QQ", "Sample Accomplished User Acceptance Testing Forms"))
h.append("<p>Sample forms accomplished by the respondents are shown below. Names and signatures are covered to keep the "
         "responses confidential.</p>")
h.append(todo("Scan two or three filled-in forms (for example, one city office, one municipal office, and one from the "
              "Provincial Agriculture Office). Cover names and signatures before scanning. Write the respondent code "
              "(R01 to R19, from Table PP.1) on each so a panelist can match the scan to the table. If the forms were "
              "answered online instead of on paper, use a screenshot of the response sheet with names hidden."))
for i in range(1, 4):
    h.append(photo_slot(f"QQ.{i}", f"Accomplished User Acceptance Testing form, respondent [code], [office]", tall=True))

# RR comments
h.append(heading("RR", "Comments and Suggestions from User Acceptance Testing"))
h.append("<p>Table RR.1 lists the answers written in Part 4 of the evaluation form, grouped by question. Answers are "
         "reproduced as written; answers in Filipino are followed by an English translation.</p>")
h.append(todo("Type the Part 4 answers from the paper forms. Leave out forms where both questions were left blank, and "
              "say how many were blank in the note. If a comment led to a change in the system, add it to the last column."))
h.append("<p class='tcap'><b>Table RR.1</b><br><i>Respondent Comments and Suggestions</i></p>")
h.append("<table><tr><th>Code</th><th>Office</th><th>What they liked most</th><th>What could be improved</th>"
         "<th>Action taken</th></tr>"
         + "".join("<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td></tr>" for _ in range(5)) + "</table>")
h.append("<p class='note'>Note. [number] of the 19 forms had no written comments.</p>")

# SS functional testing
h.append(heading("SS", "Summary of Functional Testing"))
h.append("<p>Functional testing verified each module of AgriKA-GIS against its expected behavior. The detailed test cases, "
         "expected results, observed results, and verdicts appear in Tables 22 to 25 of Chapter 4. This appendix records how "
         "the tests were run and summarizes the outcome.</p>")
h.append("<p class='tcap'><b>Table SS.1</b><br><i>Functional Testing Execution Details</i></p>")
h.append("<table><tr><th style='width:30%'>Item</th><th>Detail</th></tr>"
         "<tr><td>Date executed</td><td>September 25, 2026</td></tr>"
         "<tr><td>Build tested</td><td>[local build / deployed build]</td></tr>"
         "<tr><td>Browser</td><td>[browser and version]</td></tr>"
         "<tr><td>Accounts used</td><td>One account for each role: Administrator, Agriculturist, Rice Technician; "
         "plus a temporary test account created and deleted during Module 6 testing</td></tr>"
         "<tr><td>Executed by</td><td>[names of the researchers]</td></tr>"
         "<tr><td>Test cases</td><td>47, in four groups (Tables 22 to 25)</td></tr></table>")
h.append(todo("The test tracker (docs/Functional_Test_Tracker.xlsx) says the tests ran on the <b>local build</b>, but "
              "Chapter 4 says <b>the deployed build</b>. Pick the one that is true and use the same wording in both "
              "places."))
h.append("<p class='tcap'><b>Table SS.2</b><br><i>Functional Testing Results by Module</i></p>")
h.append("<table><tr><th>Module(s)</th><th>Detailed cases</th><th class='c'>Test cases</th><th class='c'>Passed</th>"
         "<th class='c'>Pass rate</th></tr>")
for mod, tbl, n_, p in FT:
    h.append(f"<tr><td>{mod}</td><td>{tbl}</td><td class='c'>{n_}</td><td class='c'>{p}</td><td class='c'>{100 * p / n_:.1f}%</td></tr>")
h.append("<tr><td><b>Total</b></td><td></td><td class='c'><b>47</b></td><td class='c'><b>47</b></td><td class='c'><b>100.0%</b></td></tr></table>")
h.append("<p class='note'>Note. During testing, case 3 of Table 24 was first marked for checking because the error shown "
         "in the analytics view (MAE 0.379) differed from the Objective 1 result (0.395). The difference comes from how the "
         "two are averaged: the view averages the residuals of the selected year and season, while Objective 1 pools all "
         "leave-one-year-out folds. The case was then recorded as passed, as explained under Table 26.</p>")
h.append("<p>Screenshots of selected test cases are shown below as evidence of the observed results.</p>")
h.append(todo("Add three or four screenshots, each with its case number: for example, the refused login message "
              "(Table 22, cases 4 and 5), the Agriculturist redirected to the Unauthorized page (Table 25, case 2), the "
              "rejected malformed CSV import (Table 24, case 11), and the drill-down to barangays (Table 23, case 3). "
              "Take them from the same build named in Table SS.1."))
shots = [("Table 22, cases 4 and 5", "access refused with the same message for a wrong username or password"),
         ("Table 25, case 2", "Agriculturist account redirected away from User Access Management"),
         ("Table 24, case 11", "malformed CSV import rejected with row-level errors"),
         ("Table 23, case 3", "map drilled from the province to the barangays of a municipality")]
for i, (case, what) in enumerate(shots, 1):
    h.append(photo_slot(f"SS.{i}", f"Functional test, {case}: {what}"))

h.append("</body></html>")
html = "\n".join(h)
assert "—" not in html, "em dash found"
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(html)
print("wrote", os.path.abspath(OUT))
print(f"overall {overall[4]:.2f} sd {overall[5]:.2f} alpha {alpha:.3f}")
for o, c, m in office_rows:
    print(f"  {o:22s} {c}  {m:.2f}")
