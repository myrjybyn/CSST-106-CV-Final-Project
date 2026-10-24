# Milestone 2 Progress Report

## Task designation

| Member | Assigned responsibilities |
|---|---|
| **Urrea** | Dataset acquisition and preparation: source and license documentation, archive verification, organization, participant-based train/validation/test splits, and data card. |
| **Bauyon** | Geometric posture rules, clip-level baseline evaluation, automated tests, validation metrics, and progress-report documentation. |
| **Pagalanan** | Development environment, MediaPipe/OpenCV integration, preprocessing and feature extraction, command-line prototype, and sample-output preparation. |

**Project:** POSTURE CHECK: A Computer Vision-Based System for Real-Time Exercise Posture Monitoring and Feedback

**Reporting date:** 25 October 2026

**Estimated overall completion:** **50%**

## Progress against the proposal timeline

The proposal schedules environment setup, pose-estimation trials and initial posture logic for **17–22 October**, followed by geometric features and baseline classification during **23–29 October**. The environment, acquired data, feature extraction, initial rules and file-based prototype are now available. Webcam testing from the earlier phase remains pending. Work is therefore within the current core-implementation period, with that earlier integration task carried forward.

The **50% completion estimate** reflects a functioning initial path from image/video input through pose estimation, geometric features and rules to saved output, together with prepared datasets and measured validation results. It is an engineering estimate, not a measured fraction of code or a claim that the final system is half as accurate as required. Reliable feedback, temporal behavior, webcam integration, additional exercise modes and final evaluation remain substantial work.

## Completed work and evidence

1. **Reproducible environment:** root `requirements.txt` pins dependencies. The [README](../README.md) documents Python 3.12 setup, model acquisition and execution. Dependency consistency passed; Windows instructions have not been tested.
2. **Dataset acquisition and preparation:** downloads passed published checksum checks. All 294 referenced Mendeley clips are present, with unchanged participant-disjoint splits of 210 training, 48 validation and 36 test clips. REHAB24 acquisition includes 130 videos, 260 joint arrays and segmentation metadata. Its prepared subset contains 476 repetitions split 354/65/57. Sources, licenses, labeling, class counts and preprocessing are summarized in the [current data card](MILESTONE2_DATA_CARD.md); [acquisition evidence](DATA_ACQUISITION.md) records paths and checksums.
3. **Feature extraction and algorithm:** code in `src/posture_check/` performs OpenCV decoding, BGR-to-RGB conversion, pretrained MediaPipe inference, visibility/size checks and aspect-corrected knee/hip angles and trunk lean. Fixed provisional rules produce frame feedback and whole-clip squat predictions. No custom model training is required by this approach.
4. **Prototype and supporting evidence:** `python run.py --input <image-or-video> --output <output-file>` writes annotated output and JSON. A continuous training-video run produced 463 verified output frames. **Eleven tests passed**, and [six genuine sample outputs](evidence/milestone2/README.md) are saved with provenance.

## Measured validation result

The current baseline evaluated **eight side-view squat validation clips**, covering four participants and **3,735 frames**. Whole-clip predictions were compared with source clip labels; no correctness labels were invented for individual frames.

| Measure | Result |
|---|---:|
| Overall clip accuracy, including abstention as a miss | **50% (4/8)** |
| Accuracy among assessed clips | **57.14% (4/7)** |
| Abstentions | **1 clip** |
| Macro F1, with abstentions counted as misses | **0.536** |
| Pose inference and rule-processing speed | **26.11 FPS** |

FPS excludes drawing/encoding and does not establish development-laptop webcam performance. The [full result](results/mendeley_squat_side_validation.json) includes the confusion matrix; the [protocol](VALIDATION_PROTOCOL.md) records thresholds fixed before validation. The test partition was not decoded or evaluated.

## Pending work and blockers

The initial baseline covers **side-view squats only**. Accuracy remains below the proposal's final **80% target**. Occlusion, blurred imagery, clutter and erroneous poses affect the features. A known small equipment detection is now rejected, but larger false poses remain possible. The demonstration clip itself is incorrectly flagged despite its source-good label.

There is no current acquisition or dependency blocker. Remaining technical work includes better pose-quality handling and fault definitions, temporal smoothing, movement-phase tracking, repetition counting, webcam capture, and push-up/lunge/jumping-jack rules. REHAB24 coordinate, frame-rate and annotation-index conventions still need mapping before integration. Manually verified landmark reliability and final held-out accuracy remain unmeasured.

## Revised plan

| Proposal period | Revised priorities |
|---|---|
| **25–29 October: core implementation** | Use training material to investigate pose failures and refine squat criteria; begin webcam integration and preserve the current baseline result. |
| **30 October–12 November: 80% checkpoint** | Add smoothing, phase tracking and repetition counting; measure controlled webcam behavior; expand exercise modes only as reliability permits. Record versioned validation without repeatedly tuning to the same clips. |
| **13–19 November: finalization** | Freeze the method, evaluate held-out/manual-review samples, measure laptop FPS, finalize documentation and rehearse the live demonstration. Retain the proposal's squat-focused fallback if other modes remain unreliable. |

Before submission, review and commit the deliverables, tag the submission commit **`cp2-50`**, and submit the repository link. The [hand-in checklist](MILESTONE2_HANDIN.md) identifies the supporting files; large media remains outside Git.
