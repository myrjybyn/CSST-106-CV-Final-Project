# Pose coverage and repetition-counting development review

Reviewed and implemented 16 November 2026 (Asia/Manila).

## Repository reviewed

Based on latest pushed `main`, `d4cca1a` (README update), including `ca856ca`
(custom warm-colored GUI, logo, rounded buttons and preview resizing). Those UI
changes are preserved. Development is isolated on `improve-pose-and-counting` in
`/workspace/CSST-106-CV-accuracy`; the older checkout and its unrelated local
changes/deletions were not overwritten. No commits or tags were moved.

Review findings: the main video/webcam pipeline still used independent IMAGE
inference; scale gates included padding; counting depended on EMA-smoothed form
phases; and lunge return-to-standing required the minimum of both knee angles.
These can lose usable poses and short/alternating repetition endpoints.

## Implemented changes

1. **Tracked video pose estimation.** Main video and camera runs use MediaPipe
   VIDEO mode with strictly increasing timestamps. Files use media FPS, cameras
   use elapsed time. The baseline and still images retain IMAGE mode. The same
   pretrained Lite weights are used; no custom weights were trained.
2. **Conservative padding handling.** Main inference removes paired nearly-black
   margins only: each row/column must be at least 99.5% black (all BGR channels
   at most 12); each border is at least two pixels; at least 25% of each dimension
   remains. OpenCV mask/reduction operations avoid an expensive NumPy image
   scan. This does not detect arbitrary backgrounds, gray/white padding or person
   boxes. Landmarks are mapped back for the existing preview/skeleton.
3. **Movement-only counting.** A separate state machine uses gated raw features,
   endpoint dwell of 0.10 s, 5-degree angular release hysteresis and 0.2
   shoulder-width release hysteresis for jacks. Endpoint entry thresholds remain
   those of the existing rules. Form feedback retains its independent EMA/dwell.
4. **Lunge leg tracking.** A leg must be observed extended in a confirmed ready
   stance before initiating a repetition. The bending leg is latched until its
   return to extension; the other knee may remain bent. Simultaneous flexion is
   counted once. This is a pose-based leg estimate, not verified front-leg identity.
5. **Honest rejection handling.** Missing landmarks never supply movement evidence.
   Gaps/stalls of at least 0.50 s and selected-side changes discard partial counts.
   Visibility, in-frame, view/geometry and body-size gates remain in place.
   Rejection feedback distinguishes missing pose, hidden joints, out-of-frame
   joints and unsupported scale/geometry. A nonfinite squat-confidence guard was
   also added, including the case where finite visibility hides NaN presence.

The main JSON method version is `temporal-geometric-v2`; it records pose mode,
preprocessing/counting parameters, separate movement phase and active leg. Counts
estimate movement independently of form quality. No form thresholds were adjusted
using the known Phase 3 regression outputs.

## Fixed training-only development comparison

The selection manifest was written before observing candidate outputs: the first
reviewed side-view training clip in each squat/push-up form class, plus the first
REHAB training lunge video with a half-profile Camera17 annotation. There are five
clips, 4,622 unique frames, and 9,244 reference/candidate frame passes.
This small selection is development evidence, not an independent accuracy test.

The reference reconstructs the main processing and temporal functions at
`d4cca1a`, sharing the pose wrapper's default IMAGE mode and geometric extractors;
the latter differ only by the new nonfinite squat-confidence guard. Candidate
video inference uses tracking. Model/input/manifest/code hashes are recorded.
The final run completed successfully; earlier interrupted exploratory runs are
kept only under ignored `outputs/development/`.

| Development clip | Previous usable frames | New usable frames | Previous reps | New reps |
| --- | ---: | ---: | ---: | ---: |
| pushup_correct | 49.3% | 85.5% | 2 | 4 |
| pushup_incorrect | 89.9% | 94.4% | 1 | 11 |
| squat_correct | 18.6% | 16.5% | 0 | 0 |
| squat_incorrect | 39.2% | 47.6% | 0 | 3 |
| lunge_half_profile | 58.5% | 96.1% | 9 | 15 |

