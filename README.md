# Real-Time Exercise Posture Detection and Correction Using Computer Vision

Milestone reports, the proposal, data cards and testing evidence are indexed in
[docs/README.md](docs/README.md). The editable Phase 3 report is at
[docs/phase3/Phase3_Testing_Report.docx](docs/phase3/Phase3_Testing_Report.docx).

A computer vision-based system designed to analyze exercise posture through a webcam, evaluate body movements, and provide real-time feedback to help users improve their exercise form.

## Overview

Performing exercises with improper posture can reduce workout effectiveness and increase the risk of injury. Beginners, in particular, may have difficulty identifying incorrect form without guidance from a trainer.

This project aims to address this problem by developing a real-time exercise posture detection and correction system using computer vision. The system will detect human body landmarks, calculate relevant joint angles and body alignment measurements, and compare these measurements against predefined exercise-specific criteria.

The initial scope covers four common exercises:

- Squats
- Push-ups
- Lunges
- Jumping jacks

The system is being developed as a Computer Vision Final Project for CSST 106 at Laguna State Polytechnic University.

## Objectives

- Detect and track human body landmarks using a webcam.
- Analyze body posture and movement during selected exercises.
- Identify potentially incorrect exercise form using predefined rules.
- Provide real-time visual feedback to users.
- Implement repetition counting where applicable.
- Evaluate posture classification performance and system responsiveness.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Primary programming language |
| MediaPipe Pose Landmarker | Human pose estimation and body landmark detection |
| OpenCV | Webcam access, video frame processing, and visual output |
| Geometric calculations | Joint-angle, relative-distance, and body-alignment measurements |
| Rule-based classification | Evaluation of exercise posture against predefined criteria |

## Milestone 2: how to run

The initial implementation supports **squats in side-view images or videos**.
It uses the pretrained MediaPipe Tasks Pose Landmarker and provisional geometric
rules; no custom model training is required. Other exercise evaluators, temporal
smoothing, repetition counting and live webcam input remain future work.

Use **Python 3.12**, from the repository root. On Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
export PYTHONPATH="$PWD/src"
export MPLCONFIGDIR="$PWD/.venv/matplotlib"
python scripts/download_pose_model.py
python run.py --input milestone1/posture_check/data/samples/squat_01.jpg --output outputs/squat_01.png
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`, then set
`$env:PYTHONPATH = "$PWD\src"` and `$env:MPLCONFIGDIR = "$PWD\.venv\matplotlib"`
instead of the two `export` commands. Use `py -3.12 -m venv .venv` to create the environment.
Windows installation has not yet been tested.

The model download requires HTTPS access to `storage.googleapis.com`. The script
downloads Google's version-1 Lite Tasks bundle using TLS verification, checks
the pinned SHA256 and validates the archive. Weights are kept out of Git.
Dependencies are pinned, including transitive packages. Install only this root
requirements file for milestone 2; do not combine it with milestone 1's headless
OpenCV requirement, since the two OpenCV distributions share the `cv2` module.
Linux needs the usual OpenCV shared libraries (including `libGL.so.1` and
`libglib-2.0.so.0`); these are available in the current cloud environment.

After setup, one command processes a video:

```bash
python run.py --input /path/to/squat.mp4 --output outputs/squat.mp4
```

The program writes the annotated image/video and an adjacent `.json` report with
per-frame features, phase, rule status, pose presence and processing time. Video
JSON also contains one provisional whole-clip prediction, measurements and reasons.
The root `run.py` entry point does not require setting `PYTHONPATH`; the export
above is for development tests and the validation script. Video
output has no audio. `rule_pass` means only that the provisional rule did not
flag the frame; it does **not** mean the exercise form is correct. Hidden or
out-of-frame joints and small pose detections return `unassessable`. A side view must be supplied by the
operator; the current implementation does not automatically verify camera view.

### Checks and validation

```bash
python -m unittest discover -s tests -v
python scripts/evaluate_validation.py --media-root /path/to/extracted --output outputs/side_validation_metrics.json
```

The media root must contain `Dataset Subject-wise/` matching the committed
Mendeley inventory. The current validation runner uses **eight side-view squat
validation videos**, requires every selected file, and reports clip-level
classification metrics, abstentions, FPS and feature coverage. Clip predictions
are compared to source clip labels; those labels are never copied onto frames.
See the [fixed validation protocol](docs/VALIDATION_PROTOCOL.md) for thresholds
and metric denominators. The runner never uses the test partition. Timing excludes
rendering/encoding; a separate throughput figure includes decoding. Coverage is
not landmark accuracy. Unverified milestone-one images are excluded from
classification metrics.

Large raw media is excluded from Git. The prepared cloud instance now contains
all 294 Mendeley clips referenced by the split manifests under `data/raw/mendeley`.
REHAB24 videos, 2D joint files and segmentation metadata are also downloaded and
extracted locally; see [acquisition paths and checksums](docs/DATA_ACQUISITION.md).
Run validation there with `--media-root data/raw/mendeley`. A fresh clone still
needs a separate media download.
See [milestone status and limitations](docs/MILESTONE2_STATUS.md) and
[dataset preparation](docs/DATASET_PREPARATION_M2.md). The real image and continuous
video pipelines have run. The [earlier version-one benchmark](docs/results/mendeley_squat_validation.json)
measured 31.88 processing FPS over 24 clips / 11,090 frames across all views.
The current version-two side-view result is recorded separately in
[results/mendeley_squat_side_validation.json](docs/results/mendeley_squat_side_validation.json).
Visual review exposed a small false pose on gym equipment in an obscured training
frame; the new body-size gate rejects that regression case. This does not establish
that all accepted detections or posture predictions are correct.
