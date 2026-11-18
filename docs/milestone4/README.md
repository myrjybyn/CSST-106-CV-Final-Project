# Checkpoint 4: draft technical documentation (item 6)

Submit one document: [Checkpoint4_Technical_Documentation_Draft.docx](Checkpoint4_Technical_Documentation_Draft.docx). A [Markdown preview](Checkpoint4_Technical_Documentation_Draft.md) contains the same report text for review.

Items 1-5 are existing implementation and testing work. This document fulfills item 6 by writing up that work in the required report sections:

1. Introduction: problem, objectives and project scope.
2. Data: sources, labels, participant allocation and separate evaluation sets.
3. Method: pose pipeline, interface, counting, form rules and calibration policy.
4. Experiments and results: setup, metrics, original and prospective results, laptop timing and checkpoint-3 comparison.

Discussion and limitations follow the experiments. Appendices retain the recorded test cases, interface/integration evidence and reproducibility references. Physical webcam checks remain **PENDING**.

## Existing measured evidence

- [Calibrated laptop summary](../calibration/LAPTOP_BENCHMARK_STATUS.md): **23.67 FPS / 42.25 ms per frame**; checkpoint-3 main **12.83 FPS / 77.93 ms**. Cloud timings remain separate.
- [Laptop JSON](../calibration/laptop_benchmark.json), [CSV](../calibration/laptop_benchmark.csv), [validation audit](../calibration/laptop_benchmark_validation.json) and [post-run hardware verification](../calibration/laptop_environment_verification.json).
- [Original 12-clip test results](heldout_results.json): historical CP3 versus pre-calibration v2; v2 accuracy 41.7%.
- [New 16-clip prospective results](../calibration/prospective_results.json): 43.8% uncalibrated versus 50.0% calibrated. This is a different set from the original 12 clips.
- [Known-clip historical cloud results](known_clip_results.json), [25 recorded cases](test_cases.csv), [functional cases](functional_test_cases.json) and [interface evidence](evidence/).

## One current report

The earlier application/testing report, calibration supplement and provisional combined report are superseded. Copies are retained under [milestone-four history](history/) and [calibration history](../calibration/history/); they are historical records, not additional submission documents. Original measurements remain unchanged.

Rebuild the single item-6 draft from existing evidence:

```bash
python scripts/milestone4/update_current_report.py
```

The builder uses report-only `python-docx` (also supported under `outputs/report_dependencies/`). It checks existing evidence without rerunning model inference or changing parameters. The older `build_report.py` scripts target historical documents and are not the current draft generator.

Submission source matches commit `c5196f6b2778c892d4d459090780f6d0bc6685fb` (message names `cp4-80`). The existing `cp4-80` tag was fetched from origin and verified at that commit; its target is unchanged. Documentation updates are maintained as subsequent commits on main.
