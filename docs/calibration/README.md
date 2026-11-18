# Current form calibration — form-rules-v1 / main v3

[Prospective test JSON](prospective_results.json) | [CSV](prospective_results.csv)

**Single current documentation draft (hand-in item 6):** [Technical documentation DOCX](../milestone4/Checkpoint4_Technical_Documentation_Draft.docx) ([review preview](../milestone4/Checkpoint4_Technical_Documentation_Draft.md)). It writes up the completed work in introduction, data, method and experiments sections, including calibration, results and laptop speed. The former separate calibration supplement is superseded and preserved in [history/](history/).

**Measured laptop:** [complete log](laptop_benchmark.json), [CSV](laptop_benchmark.csv), [97-check validation audit](laptop_benchmark_validation.json) and [hardware/comparison summary](LAPTOP_BENCHMARK_STATUS.md). Aggregate **23.67 processing FPS / 42.25 ms per frame**, versus historical checkpoint-3 main **12.83 FPS / 77.93 ms** on the same four known clips. CPU/RAM capture in the raw log is incomplete; [post-run verification](laptop_environment_verification.json) records AMD Athlon Silver 3050U / 5.94 GiB. Physical webcam acceptance remains **PENDING**.

The current application deploys **calibrated squat clip/session rules**. The push-up candidate did not improve validation macro F1 and lowered incorrect-form recall, so it is **not promoted**. Lunge/jack form rules remain provisional. Pose weights, raw geometry cues and movement counting are unchanged.

## Measured outcome

| Same new prospective test | Uncalibrated tracked rules | Deployed version |
| --- | ---: | ---: |
| Overall accuracy / 16 clips | 43.8% (7/16) | 50.0% (8/16) |
| Macro F1 | 0.430 | 0.517 |
| Squat accuracy / 8 clips | 50.0% | 62.5% |
| Incorrect-squat recall | 25.0% | 75.0% |
| Push-up accuracy / 8 clips | 37.5% | 37.5% |
| Assessed / abstained clips | 15 / 1 | 15 / 1 |

This is a modest gain, not reliable general form detection. Overall correct-form recall decreases from 62.5% to 50.0% while incorrect-form recall increases from 25.0% to 50.0%. Four false accepts, three false flags and one abstention remain.

**Do not compare 50.0% directly with the previous 41.7%:** the previous score was measured on the original 12 test clips. The comparison above uses a different, newly reserved 16-clip participant holdout and evaluates both decisions on identical tracked feature streams.

## Data separation and fitting

The original side-view test participants (018/020/022) had already been inspected, so they were excluded from all fitting, validation promotion and this final test. Before any new feature extraction, [plan.json](plan.json) reserved four previously unused complete training participants (017/019/021/023) as a **prospective holdout**. Recorded development runs used Mendeley subject 001 and the original validation/test participants; no custom form model had previously been trained. This is a revised split from the original training inventory, not a newly acquired external dataset.

- Fit: 54 side-view clips, 14 participants overall (13 for push-up).
- Validation: 16 clips from four original validation participants.
- Prospective holdout: 16 clips from four reserved participants; one good/bad side-view recording per exercise/person.
- Original CSV splits remain unchanged. The new plan provides separate participant-disjoint roles. All prospective participants were excluded from fitting and validation.

Numerical angle summaries are the only classifier features. No filenames, subject IDs, recording length, FPS, visibility quality or per-frame form labels enter the rule tree. Whole-clip source labels are not propagated onto frames. Coverage/movement gates remain fixed: 30 valid frames, 50% coverage and 20° movement range.

Tree depth (1 or 2) and minimum leaf size (4 or 6 clips, at least two subjects) are selected by leave-one-fitting-participant-out predictions. Promotion requires improved validation macro F1, no loss of validation incorrect-form recall, and no loss of fitting OOF macro F1 relative to the old fixed rules. No parameters/promotion choices changed after the final test.

### Decisions

- **Squat enabled:** fitting OOF macro F1 0.641; validation macro F1 0.333 → 0.500; validation incorrect-form recall 0% → 50%. Validation accuracy stays 4/8: the gain is a better balance of error types, not a validation accuracy gain. The one-split learned rule uses projected hip-angle p10 at 71.15°. This is a dataset-fitted classifier threshold, **not a universal recommended hip angle**.
- **Push-up not enabled:** candidate OOF macro F1 0.666, but validation macro F1 ties at 0.619 and incorrect-form recall drops 75% → 50%. Keep the existing rule until a stronger development result is available.

## Application behavior