Aggregate usable-pose coverage: **54.02% → 81.63%**. This is the
fraction passing geometry/confidence gates, not measured landmark accuracy.
Coverage fell on the source-correct squat; tracking is not uniformly better.
No independently reconciled full-cycle count references exist for these videos,
so higher counts alone cannot establish lower count error. The lunge source has
20 annotated segments, but segment/cycle conventions were not independently
reconciled; that value is context, not a scored repetition reference.

Form agreement on the four source-labelled Mendeley clips is unchanged at 1/4
when abstentions count as misses. The source-correct push-up changes from
abstention to an incorrect-form prediction. The two squat clips still abstain;
the incorrect push-up remains flagged. Lunge has mixed repetition-level form
labels, so it has no single whole-clip form reference. These results show why
rule calibration remains necessary. No separate jumping-jack development video
is available; its edge-case behavior is covered synthetically only at this stage.

## Known-clip regression check after freezing inference source

The four previously inspected YouTube excerpts were checked once after the
implementation was frozen. They informed earlier failure analysis, so this is
**regression evidence, not fresh held-out accuracy**. The source hashes match the
final development comparison and were checked again after evaluation. These
outputs were not used to adjust thresholds. Original Phase 3 logs, DOCX/PDF
reports, frozen configurations and historical measurements are unchanged.

References are the user's manual counts/form labels supplied after the original
predictions; they are not independently expert-verified.

| Known clip | User reference reps | Previous estimate | New estimate | New absolute error |
| --- | ---: | ---: | ---: | ---: |
| pushup | 4 | 2 | 2 | 2 |
| squat | 4 | 4 | 4 | 0 |
| lunge | 3 | 0 | 2 | 1 |
| jumping_jack | 10 | 1 | 6 | 4 |

Count MAE: **3.50 → 1.75 reps/clip**.
Form agreement remains **75%**, counting the jumping-jack abstention as a miss.
All four form references are correct, so this cannot measure incorrect-form
recognition. Push-up undercounting persists; lunge and jack counts still miss
repetitions. Combined changes were evaluated together, so these results do not
isolate the contribution of tracking, preprocessing or the new counter.

Cloud processing throughput is recorded in the JSON logs. It excludes rendering
and encoding, is based on single sequential runs, and is **not a new laptop
benchmark**. The original laptop numbers describe the older implementation.

## Verification and next calibration work

- **52 automated tests passed**, including short endpoints, alternating lunges,
  both-knee flexion without double counting, partial-cycle rejection, jitter,
  hysteresis, missing data, side changes, variable camera cadence, timestamps,
  padding/coordinate restoration and visibility/nonfinite guards.
- Actual MediaPipe tracked inference, preview updates, resource release and quit
  were exercised with a training video through the latest custom GUI under a
  virtual desktop. A physical laptop camera still requires testing.
- Inference-source hashes match both completed evaluations. No new dependencies
  were introduced. The baseline has no repetition counter and stays independent
  IMAGE mode, aside from the intentional NaN-confidence hardening shared by all
  squat extraction.

Next: manually check repetition boundaries and form faults on separate development
recordings, especially push-up and jumping-jack endpoints. Include different
people, the supported views, correct form and specific faults, and lighting /
occlusion / framing challenges. Define full and partial repetitions consistently.
Use these development recordings for calibration, then freeze parameters before
an untouched participant-separated test. Calibrate form thresholds against
labelled examples; do not infer form correctness from pose coverage or counts.
A Full-vs-Lite model experiment and new laptop speed measurements remain future
work; this change retains Lite.

## Reproduce and inspect

- `scripts/compare_development.py --media-root data/raw`: training-only selection;
  original reference functions plus candidate; writes ignored outputs by default.
- `scripts/check_regression_clips.py`: known Phase 3 excerpts; verifies exact input
  hashes and inference-source stability; writes a separate ignored log by default.
- [Development manifest](pose_counting_manifest.json), [full comparison](pose_counting_comparison.json),
  [comparison CSV](pose_counting_comparison.csv), and [regression check](phase3_regression.json).
- Main application entry points remain `python app.py` and
  `python run.py --exercise squat --method main --input input.mp4 --output output.mp4`.

These changes have not been committed or pushed.
