# Current guided-rule evaluation

This evaluation compares the existing uncalibrated fixed clip rules with the
current guided-session assessor. It does not change either method or train a model.

The selection is **all 16 clips** from the historical reserved comparison:
four participants (017, 019, 021, 023), eight side-view squats and eight side-view
push-ups, with four source-correct and four source-incorrect clips per exercise.
These inputs have already appeared in earlier experiments. This is a matched
comparison on previously exposed data, **not a new independent test**.

Reference labels are the original Mendeley whole-video labels. They are not
expert fault annotations. The preliminary AI01 repetition annotations are not used.

## Measured outcome

The run completed on **21 November 2026, Philippine time**. Both methods produced
the same prediction on all 16 clips:

| Method | Accuracy | Macro-F1 | Coverage |
| --- | ---: | ---: | ---: |
| Existing fixed clip rules | 43.75% (7/16) | 0.429825 | 93.75% (15/16) |
| Current guided-session rules | 43.75% (7/16) | 0.429825 | 93.75% (15/16) |

Both accepted six of eight source-incorrect clips, flagged two source-correct
clips, and abstained on one source-correct clip. Incorrect-form recall was 25%.
Assessed-only accuracy was 46.67% (7/15), which must be reported with coverage.
Squat accuracy was 50% (4/8); push-up accuracy was 37.5% (3/8).

**There was no measured classification gain in this comparison.** The two methods
share most squat/push-up form thresholds. Their idle-handling and evidence-gate
differences did not change the final labels on these clips. This result does not
mean either method has been validated as a reliable form judge.

For the report, add this as a new matched experiment, retaining the earlier
calibrated CLI result as a separate historical experiment. Do not describe the
historical 50% score and the new 43.75% score as a controlled improvement/regression
comparison: the classifier and runtime differ. The guided-session user interface
and target workflow are implemented features, not demonstrated accuracy gains.

## Methods

- **Baseline: fixed_clip_rules.** Existing `summarize_for_exercise` with
  `calibrated=False`, on all shared temporal records. This is whole-clip
  aggregation, not the historical single-frame baseline or calibrated classifier.
- **Final: guided_session_rules.** Unmodified `ExerciseSession.add/assess` from
  the desktop application, retaining idle exclusion, its short lead-in, and gates.

Each clip gets one shared tracked MediaPipe VIDEO pass with enhanced preprocessing.
The temporal analyzer uses the GUI's nominal 30 FPS configuration and receives
`dt_seconds=1/media_fps`, replacing live elapsed time with recorded media time.
Both decisions reuse the same smoothed features; the guided counter is installed
as in the app. Both methods use existing thresholds, with no result-driven tuning.
The historical calibration profile is not used for either decision.

Every video is decoded to its end. There is no target-based truncation, countdown,
display or recording. This measures complete-clip decisions, not the app's
automatic stopping, camera behavior, or end-to-end live speed.

Guided `good` maps to `correct`; `bad` maps to `incorrect`; `unassessable` remains
explicit. Accuracy includes every labeled clip. Macro-F1 averages the correct and
incorrect class F1 scores; abstentions contribute false negatives for their true
class. Coverage and assessed-only accuracy are reported together. Per-class
precision/recall/F1 and two-by-three confusion matrices are also saved.

There are no manual repetition references for these clips. Saved observed counts
are diagnostic values and do not establish count accuracy. Lunge, jumping jacks,
and improvement-tip accuracy are outside this evaluation.

## Reproduce

Use the root README's Python environment and model download instructions. Obtain
the Mendeley dataset and extract it under `data/raw/mendeley/` as described there.
The source, model, input hashes and protocol are fixed in [freeze.json](freeze.json).

Run from the repository root:

```bash
python scripts/evaluate_guided_rules.py --output outputs/guided_rerun/results_rerun.json
```

Use a new output filename **and stem** for each run. Existing results/evidence are
preserved; mismatched code, model, or inputs are rejected. Results may vary across
MediaPipe versions, so compare the recorded environment as well as the source.

The initial freeze was created before inference with:

```bash
python scripts/evaluate_guided_rules.py --prepare-only
```

Do not overwrite that freeze to conceal later source changes. A deliberately new
evaluation requires a separately named freeze, its own protocol, and disclosure.

## Evidence

- `results.json`: runtime, protocol, all clip predictions and measured values,
  overall/per-exercise metrics, and evidence hashes.
- `results.csv`: one row per clip and method.
- `results.md`: report-ready comparison tables and limitations.
- `audit.json`: 160 passed post-run checks covering input/source/evidence hashes,
  paired inputs, frame counts, assessment replay, and independent metric
  recomputation. These checks verify the evaluation artifacts, not the reference
  labels or clinical correctness.
- `outputs/guided_evaluation/results/`: compressed shared per-frame evidence;
  generated files are excluded from Git and can be recreated from the inputs.

Historical results under `docs/calibration/` are preserved unchanged. They use a
different classifier and earlier runtime; they should not be combined with this
run as though they were one experiment.
