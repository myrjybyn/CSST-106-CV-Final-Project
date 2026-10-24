# Six milestone-two sample outputs

These are six distinct frames extracted from the actual version-two annotated
prototype video, at fixed frame indices 0, 75, 150, 225, 300 and 400. They satisfy
the sample-output option; they are not six separate experiments or a screen recording.
The full run was decoded and verified to contain 463 output frames.

Input: `subject_005_squat_good_side.mp4` from the training partition.
Source: *Multi-View Fitness Exercise Video Dataset*,
[Mendeley Data v3, DOI 10.17632/kgbb3yn47p.3](https://doi.org/10.17632/kgbb3yn47p.3).
License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Changes: pose and rule overlays added, then frames extracted as JPEG; source face
blurring retained. Attribution is to the dataset creators credited in the source record.

The source clip is labeled good, but the provisional clip baseline predicts
incorrect. These samples demonstrate pipeline output, not verified posture
correctness. A frame's `rule_pass` is not a ground-truth form label. See
[the validation report](../../results/mendeley_squat_side_validation.json) for
the measured failures and abstention. [manifest.json](manifest.json) records
frame indices, features, rule status, provenance and file checksums.

| Sample | Actual frame output |
|---|---|
| 1 — frame 0 | [01_frame_000.jpg](01_frame_000.jpg) |
| 2 — frame 75 | [02_frame_075.jpg](02_frame_075.jpg) |
| 3 — frame 150 | [03_frame_150.jpg](03_frame_150.jpg) |
| 4 — frame 225 | [04_frame_225.jpg](04_frame_225.jpg) |
| 5 — frame 300 | [05_frame_300.jpg](05_frame_300.jpg) |
| 6 — frame 400 | [06_frame_400.jpg](06_frame_400.jpg) |
