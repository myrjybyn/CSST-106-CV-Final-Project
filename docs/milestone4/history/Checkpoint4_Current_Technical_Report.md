
# POSTURE CHECK

Current technical report — Checkpoint 4 application, calibration, evaluation and laptop benchmark. Updated 19 November 2026 (Asia/Manila). Submission snapshot: c5196f6 (commit message: cp4-80). No tag was created or moved.

This document consolidates the application/testing report and the calibration supplement. Historical checkpoint-3 and pre-calibration v2 evidence stays intact. The calibrated laptop run is complete at 23.67 FPS / 42.25 ms per frame. General form recognition remains limited: 8/16 correct on the new prospective set. Physical webcam acceptance remains PENDING.


## 1. Application and interface

The desktop app integrates a selected-exercise MediaPipe Lite VIDEO pipeline, conservative black-border removal, confidence and geometry gates, temporal smoothing, movement counting, per-frame geometry feedback and a cumulative session-form estimate. Users select squat, push-up, lunge or jumping jacks; automatic exercise recognition is not implemented. File images/videos use the CLI. Launch the GUI with python app.py.

Start Camera moves the home menu into a sidebar. The preview shows skeleton lines, feedback, movement phase, estimated reps and FPS. Settings select camera index, mirror preview and skeleton display. Stop/Start starts a new session; Quit releases capture. Session form updates about once per second from cumulative angle summaries. Whole-clip calibration does not establish frame-level or live-prefix form accuracy. The GUI does not save camera frames.

Home interface from historical cloud GUI integration; recorded input, not physical webcam evidence.

![Home interface from historical cloud GUI integration; recorded input, not physical webcam evidence.](evidence/home.png)

Accepted preview with pose, feedback and counters during historical video-substitution integration.

![Accepted preview with pose, feedback and counters during historical video-substitution integration.](evidence/live.png)

Calibrated session estimate during the validation-video GUI smoke test. Capture release and window closure passed; no physical-camera claim.

![Calibrated session estimate during the validation-video GUI smoke test. Capture release and window closure passed; no physical-camera claim.](../calibration/evidence/session_estimate.png)


## 2. Version and benchmark verification

The complete laptop log matches the calibrated evaluation freeze, including 22 source/profile/plan hashes, the Lite model checksum, all four input hashes, four split manifests, 1,700 decoded frames and recomputed aggregate/per-exercise summaries. JSON and CSV agree. The same 22 files in submission commit c5196f6b2778c892d4d459090780f6d0bc6685fb match the freeze byte for byte. The cp4-80 tag is absent locally; the commit message identifies the submission. A tag identity cannot be certified from this checkout. No application/model parameters, decision thresholds, freeze files or tags were modified for this report.

Machine-readable audit: docs/calibration/laptop_benchmark_validation.json. Raw log: docs/calibration/laptop_benchmark.json; completion 2026-11-18T15:51:50.929943+00:00. Exact log checksum is 6eb3cc1641094d133646fd95e5d839f1ac8305067c775a70ca65c5d0e35d12da.


## Measured laptop performance and checkpoint 3 comparison

Benchmark completed 18 November 2026, 23:51:50 Asia/Manila. Four original known clips; 1,700 decoded frames; one sequential pass. Processing FPS = total frames / total processing seconds; milliseconds/frame = 1000 × total processing seconds / total frames. Per-clip FPS values are not averaged arithmetically.

| Laptop version | Frames | Processing FPS | ms/frame | Count MAE |
| --- | --- | --- | --- | --- |
| Checkpoint 3 main (historical) | 1700 | 12.83 | 77.93 | 3.50 |
| Calibrated checkpoint 4 current | 1700 | 23.67 | 42.25 | 1.75 |

Observed change: +10.84 FPS (+84.5%; 1.84× throughput); -35.68 ms/frame (-45.8%). Both logs contain the same four clip identities and frame counts. This is an observed comparison across runs, not a controlled estimate of code-only speedup.

| Clip / frames | CP3 FPS / ms | Current FPS / ms | Reference / CP3 / current reps | Current form |
| --- | --- | --- | --- | --- |
| Push-up / 363 | 13.85 / 72.22 | 23.63 / 42.32 | 4 / 2 / 2 | correct |
| Squat / 483 | 13.64 / 73.31 | 23.68 / 42.24 | 4 / 4 / 4 | correct |
| Lunge / 278 | 14.11 / 70.88 | 22.48 / 44.49 | 3 / 0 / 2 | correct |
| Jumping jacks / 576 | 11.26 / 88.80 | 24.32 / 41.12 | 10 / 1 / 6 | unassessable |

