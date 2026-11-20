# Guided-rule evaluation results

Matched comparison on previously exposed Mendeley source-labeled clips. This is not a new independent test or a webcam/automatic-stop benchmark.

| Set | Method | Accuracy (all clips) | Macro-F1 | Coverage | Assessed accuracy |
| --- | --- | ---: | ---: | ---: | ---: |
| All 16 | fixed_clip_rules | 43.8% | 0.430 | 93.8% | 46.7% |
| All 16 | guided_session_rules | 43.8% | 0.430 | 93.8% | 46.7% |
| squat | fixed_clip_rules | 50.0% | 0.500 | 87.5% | 57.1% |
| squat | guided_session_rules | 50.0% | 0.500 | 87.5% | 57.1% |
| pushup | fixed_clip_rules | 37.5% | 0.365 | 100.0% | 37.5% |
| pushup | guided_session_rules | 37.5% | 0.365 | 100.0% | 37.5% |

## fixed_clip_rules

Rows are source labels; columns are predictions.

| Reference | Correct | Incorrect | Unable to assess |
| --- | ---: | ---: | ---: |
| correct | 5 | 2 | 1 |
| incorrect | 6 | 2 | 0 |

## guided_session_rules

Rows are source labels; columns are predictions.

| Reference | Correct | Incorrect | Unable to assess |
| --- | ---: | ---: | ---: |
| correct | 5 | 2 | 1 |
| incorrect | 6 | 2 | 0 |

## Interpretation limits

- Eight squat and eight push-up clips, four participants, balanced source form labels.
- Source correct/incorrect labels may cover faults outside the configured checks; they are not expert fault annotations.
- The same people/clips appeared in earlier experiments. No new generalization claim is supported.
- Only complete-clip form decisions are scored. Lunge, jumping jacks, rep-count accuracy, feedback-tip accuracy, target stopping, and live speed are not scored.
- Both methods reuse identical smoothed pose features. Guided initial-idle exclusion and its 10-frame gate differ from the baseline 30-frame gate.
- Abstentions remain misses in overall accuracy and class recall/F1; assessed-only accuracy must be read with coverage.
- No rules were changed for this evaluation. Historical calibrated CLI numbers belong to a different version/environment.

See results.json for per-class metrics, complete assessments, runtime, and provenance; results.csv contains per-clip predictions. freeze.json records the protocol and hashes.
