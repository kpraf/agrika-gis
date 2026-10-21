# -*- coding: utf-8 -*-
"""Replace the Data Flow Design section of the ORIGINAL paper with the redrawn DFD (Figure 9a/9b).

Re-runnable: it looks for the section between the Data Flow Design and Database Design headings.
A backup of the paper is written to backups/ first.
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
FIG = os.path.join(DOCS, "figures", "fig_dfd_combined.png")

os.makedirs(os.path.join(HERE, "backups"), exist_ok=True)
shutil.copy(PAPER, os.path.join(HERE, "backups", f"paper_before_dfd_{time.strftime('%Y%m%d_%H%M%S')}.html"))

s = open(PAPER, encoding="utf-8").read()

im = Image.open(FIG).convert("RGB")
w = 2400
im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
buf = io.BytesIO()
im.save(buf, "PNG", optimize=True)
b64 = base64.b64encode(buf.getvalue()).decode()

body = f"""<div class="rev" id="rev-dfd">
<p>Figure 9 presents the data flow diagrams of AgriKA-GIS in Gane–Sarson notation: rounded rectangles are processes, open-ended rectangles are data stores, shadowed rectangles are external entities, and arrows are data flows labeled with the data they carry. The context diagram (Figure 9a) shows the whole system as a single process and its five external entities: the authorized personnel (Administrator, Agriculturist, and Rice Technician), the public visitor, the Copernicus Data Space Ecosystem (Sentinel Hub API), the Open-Meteo API, and the boundary data of the Philippine Statistics Authority.</p>
<p>The level 1 diagram (Figure 9b) divides the system into six processes and four data stores and keeps the same external flows as the context diagram:</p>
<p>1.0 Manage User Access checks login credentials against D1 Users and Roles, returns a signed token, and lets the Administrator maintain user accounts.</p>
<p>2.0 Import Yield Records receives yield record files compiled from PhilRice and the City Agriculture Offices, checks the role and assigned city of the uploader in D1, validates each row, and stores the records in D2 Yield Records.</p>
<p>3.0 Acquire Weekly Satellite and Weather Data runs on the weekly schedule. Using the area boundaries in D4 and the barangays with a reported yield in D2, it requests monthly Sentinel-1 and Sentinel-2 statistics from the Copernicus Data Space Ecosystem and monthly weather from Open-Meteo, and stores the results in D3 Monthly Weather and Satellite Features.</p>
<p>4.0 Predict Rice Yield reads the feature sequences in D3 and the observed yields in D2, and writes the yields predicted by the CNN-LSTM model back to D2.</p>
<p>5.0 Present Maps, Analytics, and Reports reads D2, D3, and D4 to produce the maps, residuals (observed minus predicted, computed on request), charts, and PDF, Excel, or CSV reports, limited to the assigned city of the user; public visitors receive the read-only yield map.</p>
<p>6.0 Load Administrative Boundaries loads the municipality and barangay boundaries from the Philippine Statistics Authority data into D4.</p>
<p>As in the entity relationship diagram, the audit records (run log and import log) and the public contact form are not shown.</p>
<p class="fig"><img style="max-width:780px;width:100%" src="data:image/png;base64,{b64}"></p>
<p class="cap">Figure 9. Data Flow Diagram: (a) Context Diagram; (b) Level 1 Diagram</p>
</div>"""

a = s.index('<h1 id="data-flow-design">Data Flow Design</h1>') + len('<h1 id="data-flow-design">Data Flow Design</h1>')
b = s.index('<h1 id="database-design">', a)
s = s[:a] + body + s[b:]

# List of Figures entry
s = re.sub(r'(<span class="fmk">Figure 9</span><span class="fmd">)[^<]*(</span>)',
           r"\1Data Flow Diagram: (a) Context Diagram; (b) Level 1 Diagram\2", s, count=1)

# green note at the top, like the earlier revision notes
note = ('<div class="revbanner"><b>Data Flow Diagram redrawn, October 21, 2026.</b> Figure 9 now has a context diagram and a '
        'level 1 diagram in Gane–Sarson notation, drawn from the system as built (processes, data stores, and external '
        'entities), with a short description of each process. Jump to: <a href="#rev-dfd">Chapter 3: Data Flow Design, Figure 9</a></div>')
if "Data Flow Diagram redrawn, October 21, 2026." not in s:
    k = s.index("<div id='page'>") + len("<div id='page'>")
    s = s[:k] + note + s[k:]

open(PAPER, "w", encoding="utf-8").write(s)
print("paper updated; figure base64 KB:", len(b64) // 1000)