Timing scope: CPU pose inference, preprocessing, rules and temporal updates; excludes decoding, drawing, encoding and model initialization. Decode-plus-processing throughput logged separately. It does not establish displayed webcam FPS, end-to-end GUI latency, or sustained physical-camera performance. CP3 full-run throughput includes output work; current decode-plus-processing throughput excludes output encoding, so those end-to-end fields are not compared.

| Environment field | Current laptop evidence |
| --- | --- |
| CPU / RAM (post-run verification) | AMD Athlon Silver 3050U with Radeon Graphics; 5.94 GiB |
| OS / logical processors | Windows-11-10.0.26200-SP0; 2 logical CPUs |
| Power scheme captured during benchmark | Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced) |
| Python | 3.13.0 |
| mediapipe | 1.2.0 |
| numpy | 2.2.3 |
| opencv-contrib-python | 4.11.0.86 |
| pillow | 11.1.0 |
| Benchmark-time CPU/RAM capture | Incomplete: null CPU, RAM 0; raw log retained |

CPU model and RAM were checked after the run using the Windows registry and GlobalMemoryStatusEx, recorded in docs/calibration/laptop_environment_verification.json. They agree with the historical CP3 hardware (AMD Athlon Silver 3050U; 5.94 GiB). Windows build, Python 3.13.0, two logical CPUs and Balanced power also agree across logs. CP3 does not record dependency versions, so dependency parity cannot be verified. Plugged-in state, thermals and background workload were not logged. Current dependency names/versions above are exactly the reported distribution metadata, including mediapipe 1.2.0.

Known clips show 75% form agreement (three correct decisions, one jumping-jack abstention), count MAE 1.75 reps/clip, and one exact count. All four reference forms are correct and user-supplied after earlier predictions. These clips cannot establish incorrect-form recall or independent generalization. The squat row records calibration_id=form-rules-v1; push-up was not promoted, and lunge/jack form rules remain provisional.

Validation: PASS: complete log; exact calibrated frozen artifact match. All frozen source/profile/plan, model, manifests, clip hashes, frame counts, summaries and CSV values were checked. Submission source is byte-identical to commit c5196f6b2778c892d4d459090780f6d0bc6685fb. Local tag status: absent locally; commit message identifies cp4-80; no tag created or moved.

Before inference, CRLF text was restored to exact frozen LF bytes. The Python runner normalized source-hash dictionary keys from Windows backslashes to forward slashes. No checksum was bypassed; no evaluation algorithm or freeze was changed.

Physical webcam acceptance: PENDING. Camera open/start/stop/restart, release on Quit, lighting/occlusion behavior, and sustained displayed FPS on an actual camera require a separately recorded acceptance run.


## 3. Historical cloud timing is separate

| Cloud workload / version | Clips / frames | FPS | ms/frame |
| --- | --- | --- | --- |
| Original 12-clip test: CP3 rerun | 12 / 4,124 | 33.15 | 30.16 |
| Original 12-clip test: pre-calibration v2 | 12 / 4,124 | 50.81 | 19.68 |
| Four known clips: pre-calibration v2 | 4 / 1,700 | 50.97 | 19.62 |
| Prospective shared feature pass: calibrated v3 | 16 / 4,517 | 55.63 | 17.98 |

Cloud environment: {"location": "cloud", "python": "3.12.14", "platform": "Linux-6.18.57-x86_64-with-glibc2.41", "cpu": "AMD EPYC 9V74 80-Core Processor", "logical_cpus": 5, "dependencies": {"mediapipe": "0.10.21", "numpy": "1.26.4", "opencv-contrib-python": "4.11.0.86", "pillow": "12.3.0"}}. Shared cloud CPU scheduling and different Python/dependency versions prevent attribution of cloud/laptop differences to code. Prospective uncalibrated/current decisions reuse the same inference stream; the duplicated timing summaries are not two independent speed measurements.


## 4. Datasets, fitting and calibration decisions

| Set | Clips / people | Purpose |
| --- | --- | --- |
| Original exposed side-view test | 12 / 3 (018, 020, 022) | Historical CP3 vs pre-calibration v2 comparison; excluded from calibration |
| Calibration fitting | 54 / 14 overall; 13 push-up | Fit candidates; leave-one-fitting-participant-out selection |
| Calibration validation | 16 / 4 (004, 006, 011, 024) | Promotion guard; no test tuning |
| New prospective test | 16 / 4 (017, 019, 021, 023) | Reserved from unused original training inventory before extraction |
| Known four clips | 4; user-supplied excerpts | Speed/regression only; previously inspected |

