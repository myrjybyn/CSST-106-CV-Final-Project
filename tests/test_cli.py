"""Exercise actual image/video codecs with a fake inference boundary.

These tests verify output and missing-pose behavior, not MediaPipe inference.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from posture_check.__main__ import run


class NoPose:
    def __init__(self, model):
        pass

    def detect(self, frame):
        return []

    def close(self):
        pass


class OutputTests(unittest.TestCase):
    @patch("posture_check.__main__.PoseEstimator", NoPose)
    def test_image_output_and_json_preserve_unassessable_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input.jpg", root / "output.png"
            self.assertTrue(cv2.imwrite(str(source), np.zeros((100, 200, 3), np.uint8)))
            report = run(source, output, "unused.task")
            self.assertIsNotNone(cv2.imread(str(output)))
            self.assertEqual(report["records"][0]["status"], "unassessable")
            self.assertIsNone(report["records"][0]["features"])
            self.assertEqual(json.loads(output.with_suffix(".png.json").read_text())["frames"], 1)
            with self.assertRaises(ValueError):
                run(source, source, "unused.task")

    @patch("posture_check.__main__.PoseEstimator", NoPose)
    def test_video_round_trip_and_all_frames_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input.mp4", root / "output.mp4"
            writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 10, (200, 100))
            self.assertTrue(writer.isOpened())
            for _ in range(3):
                writer.write(np.zeros((100, 200, 3), np.uint8))
            writer.release()
            self.assertEqual(run(source, output, "unused.task")["frames"], 3)
            capture = cv2.VideoCapture(str(output))
            count = 0
            while capture.read()[0]:
                count += 1
            capture.release()
            self.assertEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
