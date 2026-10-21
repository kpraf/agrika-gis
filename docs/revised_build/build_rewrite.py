# -*- coding: utf-8 -*-
"""Build docs/AgriKA-GIS_Full_Thesis_Ch1-5_rewritten.html from the revised copy (neither source file is changed).

Chapters 1 to 3 are brought in line with what the study actually did, so that the Chapter 4 section
"Changes from the Approved Proposal" is no longer needed and is removed. The approved objective statements
themselves are kept word for word; only the paragraphs that explain them are rewritten. Run build_revised.py
first when the original changes.
"""
import html as H
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(HERE)
SRC = os.path.join(DOCS, "AgriKA-GIS_Full_Thesis_Ch1-5_revised.html")
OUT = os.path.join(DOCS, "AgriKA-GIS_Full_Thesis_Ch1-5_rewritten.html")
s = open(SRC, encoding="utf-8").read()


def once(sub):
    n = s.count(sub)
    if n != 1:
        raise SystemExit(f"anchor found {n} times: {sub[:90]!r}")
    return s.index(sub)


def para(snippet, rid, new=None, subs=()):
    """Rewrite the paragraph that contains snippet (whole text, or substitutions) and mark it with a green bar."""
    global s
    i = once(snippet)
    a = s.rfind("<p", 0, i)
    b = s.index("</p>", i) + 4
    p = s[a:b]
    if new is not None:
        p = f"<p>{new}</p>"
    for old, rep in subs:
        assert p.count(old) == 1, (rid, old[:60])
        p = p.replace(old, rep)
    s = s[:a] + f'<div class="rev" id="{rid}">{p}</div>' + s[b:]


def span(old, new, rid):
    """Replace a short piece of text (caption, table cell) and highlight it."""
    global s
    once(old)
    s = s.replace(old, f'<span class="revs" id="{rid}">{new}</span>')


# ---------------------------------------------------------------- Chapter 1
para("In response to these limitations, this study proposes AgriKA-GIS", "rw-background", new=(
    "In response to these limitations, this study developed AgriKA-GIS, a Web-based spatial decision-support system "
    "that extends the previous AgriKA model through enhanced rice yield prediction, barangay-level visualization, residual "
    "error mapping, role-based data management, and an automated data pipeline. By transforming prediction outputs into "
    "interactive geographic visualizations, AgriKA-GIS helps LGU agriculture offices monitor rice productivity, identify "
    "spatial patterns of yield variation, and support evidence-based planning and intervention at the barangay level. The "
    "study thereby bridges the gap between rice yield prediction models and their practical application in local "
    "agricultural management, giving LGU agriculture offices a spatially informed decision-support platform for "
    "monitoring, planning, and resource allocation for rice production in Laguna."))

para("Given these limitations, this study seeks to determine whether", "rw-problem", new=(
    "Given these limitations, the study set out to determine whether integrating Sentinel-1 SAR-derived information into "
    "the existing CNN-LSTM model, implementing barangay-level spatial analysis through a Web-GIS platform, and "
    "incorporating spatial error visualization and role-based data management improve rice yield prediction performance "
    "and spatial decision support for Local Government Unit agriculture offices in Laguna, compared with the previous "
    "AgriKA system."))

para("To accomplish this objective, the study will extend the existing AgriKA CNN-LSTM", "rw-obj1", new=(
    "To accomplish this objective, the study extended the existing AgriKA CNN-LSTM model by adding Sentinel-1 Synthetic "
    "Aperture Radar (SAR) backscatter (VV and VH) to Sentinel-2 vegetation indices, meteorological variables, and "
    "historical rice yield records, which reduces the dependence of the model on optical imagery that cloud cover often "
    "obscures. Because barangay harvest records were available for only 42 barangays and from 2020 onward, too few to "
    "train a separate model, the model was trained on the seasonal yields of the rice-producing cities and municipalities "
    "of Laguna and applied to the monthly features of those 42 barangays. The resulting model serves as the prediction "
    "engine of the system. Its predictive performance was evaluated using the Root Mean Square Error (RMSE), the Mean "
    "Absolute Error (MAE), and the Coefficient of Determination (R²) under leave-one-year-out cross-validation, and "
    "compared with a baseline configuration that reproduces the input classes of the previous AgriKA model, so that the "
    "contribution of Sentinel-1 could be measured."))

