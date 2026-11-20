# Guided evaluation: dataset correction

Two byte-identical video pairs have opposite source labels. Both copies of each pair were verified in the original downloaded ZIP and excluded from this separate post-hoc analysis. Original 16-clip results are preserved unchanged.

## Excluded inputs

| Exercise | Contradictory pair |
| --- | --- |
| pushup | subject_019_push_up_bad_side / subject_019_push_up_good_side |
| squat | subject_023_squat_bad_side / subject_023_squat_good_side |

## Results on 12 retained clips

| Set | Method | Accuracy | Macro-F1 | Coverage | Assessed accuracy |
| --- | --- | ---: | ---: | ---: | ---: |
| All retained clips | fixed_clip_rules | 41.67% | 0.431 | 91.67% | 45.45% |
| All retained clips | guided_session_rules | 41.67% | 0.431 | 91.67% | 45.45% |
| pushup | fixed_clip_rules | 33.33% | 0.333 | 100.00% | 33.33% |
| pushup | guided_session_rules | 33.33% | 0.333 | 100.00% | 33.33% |
| squat | fixed_clip_rules | 50.00% | 0.536 | 83.33% | 60.00% |
| squat | guided_session_rules | 50.00% | 0.536 | 83.33% | 60.00% |

## fixed_clip_rules

| Source label | Correct | Incorrect | Unable to assess |
| --- | ---: | ---: | ---: |
| correct | 3 | 2 | 1 |
| incorrect | 4 | 2 | 0 |

## guided_session_rules

| Source label | Correct | Incorrect | Unable to assess |
| --- | ---: | ---: | ---: |
| correct | 3 | 2 | 1 |
| incorrect | 4 | 2 | 0 |

## Interpretation and report correction

Duplicate removal fixes contradictory evaluation inputs; it does not fix the form classifier. The original 43.75% accuracy / 0.430 macro-F1 is the unfiltered result and must remain labeled as such. Report the cleaned analysis alongside it, not as a new untouched test or an accuracy improvement.

Both methods still agree on every retained clip. The guided rules show no measured classification gain over the matched fixed rules. Remaining source labels may describe faults outside the configured checks and have not been independently adjudicated.

The original 160-check audit validated artifacts and arithmetic, not label consistency. This additional audit detects exact-byte label conflicts and verifies them in the downloaded archive; it is not expert label validation or a near-duplicate search.

No human labels were invented or changed. Rules, source videos and original results are unchanged. The remaining squat tracking/movement abstention is retained. Lunge/jumping-jack accuracy, count accuracy, tip correctness and live target stopping remain untested.
