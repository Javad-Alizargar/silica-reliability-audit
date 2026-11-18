# Extension analysis plan, version 2

Date: 2026-11-18. This extension is post hoc relative to version 1 and was specified before running the additional analyses. Original results and scripts remain archived. It is not a preregistration and no new confirmatory claims will be made.

## Objectives

1. Characterize how source dependence, experimental context and class composition affect the interpretation of random-row, held-out-study and external validation. Estimate class-specific errors and conditional performance rather than relying on AUROC alone.
2. Compare calibration strategies on the same frozen primary random-forest outputs: pooled-row, one-per-study, study-maximum and label-conditional pooled calibration. Distinguish marginal label coverage, class-conditional coverage, whole-source coverage, accepted fraction and error among accepted predictions. Contrast conformal sets with fixed confidence-threshold abstention curves without choosing a threshold using external outcomes.
3. Test whether distance from fitting data or unseen categorical values identifies unreliable predictions. Build a mixed-type nearest-neighbor distance using only fitting data; retain all 12 existing predictors and report that the distance is a diagnostic, not a validated safety boundary.
4. Measure the relationship between the number of fitting sources and external performance while keeping calibration and external sets unchanged. This assesses data acquisition sensitivity within the same benchmark rather than proving a prospective learning curve.
5. Translate the evaluation into a standalone upload-and-audit tool. Users bring held-out probabilities, labels, source IDs and calibration/evaluation roles. The tool checks partition overlap, calculates sets and class/source diagnostics, and exports results. It contains no manuscript text, figures or download routes.

## Additional analyses

Reuse original primary five-fold splits and the primary external split. Refit the exact same random forest only to recover calibration probabilities and fit-only domain diagnostics; compare recovered test probabilities with the original saved values within 1e-12. Save calibration scores and per-candidate thresholds. No outcome-driven hyperparameter tuning.

Label-conditional calibration: for each class c, select the finite-sample quantile from calibration scores with observed class c; if none or the rank exceeds the class count, use infinity. This is row-level class conditioning and is not asserted to give source-level or shifted-distribution guarantees. Alpha grid 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30. Primary comparisons remain alpha 0.10. Report both class-specific coverage and false negatives among all truly cytotoxic observations.

Confidence-threshold abstention: accept the argmax label when max(p,1-p) >= t for t in {0.50,0.55,...,0.95,0.975,0.99}. Report risk and accepted fraction for all thresholds; do not select a best threshold on evaluation labels. Use all three original designs. Report precision-recall and ROC curves and average precision with class prevalence context.

Mixed-type distance: log1p numeric differences divided by each fitting feature's observed range, capped at one; plus categorical mismatch indicators; average across 12 equally weighted features. For each calibration/test row use its closest fitting observation. Unknown categories and out-of-range numeric inputs are separate flags. Define distance bins from the calibration-distance 50th/75th/90th percentiles per fold, independent of evaluation labels. Report row error/Brier/coverage/singleton rate with observation and source counts. Distance quantifies descriptor novelty, not mechanistic similarity or validated applicability.

Subgroups: class, assay, serum context, cell source species, primary size <=100 versus >100 nm, concentration <=10 versus (10,100] versus >100 micrograms/mL, and time <=24 versus >24 h. Retain every group in supplementary machine-readable results. Main displays require at least 30 observations and five sources; do not infer robust heterogeneity from smaller groups. Summaries across groups are exploratory and partly correlated. Concentration units remain flagged; no biological dose threshold is asserted.

Source-level diagnostics: show source size versus within-source coverage; describe correlations of group size/mean novelty and source Brier or set coverage. Report Spearman coefficient and sample counts without confirmatory p-values. Bootstrap whole source groups (2,000 resamples) for selected aggregate contrasts and conditional metrics; no interval that conditions on fixed predictions is represented as fitting uncertainty.

Learning curves: retain the original 29 calibration sources and external set. Sample nested fitting-source subsets of 10,20,40,60,86 from the 86 fitting sources using five seed-defined random source orders. Fit unchanged forests and calibrate all four rules. Report every repetition and median/range; repeated external evaluations are not independent external cohorts. Full-source fits should reproduce the original forest when the same estimator seed is used. Use a fixed estimator seed to focus on source sampling; preserve canonical row order. The five full-source entries are identical reference fits and not independent replicates.

Mechanistic/context checks: quantify shift in categorical frequencies and numerical distributions, fit-only unknown-category rates, class-conditional errors and calibration gaps. Feature importance may be evaluated only as prediction sensitivity (not causality); if used, specify permutation grouping and display variability.

Unit verification: retrieve original papers for workbook source IDs 13,84,87 and compare stated concentration units with workbook values. Do not silently correct records. If a specific error is demonstrated, record an explicit correction candidate and evaluate it as an additional labeled sensitivity; retain archived-data primary results unless a justified new analysis version is designated.