para("To accomplish this objective, the study will develop a Web-based spatial decision-support system", "rw-obj2", new=(
    "To accomplish this objective, the study developed a Web-based spatial decision-support system that integrates rice "
    "yield prediction with Geographic Information System (GIS) technologies to provide interactive barangay-level "
    "visualization of observed and predicted rice yields. The system enables authorized users to view rice productivity "
    "on color-coded maps, monitor productivity trends across cropping seasons, compare cities and barangays, and generate "
    "reports within a centralized platform, with access limited to the assigned city of each user. The system also "
    "generates residual maps from the differences between observed and predicted rice yields. These maps show where the "
    "model overestimates or underestimates rice productivity, helping users recognize locations that require field "
    "validation and judge the reliability of the predictions across barangays. The system was evaluated through "
    "functional and compatibility testing and through User Acceptance Testing (UAT) using a structured questionnaire "
    "based on the ISO/IEC 25010 software quality model."))

para("To accomplish this objective, the study will develop a data pipeline", "rw-obj3",
     subs=[("the study will develop a data pipeline", "the study developed a data pipeline")])

para("The pipeline will support consistent preparation", "rw-obj3-eval", new=(
    "The pipeline supports consistent preparation of the multi-source datasets required by the extended CNN-LSTM model "
    "and the Web-based spatial decision-support system, and keeps the satellite and weather data up to date while "
    "maintaining their integrity and consistency. The pipeline was evaluated on its ability to reliably acquire, "
    "preprocess, integrate, and deliver the data required for rice yield prediction and spatial visualization, on its "
    "unattended operation across repeated scheduled runs, and on security test cases covering the five properties stated "
    "above."))

para("these officers would be able to see which barangays", "rw-rationale",
     subs=[("these officers would be able to see", "these officers can see")])

para("provides spatial decision-support features, including barangay-level rice yield heatmaps", "rw-scope-maps",
     subs=[("barangay-level rice yield heatmaps, residual maps, seasonal visualization, and municipality-based filtering",
            "barangay-level rice yield maps, residual maps, seasonal visualization, and filtering by city, barangay, year, "
            "and cropping season")])

para("barangay-level outputs are limited to the four selected cities.", "rw-scope-uat",
     subs=[("barangay-level outputs are limited to the four selected cities.",
            "barangay-level outputs are limited to the four selected cities. The user acceptance testing was also opened to agricultural personnel of other agriculture offices in Laguna.")])

para("The implementation and evaluation of AgriKA-GIS are limited to the selected cities", "rw-delim-cities", new=(
    "- Barangay-level outputs and the participating City Agriculture Offices are limited to the selected cities of Biñan, "
    "Cabuyao, Calamba, and Santa Rosa in Laguna; the user acceptance testing also included personnel of four other "
    "agriculture offices in the province. Therefore, the findings may not be directly generalizable to other provinces "
    "or regions with different agricultural, climatic, and operational conditions."))

para("seasonal comparison, and municipality-based filtering. Advanced spatial analyses", "rw-delim-filter",
     subs=[("municipality-based filtering", "filtering by city, barangay, year, and cropping season")])

span("Figure 1. Proposed Conceptual Framework", "Figure 1. Conceptual Framework", "rw-fig1")

para("The conceptual framework of the proposed study illustrates", "rw-framework",
     subs=[("The conceptual framework of the proposed study illustrates how the researchers intend to integrate",
            "The conceptual framework of the study illustrates how the researchers integrated")])

