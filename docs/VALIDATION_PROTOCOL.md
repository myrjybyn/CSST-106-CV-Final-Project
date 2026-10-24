# Fixed milestone-two squat baseline protocol, version 2

This protocol was written before running the new side-view validation. It uses
the existing MediaPipe Lite version-1 model and original subject-disjoint splits.
No custom model is trained. No test frames are decoded or evaluated.

## Development check and quality gate

The known equipment false detection in training subject 001, side-view good
squat, frame 150 is a development regression case. In addition to the existing
confidence and in-frame checks, the shoulder-hip-knee-ankle chain must span at
least 0.35 times the image height, measured as the sum of three 2D segment lengths.
This assumes the operator supplies full-body footage with the subject filling
the frame. A small confident pose on equipment is rejected rather than passed;
no skeleton is rendered when features are rejected. This gate cannot prove that
an accepted pose is anatomically correct and can reject distant valid people.

## Clip aggregation, fixed before validation

Only side-view squat clips are within the geometric baseline's supported scope.
For a whole clip:

1. Require at least 30 assessable frames and at least 50% assessable coverage.
2. Compute the 10th and 90th percentiles of projected knee angle. If their range
   is under 20 degrees, abstain: insufficient movement was observed.
3. Predict `incorrect` if the knee-angle 10th percentile exceeds 100 degrees,
   the 90th percentile is below 145 degrees, or the 90th percentile of trunk lean
   among frames with knee angle below 145 degrees exceeds 60 degrees.
4. Otherwise predict `correct`. These names are baseline predictions used for
   comparison to source clip labels, not verified or medical form judgements.

`src/posture_check/clip.py` records the exact constants and measurements. These
rules measure projected depth, extension and lean only. They do not capture every
fault covered by a dataset's good/bad labels. The thresholds are provisional and
were not fitted to validation labels. There is no phase-sequence validation or
repetition counting yet. A still image receives no whole-clip label.

## Validation target and metrics

Use the eight side-view squat clips in the existing Mendeley validation manifest:
four participants, four correct and four incorrect source clip labels. Front and
diagonal views are excluded because the method requires a side view. The earlier
24-clip, all-view version-1 throughput result is retained as historical evidence;
it is a different workload and must not be treated as a controlled speed comparison.

Run once after tests and the development regression check pass:

```bash
PYTHONPATH=src python scripts/evaluate_validation.py --media-root data/raw/mendeley --output docs/results/mendeley_squat_side_validation.json
```

Compare one prediction per clip to its one source form label. Never propagate
clip labels to individual frames. Report all eight clips, abstentions, the full
confusion matrix, overall accuracy (abstentions count as misses), accuracy among
assessed clips, and macro F1 (abstentions count as false negatives). Do not hide
abstentions or call a low-scoring baseline successful classification.

Also report processing FPS, decoding-plus-processing FPS, pose-output coverage
and assessable coverage. Timings exclude drawing and encoding and include first
inference warm-up. Coverage is not landmark accuracy. This cloud run does not
measure laptop or webcam FPS. Preserve the test partition for a future final
evaluation after development is complete.