`config/form_rules.json` is a versioned, human-readable learned artifact. The main CLI uses enabled rules for final clip assessment and records the calibration ID and decision path. Baseline mode uses the original rules. A mismatched pose model is rejected for a calibrated mode.

The GUI keeps the custom layout and adds a **session form estimate** about once per second from cumulative numeric angles. It does not save camera frames. Frame-level geometry cues stay separate: whole-clip validation does not establish live-prefix or per-frame accuracy. Start/Stop begins a new session. The model remains a selected-exercise system, not automatic exercise recognition.

The recorded calibration run reports 63 automated software tests passing. [Native calibrated video/codec integration](validation_smoke.json) and [actual GUI session-estimate integration](gui_smoke.json) use validation media only. The GUI smoke test substitutes a video for webcam input; physical laptop-camera acceptance remains pending. Current laptop file-processing throughput is measured separately above and does not establish displayed webcam FPS.

## Reproduce

```bash
# Already-prepared plan/profile/freeze: repeat the frozen test into a NEW output.
python src/evaluate.py --output outputs/calibration/prospective_repeat.json
python app.py
```

Fitting workflow (preserve existing artifacts; use an isolated clean copy/version for refitting):

```bash
python scripts/calibration/prepare_plan.py
python scripts/calibration/collect_features.py --exercise squat
python scripts/calibration/collect_features.py --exercise pushup
python scripts/calibration/fit_rules.py
python src/evaluate.py --prepare
python src/evaluate.py
```

The collection scripts use the standard project `data/raw/` layout and matching Lite model under `models/`. Feature caches resume only when input/model/pipeline fingerprints match. Fit code refuses to overwrite an existing profile, and plan/result/freeze creation protects existing evidence. Test inputs are not decoded by the fitting workflow; their first model inference occurs after validation promotion and source/profile freeze.

`src/evaluate.py` defaults to the new `prospective` suite. It applies original and approved form decisions to the same single inference pass per clip; the doubled summary rows are not two independent timing runs. No independent model-speed comparison is claimed from that shared pass.

### Versioned laptop packages

The old v2 benchmark source is preserved in [reference/uncalibrated_v2_code.zip](reference/uncalibrated_v2_code.zip). The previous working checkout `/workspace/CSST-106-CV-accuracy` is untouched. The historical checkpoint-four package generator restores the v2 bundle rather than mixing new source with an old freeze.

For the current calibrated version, generate the small code-only export with:

```bash
python scripts/calibration/package_benchmark.py
```

Copy the existing Lite model and four original clips as described in [LAPTOP_BENCHMARK.txt](LAPTOP_BENCHMARK.txt), then run in the working laptop Python environment:

```bash
python src/evaluate.py --suite benchmark --runtime-label laptop --output docs/calibration/laptop_benchmark.json
```

The completed calibrated-version laptop log is linked above. The four known clips are only a speed/regression workload, not the new prospective test. Preserve that log and use a new output filename for reruns. On Windows, the measured run restored exact frozen LF bytes and normalized only source-hash dictionary path separators in a runner; no hash checks were bypassed. See the validation audit for provenance.

## Artifacts and limits

- [Plan](plan.json), [fit/validation search and outcomes](fitting_results.json), [squat feature summaries](squat_features.json), [push-up feature summaries](pushup_features.json).
- [Deployed rules](../../config/form_rules.json), [source/profile/input freeze](evaluation_freeze.json), [final results](prospective_results.json) and CSV.
- [Single current draft](../milestone4/Checkpoint4_Technical_Documentation_Draft.docx); [GUI/CLI integration records](gui_smoke.json) / [video smoke result](validation_smoke.json); `evidence/` holds an actual session-estimate screenshot.
- Underlying per-frame numeric angle caches and annotated smoke video stay under ignored `outputs/calibration/`; no per-frame form truth is assigned.

Only four test participants and two exercise modes are covered. Source labels combine fault types that projected 2D angles may not distinguish. Push-up performance is still weak; no calibrated lunge/jack classifier is claimed. No new repetition-reference dataset, live-prefix accuracy or physical-camera benchmark is provided. The prospective set is now exposed: future parameter changes need another independent test.

Checkpoint-four submission snapshot: commit `c5196f6` (message names `cp4-80`); the existing tag was fetched from origin, verified at this commit and preserved. Original measurements and report bodies are preserved. Current calibrated-version laptop file-processing speed is measured; physical webcam acceptance remains pending. Rebuild the single item-6 documentation draft with `python scripts/milestone4/update_current_report.py` (report-only `python-docx` dependency).
