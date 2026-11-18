"""Timestamp and inference-mode contracts, without neural inference."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from posture_check.pose import PoseEstimator


class PoseModeTests(unittest.TestCase):
    def test_files_use_media_time_even_when_processing_fast(self):
        with tempfile.NamedTemporaryFile(suffix='.task') as model, patch('posture_check.pose.vision.PoseLandmarker.create_from_options') as make:
            make.return_value.detect_for_video.return_value=SimpleNamespace(pose_landmarks=[])
            estimator=PoseEstimator(Path(model.name),video=True,fps=15)
            frame=np.zeros((20,20,3),np.uint8)
            for _ in range(4):estimator.detect(frame)
            self.assertEqual([c.args[1] for c in make.return_value.detect_for_video.call_args_list],[0,67,133,200])
            make.return_value.detect.assert_not_called();estimator.close()
            make.return_value.close.assert_called_once()

    def test_live_timestamps_increase_when_clock_rounds_to_same_ms(self):
        with tempfile.NamedTemporaryFile(suffix='.task') as model, patch('posture_check.pose.vision.PoseLandmarker.create_from_options') as make, patch('posture_check.pose.time.perf_counter',return_value=10):
            make.return_value.detect_for_video.return_value=SimpleNamespace(pose_landmarks=[])
            estimator=PoseEstimator(model.name,video=True)
            for _ in range(3):estimator.detect(np.zeros((20,20,3),np.uint8))
            self.assertEqual([c.args[1] for c in make.return_value.detect_for_video.call_args_list],[0,1,2])

    def test_image_baseline_does_not_use_video_tracking(self):
        with tempfile.NamedTemporaryFile(suffix='.task') as model, patch('posture_check.pose.vision.PoseLandmarker.create_from_options') as make:
            make.return_value.detect.return_value=SimpleNamespace(pose_landmarks=[])
            estimator=PoseEstimator(model.name)
            estimator.detect(np.zeros((20,20,3),np.uint8))
            make.return_value.detect.assert_called_once();make.return_value.detect_for_video.assert_not_called()
