import unittest
from posture_check.clip import summarize, classification_metrics


def sequence(angles, lean=30):
    return [{"features": {"knee_angle": a, "trunk_lean": lean}} for a in angles]


class ClipTests(unittest.TestCase):
    def test_clip_policy_for_full_and_limited_motion(self):
        full = sequence([170] * 20 + [90] * 20 + [170] * 20)
        self.assertEqual(summarize(full)["prediction"], "correct")
        shallow = sequence([170] * 20 + [130] * 20 + [170] * 20)
        result = summarize(shallow)
        self.assertEqual(result["prediction"], "incorrect")
        self.assertIn("limited_projected_depth", result["reasons"])

    def test_still_or_missing_data_abstains(self):
        self.assertEqual(summarize(sequence([170] * 60))["prediction"], "unassessable")
        incomplete = sequence([90, 170] * 15) + [{"features": None}] * 40
        self.assertEqual(summarize(incomplete)["prediction"], "unassessable")
        self.assertEqual(summarize([])["prediction"], "unassessable")

    def test_abstentions_remain_in_accuracy_and_recall_denominators(self):
        rows = [{"ground_truth": truth, "clip_assessment": {"prediction": pred}}
                for truth, pred in [("correct", "correct"), ("incorrect", "incorrect"),
                                    ("incorrect", "unassessable")]]
        result = classification_metrics(rows)
        self.assertAlmostEqual(result["accuracy_all_clips"], 2 / 3)
        self.assertEqual(result["accuracy_assessed_clips"], 1)
        self.assertEqual(result["abstained_clips"], 1)
        self.assertAlmostEqual(result["macro_f1_with_abstentions_as_misses"], 5 / 6)


if __name__ == "__main__":
    unittest.main()