para("the proposed AgriKA-GIS extends the existing framework", "rw-framework-2",
     subs=[("the proposed AgriKA-GIS extends", "AgriKA-GIS extends")])

para("This integration of Sentinel-1 and Sentinel-2 is expected to provide", "rw-input-s1",
     subs=[("This integration of Sentinel-1 and Sentinel-2 is expected to provide more comprehensive environmental "
            "information for rice yield prediction.",
            "This integration provides more complete environmental information for rice yield prediction, and its "
            "contribution is measured under Objective 1.")])

para("Finally, barangay boundary shapefiles are obtained", "rw-input-bounds",
     subs=[("Finally, barangay boundary shapefiles are obtained",
            "Finally, municipality and barangay boundaries are obtained from the Philippine Statistics Authority")])

para("After collecting the required datasets, the researchers preprocess the data", "rw-preprocess", new=(
    "After collecting the required datasets, the researchers prepare them for machine learning. The satellite data are "
    "summarized per area and month: the vegetation indices from the cloud-free Sentinel-2 pixels and the radar backscatter "
    "from Sentinel-1, while the meteorological data are aggregated to monthly totals and means. Each cropping season is "
    "then represented by its six monthly values, which are joined with the observed yield of the same area and season. "
    "The features are standardized, and a month with no usable observation, mainly an optical month fully obscured by "
    "cloud, is filled with the training mean."))

para("the researchers aim to improve the robustness of the prediction model", "rw-cnnlstm",
     subs=[("the researchers aim to improve", "the researchers sought to improve"),
           ("that will subsequently be visualized", "that are visualized")])

para("as an interactive barangay-level rice yield heatmap using Leaflet.js", "rw-gis",
     subs=[("This enables the Web-GIS platform to display the predictions as an interactive barangay-level rice yield "
            "heatmap using Leaflet.js.",
            "This enables the Web-GIS platform, built with React and Leaflet, to display the predictions as interactive "
            "color-coded barangay maps.")])

para("allow users to visualize predictions by city and cropping season", "rw-filters",
     subs=[("by city and cropping season", "by city, barangay, year, and cropping season")])

para("The researchers evaluate the proposed system from two perspectives", "rw-eval",
     subs=[("evaluate the proposed system", "evaluate the developed system")])

para("characteristics most relevant to the proposed system, ", "rw-eval-uat",
     subs=[("most relevant to the proposed system", "most relevant to the system"),
           ("Agricultural personnel of the participating LGU agriculture offices serve as respondents",
            "Agricultural personnel of agriculture offices in Laguna serve as respondents")])

para("The final output of the study is a Web-GIS-based decision-support platform", "rw-output", new=(
    "The final output of the study is a Web-GIS-based decision-support platform that combines rice yield prediction with "
    "interactive spatial visualization. Specifically, the system provides interactive color-coded maps of observed and "
    "predicted rice yield for the cities and municipalities of Laguna and for the rice-producing barangays of Calamba, "
    "Cabuyao, Santa Rosa, and Biñan. It also presents residual maps that highlight where the prediction model "
    "over-predicts or under-predicts rice yield relative to the recorded data. The platform further includes role-based "
    "dashboards, seasonal trend and comparison charts, and reports, with filtering by city, barangay, year, and cropping "
    "season, and its satellite and weather data are refreshed every week by the automated pipeline."))

para("the proposed study seeks to transform rice yield prediction", "rw-output-2",
     subs=[("the proposed study seeks to transform", "the study transforms")])

# ---------------------------------------------------------------- Chapter 2
para("which proposes AgriKA-GIS as a Web-based Geographic Information System", "rw-rrl-21",
     subs=[("which proposes AgriKA-GIS", "which developed AgriKA-GIS")])

