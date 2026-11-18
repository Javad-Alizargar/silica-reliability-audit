# Statistical analysis plan

Version 1.0, 2026-11-18. Written after schema and label-count inspection and before fitting predictive models. This is an exploratory secondary analysis, not a registered confirmatory study.

## Question and contribution

Can prediction sets calibrated on historical silica nanoparticle studies retain useful coverage and issue informative single-label predictions for unseen studies? We compare the statistical unit used for calibration while keeping the classifier and held-out observations fixed. Neither study-held-out validation nor conformal prediction is claimed as a new method. The proposed contribution is a reproducible application that distinguishes row coverage, study-balanced coverage, whole-study coverage, and the cost of abstention under a fixed external shift.

## Data and endpoint

Use the original Martin et al. ACS Nano 2023 workbook (10.1021/acsnano.2c11968.s003). Preserve Main_Dataset and Independent_Dataset as development and external sets. Development has 4,124 observations from 115 publication IDs; external has 905 observations in 26 source groups, including one in-house group. These are assay conditions, not independent patients or nanoparticle identities. Map source IDs to the References sheet and normalize DOIs. Merge any source IDs referring to the same DOI before splitting; otherwise retain the original identifier. Do not claim laboratory independence.

The endpoint is the published binary cytotoxicity label, corresponding to cell viability below 70% in the source methods. This is an in vitro assay endpoint, not human safety. The external sheet additionally has continuous viability, which must never be a predictor. Retain all published labels; flag disagreements with continuous thresholding rather than silently correcting them. The original size range reaches 1,000 nm, so describe the evidence as the source-defined silica particle dataset and include a <=100 nm sensitivity.

Remove exact duplicate rows within source and cohort, using all original predictor and outcome fields; preserve conflicting outcomes. Audit cross-cohort identical predictor profiles and DOI overlap, with matched-profile exclusion as a sensitivity if overlap exists. Keep missing characterization categories such as not_determined explicit. Do not infer missing numerical particle measurements from categorical bins.

## Predictors and fixed models

Use a predeclared 12-variable context set: primary size (nm), concentration (micrograms/mL), exposure time (h), serum context, surface modification, particle shape, synthesis route, cell source species, cell ID, cell disease status, exposure medium, and viability assay. Assay type is a planned experimental condition, not an outcome. Exclude publication ID, author/year, continuous viability, labels, positive-control results, interference testing and correlated readout descriptions. Numeric predictors are log1p transformed, median imputed and standardized inside each training partition. Categorical predictors are one-hot encoded with unknown categories ignored. No global feature selection or target encoding.

Four fixed baselines: development-class prevalence; logistic regression (C=1, max_iter=2000); random forest (300 trees, min_samples_leaf=3, max_features=1.0, unweighted); histogram gradient boosting (150 iterations, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1, early_stopping=False). The random forest is the prespecified primary classifier for calibration comparisons. No model or hyperparameter is selected using external outcomes. Fixed settings make nested model-selection CV unnecessary; all transformations remain inside training partitions.

## Validation and calibration

Development: five-fold shuffled stratified row CV and five-fold shuffled study GroupKFold. Within each outer training partition, reserve 25% of rows (row design) or groups (study design) for calibration. The group design keeps source groups disjoint across fit, calibration and test. The row design intentionally permits shared source groups and is a diagnostic of within-source interpolation, not an estimate of new-study performance. Use common outer assignments for all models. Primary seed 20261118; seeds +1 and +2 are predeclared sensitivity repeats.

External: preserve all 26 external source groups as a fixed evaluation set. Reserve 25% of the 115 development groups for calibration, fit on the rest, and apply the unchanged classifier and thresholds to the external observations. Repeat with four further development split seeds to report split sensitivity, without selecting a seed. External performance is retrospective reuse of an established benchmark, not prospective or new laboratory validation.

For each fitted classifier, use nonconformity score 1 minus the probability assigned to the true class. At alpha=0.10 (primary), compare (a) every calibration row, (b) one label-blind uniformly sampled row per calibration study, and (c) the maximum score within each calibration study. For n calibration units, use rank ceil((n+1)(1-alpha)); if the rank exceeds n use infinity, yielding both labels. Include candidate label c when its score is <= the selected threshold. Evaluate alpha=0.05 and 0.20 as predeclared sensitivity. Never force an empty set to contain a label.

Row-pooled calibration targets a row under row exchangeability. One-per-study calibration targets a random row from a random new study under appropriate hierarchical exchangeability. Study-maximum calibration targets simultaneous coverage of all recorded rows in a random new study under exchangeability of whole study objects. These targets differ and will be reported separately. None provides an unconditional guarantee under temporal or laboratory distribution shift. In the row validation design, group methods are diagnostic only because study disjointness is violated.

## Estimands and uncertainty

Primary external outcomes for the random forest at alpha=0.10: whole-study coverage (fraction of external source groups with every true label contained) and singleton rate (fraction of observations receiving exactly one label) for study-maximum and row-pooled calibration. Also report study-balanced row coverage and the paired difference in singleton rate. Do not turn coverage targets into assertions of demonstrated safety.

Secondary outcomes: row-weighted AUROC, average precision, Brier score, balanced accuracy at 0.5, study-balanced Brier score, row coverage, mean set size, empty-set rate, singleton error rate, and false-negative fraction among singleton predictions. Singleton error is conditional on accepted predictions and is not bounded by marginal conformal coverage. Describe missing denominators explicitly.

Use 2,000 percentile bootstrap resamples of source groups for primary fixed-prediction intervals and paired contrasts. Resample all rows within each selected group together, retaining multiplicity. These intervals condition on fitted models and split choices; they do not include model refitting uncertainty. Refit sensitivity seeds separately. No p-values or significance stars; exploratory comparisons do not support confirmatory multiple-testing claims.

## Sensitivity and negative controls

Report independent literature sources (exclude in-house ID 116), <=100 nm test observations with original models, repeated split seeds, and an assay-free predictor ablation for the primary random forest. The size restriction is a test-subset analysis, not an independently trained nanoscale-only model. If exact cross-cohort profiles exist, report results excluding them. Run a global training-label permutation control in grouped development validation to check for gross target leakage; acknowledge finite-sample chance variation. Save all fold memberships and enforce disjointness programmatically.

## Output gates

Save observed data audit, out-of-sample probabilities, prediction-set membership, thresholds, training/calibration/test memberships, environment, input and code hashes, canonical statistics, plot source tables and executable plotting code. Report weak or negative performance without changing the question.
