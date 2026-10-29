# POSTURE CHECK — Milestone 2 Data Card (REHAB24-6 subset)

**Data type:** repetition-level annotation manifests, **NOT image files or pose features**.
**Source:** Černek et al. (2024), REHAB24-6: https://zenodo.org/records/13305826
**License/conditions:** academic/non-profit, non-commercial research only; cite original publication. 
**Subset:** Ex3 table-supported push-ups; Ex5 lunges; Ex6 squats. No jumping jacks.
**Collection:** 10 participants overall, lab environment, two synchronized RGB viewpoints, 30 FPS; physiotherapist-supervised repetitions.
**Annotation:** original Segmentation.csv, correctness 1=correct / 0=incorrect; temporal start/end frames and video IDs preserved.
**Splitting:** grouped by person_id (all videos and repetitions for a person in one partition), targeting ~70/15/15; splits locked after assignment.
**Preprocessing applied:** rows filtered to exercise IDs 3, 5, 6; exercise and form labels normalized. No video frames resized or pose features extracted.
**Image sizes:** not applicable to annotation-only files. Verify per-video resolution after downloading videos.
**Training assets:** Download original `videos.zip` (2.7 GB) for RGB input, OR `2d_joints.zip` (693.4 MB) for 2D joint-feature experiments; both not included here.
**Gaps:** no jumping jacks; push-ups are table-supported; small participant pool; lab recording/mocap suits may not generalize to webcam usage.
**Leakage warning:** No random frame-level splitting. Do not merge REHAB with other sources before reconciling landmark conventions and subject identities.

## Repetition-level counts (ground-truth annotations)

| Exercise | Form | Train | Validation | Test | Total |
|---|---|---:|---:|---:|---:|
| table_pushup | correct | 37 | 10 | 5 | 52 |
| table_pushup | incorrect | 41 | 8 | 6 | 55 |
| lunge | correct | 53 | 13 | 12 | 78 |
| lunge | incorrect | 73 | 12 | 11 | 96 |
| squat | correct | 99 | 17 | 18 | 134 |
| squat | incorrect | 51 | 5 | 5 | 61 |

**Total:** 476 repetitions; train 354, val 65, test 57.
**Participants represented:** 10; train=7, val=2, test=1.

**Note:** This card describes annotation acquisition and splitting only. Mark media/landmark acquisition as pending until the corresponding ZIP is downloaded and validated.