para("which proposes AgriKA-GIS as a spatial decision-support system", "rw-rrl-22",
     subs=[("which proposes AgriKA-GIS", "which developed AgriKA-GIS"),
           ("agricultural planning in Laguna This gap provides the foundation for the present study, which extends "
            "existing remote sensing applications by integrating Sentinel-1 and Sentinel-2 imagery with deep learning and "
            "Web-GIS technologies to support barangay-level rice productivity monitoring in Laguna.",
            "agricultural planning in Laguna.")])

# ---------------------------------------------------------------- Chapter 3
para("the deployment of the proposed AgriKA-GIS platform", "rw-locale",
     subs=[("the deployment of the proposed AgriKA-GIS platform", "the deployment of the AgriKA-GIS platform")])

span("Paired t-test or Wilcoxon Signed-Rank Test",
     "Wilcoxon Signed-Rank Test (paired t-test as a check); Cohen&#x27;s d", "rw-table7")

span("Figure 8. AgriKA-GIS System Architecture of the Proposed Systems", "Figure 8. AgriKA-GIS System Architecture",
     "rw-fig8")

para("The system utilizes Leaflet.js to present interactive barangay-level heatmaps", "rw-presentation",
     subs=[("The system utilizes Leaflet.js to present interactive barangay-level heatmaps and residual maps",
            "The system uses React and Leaflet to present interactive color-coded barangay yield maps and residual maps")])

para("This module is the core spatial component of AgriKA-GIS. It displays predicted rice yield", "rw-module3",
     subs=[("displays predicted rice yield through interactive barangay-level heatmaps",
            "displays observed and predicted rice yield through interactive color-coded barangay-level maps")])

para("This is the core spatial module of the platform. It displays predicted rice yield", "rw-module3-b",
     subs=[("displays predicted rice yield through interactive barangay-level heatmaps",
            "displays observed and predicted rice yield through interactive color-coded barangay-level maps")])

para("generating comparison heatmaps between municipalities", "rw-admin",
     subs=[("generating comparison heatmaps between municipalities", "comparing municipalities in the analytics module")])

para("which automatically includes generating yield heatmaps", "rw-agri",
     subs=[("which automatically includes generating yield heatmaps to evaluate production patterns",
            "using the analytics charts and yield maps to evaluate production patterns"),
           ("downloadable PDF or CSV formats", "downloadable PDF, Excel, or CSV formats")])

# List of Figures entries for the two renamed captions
for old, new in [("Proposed Conceptual Framework", "Conceptual Framework"),
                 ("AgriKA-GIS System Architecture of the Proposed Systems", "AgriKA-GIS System Architecture")]:
    k = once(f'<span class="fmd">{old}</span>')
    s = s.replace(f'<span class="fmd">{old}</span>', f'<span class="fmd">{new}</span>')

# ---------------------------------------------------------------- Chapter 4: drop "Changes from the Approved Proposal"
a = once('<div class="rev" id="r21-changes">')
b = s.index('<div class="chapdiv" id="ch5">', a)
assert s[a:b].rstrip().endswith("</div>")
s = s[:a] + s[b:]
# the revised copy's summary box linked to it
s = re.sub(r'<li><a href="#r21-changes">.*?</a></li>', "", s, count=1)

