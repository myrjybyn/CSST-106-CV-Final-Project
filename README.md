# Posture Check

A webcam app that counts exercise repetitions and gives an overall form estimate
with improvement tips. Supports **squats, push-ups, lunges, and jumping jacks**.
Built with Python, MediaPipe, OpenCV, and Tkinter for CSST 106.

## 1. Setup

Use **Python 3.12** for the pinned dependencies in `requirements.txt`. You also need
an internet connection for installation, a webcam, and a graphical desktop.
No GPU or model training is needed.

Open a terminal in this project folder and run:

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/download_pose_model.py
```

If PowerShell blocks activation, skip that step and replace `python` with
`.\.venv\Scripts\python.exe` in the install, model-download, and run commands.

**Linux / macOS**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_pose_model.py
```

Linux may also need Tkinter and OpenCV system libraries, such as `python3-tk`,
`libgl1`, and `libglib2.0-0` on Ubuntu. Keep the environment activated when using
this project. Use the root `requirements.txt`; the milestone-one requirements
belong to the older prototype.

## 2. Run the app: one command

```bash
python app.py
```

1. Choose an exercise.
2. Set your target reps using the minus/plus buttons or type a number from 1 to 100.
3. Press **Start Session** and get into position during the 3-second countdown.
4. Complete your reps. Recording stops automatically when the target is counted.
5. Read the **Good / Bad** form estimate and improvement tips.

Use a **side view** for squats, push-ups, and lunges, and a **front view** for
jumping jacks. Keep your whole body visible. Use **End Session** or Escape to
finish early. If tracking or movement is insufficient, the app asks you to retry.
Sessions also end after 10 minutes.

Each session saves `recording.mp4` and `summary.json` in its own folder under
`outputs/sessions/`. Files stay on your device. Camera selection, mirroring, and
skeleton display are available in **Settings**.

[Full session guide and exercise criteria](docs/GUIDED_SESSION.md)

## 3. Model weights

The setup script downloads Google's pretrained **MediaPipe Pose Landmarker Lite**
model to `models/pose_landmarker_lite.task` and verifies its checksum.

[Official model download](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task)

If downloading manually, save the file at that same path. Model weights are
excluded from Git, so a fresh clone needs this download.

## 4. Sample inputs

The repository includes 20 sample images in
[`milestone1/posture_check/data/samples/`](milestone1/posture_check/data/samples/).
Try one without using a webcam:

```bash
python run.py --input milestone1/posture_check/data/samples/squat_01.jpg --output outputs/sample_squat.png --exercise squat
```

This creates `outputs/sample_squat.png` and `outputs/sample_squat.png.json`.
Images demonstrate pose detection; repetition counting needs a video or webcam.
The file-processing command uses the earlier CLI pipeline, while `app.py` uses
the guided-session rules.

For a video, use your own MP4 with the matching exercise selected:

```bash
python run.py --input my_squat.mp4 --output outputs/my_squat_checked.mp4 --exercise squat
```

Exercise names for the CLI are `squat`, `pushup`, `lunge`, and `jumping_jack`.

