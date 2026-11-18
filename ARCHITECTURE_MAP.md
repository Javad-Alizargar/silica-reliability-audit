# Data/code architecture

| Stage | Input | Code | Output |
|---|---|---|---|
| Retrieval | ACS Figshare metadata | fetch_data.py | Immutable workbook, checksums |
| Audit | Workbook | audit_data.py | canonical.csv, dictionary, cohort audit |
| Fixed models | Canonical data, initial protocol | analyze.py | Predictions, memberships, calibration thresholds |
| Aggregate metrics | Saved predictions | summarize.py, add_exact_intervals.py | Point/set metrics and uncertainty |
| Reliability extension | Primary memberships and data | analyze_v2.py, reliability.py | Class coverage, novelty, learning, example predictions |
| Contrasts | Extension outputs | summarize_v2.py | Source-bootstrap contrasts, error detection, source review |
| Local displays | Saved CSV results | plot_figures_v2.py | Locally generated plots and panel data |
| Browser example | audit_example.csv | build_research_tool.py | website/example.csv and example-data.js |
| Upload audit | Researcher's labeled CSV | website/audit.js, app.js | In-memory results and explicit downloadable reports |

The static website is self-contained. It neither reads repository directories nor requests remote services. Its example is embedded so it also opens offline. File uploads remain in memory until reload/close. Scientific plans document assumptions and seeds; they are not preregistrations or guarantees of performance on a new dataset.
