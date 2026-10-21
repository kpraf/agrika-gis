# -*- coding: utf-8 -*-
"""Put the redrawn three-tier architecture (docs/figures/fig_architecture.png) into the ORIGINAL paper as Figure 8,
and correct three System Architecture sentences that described the proposal rather than the system:
the "Spatial Query Engine" (the code links predictions to boundaries by area code; there are no spatial joins),
the PSGC shapefiles (boundaries are from PSA), and Guests seeing reports (public visitors see only the home pages
and the public map). The Logic Tier paragraph now also names the weekly pipeline shown in the figure.

Runs once: it stops if the corrections are already in. A backup goes to backups/ first.
"""
import base64
import io
import os
import shutil
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(HERE)
PAPER = os.path.join(DOCS, "AgriKA-GIS_Full_Thesis_Ch1-5.html")
FIG = os.path.join(DOCS, "figures", "fig_architecture.png")

s = open(PAPER, encoding="utf-8").read()
if "Spatial Query Engine" not in s:
    raise SystemExit("already applied")
shutil.copy(PAPER, os.path.join(HERE, "backups", f"paper_before_architecture_{time.strftime('%Y%m%d_%H%M%S')}.html"))


def para(snippet, new_html, rid):
    """Replace the whole paragraph containing snippet and mark it with the green bar."""
    global s
    assert s.count(snippet) == 1, snippet[:60]
    i = s.index(snippet)
    a = s.rfind("<p", 0, i)
    b = s.index("</p>", i) + 4
    s = s[:a] + f'<div class="rev" id="{rid}"><p>{new_html}</p></div>' + s[b:]


def sub(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


# 1. figure image
im = Image.open(FIG).convert("RGB")
im = im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS)
buf = io.BytesIO()
im.save(buf, "PNG", optimize=True)
k = s.index('<p class="cap">Figure 8. AgriKA-GIS System Architecture')
a = s.rfind('src="data:image/', 0, k) + len('src="')
b = s.index('"', a)
s = s[:a] + "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode() + s[b:]

# 2. text corrections
sub("Historical rice yield records obtained from PhilRice serve as the ground-truth data for model training and "
    "evaluation, while Philippine Standard Geographic Code (PSGC) barangay shapefiles provide the administrative "
    "boundaries required for barangay-level spatial visualization.",
    '<span class="revs" id="rev-arch-sources">Historical rice yield records obtained from PhilRice and the City '
    "Agriculture Offices serve as the ground-truth data for model training and evaluation, while the municipality and "
    "barangay boundaries of the Philippine Statistics Authority provide the administrative boundaries required for "
    "barangay-level spatial visualization.</span>")

para("These prediction outputs are subsequently processed by the Spatial Query Engine", (
    "Rice yield prediction is performed by the enhanced CNN-LSTM model, which processes remotely sensed, "
    "meteorological, and historical agricultural data to generate predicted rice yield values. The model is run by the "
    "automated data pipeline, which GitHub Actions starts every Monday at 2:00 a.m.: the pipeline acquires, "
    "preprocesses, integrates, stores, and delivers the monthly satellite and weather data, and runs the model once the "
    "six months of a cropping season are complete. The predictions are stored in the database with the code of their "
    "municipality or barangay and are linked to the corresponding boundaries by that code; PostGIS returns the "
    "boundaries as GeoJSON for display on the map."), "rev-arch-logic")

sub("Guests are provided limited, read-only access to publicly available rice productivity maps and reports.",
    '<span class="revs" id="rev-arch-public">Public visitors, who do not sign in, can view only the home pages and the '
    "public map.</span>")

# 3. note at the top, like the earlier ones
note = ('<div class="revbanner"><b>System Architecture redrawn, October 21, 2026.</b> Figure 8 now shows the three '
        "tiers as built (monthly satellite statistics, the weekly GitHub Actions pipeline, the PyTorch CNN-LSTM, the "
        "Flask API with access control, and the React + Leaflet client with six modules and four user types). Three "
        "sentences were corrected: data sources, the Logic Tier (no spatial query engine; the pipeline added), and "
        'public visitors. Jump to: <a href="#rev-arch-logic">Chapter 3: System Architecture</a></div>')
k = s.index("<div id='page'>") + len("<div id='page'>")
s = s[:k] + note + s[k:]

open(PAPER, "w", encoding="utf-8").write(s)
print("paper updated")