Fitting, validation and prospective participants are disjoint in plan.json; the original CSV split files remain as historical inventory. The prospective set is a revised split, not newly acquired external data. Whole-clip source labels do not label every frame or repetition. Both exposed test sets now require replacement for any future parameter tuning.

Candidate rules use numerical angle distributions only. Filenames, subject IDs, recording length, FPS, quality and per-frame form labels are excluded from classifier inputs. Fixed gates require 30 valid frames, 50% coverage and 20 degrees of movement. Depth 1/2 and minimum leaves 4/6 are selected using participant-held-out predictions; leaves require at least two subjects. Promotion requires higher validation macro F1 with no loss of incorrect-form recall or fitting OOF macro F1.

| Exercise | Fit OOF macro F1 | Validation macro F1 before / candidate | Decision |
| --- | --- | --- | --- |
| Squat | 0.641 | 0.333 / 0.500 | Enabled |
| Push-up | 0.666 | 0.619 / 0.619 | Not promoted |

Squat uses the fitted hip-angle p10 split at 71.15 degrees, a dataset-derived decision threshold rather than a universal recommended angle. Validation incorrect-squat recall increases from 0% to 50% while accuracy stays 4/8. Push-up ties validation macro F1 at 0.619 and lowers incorrect-form recall from 75% to 50%, so it is not promoted. Lunge/jack form rules remain provisional. Pose weights, preprocessing, motion counting and geometry gates were not calibrated.


## 5. Accuracy results: two distinct test sets

| Set / metric | Reference method | Compared method |
| --- | --- | --- |
| Original 12: accuracy | 58.3% | 41.7% |
| Original 12: macro F1 | 0.556 (CP3 rerun) | 0.413 (pre-calibration v2) |
| Original 12: usable-pose coverage | 82.0% | 95.5% |
| New prospective 16: accuracy | 43.8% (7/16; uncalibrated tracked) | 50.0% (8/16; deployed calibrated) |
| New prospective 16: macro F1 | 0.430 | 0.517 |
| New prospective 16: incorrect-form recall | 25.0% | 50.0% |
| New prospective 16: correct-form recall | 62.5% | 50.0% |
| New prospective 16: assessed / abstained | 15 / 1 | 15 / 1 |

The historical 41.7% and prospective 50.0% use different subjects and cannot be presented as a matched improvement. The valid calibration comparison is 43.8% to 50.0% on the same 16 prospective clips and shared tracked features. The original historical evaluation compared reconstructed CP3 source and v2 on the same 12 clips; it does not evaluate calibrated v3 on those clips. Coverage is accepted geometry, not independently measured landmark accuracy.

| Prospective exercise (8 each) | Accuracy before / after | Macro F1 before / after |
| --- | --- | --- |
| Squat | 50.0% / 62.5% | 0.500 / 0.661 |
| Push-up | 37.5% / 37.5% | 0.365 / 0.365 |

| Prospective uncalibrated reference | Predicted correct | Incorrect | Abstain |
| --- | --- | --- | --- |
| correct | 5 | 2 | 1 |
| incorrect | 6 | 2 | 0 |

| Prospective current reference | Predicted correct | Incorrect | Abstain |
| --- | --- | --- | --- |
| correct | 4 | 3 | 1 |
| incorrect | 4 | 4 | 0 |

Deployed prospective outcomes retain four false accepts, three false flags and one abstention. Incorrect-squat recall improves from 1/4 to 3/4; one more correct squat is falsely flagged. Push-up remains 3/8. Repetition-reference labels are unavailable on both Mendeley evaluation sets, so no held-out count MAE is reported.


## 6. Test cases and integration evidence

Historical v2 inventory: 25 cases, 18 PASS, 7 FAIL, 8 hard/edge cases. The 12 real classification cases remain separate from 12 functional passes and one GUI integration pass. These tests were not rerun for this documentation update. Prior reports record 56 software tests for v2 and 63 for calibrated v3; those are recorded run claims, not new execution results.

