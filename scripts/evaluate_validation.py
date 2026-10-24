"""Measure the fixed squat clip baseline on Mendeley side-view validation videos.

Whole-clip predictions are compared to whole-clip source labels; frames are not labeled.
All selected validation media must exist, and zero-frame runs are errors.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from posture_check.__main__ import process
from posture_check.pose import PoseEstimator
from posture_check.clip import summarize, classification_metrics, RULES
import cv2

ROOT = Path(__file__).resolve().parents[1]


def validation_paths(root):
    manifest = ROOT / "data/prepared/mendeley/val_videos.csv"
    with manifest.open(newline="", encoding="utf-8") as stream:
        rows = [r for r in csv.DictReader(stream)
                if r["exercise"] == "squat" and "/side/" in r["relative_video_path"]]
    if not rows or any(r["split"] != "val" or r["requires_review"] != "NO" for r in rows):
        raise ValueError("Expected nonempty, reviewed validation-only squat manifest")
    paths = []
    for row in rows:
        path = (root / row["relative_video_path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Manifest path escapes media root")
        if not path.is_file():
            raise FileNotFoundError(f"Validation media missing: {path}")
        paths.append((path, row))
    return manifest, paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media-root", type=Path, required=True,
                        help="Directory containing 'Dataset Subject-wise'")
    parser.add_argument("--model", type=Path, default=ROOT / "models/pose_landmarker_lite.task")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/side_validation_metrics.json")
    args = parser.parse_args()
    try:
        manifest, paths = validation_paths(args.media_root)
        estimator = PoseEstimator(args.model)
        results = []
        start = time.perf_counter()
        try:
            for path, row in paths:
                capture = cv2.VideoCapture(str(path))
                frames = detected = assessable = 0
                records = []
                seconds = 0.0
                try:
                    if not capture.isOpened():
                        raise ValueError(f"Cannot open {path}")
                    while True:
                        ok, frame = capture.read()
                        if not ok:
                            break
                        _, result = process(frame, estimator)
                        records.append(result)
                        frames += 1
                        detected += result["pose_detected"]
                        assessable += result["features"] is not None
                        seconds += result["processing_seconds"]
                    if not frames:
                        raise ValueError(f"No decoded frames: {path}")
                finally:
                    capture.release()
                results.append({"video": row["relative_video_path"], "frames": frames,
                                "ground_truth": row["form_label"],
                                "participant_id": row["participant_id"],
                                "clip_assessment": summarize(records),
                                "detected_frames": detected, "assessable_frames": assessable,
                                "processing_seconds": seconds})
                print(f"Processed {path.name}: {frames} frames")
        finally:
            estimator.close()
        elapsed = time.perf_counter() - start
        frames = sum(r["frames"] for r in results)
        seconds = sum(r["processing_seconds"] for r in results)
        report = {"measured_at_utc": datetime.now(timezone.utc).isoformat(),
                  "method_version": "squat-geometric-v2", "clip_rules": RULES,
                  "view": "side", "classification": classification_metrics(results),
                  "manifest": str(manifest.relative_to(ROOT)), "exercise": "squat",
                  "model_sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
                  "videos": len(results), "frames": frames,
                  "processing_fps": frames / seconds,
                  "decode_and_processing_fps": frames / elapsed,
                  "assessable_fraction": sum(r["assessable_frames"] for r in results) / frames,
                  "pose_detection_fraction": sum(r["detected_frames"] for r in results) / frames,
                  "timing_scope": "CPU image-mode baseline, includes first-frame warm-up; no encoding",
                  "limitations": "Provisional clip rules; side view only; source clip labels; abstentions count as misses in overall accuracy; coverage is not landmark accuracy; no test-set use.",
                  "per_video": results}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "per_video"}, indent=2))
    except (ValueError, FileNotFoundError, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
