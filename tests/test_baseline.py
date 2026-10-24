"""Geometry and rule tests use known synthetic points, not posture ground truth."""
import math
from types import SimpleNamespace
import unittest
from posture_check.baseline import assess
from posture_check.features import Features, angle, extract


class GeometryTests(unittest.TestCase):
    def test_known_joint_angles_and_degenerate_input(self):
        self.assertAlmostEqual(angle((0, 0), (0, 1), (1, 1)), 90)
        self.assertAlmostEqual(angle((0, 0), (0, 1), (0, 2)), 180)
        with self.assertRaises(ValueError):
            angle((0, 0), (0, 0), (0, 1))

    def test_aspect_correction_and_visible_side_selection(self):
        points = [SimpleNamespace(x=.5, y=.5, visibility=0., presence=0.) for _ in range(33)]
        # With a 200x100 image the two vectors at the hip are perpendicular:
        # shoulder-hip=(-20,-20), knee-hip=(-20,20).
        for index, x, y in ((12, .4, .3), (24, .5, .5), (26, .4, .7), (28, .5, .9)):
            points[index] = SimpleNamespace(x=x, y=y, visibility=.9, presence=.95)
        features = extract(points, 200, 100)
        self.assertEqual(features.side, "right")
        self.assertAlmostEqual(features.hip_angle, 90)
        self.assertAlmostEqual(features.knee_angle, 90)
        self.assertAlmostEqual(features.trunk_lean, 45)
        points[28].presence = .1
        self.assertIsNone(extract(points, 200, 100))

    def test_out_of_frame_and_nonfinite_coordinates_are_rejected(self):
        points = [SimpleNamespace(x=.5, y=.5, visibility=1., presence=1.) for _ in range(33)]
        points[11].x = math.nan
        points[12].x = 2
        self.assertIsNone(extract(points, 640, 480))

    def test_small_confident_detection_is_rejected(self):
        points = [SimpleNamespace(x=.5, y=.5, visibility=.99, presence=.99) for _ in range(33)]
        for indices in [(11, 23, 25, 27), (12, 24, 26, 28)]:
            for index, y in zip(indices, [.50, .52, .54, .56]):
                points[index].y = y
        self.assertIsNone(extract(points, 810, 1440))


class RuleTests(unittest.TestCase):
    def test_missing_pose_is_never_classified_as_a_pass(self):
        self.assertEqual(assess(None)["status"], "unassessable")

    def test_lean_flag_is_phase_gated(self):
        self.assertEqual(assess(Features("left", 90, 90, 65, .9))["status"], "rule_flag")
        self.assertEqual(assess(Features("left", 170, 170, 65, .9))["phase"], "standing")
        result = assess(Features("left", 90, 90, 40, .9))
        self.assertEqual(result["status"], "rule_pass")
        self.assertIn("does not establish correct form", result["feedback"])


if __name__ == "__main__":
    unittest.main()
