"""Known pose geometry and clip behavior; not real-data accuracy claims."""
import math
from types import SimpleNamespace
import unittest
from posture_check.exercises import (extract_for_exercise, assess_for_exercise,
                                     summarize_for_exercise)


def landmarks(coordinates):
    points = [SimpleNamespace(x=.5, y=.5, visibility=0., presence=0.) for _ in range(33)]
    for index, (x, y) in coordinates.items():
        points[index] = SimpleNamespace(x=x / 1000, y=y / 1000, visibility=.95, presence=.95)
    return points


def pushup(hip=(500, 300)):
    return landmarks({11: (200, 300), 13: (300, 400), 15: (400, 300),
                      23: hip, 27: (900, 300)})


def lunge():
    return landmarks({11: (400, 150), 12: (450, 150), 23: (400, 450), 24: (450, 450),
                      25: (350, 650), 26: (650, 700), 27: (500, 650), 28: (750, 900)})


def jack(opened):
    return landmarks({11: (400, 250), 12: (600, 250), 23: (450, 500), 24: (550, 500),
                      15: (300, 50) if opened else (420, 480),
                      16: (700, 50) if opened else (580, 480),
                      25: (350, 700) if opened else (450, 700),
                      26: (650, 700) if opened else (550, 700),
                      27: (200, 900) if opened else (450, 900),
                      28: (800, 900) if opened else (550, 900)})


class FeatureTests(unittest.TestCase):
    def test_pushup_uses_elbow_and_body_alignment(self):
        f = extract_for_exercise(pushup(), 1000, 1000, 'pushup')
        self.assertAlmostEqual(f.elbow_angle, 90)
        self.assertAlmostEqual(f.body_alignment, 180)
        self.assertEqual(assess_for_exercise(f, 'pushup')['phase'], 'bottom')
        bad = extract_for_exercise(pushup((500, 450)), 1000, 1000, 'pushup')
        self.assertEqual(assess_for_exercise(bad, 'pushup')['status'], 'rule_flag')

    def test_wall_pose_is_not_treated_as_standard_pushup(self):
        p = landmarks({11: (500, 100), 13: (450, 250), 15: (400, 400),
                       23: (500, 400), 27: (500, 900)})
        self.assertIsNone(extract_for_exercise(p, 1000, 1000, 'pushup'))

    def test_lunge_uses_both_legs_without_requiring_wrists(self):
        f = extract_for_exercise(lunge(), 1000, 1000, 'lunge')
        self.assertIsNotNone(f)
        self.assertNotEqual(f.left_knee_angle, f.right_knee_angle)
        self.assertAlmostEqual(f.trunk_lean, 0)
        self.assertEqual(assess_for_exercise(f, 'lunge')['phase'], 'bottom')

    def test_jack_distinguishes_open_closed_and_asymmetric_arms(self):
        for opened, expected in [(True, 'open'), (False, 'closed')]:
            f = extract_for_exercise(jack(opened), 1000, 1000, 'jumping_jack')
            self.assertEqual(assess_for_exercise(f, 'jumping_jack')['phase'], expected)
        p = jack(True)
        p[16].x, p[16].y = .58, .48
        f = extract_for_exercise(p, 1000, 1000, 'jumping_jack')
        self.assertEqual(assess_for_exercise(f, 'jumping_jack')['status'], 'rule_flag')

    def test_missing_low_visibility_or_nonfinite_joints_abstain(self):
        for exercise, make, index in [('pushup', pushup, 15), ('lunge', lunge, 28),
                                       ('jumping_jack', lambda: jack(True), 16)]:
            self.assertIsNone(extract_for_exercise([], 1000, 1000, exercise))
            for value in [0., math.nan]:
                p = make();p[index].presence = value
                self.assertIsNone(extract_for_exercise(p, 1000, 1000, exercise))
            self.assertEqual(assess_for_exercise(None, exercise)['status'], 'unassessable')

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_for_exercise([], 1000, 1000, 'cycling')


class ClipTests(unittest.TestCase):
    def test_pushup_clip_range_and_alignment(self):
        rows = [{'features': {'elbow_angle': a, 'body_alignment': 180}, 'phase': 'transition'}
                for a in [170] * 20 + [90] * 20 + [170] * 20]
        self.assertEqual(summarize_for_exercise(rows, 'pushup')['prediction'], 'correct')
        for row in rows:
            row['features']['body_alignment'] = 130
        result = summarize_for_exercise(rows, 'pushup')
        self.assertIn('projected_body_misalignment', result['reasons'])
        self.assertEqual(result['prediction'], 'incorrect')

    def test_lunge_clip_requires_motion_not_only_a_bent_pose(self):
        rows = [{'features': {'left_knee_angle': a, 'right_knee_angle': a + 5,
                              'trunk_lean': 10}} for a in [170] * 20 + [90] * 20 + [170] * 20]
        self.assertEqual(summarize_for_exercise(rows, 'lunge')['prediction'], 'correct')
        still = [rows[20]] * 60
        self.assertEqual(summarize_for_exercise(still, 'lunge')['prediction'], 'unassessable')

    def test_jack_motion_is_separate_from_form_quality(self):
        rows = [{'features': {}, 'phase': phase} for phase in ['open'] * 20 + ['closed'] * 20]
        result = summarize_for_exercise(rows, 'jumping_jack')
        self.assertTrue(result['movement_observed'])
        self.assertEqual(result['prediction'], 'unassessable')
        self.assertEqual(result['reasons'], ['form_classification_not_validated'])

    def test_all_modes_abstain_with_insufficient_coverage(self):
        for exercise in ['pushup', 'lunge', 'jumping_jack']:
            self.assertEqual(summarize_for_exercise([{'features': None}] * 60, exercise)['prediction'], 'unassessable')


if __name__ == '__main__':
    unittest.main()
