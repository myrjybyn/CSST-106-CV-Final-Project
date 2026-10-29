# POSTURE CHECK — Milestone 2 dataset-only preparation kit

**This kit does not contain or silently generate a training dataset.** It helps you acquire, inventory, group-split, and document real datasets. Follow original source download and reuse conditions.

## Recommended downloads

1. **Mendeley Data, V3 (2026):** https://data.mendeley.com/datasets/kgbb3yn47p/3  
   Download ONLY `Dataset Subject-wise.zip` (2.9 GB). The three ~2.9GB ZIPs contain the same videos organized differently; downloading all duplicates media. Licensed CC BY 4.0. The relevant activities are bodyweight squat and standard push-up, labeled good/bad form from 26 participants and multiple viewpoints. After extracting the ZIP, inspect the naming scheme and run the inventory script below. **Do not claim images were acquired until downloaded.**

2. **REHAB24-6 (2024):** https://zenodo.org/records/13305826  
   Download `Segmentation.csv` (53.3 KB), then choose **either** `videos.zip` (2.7 GB, if training on RGB frames) **or** `2d_joints.zip` (693.4 MB, if experimenting with pose features). Other modality ZIPs are optional, not needed for an initial dataset. Ex3 table-supported push-ups, Ex5 lunge, Ex6 squat. Correctness annotations at **repetition** level. Non-commercial academic/non-profit research only with citation. Do not treat joint positions as equivalent to MediaPipe landmarks without mapping and validation. See REHAB24 paper and license for details.

3. **Existing Milestone 1 footage:** Use only as separate *exercise-identity demonstration/evidence*. There are no ground-truth form correctness labels; five extracted frames per activity are too few for meaningful quality training. In particular jumping-jack form is currently **unlabeled** and is not covered by datasets 1 and 2.

## REHAB24-6: metadata acquisition and group split

This uses only Python's standard library:

```powershell
python prepare_rehab24.py
```

It downloads the official `Segmentation.csv` annotation file, falling back to a GitHub **mirror of annotations** if Zenodo rate-limits. If both fail, download the file manually from the Zenodo page and save it as `data/raw/rehab24/Segmentation.csv` before rerunning.

The script outputs:

```
data/prepared/rehab24/
  all_repetitions.csv
  train_repetitions.csv
  val_repetitions.csv
  test_repetitions.csv
  subject_assignments.csv
```

The data card is written to `docs/data_cards/DATA_CARD_REHAB24.md`. The optional `--data-card` flag overrides its destination.

Subjects, including all their videos and repetitions, stay in the **same split**. The split approximates 70/15/15 according to repetition counts. No frames are copied because the RGB videos have not been downloaded by this script. Preserve the test partition unchanged throughout training/tuning.

## Mendeley: inventory the downloaded videos

Extract the Mendeley `Dataset Subject-wise.zip` and run:

```powershell
python inventory_mendeley.py --root "C:\path\to\extracted\Dataset Subject-wise"
```

Review `data/prepared/mendeley_inventory.csv`. The script attempts to infer activity, good/bad form, and person ID from filenames and folders, flagging anything unknown as `REVIEW`; **inspect actual archive organization and manually verify every uncertain row**. Split by participant (not by individual frames) only AFTER verifying video labels and IDs. Never rename incorrect as correct to make the class counts balance.

## What to hand over to model-development teammate

- Links to original dataset records and licenses, including formal citations.
- Actual acquired/downloaded videos or joint arrays in locally-accessible storage, or a shared-drive link (not large ZIP files in Git).
- Locked train/validation/test participant/video ID manifests.
- Exercise and form label mapping, plus which exercises remain unsupported.
- One-page data card including observed counts per class/split, image resolution after inspection, preprocessing, validation notes, and limitations.

## Suggested repository layout

```
data/
  README.md                  # link to large media + exact acquisition instructions
  prepared/
    rehab24/                 # annotation manifests + data card
    mendeley_inventory.csv   # after acquisition and manual review
src/                        # training/prediction preprocessing belongs to engineering teammate
```

Never commit large media archives, `.venv`, raw video frames from every second, or model weights. Use Git LFS or shared Drive for large assets if your team requires mirrored storage.

## Caveats for POSTURE CHECK

- Exercise IDs and correct/incorrect form are separate labels.
- Mendeley labels are clip-level, REHAB24 labels are repetition-level.
- REHAB24 table-supported push-ups are **not** standard push-ups.
- Physiotherapy lab data and gym videos have different domains; do not blindly mix coordinates.
- Jumping-jack movement examples do **not** have form-quality ground truth; collect labeled examples with consistent criteria or keep the feature to exercise recognition only until reviewed data exists.
- Randomly dividing neighboring video frames over train/val/test leaks almost-identical examples.

After reviewing the Mendeley inventory, save and run the subject-aware splitting command:

```powershell
python split_mendeley_inventory.py
```

This refuses unknown labels/participants and generates `data/prepared/mendeley/{train,val,test}_videos.csv` and `subject_assignments.csv`. The data card is written to `docs/data_cards/DATA_CARD_MENDELEY.md`. It never copies frames between partitions.
