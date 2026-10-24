# Acquired media in the prepared cloud environment

All four user-supplied downloads were acquired over verified HTTPS and matched
their publishers' size and checksum metadata. Large archives and extracted media
are local, ignored files under `data/raw/`; they are not included in a Git clone.
The original prepared manifests, labels, and data cards were left unchanged.

## Mendeley Data, version 3

Source: https://data.mendeley.com/datasets/kgbb3yn47p/3
File: `Dataset Subject-wise.zip` (3,113,825,556 bytes).
Published SHA256:
`6f6bfda33f094ba13e8509b1cd9a5c1e479062fd0e7749f6b6713db7d588ef84`.
License: CC BY 4.0; preserve the source attribution documented in the data card.

The complete archive is retained at `data/raw/mendeley/Dataset Subject-wise.zip`.
Only the 294 squat/push-up clips referenced by the committed manifests were
extracted, under `data/raw/mendeley/Dataset Subject-wise/`. Each extracted entry
passed ZIP CRC verification. Every manifest path exists:

| Partition | Clips | Participants |
|---|---:|---:|
| Train | 210 | 18 |
| Validation | 48 | 4 |
| Test | 36 | 3 |

For the existing validation command, use `--media-root data/raw/mendeley`.
The test clips were extracted and checked for file presence, but not evaluated
or used to adjust the algorithm. Published clip-level form labels were not
converted into frame-level correctness labels.

## REHAB24-6

Source: https://zenodo.org/records/13305826
Retain the source's academic/non-commercial conditions and citation requirements
described in the existing REHAB24 data card.

| Download | Bytes | Published MD5 |
|---|---:|---|
| `videos.zip` | 2,651,613,914 | `ed183a245a1b171638e422f7a288e5a8` |
| `2d_joints.zip` | 693,401,748 | `dbfbc09d3f087482abc3f6c23bcf48bd` |
| `Segmentation.csv` | 53,290 | `90b8fbd7445dd050bf27b17126c78fbe` |

All three original files are retained in `data/raw/rehab24/`. The video archive
was extracted to `data/raw/rehab24/videos/` (130 MP4s), and the joint archive to
`data/raw/rehab24/2d_joints/` (260 NPY files). Extraction checked ZIP CRCs and
rejected paths escaping the destination or symbolic-link entries.

All 28 recording IDs referenced by the prepared subset have both camera files
present (56 videos). Re-running annotation preparation into a separate ignored
output directory reproduced all five committed REHAB24 CSV manifests exactly:
476 repetitions, split 354 / 65 / 57 across train / validation / test.

REHAB24 has been acquired but was not used in the MediaPipe validation run.
Its joint conventions, 30/120 FPS variants, temporal annotation indices and camera
orientation must be reconciled before integrating those features or labels.

## Provenance and measured results

Each dataset directory contains `source_metadata.json`,
`download_provenance.json` and `manifest_presence_check.json`. REHAB24 also has
per-download provenance with both the published MD5 and a locally computed
SHA256. Interrupted transfers were resumed using checked HTTP byte ranges;
complete files were checksum-verified before extraction or use.

The real Mendeley squat validation measurement is saved in
[results/mendeley_squat_validation.json](results/mendeley_squat_validation.json):
24 clips, 11,090 frames, 31.88 processing FPS. The measured coverage rates do not
establish pose or posture correctness; see
[milestone status](MILESTONE2_STATUS.md) for the observed false detection and
remaining model-quality limitations.
