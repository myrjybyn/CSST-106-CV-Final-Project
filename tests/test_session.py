"""Guided session rules, automatic stopping, recording, and resource checks."""
import copy
import itertools
import json
from pathlib import Path
import queue
import tempfile
import threading
import unittest
from unittest.mock import patch

import numpy as np

from posture_check.gui import camera_worker
from posture_check.session import ExerciseSession, SessionRecorder, GuidedRepetitionCounter
from posture_check.temporal import TemporalAnalyzer
from test_temporal import sample


def cycle(exercise, change=None):
    session = ExerciseSession(exercise)
    analyzer = TemporalAnalyzer(exercise, 30)
    for lowered in (False, True, False):
        raw = sample(exercise, lowered)
        if change:
            change(raw['features'], lowered)
        for _ in range(30):
            session.add(analyzer.update(copy.deepcopy(raw)))
    return session


class SessionTests(unittest.TestCase):
    def test_good_full_cycles_for_all_four_exercises(self):
        for exercise in ('squat', 'pushup', 'lunge', 'jumping_jack'):
            with self.subTest(exercise=exercise):
                result = cycle(exercise).assess()
                self.assertEqual(result['prediction'], 'good', result)
                self.assertFalse(result['issues'])

    def test_squat_depth_has_a_specific_tip(self):
        def shallow(features, lowered):
            features['knee_angle'] = 120 if lowered else 170
        result = cycle('squat', shallow).assess()
        self.assertEqual(result['prediction'], 'bad')
        self.assertIn('limited_depth', result['issues'])
        self.assertTrue(any('lowering' in tip for tip in result['tips']))

    def test_shallow_movement_can_count_but_still_fail_form(self):
        counter = GuidedRepetitionCounter('squat')
        for lowered in (False, True, False):
            features = sample('squat', lowered)['features']
            features['knee_angle'] = 120 if lowered else 170
            for _ in range(20):
                counter.update(features, .05)
        self.assertEqual(counter.count, 1)
        result = cycle('squat', lambda f, low: f.update(knee_angle=120 if low else 170)).assess()
        self.assertEqual(result['prediction'], 'bad')

    def test_pushup_alignment_and_return_are_separate_checks(self):
        def misaligned(features, lowered):
            features['body_alignment'] = 140
            features['elbow_angle'] = 80 if lowered else 125
        result = cycle('pushup', misaligned).assess()
        self.assertEqual(result['prediction'], 'bad')
        self.assertIn('body_alignment', result['issues'])
        self.assertIn('incomplete_extension', result['issues'])

    def test_jack_checks_foot_spacing_and_symmetry(self):
        def uneven(features, lowered):
            if lowered:
                features['right_arm_angle'] = 90
                features['ankle_width_ratio'] = 1.5
        result = cycle('jumping_jack', uneven).assess()
        self.assertEqual(result['prediction'], 'bad')
        self.assertIn('feet_not_spread', result['issues'])
        self.assertIn('arm_asymmetry', result['issues'])

    def test_tracking_loss_is_not_good_or_bad_form(self):
        session = cycle('squat')
        for _ in range(200):
            session.add({'features': None})
        result = session.assess()
        self.assertEqual(result['prediction'], 'unassessable')
        self.assertEqual(result['reason'], 'insufficient_pose_coverage')

    def test_waiting_in_start_position_does_not_dilute_depth(self):
        session = ExerciseSession('squat')
        standing = dict(sample('squat'), instantaneous_phase='standing')
        for _ in range(2000):
            session.add(standing)
        self.assertFalse(session.records)
        self.assertEqual(len(session.before_movement), 15)
        self.assertEqual(session.assess()['reason'], 'insufficient_observed_movement')

    def test_recording_paces_frames_by_elapsed_time(self):
        frame = np.zeros((32, 32, 3), dtype=np.uint8)
        with patch('posture_check.session.cv2.VideoWriter') as factory:
            recorder = SessionRecorder('unused.mp4', frame)
            recorder.write(frame, 0)
            recorder.write(frame, .02)
            recorder.write(frame, .15)
            self.assertEqual(factory.return_value.write.call_count, 4)
            recorder.close()
            factory.return_value.release.assert_called_once()

    def test_encoder_failure_releases_writer(self):
        with patch('posture_check.session.cv2.VideoWriter') as factory:
            factory.return_value.isOpened.return_value = False
            with self.assertRaises(RuntimeError):
                SessionRecorder('unused.mp4', np.zeros((32, 32, 3), dtype=np.uint8))
            factory.return_value.release.assert_called_once()

    def test_target_stops_worker_saves_summary_and_releases_everything(self):
        frames = itertools.chain.from_iterable([sample('squat', low)] * 20 for low in (False, True, False))
        clock = itertools.count(0, .05)
        with tempfile.TemporaryDirectory() as folder, \
                patch('posture_check.gui.cv2.VideoCapture') as capture, \
                patch('posture_check.gui.PoseEstimator') as model, \
                patch('posture_check.gui.SessionRecorder') as recorder, \
                patch('posture_check.gui.process', side_effect=lambda *a, **k: ([], copy.deepcopy(next(frames)))), \
                patch('posture_check.gui.time.perf_counter', side_effect=lambda: next(clock)):
            capture.return_value.read.return_value = (True, np.zeros((32, 32, 3), dtype=np.uint8))
            mailbox = queue.Queue(maxsize=1)
            camera_worker(mailbox, threading.Event(), 'unused', 'squat', 0, True, False,
                          target=1, output_root=folder, countdown_seconds=0)
            kind, summary = mailbox.get_nowait()
            self.assertEqual(kind, 'complete', summary)
            self.assertEqual(summary['end_reason'], 'target_reached')
            self.assertEqual(summary['completed_reps'], 1)
            self.assertEqual(summary['assessment']['prediction'], 'good')
            self.assertEqual(json.loads(Path(summary['report_path']).read_text())['target_reps'], 1)
            recorder.return_value.close.assert_called_once()
            capture.return_value.release.assert_called_once()
            model.return_value.close.assert_called_once()

    def test_cancel_during_countdown_creates_no_recording(self):
        stop = threading.Event()
        stop.set()
        with tempfile.TemporaryDirectory() as folder, \
                patch('posture_check.gui.cv2.VideoCapture'), patch('posture_check.gui.PoseEstimator'):
            mailbox = queue.Queue(maxsize=1)
            camera_worker(mailbox, stop, 'unused', 'squat', 0, False, False, output_root=folder)
            kind, summary = mailbox.get_nowait()
            self.assertEqual(kind, 'complete')
            self.assertEqual(summary['end_reason'], 'cancelled_before_recording')
            self.assertIsNone(summary['video_path'])
            self.assertFalse(list(Path(folder).iterdir()))


if __name__ == '__main__':
    unittest.main()
