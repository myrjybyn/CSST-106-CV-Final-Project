# Milestone 2 data card — current implementation

**Primary source:** [Mendeley Data v3, DOI 10.17632/kgbb3yn47p.3](https://data.mendeley.com/datasets/kgbb3yn47p/3),
Multi-View Fitness Exercise Video Dataset. **License:** CC BY 4.0; retain source
attribution. The downloaded Subject-wise archive matched its published SHA256.

**Acquired subset:** all 294 clips listed by the team's existing manifests,
representing 25 participants and front/side/diagonal views. These are MP4 videos,
not independently labeled frames. Source filenames/folders encode participant,
exercise, good/bad form and view. Good maps to `correct`, bad to `incorrect`.
These source labels were reused; this implementation did not manually relabel clips.

| Exercise | Source form | Train | Validation | Test |
|---|---|---:|---:|---:|
| Squat | Correct | 54 | 12 | 9 |
| Squat | Incorrect | 54 | 12 | 9 |
| Push-up | Correct | 51 | 12 | 9 |
| Push-up | Incorrect | 51 | 12 | 9 |
| **Total** | | **210** | **48** | **36** |

**Splitting:** original participant-disjoint manifests retained unchanged,
18/4/3 participants in train/validation/test. All views of a participant remain
in that partition. There is no random neighboring-frame split.

**Current evaluation subset:** eight side-view squat validation clips, four
participants, four correct / four incorrect source labels, 3,735 decoded frames.
Native resolutions observed in that subset: 540×960 and 810×1440. No frame receives
its clip's form label. One whole-clip prediction is compared to one source label.

**Preprocessing / features:** OpenCV decoding and BGR-to-RGB conversion; pretrained
MediaPipe Lite Pose Landmarker v1 on CPU; native image coordinates scaled to
pixels for 2D knee/hip angles and trunk lean. Require confidence and in-frame
joints and a shoulder-hip-knee-ankle chain at least 35% of image height. Rejected
frames have null features. Whole-clip percentile rules, coverage requirements and
abstention handling are fixed in [the protocol](VALIDATION_PROTOCOL.md).

**Limits:** blurred faces, occlusion, gym clutter, multiple people and camera
perspective can cause false or missing poses. Geometric thresholds capture only
some form faults. No clinical or anatomical correctness is established. The test
split was not decoded/evaluated. Push-ups are acquired but not yet implemented;
this dataset does not supply lunge/jumping-jack examples.

**Additional acquired data:** REHAB24-6, [Zenodo 13305826](https://zenodo.org/records/13305826):
130 RGB videos, 260 joint arrays and segmentation CSV. Existing subset annotations
have 476 repetitions, split 354/65/57; see the original
[REHAB24 card](../data/prepared/rehab24/DATA_CARD_REHAB24.md) for class counts,
citation and academic/non-commercial conditions. This data is not used in the
current benchmark; coordinate and temporal conventions must be mapped first.

**Storage:** local media under `data/raw/` is excluded from Git. See
[acquisition evidence](DATA_ACQUISITION.md) for archive checksums and exact paths.