# ---------------------------------------------------------------- summary box
LINKS = [
    ("Chapter 1", [
        ("rw-background", "Background: \"this study proposes\" now \"this study developed\" (pipeline included)"),
        ("rw-problem", "Statement of the Problem: \"set out to determine\""),
        ("rw-obj1", "Objective 1 explanation: what was done; municipality-trained model applied to 42 barangays; "
                    "leave-one-year-out; baseline comparison (objective statement unchanged)"),
        ("rw-obj2", "Objective 2 explanation: what the system does; functional, compatibility, and UAT evaluation"),
        ("rw-obj3", "Objective 3 explanation: \"will develop\" now \"developed\""),
        ("rw-obj3-eval", "Objective 3 evaluation sentence in past tense"),
        ("rw-rationale", "Rationale: \"would be able to see\" now \"can see\""),
        ("rw-scope-maps", "Scope: yield maps (not heatmaps); filters by city, barangay, year, and season"),
        ("rw-scope-uat", "Scope: UAT also opened to other agriculture offices"),
        ("rw-delim-cities", "Delimitations: four cities for barangay outputs; UAT also included four other offices"),
        ("rw-delim-filter", "Delimitations: filters described as built"),
        ("rw-fig1", "Figure 1 caption: \"Proposed\" removed (List of Figures too)"),
        ("rw-framework", "Conceptual Framework: \"intend to integrate\" now \"integrated\""),
        ("rw-framework-2", "Conceptual Framework: \"the proposed AgriKA-GIS\" now \"AgriKA-GIS\""),
        ("rw-input-s1", "Input: Sentinel-1 contribution measured under Objective 1"),
        ("rw-input-bounds", "Input: PSA municipality and barangay boundaries"),
        ("rw-preprocess", "Preprocessing: monthly values, six-month seasons, standardization, training-mean fill"),
        ("rw-cnnlstm", "CNN-LSTM: \"aim to\" and \"will be\" removed"),
        ("rw-gis", "GIS Integration: React and Leaflet, color-coded barangay maps"),
        ("rw-filters", "GIS Integration: filters by city, barangay, year, and season"),
        ("rw-eval", "Evaluation: \"proposed system\" now \"developed system\""),
        ("rw-eval-uat", "Evaluation: respondents from agriculture offices in Laguna"),
        ("rw-output", "Output: what the platform provides, including the weekly data refresh"),
        ("rw-output-2", "Output: \"the proposed study seeks to transform\" now \"the study transforms\"")]),
    ("Chapter 2", [
        ("rw-rrl-21", "Synthesis 2.1: \"proposes\" now \"developed\""),
        ("rw-rrl-22", "Synthesis 2.2: \"proposes\" now \"developed\"; duplicated closing sentence removed")]),
    ("Chapter 3", [
        ("rw-locale", "Research Locale: \"proposed\" removed"),
        ("rw-table7", "Table 7: Wilcoxon signed-rank test (paired t-test as a check) and Cohen's d"),
        ("rw-fig8", "Figure 8 caption: \"of the Proposed Systems\" removed (List of Figures too)"),
        ("rw-presentation", "Presentation Tier: React and Leaflet, color-coded maps"),
        ("rw-module3", "Major System Modules, Module 3: observed and predicted yield maps"),
        ("rw-module3-b", "Module 3 (second description): observed and predicted yield maps"),
        ("rw-admin", "User Profile, Administrator: municipalities compared in the analytics module"),
        ("rw-agri", "User Profile, Agriculturists: analytics charts and yield maps; PDF, Excel, or CSV")]),
]
for _, items in LINKS:
    for rid, _ in items:
        assert f'id="{rid}"' in s, rid
groups = "".join(
    f"<p style=\"margin:8px 0 2px\"><b>{H.escape(g)}</b></p><ul style=\"margin:0 0 4px 18px;padding:0\">"
    + "".join(f'<li><a href="#{rid}">{H.escape(t)}</a></li>' for rid, t in items) + "</ul>"
    for g, items in LINKS)
banner = ('<div class="revbanner"><b>Chapters 1 to 3 rewritten, October 21, 2026.</b> This copy is built on the revised '
          'copy. Chapters 1 to 3 now describe what the study did, so the Chapter 4 section "Changes from the Approved '
          'Proposal" was removed. The approved objective statements are unchanged; only the paragraphs that explain them '
          'were rewritten. Each change below has a green bar or highlight; click a line to jump to it. The original and '
          'the revised copy are unchanged.' + groups + "</div>")
k = once("<div id='page'>") + len("<div id='page'>")
s = s[:k] + banner + s[k:]

open(OUT, "w", encoding="utf-8").write(s)
print("written", OUT, len(s))
