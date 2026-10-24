# Phase 2 hand-in checklist

This is an initial **side-view squat** implementation of the proposal's pretrained
pose plus geometric rules approach. It is not the completed four-exercise system.

| Required deliverable | File / evidence |
|---|---|
| Pinned environment and fresh-clone instructions | Root `requirements.txt`; `README.md` |
| Acquired data, fixed splits, one-page data card | `docs/MILESTONE2_DATA_CARD.md`; existing CSVs in `data/prepared/`; checksum/presence records under local `data/raw/` |
| Preprocessing / feature code in `src/` | `src/posture_check/pose.py`, `features.py`; features also written into prototype JSON |
| Initial algorithm and measured validation result | `baseline.py`, `clip.py`; `docs/results/mendeley_squat_side_validation.json`; fixed protocol in `docs/VALIDATION_PROTOCOL.md` |
| One-command prototype | `run.py`; MP4 + JSON from a real training clip, verified in `docs/results/demo_verification.json` |
| At least six screenshots/sample outputs or a short recording | Six actual annotated video-frame outputs in [docs/evidence/milestone2](evidence/milestone2/README.md), with provenance and checksums |

## Reproduce the demo

Complete the Python 3.12 setup and model download in README first. Then, from the
repository root with the virtual environment activated:

```bash
python run.py --input "data/raw/mendeley/Dataset Subject-wise/subject_005/squat/good/side/subject_005_squat_good_side.mp4" --output outputs/milestone2_demo.mp4
```

This writes an annotated MP4 and adjacent `.mp4.json` with per-frame features and
a provisional whole-clip assessment. The verified run produced 463 output frames.
The source clip is labeled good, while this baseline flags it; include that
failure in the explanation rather than presenting the prediction as ground truth.
For an image-only demo requiring no large dataset download, use the committed
`milestone1/posture_check/data/samples/squat_01.jpg` as input with a PNG output.

## Report the actual measured result

Version two evaluated **8 side-view squat validation clips / 4 participants /
3,735 frames**. It measured **26.11 processing FPS**, **50% accuracy on all clips**
(4/8, counting the one abstention as a miss), **57.14% assessed-only accuracy**
(4/7), and **macro F1 0.536**. Drawing and encoding are excluded from FPS.

| Source truth | Predicted correct | Predicted incorrect | Abstained |
|---|---:|---:|---:|
| Correct | 2 | 1 | 1 |
| Incorrect | 2 | 2 | 0 |

These are baseline results, below the proposal's final 80% accuracy goal. No test
clip was decoded/evaluated, no frame-level correctness labels were invented, and
no thresholds were retuned after the validation run. Pose-output coverage is not
landmark accuracy. Eleven automated tests passed; actual model execution and
video decoding were verified separately.

## Demo explanation

Show input → pose estimation → confidence/body-size gates → joint-angle features
→ frame rules and clip aggregation → annotated output + JSON. Explain the known
small equipment-pose regression now rejected by the size gate, and acknowledge
that other pose errors and form-classification failures remain. Future work covers
pose reliability, temporal smoothing, repetition counting, webcam input and the
other exercise modes. See `docs/MILESTONE2_STATUS.md` for full limitations.

Large datasets, weights and generated videos remain outside Git. Include the
source links/acquisition instructions and retained split manifests with the hand-in.
