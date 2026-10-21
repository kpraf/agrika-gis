"""
make_dfd.py
===========

Data flow diagrams of AgriKA-GIS in Gane-Sarson notation, black and white:

    fig_dfd_context.png   context diagram: the whole system as process 0 and its external entities
    fig_dfd_level1.png    level 1: the eight processes, six data stores, and the same external flows

Drawn from the code, not from the proposal:
    backend/auth.py, users.py            log in, signed token; account management (Administrator)
    backend/scripts/import_boundaries.py one-time load of the PSA municipality/barangay boundaries
    backend/yields.py  POST /import      yield record file, checked against role and assigned city,
                                         validated row by row, logged in yield_import_log
    backend/scripts/run_pipeline.py      weekly: Sentinel Hub Statistical API (Copernicus Data Space)
                                         and Open-Meteo for the 30 municipalities and the barangays
                                         with a reported yield -> monthly feature tables; pipeline_runs
    backend/scripts/predict_season.py    CNN-LSTM forecast of a completed season -> predictions
    backend/yields.py, features.py,
    boundaries.py (GET)                  maps, residuals (observed - predicted, computed on request),
                                         trends, comparison; the public map needs no sign-in
    src/components/reports               PDF / Excel / CSV reports, incl. the data import history

Rules followed (Gane & Sarson; Lucid DFD tutorial): every flow starts or ends at a process;
no entity-to-store, store-to-store, or entity-to-entity flow; every process and store has an
input and an output; process names are verb phrases, stores and flows are noun phrases; the
level 1 diagram keeps exactly the external flows of the context diagram (balancing).

The public contact form (contact_messages) is outside the rice-data flow and, like the ERD,
is not shown.

Usage
    python docs/figures/make_dfd.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})
INK = "black"
LBL = 6.6     # flow label font size
NAME = 7.6    # node name font size


class DFD:
    def __init__(self, w, h):
        self.fig = plt.figure(figsize=(w, h), dpi=300)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(0, h)
        self.ax.set_aspect("equal")
        self.ax.axis("off")
        self.nodes = {}

    # ---- shapes -------------------------------------------------------------
    def entity(self, key, x, y, w, h, text):
        ax = self.ax
        ax.add_patch(Rectangle((x - w / 2 + 0.06, y - h / 2 - 0.06), w, h, fc=INK, ec=INK, lw=0, zorder=2))  # shadow
        box = Rectangle((x - w / 2, y - h / 2), w, h, fc="white", ec=INK, lw=1.1, zorder=3)
        ax.add_patch(box)
        ax.text(x, y, text, ha="center", va="center", fontsize=NAME, fontweight="bold", zorder=4, linespacing=1.15)
        self.nodes[key] = box

    def process(self, key, x, y, w, h, num, text):
        ax = self.ax
        box = FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.12",
                             fc="white", ec=INK, lw=1.1, zorder=3)
        ax.add_patch(box)
        band = 0.24
        ax.plot([x - w / 2, x + w / 2], [y + h / 2 - band] * 2, color=INK, lw=0.9, zorder=4)
        ax.text(x, y + h / 2 - band / 2, num, ha="center", va="center", fontsize=NAME, zorder=4)
        ax.text(x, y - band / 2, text, ha="center", va="center", fontsize=NAME, zorder=4, linespacing=1.15)
        self.nodes[key] = box

    def store(self, key, x, y, w, h, sid, text):
        ax = self.ax
        x0, x1, y0, y1 = x - w / 2, x + w / 2, y - h / 2, y + h / 2
        clip = Rectangle((x0, y0), w, h, fc="white", ec="none", zorder=3)
        ax.add_patch(clip)
        idw = 0.36
        ax.plot([x1, x0, x0, x1], [y1, y1, y0, y0], color=INK, lw=1.1, zorder=4, solid_capstyle="butt")
        ax.plot([x0 + idw] * 2, [y0, y1], color=INK, lw=0.9, zorder=4)
        ax.text(x0 + idw / 2, y, sid, ha="center", va="center", fontsize=NAME, zorder=4)
        ax.text(x0 + idw + (w - idw) / 2, y, text, ha="center", va="center", fontsize=NAME, zorder=4, linespacing=1.15)
        self.nodes[key] = clip

    # ---- flows --------------------------------------------------------------
    def flow(self, a, b, label, rad=0.0, t=0.5, dx=0.0, dy=0.0, pa=None, pb=None):
        A, B = self.nodes[a], self.nodes[b]

        def center(p):
            bb = p.get_bbox() if hasattr(p, "get_bbox") else None
            if isinstance(p, FancyBboxPatch):
                return p.get_x() + p.get_width() / 2, p.get_y() + p.get_height() / 2
            return p.get_x() + p.get_width() / 2, p.get_y() + p.get_height() / 2

        ca = pa or center(A)
        cb = pb or center(B)
        arr = FancyArrowPatch(ca, cb, patchA=None if pa else A, patchB=None if pb else B,
                              arrowstyle="-|>,head_length=4.5,head_width=2.4",
                              connectionstyle=f"arc3,rad={rad}", color=INK, lw=0.8, zorder=1,
                              shrinkA=1.5, shrinkB=1.5)
        self.ax.add_patch(arr)
        # label near the curve: midpoint of the chord pushed toward the bulge of the arc
        mx = ca[0] + (cb[0] - ca[0]) * t
        my = ca[1] + (cb[1] - ca[1]) * t
        if rad:
            nx, ny = (cb[1] - ca[1]), -(cb[0] - ca[0])
            mx += nx * rad * 0.5
            my += ny * rad * 0.5
        self.ax.text(mx + dx, my + dy, label, ha="center", va="center", fontsize=LBL, zorder=5,
                     linespacing=1.1, bbox=dict(fc="white", ec="none", pad=0.6))

    def save(self, name):
        out = os.path.join(HERE, name)
        self.fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.12)
        print("wrote", out)


def path(d, pts, label=None, lpos=None, ha="center", double=False, lw=0.85):
    """Orthogonal flow through the given points; arrowhead at the last point (both ends if double)."""
    ax = d.ax
    xs, ys = zip(*pts)
    ax.plot(xs[:-1], ys[:-1], color=INK, lw=lw, zorder=1, solid_capstyle="butt")
    style = "<|-|>" if double else "-|>"
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle=f"{style},head_length=5,head_width=2.6",
                                 color=INK, lw=lw, zorder=1, shrinkA=0, shrinkB=0))
    if double and len(pts) > 2:
        ax.add_patch(FancyArrowPatch(pts[1], pts[0], arrowstyle="-|>,head_length=5,head_width=2.6",
                                     color=INK, lw=lw, zorder=1, shrinkA=0, shrinkB=0))
    if label:
        x, y = lpos
        ax.text(x, y, label, ha=ha, va="center", fontsize=LBL, zorder=5, linespacing=1.1,
                bbox=dict(fc="white", ec="none", pad=0.8))


# ============================================================== context diagram
def context():
    global LBL, NAME
    LBL, NAME = 7.4, 8.6
    d = DFD(11.4, 5.35)
    cx, cy, w, h = 5.7, 3.9, 2.6, 2.2
    d.process("P0", cx, cy, w, h, "0", "AgriKA-GIS\nSpatial Decision-Support\nSystem")
    L, R, T, B = cx - w / 2, cx + w / 2, cy + h / 2, cy - h / 2
    d.entity("E1", 1.15, cy, 1.85, 1.6, "Authorized\nPersonnel\n\n(Administrator,\nAgriculturist,\nRice Technician)")
    d.entity("E2", cx, 0.55, 1.9, 0.5, "Public Visitor")
    d.entity("E3", 10.25, cy + 0.65, 1.85, 0.8, "Copernicus Data\nSpace (Sentinel\nHub API)")
    d.entity("E4", 10.25, cy - 0.65, 1.85, 0.5, "Open-Meteo API")
    d.entity("E5", 10.25, 1.35, 1.85, 0.6, "PSA Boundary\nData")
    e1r, er = 1.15 + 1.85 / 2, 10.25 - 1.85 / 2
    path(d, [(e1r, cy + 0.25), (L, cy + 0.25)],
         "login credentials, account details,\nyield record files, map selections,\nreport requests", ((e1r + L) / 2, cy + 0.85))
    path(d, [(L, cy - 0.25), (e1r, cy - 0.25)],
         "signed token, account list,\nimport summaries, maps, residuals,\ncharts, PDF / Excel / CSV reports", ((e1r + L) / 2, cy - 0.85))
    path(d, [(cx - 0.45, 0.8), (cx - 0.45, B)], "map\nselections", (cx - 1.0, 1.75))
    path(d, [(cx + 0.1, B), (cx + 0.1, 0.8)], "public\nyield map", (cx + 0.6, 1.75))
    path(d, [(R, cy + 0.8), (er, cy + 0.8)], "area and month requests", ((R + er) / 2, cy + 1.02))
    path(d, [(er, cy + 0.5), (R, cy + 0.5)], "Sentinel-1/2 monthly statistics", ((R + er) / 2, cy + 0.28))
    path(d, [(R, cy - 0.5), (er, cy - 0.5)], "area and month requests", ((R + er) / 2, cy - 0.28))
    path(d, [(er, cy - 0.8), (R, cy - 0.8)], "monthly weather", ((R + er) / 2, cy - 1.02))
    path(d, [(er, 1.35), (R - 0.25, 1.35), (R - 0.25, B)], "municipality and barangay boundaries", ((er + R - 0.25) / 2, 1.6))
    d.save("fig_dfd_context.png")


# ============================================================== level 1
def level1(lbl=7.4, name=8.6, out="fig_dfd_level1.png"):
    global LBL, NAME
    LBL, NAME = lbl, name
    d = DFD(18.4, 10.2)
    PW, PH = 2.3, 1.0
    SW, SH = 2.45, 0.56
    YT, YM, YB = 7.9, 5.3, 2.4          # top, middle, bottom rows
    # external entities
    d.entity("E1", 0.95, 5.15, 1.55, 6.6, "Authorized\nPersonnel\n\n(Administrator,\nAgriculturist,\nRice Technician)")
    d.entity("E2", 5.25, 0.55, 1.9, 0.5, "Public Visitor")
    d.entity("E3", 17.35, 8.45, 1.8, 0.8, "Copernicus Data\nSpace (Sentinel\nHub API)")
    d.entity("E4", 17.35, 7.15, 1.8, 0.5, "Open-Meteo API")
    d.entity("E5", 17.35, YB, 1.8, 0.65, "PSA Boundary\nData")
    # processes
    d.process("P1", 4.1, YT, PW, PH, "1.0", "Manage User\nAccess")
    d.process("P2", 7.3, YT, PW, PH, "2.0", "Import Yield\nRecords")
    d.process("P3", 14.4, YT, PW, PH, "3.0", "Acquire Weekly\nSatellite and\nWeather Data")
    d.process("P4", 10.75, YM, PW, PH, "4.0", "Predict Rice Yield\n(CNN-LSTM)")
    d.process("P5", 5.25, YB, 4.0, PH, "5.0", "Present Maps, Analytics,\nand Reports")
    d.process("P6", 14.4, YB, PW, PH, "6.0", "Load Administrative\nBoundaries")
    # data stores
    d.store("D1", 4.1, YM, SW, SH, "D1", "Users and Roles")
    d.store("D2", 7.3, YM, SW, SH, "D2", "Yield Records\n(Observed, Predicted)")
    d.store("D3", 14.4, YM, SW, SH, "D3", "Monthly Weather and\nSatellite Features")
    d.store("D4", 10.75, YB, SW, SH, "D4", "Boundaries, Areas,\nand Seasons")

    e1r = 0.95 + 1.55 / 2                  # right edge of E1
    p1l, p1r = 4.1 - PW / 2, 4.1 + PW / 2
    p2l, p2r = 7.3 - PW / 2, 7.3 + PW / 2
    p3l, p3r = 14.4 - PW / 2, 14.4 + PW / 2
    p4l, p4r = 10.75 - PW / 2, 10.75 + PW / 2
    p5l, p5r = 5.25 - 2.0, 5.25 + 2.0
    p6l, p6r = 14.4 - PW / 2, 14.4 + PW / 2
    top = lambda y: y + PH / 2
    bot = lambda y: y - PH / 2
    s_top, s_bot = YM + SH / 2, YM - SH / 2
    e3l, e4l, e5l = 17.35 - 0.9, 17.35 - 0.9, 17.35 - 0.9

    # --- 1.0 Manage User Access
    path(d, [(e1r, YT + 0.2), (p1l, YT + 0.2)], "login credentials,\naccount details", ((e1r + p1l) / 2, YT + 0.5))
    path(d, [(p1l, YT - 0.2), (e1r, YT - 0.2)], "signed token,\naccount list", ((e1r + p1l) / 2, YT - 0.5))
    path(d, [(4.1, bot(YT)), (4.1, s_top)], "user accounts\nand roles", (4.1 + 0.62, (bot(YT) + s_top) / 2), double=True)
    # --- 2.0 Import Yield Records (E1 reaches it over the top of 1.0)
    path(d, [(0.75, 5.15 + 3.3), (0.75, 9.55), (7.05, 9.55), (7.05, top(YT))], "yield record file (PhilRice / CAO)", (3.9, 9.55))
    path(d, [(7.55, top(YT)), (7.55, 9.9), (0.45, 9.9), (0.45, 5.15 + 3.3)], "import summary", (3.9, 9.9))
    path(d, [(4.1 + SW / 2, YM), (5.65, YM), (5.65, YT), (p2l, YT)], "role and\nassigned city", (5.65, (YM + YT) / 2))
    path(d, [(7.3, bot(YT)), (7.3, s_top)], "validated\nyield records", (7.3 + 0.62, (bot(YT) + s_top) / 2))
    # --- 3.0 Acquire weekly data
    path(d, [(p3r, YT + 0.42), (e3l, YT + 0.42)], "area and month\nrequests", ((p3r + e3l) / 2, YT + 0.78))
    path(d, [(e3l, YT + 0.12), (p3r, YT + 0.12)], None)
    d.ax.text((p3r + e3l) / 2, YT - 0.05, "Sentinel-1/2 monthly\nstatistics", ha="center", va="top", fontsize=LBL,
              zorder=5, linespacing=1.1, bbox=dict(fc="white", ec="none", pad=0.8))
    path(d, [(p3r, YT - 0.62), (e4l, YT - 0.62)], None)
    path(d, [(e4l, YT - 0.9), (p3r, YT - 0.9)], None)
    d.ax.text((p3r + e4l) / 2, YT - 1.25, "area and month requests /\nmonthly weather", ha="center", va="center",
              fontsize=LBL, zorder=5, linespacing=1.1, bbox=dict(fc="white", ec="none", pad=0.8))
    path(d, [(14.4, bot(YT)), (14.4, s_top)], "monthly\nfeatures", (14.4 + 0.55, (bot(YT) + s_top) / 2))
    path(d, [(7.3 + SW / 2 - 0.25, s_top), (7.3 + SW / 2 - 0.25, 6.75), (13.75, 6.75), (13.75, bot(YT))],
         "barangays with reported yield", (10.75, 6.75))
    path(d, [(10.75 + SW / 2, YB + 0.12), (12.6, YB + 0.12), (12.6, YT - 0.25), (p3l, YT - 0.25)],
         "area\nboundaries", (12.6, 4.35))
    # --- 4.0 Predict
    path(d, [(14.4 - SW / 2, YM), (p4r, YM)], "feature\nsequences", ((14.4 - SW / 2 + p4r) / 2 - 0.25, YM + 0.42))
    path(d, [(7.3 + SW / 2, YM + 0.17), (p4l, YM + 0.17)], "observed yields", ((7.3 + SW / 2 + p4l) / 2, YM + 0.45))
    path(d, [(p4l, YM - 0.17), (7.3 + SW / 2, YM - 0.17)], "predicted yields", ((7.3 + SW / 2 + p4l) / 2, YM - 0.45))
    # --- 5.0 Present maps, analytics, and reports
    path(d, [(e1r, YB + 0.2), (p5l, YB + 0.2)], "map selections,\nreport requests", ((e1r + p5l) / 2, YB + 0.55))
    path(d, [(p5l, YB - 0.2), (e1r, YB - 0.2)], "maps, residuals,\ncharts, reports", ((e1r + p5l) / 2, YB - 0.55))
    path(d, [(4.95, 0.8), (4.95, bot(YB))], "map\nselections", (4.45, 1.36))
    path(d, [(5.55, bot(YB)), (5.55, 0.8)], "public\nyield map", (6.08, 1.36))
    path(d, [(6.3, s_bot), (6.3, top(YB))], "observed and\npredicted yields", (6.3 - 0.75, (s_bot + top(YB)) / 2))
    path(d, [(10.75 - SW / 2, YB), (p5r, YB)], "boundaries", ((10.75 - SW / 2 + p5r) / 2, YB + 0.22))
    path(d, [(13.85, s_bot), (13.85, 3.6), (7.0, 3.6), (7.0, top(YB))], "environment layers", (9.6, 3.6))
    # --- 6.0 Load boundaries
    path(d, [(e5l, YB), (p6r, YB)], "boundary\nfiles", ((e5l + p6r) / 2, YB + 0.38))
    path(d, [(p6l, YB - 0.15), (10.75 + SW / 2, YB - 0.15)], "municipality and\nbarangay boundaries", ((p6l + 10.75 + SW / 2) / 2 + 0.1, YB - 0.62))
    d.save(out)


def combined():
    """Paper Figure 9: (a) context diagram above (b) level 1, one image so figure numbers stay."""
    from PIL import Image, ImageDraw, ImageFont
    a = Image.open(os.path.join(HERE, "fig_dfd_context.png")).convert("RGB")
    b = Image.open(os.path.join(HERE, "fig_dfd_level1.png")).convert("RGB")
    W = b.width
    k = 0.66 * W / a.width                  # context diagram at two-thirds of the page width
    a = a.resize((int(a.width * k), int(a.height * k)), Image.LANCZOS)
    font = ImageFont.truetype(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arialbd.ttf"), 64)
    gap, head = 90, 110
    out = Image.new("RGB", (W, head + a.height + gap + head + b.height), "white")
    dr = ImageDraw.Draw(out)
    dr.text((40, 20), "(a) Context diagram", fill="black", font=font)
    out.paste(a, ((W - a.width) // 2, head))
    y = head + a.height + gap
    dr.text((40, y + 20), "(b) Level 1 diagram", fill="black", font=font)
    out.paste(b, ((W - b.width) // 2, y + head))
    path_ = os.path.join(HERE, "fig_dfd_combined.png")
    out.save(path_, optimize=True)
    print("wrote", path_, out.size)


if __name__ == "__main__":
    context()
    level1()
    combined()
    level1(lbl=9.6, name=10.6, out="fig_dfd_level1_slide.png")   # larger text for the defense slide
