# -*- coding: utf-8 -*-
"""Swap the embedded image of Figure X (Weekly Scheduled Run of the Data Pipeline) in the ORIGINAL paper for the
current docs/figures/fig_scheduled_pipeline.png. Re-runnable. A backup goes to backups/ first."""
import base64
import os
import shutil
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(HERE)
PAPER = os.path.join(DOCS, "AgriKA-GIS_Full_Thesis_Ch1-5.html")
FIG = os.path.join(DOCS, "figures", "fig_scheduled_pipeline.png")

s = open(PAPER, encoding="utf-8").read()
shutil.copy(PAPER, os.path.join(HERE, "backups", f"paper_before_pipeline_fig_{time.strftime('%Y%m%d_%H%M%S')}.html"))

k = s.index('<p class="cap">Figure X. Weekly Scheduled Run of the Data Pipeline</p>')
a = s.rfind('src="data:image/png;base64,', 0, k) + len('src="')
b = s.index('"', a)
s = s[:a] + "data:image/png;base64," + base64.b64encode(open(FIG, "rb").read()).decode() + s[b:]
open(PAPER, "w", encoding="utf-8").write(s)
print("Figure X image replaced")
