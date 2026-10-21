# -*- coding: utf-8 -*-
"""Split the combined DFD (Figure 9a/9b) of the ORIGINAL paper into two figures:
Figure 9 Context Diagram and Figure 10 Level 1 Data Flow Diagram. Figures 10 to 26 become 11 to 27
(captions, List of Figures, and in-text references). Supersedes the figure part of insert_dfd.py.

Runs once: it stops if the paper already has the separate Level 1 figure. A backup goes to backups/ first.
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
FIGS = os.path.join(DOCS, "figures")

s = open(PAPER, encoding="utf-8").read()
if "Figure 10. Level 1 Data Flow Diagram" in s:
    raise SystemExit("already separated")
shutil.copy(PAPER, os.path.join(HERE, "backups", f"paper_before_dfd_split_{time.strftime('%Y%m%d_%H%M%S')}.html"))


def b64(name, w):
    im = Image.open(os.path.join(FIGS, name)).convert("RGB")
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


# 1. renumber Figures 10-26 -> 11-27 (one pass, so nothing is shifted twice)
s = re.sub(r"\bFigure (1\d|2[0-6])\b", lambda m: f"Figure {int(m.group(1)) + 1}", s)

# 2. List of Figures: Figure 9 is the context diagram; Level 1 is the new Figure 10
s = re.sub(r'(<span class="fmk">Figure 9</span><span class="fmd">)[^<]*(</span></div>)',
           r'\1Context Diagram\2<div class="fmrow"><span class="fmk">Figure 10</span>'
           r'<span class="fmd">Level 1 Data Flow Diagram</span></div>', s, count=1)

# 3. the Data Flow Design section: two figures, each after its own description
ctx, lv1 = b64("fig_dfd_context.png", 1800), b64("fig_dfd_level1.png", 2400)
body = f"""<div class="rev" id="rev-dfd">
<p>Figures 9 and 10 present the data flow diagrams of AgriKA-GIS in Gane–Sarson notation: rounded rectangles are processes, open-ended rectangles are data stores, shadowed rectangles are external entities, and arrows are data flows labeled with the data they carry. The context diagram (Figure 9) shows the whole system as a single process and its five external entities: the authorized personnel (Administrator, Agriculturist, and Rice Technician), the public visitor, the Copernicus Data Space Ecosystem (Sentinel Hub API), the Open-Meteo API, and the boundary data of the Philippine Statistics Authority.</p>
<p class="fig"><img style="max-width:640px;width:100%" src="data:image/png;base64,{ctx}"></p>
<p class="cap">Figure 9. Context Diagram</p>
<p>The level 1 diagram (Figure 10) divides the system into six processes and four data stores and keeps the same external flows as the context diagram:</p>"""
a = s.index('<div class="rev" id="rev-dfd">')
k = s.index("<p>1.0 Manage User Access", a)
s = s[:a] + body + s[k:]

old_fig = re.search(r'<p class="fig"><img style="max-width:780px;width:100%" src="data:image/png;base64,[^"]+"></p>\s*'
                    r'<p class="cap">Figure 9\. Data Flow Diagram: \(a\) Context Diagram; \(b\) Level 1 Diagram</p>', s)
s = s[:old_fig.start()] + (f'<p class="fig"><img style="max-width:780px;width:100%" src="data:image/png;base64,{lv1}"></p>\n'
                           '<p class="cap">Figure 10. Level 1 Data Flow Diagram</p>') + s[old_fig.end():]

# 4. top note
s = re.sub(r'<div class="revbanner"><b>Data Flow Diagram redrawn, October 21, 2026\.</b>.*?</div>',
           '<div class="revbanner"><b>Data Flow Diagram redrawn, October 21, 2026.</b> The context diagram is now Figure 9 and '
           'the level 1 diagram is Figure 10 (Gane–Sarson notation, drawn from the system as built), with a short description '
           'of each process; Figures 10 to 26 were renumbered 11 to 27. Jump to: '
           '<a href="#rev-dfd">Chapter 3: Data Flow Design, Figures 9 and 10</a></div>', s, count=1, flags=re.S)

open(PAPER, "w", encoding="utf-8").write(s)
print("paper updated")
