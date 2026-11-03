"""
make_use_case.py
================

UML use case diagram of AgriKA-GIS for the defense slides, drawn from the route
guards in src/App.jsx, NAV_BY_ROLE in src/components/layout/DashboardSidebar.jsx and
what each module page offers:

    administrator     monitoring, map, compare, reports and import, user management
    agriculturist     monitoring, map, compare, reports and import (assigned city)
    rice_technician   monitoring, map, reports and import (assigned city)
    public visitor    home pages only (post-defense revision: the yield map is for signed-in users)

Drawn like the earlier Figure 11: black and white, a tall system boundary, round
use cases, arrows from the actors, and <<include>> steps on the right.

    fig_use_case.png

Usage
    python docs/figures/make_use_case.py
"""
import math
import os
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})

INK = "black"
W_IN, H_IN = 5.6, 7.6

fig = plt.figure(figsize=(W_IN, H_IN), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W_IN)
ax.set_ylim(0, H_IN)
ax.set_aspect("equal")
ax.axis("off")

# tall system boundary
BX0, BX1, BY0, BY1 = 1.45, 5.5, 0.05, 7.55
ax.add_patch(Rectangle((BX0, BY0), BX1 - BX0, BY1 - BY0, fc="white", ec=INK, lw=1.0, zorder=0))
ax.text((BX0 + BX1) / 2, BY1 - 0.18, "AgriKA-GIS", ha="center", va="center", fontsize=10, fontweight="bold")

# base use cases (left column) and included steps (right column), top to bottom
BASE = [
    "View Home and System Information",
    "Log In to Portal",
    "View Rice Yield Heatmap",
    "Monitor Rice Yield",
    "Import Yield Records",
    "Generate Yield Reports",
    "Analyze and Compare Yields",
    "Manage User Accounts",
]
INCL = [
    "Verify Role and Assigned City",
    "Search Municipality or Barangay",
    "Switch Observed, Predicted, Residual",
    "Apply Season and Year Filters",
    "View Historical Trends",
    "Validate and Preview Rows",
    "Export as PDF, Excel, or CSV",
    "Generate Comparison Charts",
    "Assign Role and Municipality",
]
INCLUDES = [
    ("Log In to Portal", "Verify Role and Assigned City"),
    ("View Rice Yield Heatmap", "Search Municipality or Barangay"),
    ("View Rice Yield Heatmap", "Switch Observed, Predicted, Residual"),
    ("View Rice Yield Heatmap", "Apply Season and Year Filters"),
    ("Monitor Rice Yield", "Apply Season and Year Filters"),
    ("Monitor Rice Yield", "View Historical Trends"),
    ("Import Yield Records", "Validate and Preview Rows"),
    ("Generate Yield Reports", "Export as PDF, Excel, or CSV"),
    ("Analyze and Compare Yields", "Generate Comparison Charts"),
    ("Manage User Accounts", "Assign Role and Municipality"),
]

POS = {}


def usecase(name, cx, cy, r, fs):
    ax.add_patch(Circle((cx, cy), r, fc="white", ec=INK, lw=0.9, zorder=2))
    ax.text(cx, cy, textwrap.fill(name, 12), ha="center", va="center", fontsize=fs,
            linespacing=1.1, zorder=3)
    POS[name] = (cx, cy, r)


R_BASE, R_INCL = 0.40, 0.37
for i, name in enumerate(BASE):
    usecase(name, 2.45, 6.85 - i * 0.905, R_BASE, 7.6)
for i, name in enumerate(INCL):
    usecase(name, 4.55, 6.92 - i * 0.81, R_INCL, 7.0)


def rim(name, toward, max_deg=30):
    """Point on the circle facing `toward`, kept within max_deg of the left/right edge
    so a line never cuts the neighbouring circles."""
    cx, cy, r = POS[name]
    left = toward[0] < cx
    ang = math.degrees(math.atan2(toward[1] - cy, abs(toward[0] - cx)))
    ang = max(-max_deg, min(max_deg, ang))
    a = math.radians(ang)
    return (cx - r * math.cos(a) if left else cx + r * math.cos(a)), cy + r * math.sin(a)


def arrow(a, b, dashed=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>,head_length=5,head_width=2.6", color=INK,
                                 lw=0.75, linestyle=(0, (3, 2)) if dashed else "-", zorder=1,
                                 shrinkA=0, shrinkB=0.5, mutation_scale=1))


for base, inc in INCLUDES:
    bx, by, _ = POS[base]
    ix, iy, _ = POS[inc]
    a, b = rim(base, (ix, iy)), rim(inc, (bx, by))
    arrow(a, b, dashed=True)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ax.text(mx, my + 0.05, "«include»", ha="center", va="bottom", fontsize=5.6, zorder=3,
            bbox=dict(fc="white", ec="none", pad=0.3))


def actor(x, y, name):
    """Stick figure with its feet at y; returns the point the arrows leave from."""
    s = 0.21
    ax.add_patch(Circle((x, y + 2.55 * s), 0.38 * s, fc="white", ec=INK, lw=1.0, zorder=3))
    kw = dict(color=INK, lw=1.0, zorder=3, solid_capstyle="round")
    ax.plot([x, x], [y + 2.17 * s, y + 1.0 * s], **kw)                       # body
    ax.plot([x - 0.75 * s, x + 0.75 * s], [y + 1.85 * s] * 2, **kw)          # arms
    ax.plot([x - 0.6 * s, x, x + 0.6 * s], [y, y + 1.0 * s, y], **kw)        # legs
    ax.text(x, y - 0.08, name, ha="center", va="top", fontsize=8.5)
    return x + 0.18, y + 1.6 * s


REGISTERED = ["Log In to Portal", "View Rice Yield Heatmap", "Monitor Rice Yield",
              "Import Yield Records", "Generate Yield Reports"]
ACTORS = [
    ("Public Visitor", 6.25, ["View Home and System Information"]),
    ("Rice Technician", 4.45, REGISTERED),
    ("Agriculturist", 2.65, REGISTERED + ["Analyze and Compare Yields"]),
    ("Administrator", 0.85, REGISTERED + ["Analyze and Compare Yields", "Manage User Accounts"]),
]
for name, y, cases in ACTORS:
    start = actor(0.6, y, name)
    for c in cases:
        arrow(start, rim(c, start))

out = os.path.join(HERE, "fig_use_case.png")
fig.savefig(out, dpi=300, facecolor="white")
print("wrote", out)
