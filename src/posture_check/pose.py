"""MediaPipe CPU pose estimation: independent images or tracked video frames."""
import math
from pathlib import Path
import time
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class PoseEstimator:
    def __init__(self, model, *, video=False, fps=None):
        if not Path(model).is_file():
            raise FileNotFoundError(f"Model missing: {model}. Run python scripts/download_pose_model.py")
        if fps is not None and (not math.isfinite(fps) or not 0 < fps < 1000):
            raise ValueError('Valid video FPS required')
        self.video, self.fps = video, fps
        self.frame_index, self.last_timestamp = 0, -1
        self.started = time.perf_counter()
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model),
                                            delegate=python.BaseOptions.Delegate.CPU),
            running_mode=vision.RunningMode.VIDEO if video else vision.RunningMode.IMAGE,
            num_poses=1, min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5, min_tracking_confidence=0.5,
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)

    def detect(self, frame):
        image = mp.Image(image_format=mp.ImageFormat.SRGB,
                         data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if self.video:
            # Files use media time; webcams use actual elapsed capture/inference
            # time. Both remain strictly increasing after timestamp rounding.
            milliseconds = (self.frame_index*1000/self.fps if self.fps is not None
                            else (time.perf_counter()-self.started)*1000)
            stamp = max(self.last_timestamp+1, round(milliseconds))
            result = self.detector.detect_for_video(image,stamp)
            self.frame_index += 1
            self.last_timestamp = stamp
        else:
            result = self.detector.detect(image)
        return result.pose_landmarks[0] if result.pose_landmarks else []

    def close(self):
        self.detector.close()