| Historical case | Input / condition | Expected | Actual | Status |
| --- | --- | --- | --- | --- |
| H01 | mendeley/Dataset Subject-wise/subject_018/push_up/bad/side/subject_018_push_up_bad_side.mp4; source side view; full original video | incorrect | incorrect | PASS |
| H02 | mendeley/Dataset Subject-wise/subject_018/push_up/good/side/subject_018_push_up_good_side.mp4; source side view; full original video | correct | correct | PASS |
| H03 | mendeley/Dataset Subject-wise/subject_018/squat/bad/side/subject_018_squat_bad_side.mp4; source side view; full original video | incorrect | correct | FAIL |
| H04 | mendeley/Dataset Subject-wise/subject_018/squat/good/side/subject_018_squat_good_side.mp4; source side view; full original video | correct | correct | PASS |
| H05 | mendeley/Dataset Subject-wise/subject_020/push_up/bad/side/subject_020_push_up_bad_side.mp4; source side view; full original video | incorrect | correct | FAIL |
| H06 | mendeley/Dataset Subject-wise/subject_020/push_up/good/side/subject_020_push_up_good_side.mp4; source side view; full original video | correct | incorrect | FAIL |
| H07 | mendeley/Dataset Subject-wise/subject_020/squat/bad/side/subject_020_squat_bad_side.mp4; source side view; full original video | incorrect | correct | FAIL |
| H08 | mendeley/Dataset Subject-wise/subject_020/squat/good/side/subject_020_squat_good_side.mp4; source side view; full original video | correct | incorrect | FAIL |
| H09 | mendeley/Dataset Subject-wise/subject_022/push_up/bad/side/subject_022_push_up_bad_side.mp4; source side view; full original video | incorrect | incorrect | PASS |
| H10 | mendeley/Dataset Subject-wise/subject_022/push_up/good/side/subject_022_push_up_good_side.mp4; source side view; full original video | correct | incorrect | FAIL |
| H11 | mendeley/Dataset Subject-wise/subject_022/squat/bad/side/subject_022_squat_bad_side.mp4; source side view; full original video | incorrect | correct | FAIL |
| H12 | mendeley/Dataset Subject-wise/subject_022/squat/good/side/subject_022_squat_good_side.mp4; source side view; full original video | correct | correct | PASS |
| F01 | squat endpoint trace; Observed ready → lowered/open → ready, 12 frames each at 30 FPS | {"reps": 1} | {"reps": 1} | PASS |
| F02 | pushup endpoint trace; Observed ready → lowered/open → ready, 12 frames each at 30 FPS | {"reps": 1} | {"reps": 1} | PASS |
| F03 | lunge endpoint trace; Observed ready → lowered/open → ready, 12 frames each at 30 FPS | {"reps": 1} | {"reps": 1} | PASS |
| F04 | jumping_jack endpoint trace; Observed ready → lowered/open → ready, 12 frames each at 30 FPS | {"reps": 1} | {"reps": 1} | PASS |
| F05 | squat starting at bottom; Partial starting repetition must not count | {"reps": 0} | {"reps": 0} | PASS |
| F06 | push-up trace with 0.8-second gap; Discard partial cycle across missing data | {"reps": 0} | {"reps": 0} | PASS |
| F07 | known push-up landmarks; wrist presence 0.1; Occluded required wrist must cause abstention | {"status": "unassessable", "features": null} | {"status": "unassessable", "features": null} | PASS |
| F08 | camera-open failure stub; Show camera error and release capture | {"message_type": "error", "capture_released": true} | {"message_type": "error", "capture_released": true} | PASS |
| F09 | nonexistent missing.mp4; Reject missing input without writing an output | {"error": "FileNotFoundError", "output_exists": false} | {"error": "FileNotFoundError", "output_exists": false} | PASS |
| F10 | uniform black 240×160 PNG; No person; annotated output and JSON, no form pass or invented count | {"decoded": true, "frames": 1, "status": "unassessable", "reps": null} | {"decoded": true, "frames": 1, "status": "unassessable", "reps": null} | PASS |
| F11 | three-frame black MP4 at 15 FPS; Tracked main method preserves output frames and does not invent a person/rep | {"decoded_frames": 3, "reps": 0, "all_unassessable": true} | {"decoded_frames": 3, "reps": 0, "all_unassessable": true} | PASS |
| F12 | same PNG as input and output; Protect source file against overwrite | {"error": "ValueError", "input_unchanged": true} | {"error": "ValueError", "input_unchanged": true} | PASS |
| UI01 | Training push-up video (rejected-view screenshot); previously inspected squat excerpt at frame 90 (accepted-preview screenshot); Virtual desktop; two recorded videos substituted for webcam capture; actual pose inference and GUI thread used. Known squat clip used for UI display, not new accuracy evidence. | Home and live preview render; stopping releases capture and re-enables start; quit closes window. | Home, accepted live preview and rejected-view screenshots saved; capture released; start re-enabled; both windows closed. | PASS |

