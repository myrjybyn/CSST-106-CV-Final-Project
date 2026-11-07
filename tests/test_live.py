"""Live timing and resource-lifecycle checks without requiring a webcam."""
import queue
import threading
import unittest
from unittest.mock import patch

import numpy as np
from posture_check.gui import camera_worker, publish_latest
from posture_check.temporal import TemporalAnalyzer
from test_temporal import sample


class LiveTests(unittest.TestCase):
    def test_wall_time_cycles_across_camera_cadences(self):
        for dt in (.025, .08, .16):
            for mode in ('squat', 'pushup', 'lunge', 'jumping_jack'):
                analyzer = TemporalAnalyzer(mode, 30)
                for lowered in (False, True, False):
                    for _ in range(round(1.5/dt)):
                        analyzer.update(sample(mode, lowered), dt_seconds=dt)
                self.assertEqual(analyzer.count, 1, (dt, mode))

    def test_camera_stall_cannot_complete_partial_cycle(self):
        a = TemporalAnalyzer('squat', 30)
        for lower in (False, True):
            for _ in range(20):
                a.update(sample('squat', lower), dt_seconds=.08)
        a.update(sample('squat'), dt_seconds=1.0)
        for _ in range(20):
            a.update(sample('squat'), dt_seconds=.08)
        self.assertEqual(a.count, 0)

    def test_invalid_live_elapsed_rejected(self):
        a = TemporalAnalyzer('squat', 30)
        for dt in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                a.update(sample('squat'), dt_seconds=dt)

    def test_preview_keeps_only_latest(self):
        q = queue.Queue(maxsize=1)
        publish_latest(q, 1);publish_latest(q, 2)
        self.assertEqual(q.get_nowait(), 2)

    def test_camera_failure_releases_capture(self):
        with patch('posture_check.gui.cv2.VideoCapture') as factory:
            factory.return_value.isOpened.return_value = False
            q = queue.Queue(maxsize=1)
            camera_worker(q, threading.Event(), 'unused', 'squat', 0, True, True)
            self.assertEqual(q.get_nowait()[0], 'error')
            factory.return_value.release.assert_called_once()

    def test_inference_failure_closes_model_and_camera(self):
        with patch('posture_check.gui.cv2.VideoCapture') as capture, patch('posture_check.gui.PoseEstimator') as model:
            capture.return_value.read.return_value = (True, np.zeros((32,32,3),dtype=np.uint8))
            model.return_value.detect.side_effect = RuntimeError('Inference failed')
            q=queue.Queue(maxsize=1)
            camera_worker(q,threading.Event(),'unused','squat',0,True,True)
            self.assertEqual(q.get_nowait(), ('error', 'Inference failed'))
            capture.return_value.release.assert_called_once()
            model.return_value.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
