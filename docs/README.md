# Project documentation and milestone reports

All submission documents and reports are maintained under this directory.
The repository-root README and the milestone-one component README remain entry
points for setup and execution. Data, code, weights and runtime outputs retain
their respective directories.

## Proposal and design

- [Project proposal](Project_Proposal.pdf)
- [Workflow diagram](design/Workflow.png) and [editable diagram](design/Workflow.drawio)

## Milestone 1

- [Data evidence and feasibility review](milestone1/DATA_EVIDENCE.md)
- Original sample data and generated feasibility images remain in
  `milestone1/posture_check/`; they are inputs/runtime artifacts rather than reports.

## Milestone 2

- [Progress report and task designation](MILESTONE2_STATUS.md)
- [Hand-in checklist](MILESTONE2_HANDIN.md)
- [Current data card](MILESTONE2_DATA_CARD.md)
- [Dataset preparation](DATASET_PREPARATION_M2.md) and [acquisition evidence](DATA_ACQUISITION.md)
- Original cards: [Mendeley](data_cards/DATA_CARD_MENDELEY.md), [REHAB24](data_cards/DATA_CARD_REHAB24.md)
- [Validation protocol](VALIDATION_PROTOCOL.md), [measured results](results/),
  and [six sample outputs](evidence/milestone2/README.md)

## Milestone 3

- [Submitted PDF report](phase3/PHASE_3_Report.pdf)
- [Editable testing report](phase3/Phase3_Testing_Report_Editable.docx)
- [Comparison CSV](phase3/comparison_summary.csv)
- [Laptop benchmark summary](phase3/LAPTOP_BENCHMARK_STATUS.md), [per-exercise timings](phase3/laptop_comparison.csv), and [completed log](phase3/laptop_test_log.json)
- [Reference metrics and confusion matrices](phase3/reference_metrics.json)
- [User-supplied reference annotations](phase3/reference_annotations.json)
- [Fixed test manifest](phase3/test_manifest.json) and [original test log](phase3/test_log.json)
- [Failure manifest](phase3/failure_manifest.json) and [failure contact sheet](phase3/failure_contact_sheet.jpg)

Historical logs preserve paths used during their original runs, including the
former `reports/phase3/` location. Current files and new generator outputs use
`docs/phase3/`. No inference results were changed by this reorganization.

Generated download ZIPs are stored locally in `docs/` and excluded from Git;
the underlying report, scripts, metrics and evidence are versioned here.

## Milestone 4

- [Single draft technical documentation, item 6 (DOCX)](milestone4/Checkpoint4_Technical_Documentation_Draft.docx) and [review preview](milestone4/Checkpoint4_Technical_Documentation_Draft.md): introduction, data, method and experiments, using the completed work for items 1-5.
- [Validated calibrated laptop benchmark and CP3 comparison](calibration/LAPTOP_BENCHMARK_STATUS.md): **23.67 FPS / 42.25 ms per frame**, separately from cloud results. Physical webcam acceptance remains **PENDING**.
- [Hand-in status and commands](milestone4/README.md)
- [Historical reports archive](milestone4/history/): superseded versions, not additional submission documents.
- [Held-out test results](milestone4/heldout_results.json) and [CSV](milestone4/heldout_results.csv)
- [All 25 test cases](milestone4/test_cases.csv)
- [Laptop benchmark instructions](milestone4/LAPTOP_BENCHMARK.txt)
- [Interface captures and GUI test log](milestone4/evidence/)

## Ongoing development

- [Pose coverage and repetition-counting review](development/POSE_COUNTING_REVIEW.md)
- [Fixed training-only comparison manifest](development/pose_counting_manifest.json)
- [Development measurements](development/pose_counting_comparison.json)
- [Known-clip regression check](development/phase3_regression.json) — previously inspected clips, not a fresh held-out test.

## Current form calibration

- [Calibration protocol and current status](calibration/README.md)
- [Historical calibration report archive](calibration/history/): calibration is now written into the single item-6 draft above.
- [Fitting and validation decisions](calibration/fitting_results.json)
- [Prospective test results](calibration/prospective_results.json) and [CSV](calibration/prospective_results.csv)
- [Calibrated-version laptop instructions](calibration/LAPTOP_BENCHMARK.txt)

The application/testing report, calibration supplement and provisional combined report are archived under `history/`. Only the item-6 technical documentation draft above is current. It has introduction, data, method and experiments sections. The original 12-clip test (41.7% pre-calibration v2) and new 16-clip prospective test (43.8% uncalibrated versus 50.0% calibrated) remain distinct.

Version verification matches the calibrated frozen artifacts to submission commit `c5196f6b2778c892d4d459090780f6d0bc6685fb`, whose message names `cp4-80`. The existing `cp4-80` tag was fetched from origin and verified at that commit; its target is unchanged. See the [validation audit](calibration/laptop_benchmark_validation.json).

## Current guided-rule comparison

- [Dataset correction and cleaned comparison](guided_evaluation/cleaned_results.md) — conflicting exact-duplicate labels excluded in a separately disclosed post-hoc analysis; original results preserved.
- [Protocol and reproduction](guided_evaluation/README.md)
- [Frozen methods and 16-video selection](guided_evaluation/freeze.json)
- [Results tables](guided_evaluation/results.md), [raw results](guided_evaluation/results.json), and [per-clip CSV](guided_evaluation/results.csv)

This compares existing fixed clip rules with current guided-session rules on the
same previously exposed squat/push-up videos. It is separate from the historical
calibrated classifier and does not measure automatic stopping or live webcam speed.