Functional traces/landmarks are synthetic; camera-open failure is mocked; black PNG/three-frame video checks exercise actual MediaPipe/codecs. Neither mocked devices nor recorded-video GUI substitution verifies physical camera acceptance. Classification PASS/FAIL values are not combined with software tests to calculate accuracy.

| Prospective input | Reference | Uncalibrated | Deployed | Status |
| --- | --- | --- | --- | --- |
| subject_017_push_up_bad_side | incorrect | correct | correct | FAIL |
| subject_017_push_up_good_side | correct | correct | correct | PASS |
| subject_017_squat_bad_side | incorrect | incorrect | incorrect | PASS |
| subject_017_squat_good_side | correct | correct | incorrect | FAIL |
| subject_019_push_up_bad_side | incorrect | correct | correct | FAIL |
| subject_019_push_up_good_side | correct | correct | correct | PASS |
| subject_019_squat_bad_side | incorrect | correct | incorrect | PASS |
| subject_019_squat_good_side | correct | correct | correct | PASS |
| subject_021_push_up_bad_side | incorrect | incorrect | incorrect | PASS |
| subject_021_push_up_good_side | correct | incorrect | incorrect | FAIL |
| subject_021_squat_bad_side | incorrect | correct | incorrect | PASS |
| subject_021_squat_good_side | correct | unassessable | unassessable | FAIL |
| subject_023_push_up_bad_side | incorrect | correct | correct | FAIL |
| subject_023_push_up_good_side | correct | incorrect | incorrect | FAIL |
| subject_023_squat_bad_side | incorrect | correct | correct | FAIL |
| subject_023_squat_good_side | correct | correct | correct | PASS |

| Integration / acceptance check | Recorded result / scope |
| --- | --- |
| Calibrated validation video / codec | PASS: 435 frames; incorrect; form-rules-v1; validation_smoke.json |
| Calibrated session UI | PASS: review technique; capture released; window closed; gui_smoke.json; validation video substituted |
| Current laptop file benchmark | PASS: four complete runs / 1,700 frames; exact hash/summary validation |
| Actual physical webcam open/start/stop/restart/Quit | PENDING — no physical-camera evidence |
| Actual camera lighting / occlusion / view feedback | PENDING — recorded/synthetic evidence only |
| Sustained physical-camera displayed FPS / latency | PENDING — processing throughput is not a GUI camera measurement |
| Live-prefix / per-frame form accuracy | PENDING — no independently labelled live-prefix evaluation |


## 7. Limitations and next validation

Evidence covers only four prospective participants and two calibrated-candidate exercise modes. Source labels combine faults that projected 2D angles may not distinguish; no independent landmark ground truth was collected. Side-view assumptions, hidden joints, unsupported variations and view ambiguity limit assessment. Lunge/jacks lack a suitable paired independent form set; incorrect-form performance cannot be inferred from four all-correct regression references. The session estimate is provisional and is not medical guidance or validated live coaching.

Timing is a single sequential pass, with unmatched dependency provenance between historical/current laptop runs and incomplete benchmark-time CPU/RAM capture. Hardware verification is post-run. No repeated-run variance, physical-camera throughput, plugged-in state or thermal controls were recorded. Preserve abstention and collect new independently annotated faults, rep boundaries and participants before further tuning or stronger claims.


## 8. Evidence, preservation and reproduction

Authoritative current files: config/form_rules.json; docs/calibration/plan.json, fitting_results.json, evaluation_freeze.json, prospective_results.json/csv, laptop_benchmark.json/csv, laptop_environment_verification.json, laptop_benchmark_validation.json, validation_smoke.json and gui_smoke.json. Historical measurements remain under docs/phase3 and docs/milestone4. The old v2 source ZIP remains docs/calibration/reference/uncalibrated_v2_code.zip.

Run this report-only builder: python scripts/milestone4/update_current_report.py (python-docx required; local outputs/report_dependencies is supported). It validates existing evidence and rebuilds the consolidated DOCX/Markdown plus clearly dated addenda on both prior editable reports. Original DOCX files are archived under each report folder/history before the first update. It does not rerun the now-exposed test sets or alter tags/model parameters. A new benchmark inference run must use a new output filename and a runner that handles Windows path-key separators while preserving hash checks.
