"""Evaluation checks for label mapping, shared records and abstention scoring."""
import copy
import importlib.util
from pathlib import Path
import unittest

from posture_check.evaluation import classification
from posture_check.exercises import summarize_for_exercise
from posture_check.session import ExerciseSession, GuidedRepetitionCounter
from posture_check.temporal import TemporalAnalyzer
from test_temporal import sample

SPEC = importlib.util.spec_from_file_location(
    'evaluate_guided_rules', Path(__file__).resolve().parents[1] / 'scripts/evaluate_guided_rules.py')
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class GuidedEvaluationTests(unittest.TestCase):
    def test_abstentions_are_misses_without_becoming_a_third_reference_class(self):
        rows = [dict(reference_form=truth, prediction=prediction) for truth, prediction in
                [('correct', 'correct'), ('correct', 'unassessable'),
                 ('incorrect', 'correct'), ('incorrect', 'incorrect')]]
        metrics = classification(rows)
        self.assertEqual(metrics['accuracy_all'], .5)
        self.assertEqual(metrics['classification_coverage'], .75)
        self.assertAlmostEqual(metrics['accuracy_assessed'], 2 / 3)
        self.assertAlmostEqual(metrics['macro_f1'], (.5 + 2 / 3) / 2)
        self.assertEqual(metrics['per_class']['correct']['recall'], .5)

    def test_gui_label_mapping_preserves_unassessable(self):
        for prediction, expected in [('good', 'correct'), ('bad', 'incorrect'),
                                     ('unassessable', 'unassessable')]:
            self.assertEqual(evaluation.canonical_prediction({'prediction': prediction}), expected)

    def test_both_assessors_match_direct_calls_on_shared_timed_records(self):
        for exercise in ('squat', 'pushup'):
            analyzer = TemporalAnalyzer(exercise, 30)
            analyzer.counter = GuidedRepetitionCounter(exercise)
            direct_session = ExerciseSession(exercise)
            records = []
            for lowered in (False, True, False):
                for _ in range(30):
                    record = analyzer.update(copy.deepcopy(sample(exercise, lowered)), dt_seconds=1 / 15)
                    records.append(record)
                    direct_session.add(record)
            before = copy.deepcopy(records)
            results = evaluation.assess_records(exercise, records)
            self.assertEqual(records, before)
            self.assertEqual(results['fixed_clip_rules'], summarize_for_exercise(records, exercise, calibrated=False))
            self.assertEqual(results['guided_session_rules'], direct_session.assess())
            self.assertEqual(results['guided_session_rules']['prediction'], 'good')


if __name__ == '__main__':
    unittest.main()
