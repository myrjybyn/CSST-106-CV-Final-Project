"""MediaPipe Tasks Pose Landmarker, CPU image mode for a per-frame baseline."""
from pathlib import Path
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class PoseEstimator:
    def __init__(self, model):
        if not Path(model).is_file():
            raise FileNotFoundError(f"Model missing: {model}. Run python scripts/download_pose_model.py")
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model),
                                            delegate=python.BaseOptions.Delegate.CPU),
            running_mode=vision.RunningMode.IMAGE, num_poses=1,
            min_pose_detection_confidence=0.5, min_pose_presence_confidence=0.5,
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)

    def detect(self, frame):
        image = mp.Image(image_format=mp.ImageFormat.SRGB,
                         data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        result = self.detector.detect(image)
        return result.pose_landmarks[0] if result.pose_landmarks else []

    def close(self):
        self.detector.close()
