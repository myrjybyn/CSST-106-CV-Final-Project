# POSTURE CHECK â€” Milestone 1 Technical Evidence

**Full project title:** POSTURE CHECK: A COMPUTER VISION-BASED SYSTEM FOR REAL-TIME EXERCISE POSTURE MONITORING AND FEEDBACK

## Dataset evidence
- `data/samples/`: 20 human-reviewed extracted video frames; five each for squats, push-ups, lunges, and jumping jacks.
- `data/labels.csv`: image names, source videos, timestamps, action labels/variations, and provenance. **Form correctness is UNVERIFIED**; this is not a posture-classification dataset.
- `outputs/contact_sheet_20.png`: reviewer-checked 20-frame contact sheet.
- `docs/DATA_EVIDENCE.md`: source links, licenses, dataset limitations, and proposed future data plan.

## Feasibility spike
- `scripts/five_image_spike.py`: reads five of the committed sample JPGs and performs grayscale conversion, Gaussian blur, and Canny edge detection.
- `outputs/feasibility_spike_screenshot.png`: actual result from a successful local run, displaying five inputs and corresponding edge maps.

The spike establishes that the OpenCV processing pipeline works with the selected images. It **does not** establish landmark detection, correct-versus-incorrect posture, classification accuracy, or real-time performance.

## Run from a fresh clone

From this `milestone1/posture_check` directory, install dependencies and run the spike:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts/five_image_spike.py
```

The 20 input JPGs are already in the repository. Downloading all raw videos is **not required** to reproduce the five-image spike. The optional video preparation and manual frame-review scripts are included for future data collection. Re-running the original preparation script can overwrite reviewed labels, so do not run it on your submitted samples unless you intentionally want to regenerate and review them.

The full original videos are not committed; see `docs/DATA_EVIDENCE.md` for their links and licensing terms.
