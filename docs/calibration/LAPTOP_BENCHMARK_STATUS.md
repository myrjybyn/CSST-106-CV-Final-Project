# Calibrated checkpoint-four laptop benchmark — validated

Updated 19 November 2026 (Asia/Manila). The [raw laptop log](laptop_benchmark.json) completed all four original known clips, 1,700 frames, at `2026-11-18T15:51:50.929943+00:00` (18 November, 23:51:50 Asia/Manila). Its [CSV](laptop_benchmark.csv) agrees with JSON.

| Laptop measurement, same known clips | Processing FPS | ms/frame | Count MAE |
| --- | ---: | ---: | ---: |
| Historical checkpoint 3 main | 12.83 | 77.93 | 3.50 |
| Calibrated checkpoint 4 current | **23.67** | **42.25** | **1.75** |

Observed throughput increased by 10.84 FPS (+84.5%; 1.84×); processing time decreased by 35.68 ms/frame (45.8%). Aggregates use total frames divided by total processing seconds. They exclude model initialization, decoding, drawing and encoding. This does not measure displayed webcam FPS. Single passes, unmatched dependency provenance, and unrecorded workload/thermal conditions prevent attribution to code alone.

| Clip | Frames | Current FPS | Current ms/frame | CP3 / current reps | Current form |
| --- | ---: | ---: | ---: | --- | --- |
| Push-up | 363 | 23.63 | 42.32 | 2 / 2 | correct |
| Squat | 483 | 23.68 | 42.24 | 4 / 4 | correct |
| Lunge | 278 | 22.48 | 44.49 | 0 / 2 | correct |
| Jumping jacks | 576 | 24.32 | 41.12 | 1 / 6 | unassessable |

The [validation audit](laptop_benchmark_validation.json) passes 97 checks: completion, exact frozen source/profile/plan and model identity, split-manifest checksums, four unique inputs and their hashes, frame counts, summary arithmetic, per-exercise results, CSV consistency and explicit squat `form-rules-v1` integration. All 22 frozen source/profile/plan files also match submission commit `c5196f6b2778c892d4d459090780f6d0bc6685fb`. The existing `cp4-80` tag was fetched from origin and verified at this commit. Its target is unchanged.

Before the recorded inference run, Windows CRLF text files were restored to exact frozen LF bytes. A Python runner normalized only source-hash dictionary key separators to `/`; the code, profile, model, manifest and input hashes were still enforced. The evaluator and frozen artifacts remain unchanged.

The raw log captured Windows 11 build 26200, Python 3.13.0, two logical CPUs and Balanced power. CPU model was null and RAM was zero, correctly marked incomplete. [Post-run hardware verification](laptop_environment_verification.json), using the Windows registry and `GlobalMemoryStatusEx`, recorded **AMD Athlon Silver 3050U with Radeon Graphics / 5.94 GiB RAM**, consistent with checkpoint 3. This is separately dated evidence, not a rewrite of benchmark-time metadata. Reported current dependency distributions are MediaPipe 1.2.0, NumPy 2.2.3, opencv-contrib-python 4.11.0.86 and Pillow 11.1.0; checkpoint-3 dependency versions were not recorded.

Historical cloud results remain unchanged: pre-calibration v2 four-known-clip throughput 50.97 FPS / 19.62 ms; original 12-clip cloud test CP3 rerun 33.15 FPS / 30.16 ms versus v2 50.81 FPS / 19.68 ms. The calibrated prospective cloud shared feature pass records 55.63 FPS / 17.98 ms across 16 clips / 4,517 frames; before/after decisions share inference and are not independent timing runs. These are different workloads/environments from laptop timing.

The known four-clip workload is for speed/regression only: three correct form decisions and one abstention (75% agreement), with all reference forms user-labelled correct after earlier predictions. It does not establish incorrect-form recall. Keep the historical original 12-clip test (41.7% v2 accuracy) separate from the new 16-clip prospective test (43.8% uncalibrated versus 50.0% calibrated).

**Physical webcam acceptance remains PENDING**: actual camera open/start/stop/restart/release, lighting/occlusion behavior, displayed FPS and sustained camera latency have no verified acceptance record. Existing GUI smoke tests use recorded video; device failures use mocks.

Review the single item-6 [technical documentation draft](../milestone4/Checkpoint4_Technical_Documentation_Draft.docx) or its [Markdown preview](../milestone4/Checkpoint4_Technical_Documentation_Draft.md). The earlier application/testing report, calibration supplement and provisional combined report are superseded and preserved in `history/` directories. Rebuild the single draft with `python scripts/milestone4/update_current_report.py` using report-only `python-docx`. Documentation revisions follow the original tagged application snapshot.
