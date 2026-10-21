# -*- coding: utf-8 -*-
"""Figure 8, AgriKA-GIS System Architecture (three tiers), redrawn from the system as built.

Style follows common three-tier reference diagrams: one column per tier with a header, black and white (logos keep
their colors), gray panels, logo tiles with a short label, and arrows between the tiers. Content replaces the
proposal-era figure (ResNet50, Green Ratio, soil-moisture derivation, image file storage, Guest Viewer) with the
monthly Statistical API features, the weekly GitHub Actions pipeline, the PyTorch CNN-LSTM, the Flask API with
JWT-based access control, and the React + Leaflet client.

Icons: docs/figures/icons (logos from the `diagrams` package resources; line icons from the scheduled-run figure;
the five line icons share one style and stroke: satellite, weather (cloud-sun-rain), records (clipboard-list), and
lock-line (lock) from Lucide (ISC), boundary from Tabler "polygon" (MIT), all on the full 24-unit canvas at stroke 1.75
in #1e293b and never cropped, so their lines come out equally thick).
Writes fig_architecture.png and an editable fig_architecture.svg (text stays text, for Figma).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Wedge
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(HERE, "icons")
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "svg.fonttype": "none"})

PANEL, EDGE = "#f2f2f2", "#bdbdbd"     # black and white only: neutral grays
INK, MUTED = "#111111", "#555555"
LINE_ICONS = {"satellite", "weather", "records", "boundary", "lock-line"}

W, H = 16.0, 8.6
TOP = 8.45
DPI = 300
HEAD = 0.62
TH, TG = 1.5, 0.2            # tile height, gap between tiles
Y0 = TOP - HEAD - 0.42       # first section label
BOT = Y0 - 0.22 - 2 * TH - TG - 0.52 - 1.62 - 0.25   # just under the database tile

fig = plt.figure(figsize=(W, H), dpi=DPI)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_autoscale_on(False)
ax.axis("off")


def rbox(x, y, w, h, fc, ec, lw=1.0, r=0.08, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw,
                                zorder=z))


def icon(name, cx, cy, size):
    im = Image.open(os.path.join(ICONS, name + ".png")).convert("RGBA")
    if name in LINE_ICONS:                         # line icons in neutral black; logos keep their colors
        alpha = im.getchannel("A")
        im = Image.new("RGBA", im.size, INK)
        im.putalpha(alpha)
    w, h = im.size
    s = size / max(w, h)
    dw, dh = w * s, h * s
    im = im.resize((max(1, round(dw * DPI)), max(1, round(dh * DPI))), Image.LANCZOS)   # resample once, here
    ax.imshow(im, extent=[cx - dw / 2, cx + dw / 2, cy - dh / 2, cy + dh / 2], zorder=3, interpolation="none")


def tier(x, w, num, title, sub):
    rbox(x, BOT, w, TOP - BOT, PANEL, INK, lw=1.3, r=0.12)
    rbox(x, TOP - HEAD, w, HEAD, "white", "none", r=0.12, z=2)
    ax.add_patch(plt.Rectangle((x + 0.01, TOP - HEAD), w - 0.02, 0.15, fc="white", ec="none", zorder=2))
    ax.plot([x, x + w], [TOP - HEAD, TOP - HEAD], color=INK, lw=1.3, zorder=3)          # rule under the header
    ax.add_patch(FancyBboxPatch((x, BOT), w, TOP - BOT, boxstyle="round,pad=0,rounding_size=0.12", fc="none",
                                ec=INK, lw=1.3, zorder=3))
    ax.add_patch(plt.Circle((x + 0.33, TOP - HEAD / 2), 0.19, fc="white", ec=INK, lw=1.2, zorder=4))
    ax.text(x + 0.33, TOP - HEAD / 2, num, color=INK, fontsize=12, fontweight="bold", ha="center", va="center",
            zorder=5)
    ax.text(x + 0.66, TOP - HEAD / 2 + 0.1, title, color=INK, fontsize=13, fontweight="bold", va="center", zorder=4)
    ax.text(x + 0.66, TOP - HEAD / 2 - 0.15, sub, color=MUTED, fontsize=9.5, va="center", zorder=4)


def label(x, y, text):
    ax.text(x, y, text, fontsize=9, fontweight="bold", color=MUTED, va="center")


def tile(x, y, w, h, icons, title, sub, isize=0.62):
    """White tile with its top-left at (x, y): icon(s) centered on top, title and one short line below."""
    rbox(x, y - h, w, h, "white", EDGE, lw=1.0)
    n = len(icons)
    for k, name in enumerate(icons):
        icon(name, x + w / 2 + (k - (n - 1) / 2) * (isize + 0.12), y - 0.14 - isize / 2, isize)
    ty = y - 0.26 - isize
    ax.text(x + w / 2, ty, title, ha="center", va="center", fontsize=10.6, fontweight="bold", color=INK)
    ax.text(x + w / 2, ty - 0.25, sub, ha="center", va="center", fontsize=8.9, color=MUTED, linespacing=1.3)


def person(cx, cy, s=0.16):
    ax.add_patch(plt.Circle((cx, cy + s * 0.9), s * 0.55, fc=INK, ec=INK, zorder=3))
    ax.add_patch(Wedge((cx, cy - s * 0.6), s, 0, 180, fc=INK, ec=INK, zorder=3))


def link(x1, x2, y, text):
    ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle="<|-|>", mutation_scale=14, lw=1.6, color=INK,
                                 shrinkA=2, shrinkB=2, zorder=5))
    ax.text((x1 + x2) / 2, y + 0.3, text, ha="center", va="center", fontsize=8.8, color=INK, linespacing=1.3)


GAP = 0.62
TW = (W - 0.3 - 2 * GAP) / 3
X = [0.15 + k * (TW + GAP) for k in range(3)]
PAD = 0.22                         # inner padding
CW = (TW - 2 * PAD - TG) / 2       # two tiles per row
y0 = Y0

# ---------------------------------------------------------------- 1. data tier
x = X[0]
tier(x, TW, "1", "DATA TIER", "data sources and storage")
label(x + PAD, y0, "SOURCES")
r1 = y0 - 0.22
tile(x + PAD, r1, CW, TH, ["satellite"], "Sentinel-1, Sentinel-2", "Copernicus Data Space")
tile(x + PAD + CW + TG, r1, CW, TH, ["weather"], "Weather", "Open-Meteo API")
r2 = r1 - TH - TG
tile(x + PAD, r2, CW, TH, ["records"], "Yield records", "PhilRice, City Agri. Offices")
tile(x + PAD + CW + TG, r2, CW, TH, ["boundary"], "Boundaries", "PSA, 30 + 682 areas")
label(x + PAD, r2 - TH - 0.3, "STORAGE")
r3 = r2 - TH - 0.52
tile(x + PAD, r3, TW - 2 * PAD, 1.62, ["postgresql", "postgis"], "PostgreSQL + PostGIS",
     "yields, monthly features, predictions, boundaries, users, run log", isize=0.66)

# ---------------------------------------------------------------- 2. logic tier
x = X[1]
tier(x, TW, "2", "LOGIC TIER", "processing and application logic")
label(x + PAD, y0, "PROCESSING")
tile(x + PAD, r1, CW, TH, ["github-actions"], "Weekly data pipeline", "GitHub Actions, Mon 2:00 a.m.")
tile(x + PAD + CW + TG, r1, CW, TH, ["python"], "CNN-LSTM model", "PyTorch, six monthly steps")
label(x + PAD, r1 - TH - 0.11, "")
tile(x + PAD, r2, CW, TH, ["flask"], "Flask REST API", "GeoJSON, yields, predictions")
tile(x + PAD + CW + TG, r2, CW, TH, ["lock-line"], "Access control", "JWT; role and city checked")
label(x + PAD, r2 - TH - 0.3, "WHAT THE PIPELINE DOES")
steps = ["Acquire", "Preprocess", "Integrate", "Store", "Deliver"]
sw = (TW - 2 * PAD - 4 * 0.1) / 5
for k, st in enumerate(steps):
    sx = x + PAD + k * (sw + 0.1)
    rbox(sx, r3 - 0.62, sw, 0.62, "white", EDGE)
    ax.text(sx + sw / 2, r3 - 0.31, st, ha="center", va="center", fontsize=9.2, fontweight="bold", color=INK)
    if k:
        ax.add_patch(FancyArrowPatch((sx - 0.1, r3 - 0.31), (sx, r3 - 0.31), arrowstyle="-|>", mutation_scale=8,
                                     lw=0.9, color=INK, shrinkA=0, shrinkB=0, zorder=4))
ax.text(x + TW / 2, r3 - 0.98, "every Monday, for 30 municipalities and the barangays with a reported yield;\n"
        "the model runs once a season's six months are complete",
        ha="center", va="center", fontsize=8.9, color=MUTED, linespacing=1.35)

# ---------------------------------------------------------------- 3. presentation tier
x = X[2]
tier(x, TW, "3", "PRESENTATION TIER", "Web-GIS application in the browser")
label(x + PAD, y0, "CLIENT")
tile(x + PAD, r1, TW - 2 * PAD, TH, ["react", "leaflet"], "React + Leaflet web app", "maps, charts, and reports")
label(x + PAD, r1 - TH - 0.2, "SIX MODULES")
mods = ["1  Home and System Info", "2  Yield Monitoring", "3  Spatial GIS", "4  Analytics and Comparison",
        "5  Reports and Import/Export", "6  User Access Management"]
mw = (TW - 2 * PAD - TG) / 2
my = r1 - TH - 0.4
for k, m in enumerate(mods):
    mx = x + PAD + (k % 2) * (mw + TG)
    yy = my - (k // 2) * 0.5
    rbox(mx, yy - 0.4, mw, 0.4, "white", EDGE, r=0.06)
    ax.text(mx + 0.14, yy - 0.2, m, va="center", fontsize=9.1, color=INK)
label(x + PAD, my - 1.5 - 0.15, "USERS")
roles = [("Administrator", "whole province"), ("Agriculturist", "assigned city"),
         ("Rice Technician", "assigned city"), ("Public Visitor", "public map")]
rw = (TW - 2 * PAD) / 4
ry = my - 1.5 - 0.62
for k, (role, scope) in enumerate(roles):
    cx = x + PAD + rw * k + rw / 2
    person(cx, ry - 0.2)
    ax.text(cx, ry - 0.62, role, ha="center", va="center", fontsize=9.2, fontweight="bold", color=INK)
    ax.text(cx, ry - 0.86, scope, ha="center", va="center", fontsize=8.6, color=MUTED)

# ---------------------------------------------------------------- links between tiers
mid = (TOP - HEAD + BOT) / 2 + 0.3
link(X[0] + TW, X[1], mid, "SQL\nover TLS")
link(X[1] + TW, X[2], mid, "HTTPS\nJSON")

# trim the canvas to the panels (same scale, nothing distorted)
ax.set_ylim(BOT - 0.08, H)
fig.set_size_inches(W, H - (BOT - 0.08))

out = os.path.join(HERE, "fig_architecture.png")
fig.savefig(out, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.08)
fig.savefig(out[:-4] + ".svg", facecolor="white", bbox_inches="tight", pad_inches=0.08)
print("wrote", out, "and .svg")
