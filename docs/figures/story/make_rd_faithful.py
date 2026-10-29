# -*- coding: utf-8 -*-
"""Figure 2, Research Design of the Study.

Keeps the layout and the eight phases of the approved figure; only the activities were brought in line with
the system as built (monthly statistics, NDWI and VV/VH, the weekly pipeline, React/Leaflet/Flask, Wilcoxon).

Writes fig_research_design.png and an editable fig_research_design.svg (text stays text, for Figma).
"""
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "svg.fonttype": "none"})

W = 7.6
XL, WL = 0.08, 3.05      # phase box
XR, WR = 3.62, 3.9       # activity box
LINE = 0.215
FS, TS = 9.4, 12.5       # bullet text, phase title
WRAP_R, WRAP_T = 57, 26

PHASES = [
    ("1. Planning and Requirements Gathering",
     ["Review of related literature and the existing AgriKA system",
      "Structured interviews with City Agriculturists and Rice Technicians",
      "Identify problems, needs, and system requirements",
      "Define system objectives and project scope"]),
    ("2. Data Collection",
     ["Sentinel-2 and Sentinel-1 pictures of the rice fields, one per growth phase (Sentinel Hub API)",
      "Historical rice yield records (PhilRice, City Agriculture Offices)",
      "Weather: temperature on the picture date (Open-Meteo API)",
      "Municipality and barangay boundaries (PSA); rice-field outlines of the previous AgriKA study",
      "Collected by an automated pipeline that runs every week"]),
    ("3. Data Preprocessing",
     ["Three growth phases per season; clearest Sentinel-2 date with under 30% cloud over the rice fields",
      "Sentinel-1 date nearest the NDVI picture; terrain-corrected, in decibels",
      "224 x 224 NDVI and Sentinel-1 pictures; ResNet50 turns each into 2,048 values; green ratio",
      "Missing pictures filled by the previous study's rule; min-max scaling"]),
    ("4. Enhanced CNN-LSTM Model Development",
     ["Read the three growth phases of a season as one sequence",
      "Train without and with the Sentinel-1 pictures (baseline and enhanced)",
      "Leave-one-year-out cross-validation; 12 training runs averaged",
      "Generate predicted seasonal rice yield values"]),
    ("5. GIS Integration",
     ["Store predictions in a PostgreSQL/PostGIS spatial database",
      "Link predictions to municipality and barangay boundaries",
      "Yield maps and residual maps at municipality and barangay level",
      "Filtering by city and cropping season"]),
    ("6. WebGIS Development (Agile)",
     ["Develop the Web-GIS (React, Leaflet, Flask) in two iterations",
      "Interactive dashboards and maps",
      "Role-based access control and user management",
      "Reports and data import/export (PDF, Excel, CSV)"]),
    ("7. Evaluation",
     ["Model metrics: RMSE, MAE, and R²",
      "Significance: Shapiro-Wilk, then Wilcoxon signed-rank (paired t-test as a check) vs. the baseline (α = 0.05)",
      "System: functional and security test cases; User Acceptance Testing via ISO/IEC 25010 "
      "(City Agriculturists and Rice Technicians)",
      "Pipeline: reliability of the weekly automated runs",
      "Descriptive statistics: weighted mean, SD, Cronbach's alpha"]),
    ("8. Results, Conclusion, and Recommendations",
     ["Interpret model performance and user acceptance results",
      "Discuss findings against the objectives",
      "Draw conclusions and recommendations"]),
]


def rbox(ax, x, y, w, h, fc, lw):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=fc, ec="black", lw=lw))


def main():
    pad, gap = 0.17, 0.32
    rows = []
    for title, items in PHASES:
        lines = []
        for it in items:
            for k, ln in enumerate(textwrap.wrap(it, WRAP_R, break_on_hyphens=False)):
                lines.append((k == 0, ln))
        rows.append((textwrap.wrap(title, WRAP_T), lines, len(lines) * LINE + 2 * pad + 0.04))
    H = sum(r[2] for r in rows) + gap * (len(rows) - 1) + 0.1

    fig = plt.figure(figsize=(W, H), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    y = H - 0.05
    prev = None
    for tlines, lines, h in rows:
        top, bot = y, y - h
        mid = (top + bot) / 2

        rbox(ax, XL, bot, WL, h, "white", 1.3)
        ty = mid + (len(tlines) - 1) * 0.13
        for k, ln in enumerate(tlines):
            ax.text(XL + 0.2, ty - k * 0.26, ln, fontsize=TS, fontweight="bold", va="center")

        rbox(ax, XR, bot, WR, h, "#f1f1f1", 1.0)
        ly = top - pad - 0.02
        for first, ln in lines:
            if first:
                ax.text(XR + 0.14, ly, "•", fontsize=FS, va="top")
            ax.text(XR + 0.3, ly, ln, fontsize=FS, va="top")
            ly -= LINE

        ax.plot([XL + WL, XR], [mid, mid], color="black", lw=1.0)
        if prev is not None:
            ax.add_patch(FancyArrowPatch((XL + WL / 2, prev), (XL + WL / 2, top), arrowstyle="-|>",
                                         mutation_scale=10, lw=1.0, color="black", shrinkA=0, shrinkB=0))
        prev = bot
        y = bot - gap

    out = os.path.join(HERE, "fig_research_design_faithful.png")
    fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.08)
    fig.savefig(out[:-4] + ".svg", facecolor="white", bbox_inches="tight", pad_inches=0.08)
    print("wrote", out, "and .svg")


if __name__ == "__main__":
    main()
