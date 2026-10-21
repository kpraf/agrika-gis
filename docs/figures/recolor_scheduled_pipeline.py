# -*- coding: utf-8 -*-
"""Recolor fig_scheduled_pipeline.svg (the weekly scheduled run, paper Figure X/28) away from blue, then re-render the PNG.

The original generator (fig_schedule_v2.py) needed the `diagrams` package icons and is no longer runnable, so the
matplotlib SVG it wrote is edited directly: light-blue panels become neutral gray, the GitHub-blue accent (timeline,
run box) becomes the MMCL green of the defense deck, the database arrows become slate so they do not clash with it,
and the blue GitHub Actions icon is tinted to match; the PostgreSQL elephant keeps its brand blue. Re-running is harmless.

Needs Playwright with Chrome to render the PNG.
"""
import base64
import io
import os
import re

from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(HERE, "fig_scheduled_pipeline.svg")
PNG = os.path.join(HERE, "fig_scheduled_pipeline.png")

ACCENT = "#1f6b3a"   # MMCL green (was GitHub blue #2088ff)
SWAP = {
    "#e3f2fb": "#f3f4f6",   # panel fill
    "#a9b7c4": "#c7ccd3",   # panel edge
    "#2088ff": ACCENT,      # timeline markers, run box, "each one starts a run"
    "#2f7d32": "#334155",   # database arrows (green would clash with the accent)
}


def tint(png_b64, color=None):
    """Grayscale the icon; with color, map dark-to-light onto color-to-white."""
    im = Image.open(io.BytesIO(base64.b64decode(png_b64))).convert("RGBA")
    alpha = im.getchannel("A")
    g = ImageOps.grayscale(im.convert("RGB"))
    out = ImageOps.colorize(g, black=color, white="white") if color else g.convert("RGB")
    out = out.convert("RGBA")
    out.putalpha(alpha)
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def bluish(png_b64):
    im = Image.open(io.BytesIO(base64.b64decode(png_b64))).convert("RGBA")
    px = [p for p in im.getdata() if p[3] > 128]
    r, g, b = (sum(p[k] for p in px) / len(px) for k in range(3))
    return b - r > 40


s = open(SVG, encoding="utf-8").read()
for old, new in SWAP.items():
    s = re.sub(re.escape(old), new, s, flags=re.I)

icons = 0


def fix(m):
    global icons
    data = m.group(2).strip()
    if not bluish(data):
        return m.group(0)
    if Image.open(io.BytesIO(base64.b64decode(data))).size[0] >= 92:   # PostgreSQL elephant keeps its brand blue
        return m.group(0)
    icons += 1
    return m.group(1) + tint(data, ACCENT) + m.group(3)   # GitHub Actions icon


s = re.sub(r'(href="data:image/png;base64,)([^"]+)(")', fix, s)
open(SVG, "w", encoding="utf-8").write(s)
print("recolored; icons tinted:", icons)

# render the PNG at the original width (2486 px) from the SVG
from playwright.sync_api import sync_playwright

w_pt, h_pt = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s).groups())
w_px, h_px = w_pt * 96 / 72, h_pt * 96 / 72
scale = 2486 / w_px
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": int(w_px) + 1, "height": int(h_px) + 1}, device_scale_factor=scale)
    pg.set_content(f'<html><body style="margin:0;background:white">'
                   f'<img src="file:///{SVG.replace(os.sep, "/")}" style="display:block;width:{w_px}px"></body></html>')
    pg.goto(f"file:///{SVG.replace(os.sep, '/')}")
    pg.screenshot(path=PNG, clip={"x": 0, "y": 0, "width": w_px, "height": h_px})
    b.close()
print("wrote", PNG, Image.open(PNG).size)
