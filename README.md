# NanoReliability

Upload labeled model predictions, check source separation, compare calibration rules and export an auditable reliability report. The standalone browser workbench runs locally and does not send uploaded files to a server.

Version v2.0.1. This repository supplies data and code for a reproducible silica cytotoxicity benchmark and a reusable binary-prediction audit.

Software is licensed under [MIT](LICENSE). Original and derived data retain [CC BY-NC 4.0](DATA_LICENSE.md); the software license does not relicense the data.

[Archived release v2.0.1](https://github.com/Javad-Alizargar/silica-reliability-audit/releases/tag/v2.0.1) is preserved at [Zenodo version DOI 10.5281/zenodo.24347308](https://doi.org/10.5281/zenodo.24347308).

## Use the workbench

Open [website/index.html](website/index.html), choose **Load example** or select a CSV, check the column mappings and run the audit. Alternatively, run `python -m http.server 8766 --bind 127.0.0.1 --directory website` and open the loopback address. Host only `website/` if deploying the tool.

Required fields: source/study identifier, binary measured label, predicted probability of label 1 and role (`calibration` or `evaluation`). Unique observation IDs are recommended. Optional fitting rows support source-overlap checks; they do not fit a model. Probabilities must come from a frozen model without access to calibration or evaluation labels during fitting.

The default policy blocks overlapping source groups. Turn it off only for an explicitly intended within-source analysis. The tool compares pooled rows, one per study, study maximum and label-conditional calibration. Inspect class coverage, whole-source coverage, singleton counts/errors, the confidence-threshold curve and individual sources. Export JSON, prediction sets, rule summaries and source CSVs. The JSON records configuration, selected sampling rows and an input fingerprint when available.

Source IDs cannot establish biological independence. Observed coverage does not bound errors among accepted decisions. Infinite thresholds are valid for insufficient calibration units; singleton error is undefined when no singletons exist. The browser reports observed metrics without confidence intervals. These outputs assess recorded labels and do not certify material safety.

## Data and provenance

The original workbook accompanies Martin et al., [ACS Nano 2023](https://doi.org/10.1021/acsnano.2c11968), and is available from [ACS Figshare](https://doi.org/10.1021/acsnano.2c11968.s003), under **CC BY-NC 4.0**. Its SHA-256 is `cb637a97a24166d13492a22102c913e45a3e868fab52a56f9fb97202552dfd87`. See [DATA_LICENSE.md](DATA_LICENSE.md).

This package includes derived analysis inputs, machine-readable outputs and an actual held-out/calibration example. The raw workbook can be retrieved from its original host. The derived data remove eight exact duplicate development rows, preserve source labels, define 12 predictors and retain source provenance. Source 87 high concentrations were verified against original mg/mL axes; mappings for sources 13 and 84 remain unresolved and are not silently corrected.

## Reproduce the calculations

Python 3.12 was used. Two environments preserve the versions actually executed: `requirements-data.txt` for workbook processing and `requirements-analysis.txt` for modeling, statistics and plots. Fresh environment installation has not been tested. The included processed CSV can be used directly for model reproduction; rebuilding it requires the data environment.

1. `python scripts/fetch_data.py` retrieves and verifies the workbook and companion source archive. The companion code is not executed or required by the models. Automatic downloads stop at 2 GB.
2. Data environment: `python scripts/audit_data.py`.
3. Analysis environment: `python scripts/analyze.py`, then `python scripts/summarize.py` and `python scripts/add_exact_intervals.py`.
4. Analysis environment: `python scripts/analyze_v2.py`, then `python scripts/summarize_v2.py` and `python scripts/build_research_tool.py`.
5. Optional: `python scripts/plot_figures_v2.py` generates local scientific displays from saved results. Generated publication assets are not part of this repository or the website.

The original and extension protocols in `reports/` are scientific execution documentation. The extension is post hoc relative to the original analysis. No model or alpha was selected using evaluation performance. Checkpoints are generated locally; preserve their input/code fingerprints. The V2 checkpoints directory must exist (retained through `.gitkeep`).

## Tests

Run `python scripts/test_methods.py` in the analysis environment. Run `node scripts/test_research_tool.cjs`, then `python scripts/verify_tool_parity.py`. The browser sampler uses documented LCG32 state, sorted source IDs and input row order; the scientific pipeline uses NumPy. The three non-random calibration rules match the example outputs, while sampled row IDs are exported explicitly. Browser QA uses Playwright and Edge, with the tool served on port 8766.

The executed revision passed 17 hand-computed/parser checks and 26 independent JavaScript/Python comparisons. Browser QA covered 28 rule/alpha combinations and upload, mapping, overlap, invalid-input, export and mobile flows. The original 157-fit benchmark was separately rerun locally. The revision recovered 11 primary fits to floating-point precision and added 20 reduced-source fits. These checks are computational verification, not independent scientific replication.

## Repository contents and citation

`scripts/` contains executable analysis and tool checks; `data/processed/` contains permitted derived inputs; `results/` contains saved numeric outputs; `website/` contains the isolated tool; `download/` provides retrieval provenance. The repository excludes authoring drafts, publication assets and third-party full-text articles.

Use [CITATION.cff](CITATION.cff) to cite the software and cite the original dataset separately. The MIT source-code license does not replace the dataset's noncommercial attribution conditions. No third-party source text is redistributed.
