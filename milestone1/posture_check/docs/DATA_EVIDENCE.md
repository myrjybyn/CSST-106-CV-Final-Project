# DATA EVIDENCE & FEASIBILITY — POSTURE CHECK

Updated: 2026-10-15. Sources were verified through their public descriptions. This file is a factual source review + a reproducible generation plan; the actual frames are generated locally by running `python run_all.py`.

## A. Data acquisition for the Milestone 1 contact sheet

Four clips from Wikimedia Commons (5 frames each = 20 samples) ensure demonstrable provenance and documented reuse rights.

| Action label | Source video | File used locally | Author | License |
|---|---|---|---|---|
| Squat | https://commons.wikimedia.org/wiki/File:Squat_-_exercise_demonstration_video.webm | squat.webm | FitnessScape | CC BY 3.0 |
| Push-up | https://commons.wikimedia.org/wiki/File:Muscle_Strengthening_at_Home_-_Push-ups.webm | pushup.webm | US CDC | US federal government public domain |
| Lunge | https://commons.wikimedia.org/wiki/File:Forward_lunge_training.webm | lunge.webm | Skhulile Mthiyane | CC BY-SA 4.0 |
| Jumping jack | https://commons.wikimedia.org/wiki/File:Jumping_jacks_and_burpees.webm | jumping_jack.webm | Taco fleur | CC BY-SA 4.0 |

**Attribution:** Cite creators, original source, and exact licenses in both the report and repository. Images extracted from CC BY-SA sources are adaptations: retain attribution, indicate that the image is a still frame extracted from the source, and honor share-alike terms when distributing derivatives. Avoid uploading full raw videos to the repository.

**Labels in the contact sheet:** action/exercise type (derived from source video subject), time in source, `Form correctness: UNVERIFIED`. These are NOT correct/incorrect posture annotations. Human inspection of the individual sampled frames is necessary because introductory segments or other movements may be present in the original videos, particularly in the combination 'Jumping jacks and burpees' clip.

**Data variety/limitations:** these four clips offer 4 types of movement and several temporal positions but only one clip per class. The distribution is not representative of diverse body types, lighting, clothes, backgrounds, ages, camera views, or correct/incorrect form. It is valid for a small acquisition-and-toolchain check, not for estimating model classification accuracy.

## B. Future dataset candidates

**1. REHAB24-6** https://zenodo.org/records/13305826
- Dataset contains 65 recordings, 1,072 annotated repetitions, multi-view RGB plus joint positions, binary exercise correctness, lighting/view variation.
- Three overlapping exercises: squat, leg lunge, table-supported push-up; NO jumping jack.
- Source license is academic/non-profit NON-COMMERCIAL research use with attribution, described as CC BY-NC by OpenAIRE. The official dataset restrictions override contradictory descriptions in derivative repositories.
- Relevant for the actual correct/incorrect posture research and evaluation phase. Extract labels at **repetition** level, not assume that all frames from the same repetition are independently labeled.
- Paper: Černek et al. (2024), "REHAB24-6: Physical Therapy Dataset for Analyzing Pose Estimation Methods", SISAP.

**2. Pose Estimation Model Comparison** https://github.com/DrishtiRai777/Pose-Estimation-Model-Comparison
- Includes small exercise videos `jj.mp4`, `lunges.mp4`, `pushup.mp4`, `squat.mp4` and landmarks extracted by BlazePose / YOLO / MoveNet.
- Matches all four classes, but no confirmed correct/incorrect ground truth, and no explicit license was found in the inspected repository listing. Seek permission before republishing content. Useful for learning/landmark evaluation, not as a validated form-correctness set.

**3. Body-weight exercises** https://github.com/andrebert/body-weight-exercises
- Contains accelerometer/sensor readings of 8 exercises for 26 subjects, 11,000+ individual reps. Quality ratings (1 excellent – 5 very bad) apply to labeled exercises including lunges, squats and jumping jacks. Push-ups lacked rep segmentation and labeling in the repository description.
- Sensor features aren't camera images; use as supplementary label-design inspiration, not as a substitute for video samples.

## C. Feasibility operation

**Baseline spike:** For five actual frames (2 squat, 1 push-up, 1 lunge, 1 jumping jack), load through `cv2.imread`, convert to grayscale, apply Gaussian blur (5x5), compute Canny edges with thresholds (50,150), save each result, create the side-by-side panel screenshot. This is exactly the classical CV operation named as an acceptable example in the course guide.

**Optional stronger model test:** Pretrained MediaPipe Pose Landmarker detects up to 33 body keypoints and draws a skeleton; use `python scripts/pose_spike_optional.py`. This detects **pose only**, not exercise accuracy. Verify it independently on your laptop before using it for a class demo.

**Result documentation, after running:** Fill in date, machine CPU, Python/OpenCV version, count of 5 decoded files, time to process, count of frames where landmarks were detected (optional). Do not cite percentage of frames with edges as correct/incorrect form accuracy. Save output screenshot in the repository.

## D. Proposed methods after M1

Camera frames -> resizing/colorspace and detection -> pose landmarks -> joint-angle/normalized-distance features -> phase-aware exercise-specific thresholds/rules -> smoothing and feedback overlay.

- **Minimum viable method:** one or two exercises, real-time MediaPipe landmarks + manually-reviewed exercise-angle rules (e.g. squat knee flexion phase). Feedback only on frames with sufficiently visible joints.
- **Main method:** pose landmarks over multiple video frames, exercise-phase tracking, stabilized angle estimates and rule-based quality flags; explore supervised form-quality models ONLY if sufficient validated correct/incorrect labels are acquired.
- **Metrics:** landmark detection rate, estimated frames per second and latency, and precision/recall/F1 for labeled *form-correctness repetitions* on held-out participants. Compare models using the same camera/data and identical splits.
- **Proposed split for larger research datasets:** 70% train / 15% validation / 15% test by participant/session. Never randomly split adjacent frames of the same subject/video across sets.

## E. The required submission artifacts

`outputs/contact_sheet_20.png`, `data/labels.csv`, `data/samples/` (20 real frames), `scripts/prepare_data.py`, `scripts/five_image_spike.py`, `outputs/feasibility_spike_screenshot.png`, and the proposal PDF (plus nine outline items). Verify the files exist after executing the code.

For delivery, instructor guide specifies one Milestone-1 tag `cp1-proposal` and at least one commit per member, due 2026-10-15 at 11:30 PM.
