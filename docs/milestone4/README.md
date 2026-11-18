# Checkpoint 4 — pre-calibration v2 application and testing hand-in

**Historical v2 results.** Current form-rule calibration is documented in [../calibration/README.md](../calibration/README.md). The v2 source/freeze are preserved in `../calibration/reference/uncalibrated_v2_code.zip`; the latest source uses v3 and intentionally will not pass the old v2 source checksum. Use the current calibration commands for new evaluation and the matching versioned laptop package.

[Editable report](Checkpoint4_Application_Testing_Report.docx) — six pages, generated from measured logs. No submission PDF is generated here.

| Requirement | Deliverable / status |
| --- | --- |
| 1. Nearly complete integrated application | `app.py`, selected four-exercise webcam pipeline; `run.py` for annotated images/videos and JSON. Functional integration tested. |
| 2. Interface / visualization | Existing custom desktop GUI preserved; [actual home](evidence/home.png), [accepted preview](evidence/live.png), [rejected view](evidence/rejected_view.png), and [GUI integration provenance](evidence/gui_test_log.json). Recorded videos substitute for a webcam in the cloud smoke test. |
| 3. Held-out evaluation, laptop speed, checkpoint changes | `src/evaluate.py`; [frozen protocol/inputs/code](evaluation_freeze.json); [24 matched held-out runs](heldout_results.json), [CSV](heldout_results.csv). **Current laptop FPS/change remains pending**; old checkpoint-3 laptop log is preserved under `docs/phase3/`. |
| 4. Performance and limitations | Report sections 2, 3 and 6, including accuracy regression, false accepts/flags, unsupported views/variants and dataset gaps. |
| 5. At least 10 cases, at least 3 hard/edge | [25 cases CSV](test_cases.csv) / [JSON](test_cases.json): 12 real held-out classifications, 12 functional cases (8 hard/edge), one GUI integration case. Seven classification failures are retained. |

## Measured results

- Held-out **supported subset**: 12 full side-view Mendeley test clips, participants 018/020/022; six correct and six incorrect source labels; 4,124 decoded frames per method. The other 24 front/diagonal test videos are excluded by the declared side-view scope.
- Checkpoint-3 method was reconstructed exactly from the `cp3-core` source snapshot and rerun on the same inputs. This is a new matched evaluation, not a historical claim about what was measured at checkpoint 3.
- Accuracy **58.3% → 41.7%**; macro F1 **0.556 → 0.413**; usable-pose coverage **82.0% → 95.5%**. Four false accepts and three false flags remain; all three incorrect-squat labels are missed. Increased coverage is not validated landmark or form accuracy.
- All 12 clips receive a form prediction (no clip abstentions). Held-out count references are unavailable, so count MAE is not invented.
- On the separate four previously inspected excerpts, [known-clip results](known_clip_results.json) from `src/evaluate.py` retain count MAE **3.50 → 1.75 reps/clip** and 75% form agreement. These are known regression examples with post-run user references, not new held-out evidence; they cover no incorrect reference form.
- **56 automated software tests pass.** [12 executable functional cases](functional_test_cases.json) pass. The combined 25-case inventory has 18 PASS and 7 FAIL; software passes must not be used to inflate model accuracy.

Code/model/input/split hashes were frozen before held-out inference. Thresholds were not changed after seeing these held-out results. They must not be tuned using this now-exposed test set.

## Reproduce

From the project root with the existing dependencies and model installed:

```bash
python src/evaluate.py --data-root data/raw --output outputs/milestone4/heldout_repeat.json
python scripts/milestone4/run_test_cases.py
```

Use a new output filename for evaluation runs; completed logs are not overwritten. `src/evaluate.py --prepare --freeze NEW_FILE.json --data-root data/raw` prepares a new version before inference; preserve the current historical freeze and results. Training/validation/test participant disjointness and supported-view selection are checked during preparation.

The current interface is tested with actual pose inference under a virtual desktop. A physical webcam on the demo laptop still needs an acceptance run. The desktop supports webcam input; image/video files use the CLI. No GUI upload claim is made.

## Finish the laptop measurement

The current laptop result cannot be measured from the cloud. Use the small code-only package provided in chat and the [instructions](LAPTOP_BENCHMARK.txt), or generate the local ZIP with [package_benchmark.py](../../scripts/milestone4/package_benchmark.py). The generated ZIP is excluded from Git. It reuses the existing Lite model and the original four videos; those large files are excluded. The package generator is `scripts/milestone4/package_benchmark.py`.

Use the Python environment that successfully ran the previous benchmark:

```bash
python src/evaluate.py --suite benchmark --runtime-label laptop --output docs/milestone4/laptop_benchmark.json
```

Run on the same demo laptop, power mode and original input files. Wait for all four runs and `Completed`. Supply the resulting `laptop_benchmark.json`; it must include `completed_at_utc`. The report generator verifies suite/method/source/model identity and rebuilds the DOCX from that log:

```bash
python scripts/milestone4/build_report.py --laptop-log docs/milestone4/laptop_benchmark.json
```

The builder requires `python-docx` in a report-only environment (not an application dependency). Original checkpoint-3 hardware: AMD Athlon Silver 3050U, two logical CPUs, 5.94 GiB reported RAM, Windows 11, Balanced, Python 3.13.0; main processing throughput 12.83 FPS. Current cloud throughput is logged separately and does not replace the missing current laptop number.

## Files

- `evaluation_freeze.json`: supported test selection, known speed/regression workload, participant identities and source/model/input/manifest checksums.
- `heldout_results.json/csv`: same-test-set checkpoint-3/current comparison, per-class and per-exercise metrics, confusion matrices and timing scope.
- `known_clip_results.json/csv`: separate four-clip current regression/speed workload, measured in the cloud.
- `functional_test_cases.json/csv`: synthetic trace/landmark contracts, mocked unavailable camera, and actual MediaPipe image/video codec checks.
- `test_cases.json/csv`: all case IDs, input, condition, expected, actual, result and provenance. No failures removed.
- `evidence/`: unaltered GUI screenshots and integration log; no physical-webcam claim.
- `Checkpoint4_Application_Testing_Report.docx`: editable summary, rebuilt by the report-only script.

The combined checkpoint-four submission is tagged `cp4-80`. This report remains historical v2 evidence; current calibrated results are in ../calibration/. Previous checkpoint tags are preserved.
