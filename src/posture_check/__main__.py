"""One command for annotated image/video output and per-frame feature evidence."""
import argparse
import json
from pathlib import Path
import time
import cv2
from .baseline import assess
from .clip import summarize, RULES
from .features import extract
from .pose import PoseEstimator

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CONNECTIONS = ((11, 12), (11, 23), (12, 24), (23, 24), (23, 25),
               (25, 27), (24, 26), (26, 28))


def process(frame, estimator):
    start = time.perf_counter()
    landmarks = estimator.detect(frame)
    height, width = frame.shape[:2]
    features = extract(landmarks, width, height)
    result = assess(features)
    result["features"] = features.to_dict() if features else None
    result["pose_detected"] = bool(landmarks)
    result["processing_seconds"] = time.perf_counter() - start
    return landmarks, result


def annotate(frame, landmarks, result):
    canvas = frame.copy()
    height, width = frame.shape[:2]
    for a, b in CONNECTIONS:
        if result["features"] is not None and landmarks and all(min(landmarks[i].visibility, landmarks[i].presence) >= .5 for i in (a, b)):
            points = [(int(landmarks[i].x * width), int(landmarks[i].y * height)) for i in (a, b)]
            cv2.line(canvas, points[0], points[1], (0, 220, 255), 2)
    canvas = cv2.copyMakeBorder(canvas, 0, 90, 0, max(0, 750 - width), cv2.BORDER_CONSTANT)
    lines = [f"SQUAT BASELINE | {result['status']} | {result['phase']}", result["feedback"],
             "Provisional 2D rules; use a side view. Not validated posture advice."]
    for i, line in enumerate(lines):
        cv2.putText(canvas, line, (8, height + 23 + 26 * i), cv2.FONT_HERSHEY_SIMPLEX,
                    .48, (255, 255, 255), 1, cv2.LINE_AA)
    return canvas


def run(source, output, model):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("Input and output must be different files")
    if not source.is_file():
        raise FileNotFoundError(source)
    is_image = source.suffix.lower() in IMAGE_EXTENSIONS
    if (is_image and output.suffix.lower() not in IMAGE_EXTENSIONS) or (not is_image and output.suffix.lower() != ".mp4"):
        raise ValueError("Use an image output extension for images, or .mp4 for videos")
    output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    capture = writer = None
    estimator = PoseEstimator(model)
    try:
        if is_image:
            frame = cv2.imread(str(source))
            if frame is None:
                raise ValueError(f"Cannot decode image: {source}")
            landmarks, result = process(frame, estimator)
            records.append(dict(frame_index=0, **result))
            if not cv2.imwrite(str(output), annotate(frame, landmarks, result)):
                raise RuntimeError(f"Cannot write {output}")
        else:
            capture = cv2.VideoCapture(str(source))
            if not capture.isOpened():
                raise ValueError(f"Cannot open video: {source}")
            fps = capture.get(cv2.CAP_PROP_FPS)
            if not 0 < fps < 1000:
                raise ValueError("Video has invalid FPS metadata")
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                landmarks, result = process(frame, estimator)
                records.append(dict(frame_index=len(records), **result))
                canvas = annotate(frame, landmarks, result)
                # Most MP4 encoders require even dimensions.
                h, w = canvas.shape[:2]
                canvas = cv2.copyMakeBorder(canvas, 0, h % 2, 0, w % 2, cv2.BORDER_CONSTANT)
                if writer is None:
                    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps,
                                             (canvas.shape[1], canvas.shape[0]))
                    if not writer.isOpened():
                        raise RuntimeError(f"Cannot create video: {output}")
                writer.write(canvas)
            if not records:
                raise ValueError("Video contains no decodable frames")
    finally:
        estimator.close()
        if capture is not None:
            capture.release()
        if writer is not None:
            writer.release()
    report = {"input": str(source), "exercise": "squat", "method": "single-frame baseline",
              "method_version": "squat-geometric-v2", "clip_rules": RULES,
              "clip_assessment": summarize(records) if not is_image else None,
              "clip_assumption": "Side-view squat clip supplied by operator; thresholds provisional",
              "frames": len(records), "records": records,
              "processing_fps": len(records) / sum(r["processing_seconds"] for r in records),
              "timing_scope": "pose inference and rules; excludes decoding, drawing and encoding"}
    output.with_suffix(output.suffix + ".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", type=Path, default=Path("models/pose_landmarker_lite.task"))
    args = parser.parse_args()
    try:
        report = run(args.input, args.output, args.model)
    except (ValueError, FileNotFoundError, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Wrote {args.output} and JSON evidence; {report['frames']} frames, {report['processing_fps']:.2f} processing FPS")


if __name__ == "__main__":
    main()
