# -*- coding: utf-8 -*-
"""Table X1 (Pipeline Runs Recorded in the Run Log) of the ORIGINAL paper: keep only the runs started by the
weekly schedule (P2, P3). The five test runs on the development machine and the on-demand run P1 are summarized
in the table note, and the sentences that cited them are reworded. User's decision, 2026-10-21.

Runs once (stops if the test-run rows are already gone). A backup goes to backups/ first.
"""
import os
import re
import shutil
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.join(os.path.dirname(HERE), "AgriKA-GIS_Full_Thesis_Ch1-5.html")

s = open(PAPER, encoding="utf-8").read()
if "<td>2026-10-11 14:03</td>" not in s:
    raise SystemExit("already trimmed")
shutil.copy(PAPER, os.path.join(HERE, "backups", f"paper_before_run_table_{time.strftime('%Y%m%d_%H%M%S')}.html"))


def sub(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)


# 1. table: drop rows 1 to 5, the production-database divider, and P1
a = s.index("<tr><td>1</td><td>2026-10-11 14:03</td>")
b = s.index("<tr><td>P2</td>", a)
s = s[:a] + s[b:]

# 2. lead-in, note, and the paragraph after the table
sub("Table X1 presents the runs recorded at the time of writing.",
    "Table X1 presents the runs started by the weekly schedule at the time of writing.")
note = re.search(r'<p class="note"><i>Note\. PHT = Philippine time\. Runs 1 to 5 were executed.*?</i></p>', s, re.S)
s = s[:note.start()] + (
    '<p class="note"><i>Note. PHT = Philippine time. Only the runs started by the weekly schedule are shown. Before '
    'them, on October 11, 2026, the pipeline was tested in five runs on the development machine, and Run P1, started '
    'by hand on the scheduler service, brought the production database up to date and stored the 29 municipal and 42 '
    'barangay predictions for the dry season of 2026. Feature rows and area-months count the meteorological and '
    'satellite tables together. Area-months verified is the number of area-months found in the database for the '
    'processed months against the number expected. Minutes are those of the whole scheduler job.</i></p>') + s[note.end():]

a = s.index("<p>All eight runs completed every stage with no integrity violation.")
b = s.index("</p>", a) + 4
s = s[:a] + (
    "<p>Both runs completed every stage with no integrity violation. Runs P2 and P3 were started by the weekly "
    "schedule itself, on Monday, October 12 and Monday, October 19, 2026, with no person starting or supervising them. "
    "Both were scheduled for 2:00 a.m.; the scheduler service queues scheduled jobs and starts them when a shared "
    "runner becomes available, which is why they started at 5:13 a.m. and 3:52 a.m. Each acquired September and "
    "October 2026 at both levels, refreshed the 288 area-months already held without adding a record, verified all "
    "288, and recorded an encrypted connection. Because both runs processed months already in the database and "
    "added no record, they also show that repeated update cycles neither lose nor duplicate records. At the time of "
    "writing, two consecutive scheduled runs had completed without intervention.</p>") + s[b:]

# 3. other sentences that cited the removed runs
sub("Run P1 in Table X1, executed against the production database, recorded an encrypted connection.",
    "Runs P2 and P3 in Table X1, executed against the production database, recorded an encrypted connection.")
sub("the missing month was retrieved by Run 1 in Table X1,",
    "the missing month was retrieved in a run on October 11, 2026,")
sub("The eight runs recorded at the time of writing, five on the development machine and three by the scheduler "
    "service against the production database, two of them started by the weekly schedule itself on October 12 and "
    "October 19, 2026, completed all stages with no integrity violation, and those that repeated months already "
    "loaded duplicated no record.",
    "The runs started by the weekly schedule itself on October 12 and October 19, 2026, completed all stages with "
    "no integrity violation, and, although both repeated months already loaded, duplicated no record.")

open(PAPER, "w", encoding="utf-8").write(s)
print("paper updated")