For the labeled squat/push-up dataset, download **Dataset Subject-wise.zip** from
[Mendeley Data, version 3](https://data.mendeley.com/datasets/kgbb3yn47p/3).
Extract it so the folder is `data/raw/mendeley/Dataset Subject-wise/`.
The prepared subset lists 294 videos in `data/prepared/mendeley/`.
Large videos are excluded from Git. The dataset uses CC BY 4.0; keep its attribution.
See [dataset sources and checksums](docs/DATA_ACQUISITION.md).

## 5. Reproduce the checks and reported results

### Current app checks

From the project folder, run the automated tests:

```powershell
$env:PYTHONPATH = "src;tests"
python -m unittest discover -s tests -v
```

On Linux/macOS, use:

```bash
PYTHONPATH=src:tests python -m unittest discover -s tests -v
```

The current suite has **77 tests** and should finish with `OK`. These check
software behavior, including counting, form rules, automatic stopping, and
recording cleanup; they do not establish form-classification accuracy.

To check the desktop layout and save example UI screenshots without opening
the camera:

```bash
python scripts/check_guided_session_ui.py
```

Screenshots and the check log are saved in `outputs/guided_session_smoke/`.
For a webcam check, run `python app.py`, complete a short set, and verify the
saved recording, target count, and summary.

### Current guided-rule comparison

The [guided evaluation folder](docs/guided_evaluation/README.md) documents a
matched squat/push-up comparison between the existing fixed clip rules and the
current guided rules. It uses 16 previously exposed, source-labeled Mendeley
videos. This is a complete-video test, not a new independent test or a measurement
of webcam operation and automatic stopping.

[Recorded results](docs/guided_evaluation/results.md): both methods scored
43.75% accuracy and 0.430 macro-F1, assessing 15 of 16 clips. No classification
improvement was measured on this set.

After downloading the model and dataset, reproduce it with:

```bash
python scripts/evaluate_guided_rules.py --output outputs/guided_rerun/results_rerun.json
```

Use a new output filename and stem for each run. The script checks the frozen
code, model, and video hashes, then saves JSON, CSV, and Markdown results.

### Earlier reported accuracy and speed

The earlier clip-level results are preserved in
[docs/calibration/README.md](docs/calibration/README.md), with raw results in
`docs/calibration/prospective_results.json` and `laptop_benchmark.json`.
**Those figures describe the earlier calibrated pipeline, not the current guided app.**

To rerun them, use a separate copy of the matching source revision. Use Linux or
WSL for the frozen evaluator, which stores paths with `/` separators:

```bash
git -c core.autocrlf=false clone https://github.com/myrjybyn/CSST-106-CV-Final-Project.git ../posture-check-results
cd ../posture-check-results
git checkout c5196f6b2778c892d4d459090780f6d0bc6685fb
```

Set up a Python environment, download the model, and place the Mendeley dataset
in that copy using the steps above. Then run:

```bash
python src/evaluate.py --suite prospective --output outputs/reproduced/prospective.json
```

For the earlier laptop benchmark, also provide the four original clips in
`data/raw/phase3_user/`: `push_up.mp4`, `squat.mp4`, `lunge.mp4`, and
`jumping_jacks.mp4`. These clips are local and must accompany the submission
separately if that benchmark is reported. Their original download URLs were not
recorded. Run from the matching source copy:

```bash
python src/evaluate.py --suite benchmark --runtime-label laptop --output outputs/reproduced/laptop_benchmark.json
```

Use a new output filename for each rerun. The evaluator checks code, model, and
input hashes. Running it against the updated GUI source will fail its old checksum
check. Speed varies with hardware and environment; see the recorded
[laptop environment and procedure](docs/calibration/LAPTOP_BENCHMARK_STATUS.md).

## 6. Project files and report material

| Location | Contents |
| --- | --- |
| `app.py` | Desktop app entry point |
| `src/posture_check/` | Pose detection, counting, form rules, recording, and interface |
| `run.py` | Image/video processing entry point |
| `tests/` | Automated software checks |
| `scripts/` | Model download, dataset preparation, evaluation, and report tools |
| `assets/` | Interface artwork |
| `data/prepared/` | Dataset manifests and splits |
| `docs/` | Proposal, methodology, experiments, results, references, and report drafts |
| `outputs/` | Generated recordings, screenshots, and processing results; excluded from Git |

[Documentation index](docs/README.md) links to the existing report material.
[Task-designation records](docs/MILESTONE2_STATUS.md) provide a starting point
for the contribution table; confirm the final contributions with the team.

Form estimates use selected 2D movement criteria. Camera angle, lighting,
occlusion, and missed counts can affect the result. Complete-clip evaluation does
not establish reliable form assessment for every person, exercise, or camera setup.
