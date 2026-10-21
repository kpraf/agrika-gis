# -*- coding: utf-8 -*-
"""Put the updated Research Design figure (Figure 2) into the ORIGINAL paper, just above its caption.

Re-runnable: an earlier insertion (div#rev-design) is replaced. A backup of the paper is written to backups/ first.
build_revised.py rewrites the section text up to this div, so the figure carries over to the revised copy.
"""
import base64
import io
import os
import re
import shutil
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(HERE)
PAPER = os.path.join(DOCS, "AgriKA-GIS_Full_Thesis_Ch1-5.html")
FIG = os.path.join(DOCS, "figures", "fig_research_design.png")

os.makedirs(os.path.join(HERE, "backups"), exist_ok=True)
shutil.copy(PAPER, os.path.join(HERE, "backups", f"paper_before_design_{time.strftime('%Y%m%d_%H%M%S')}.html"))

s = open(PAPER, encoding="utf-8").read()

im = Image.open(FIG).convert("RGB")
w = 2000
im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
buf = io.BytesIO()
im.save(buf, "PNG", optimize=True)
b64 = base64.b64encode(buf.getvalue()).decode()

body = f"""<div class="rev" id="rev-design">
<p>Figure 2 presents the research design: the eight phases of the study and the main activities in each phase, from planning and requirements gathering to the results, conclusion, and recommendations.</p>
<p class="fig"><img style="max-width:780px;width:100%" src="data:image/png;base64,{b64}"></p>
</div>"""

s = re.sub(r'<div class="rev" id="rev-design">.*?</div>', "", s, count=1, flags=re.S)
k = s.index('<p class="cap">Figure 2. Research Design of the Study</p>')
s = s[:k] + body + s[k:]

note = ('<div class="revbanner"><b>Research Design figure updated, October 21, 2026.</b> Figure 2 keeps its eight '
        'phases and layout; the activities now match the system as built (monthly satellite statistics, NDWI and VV/VH, '
        'the weekly automated pipeline, React/Leaflet/Flask, Wilcoxon signed-rank test). Jump to: '
        '<a href="#rev-design">Chapter 3: Research Design, Figure 2</a></div>')
s = re.sub(r'<div class="revbanner"><b>Research Design figure [^<]*</b>.*?</div>', "", s, count=1, flags=re.S)
k = s.index("<div id='page'>") + len("<div id='page'>")
s = s[:k] + note + s[k:]

open(PAPER, "w", encoding="utf-8").write(s)
print("paper updated; figure base64 KB:", len(b64) // 1000)
