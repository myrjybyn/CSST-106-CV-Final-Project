import importlib.util
from pathlib import Path
import unittest
from posture_check.evaluation import classification, summarize


class EvaluationTests(unittest.TestCase):
    def test_abstentions_reduce_overall_recall_and_f1(self):
        rows=[{'reference_form':truth,'prediction':pred} for truth,pred in [('correct','correct'),('correct','unassessable'),('incorrect','correct'),('incorrect','incorrect')]]
        m=classification(rows)
        self.assertEqual(m['accuracy_all'],.5);self.assertAlmostEqual(m['accuracy_assessed'],2/3)
        self.assertEqual(m['classification_coverage'],.75)
        self.assertEqual(m['per_class']['correct']['recall'],.5)
        self.assertEqual(m['per_class']['correct']['precision'],.5)
        self.assertAlmostEqual(m['macro_f1'],(.5+2/3)/2)

    def test_absent_incorrect_class_does_not_claim_binary_macro_f1(self):
        m=classification([{'reference_form':'correct','prediction':'correct'}])
        self.assertIsNone(m['macro_f1']);self.assertEqual(m['per_class']['incorrect']['support'],0)

    def test_unknown_references_not_assigned_labels_or_zero_count_error(self):
        r={'reference_form':None,'prediction':'incorrect','frames':20,'assessable_frames':10,'processing_seconds':2,'reference_reps':None,'estimated_reps':9}
        m=summarize([r]);self.assertEqual(m['classification']['labelled_clips'],0)
        self.assertIsNone(m['count_mae']);self.assertEqual(m['processing_fps'],10)

    def test_test_subjects_are_disjoint_and_supported_views_fixed(self):
        p=Path(__file__).resolve().parents[1]/'src/evaluate.py'
        spec=importlib.util.spec_from_file_location('milestone_evaluate',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        suites=module.suite_rows();self.assertEqual(len(suites['heldout']),12)
        self.assertTrue(all(c['split']=='test' and '/side/' in c['file'] for c in suites['heldout']))
        self.assertEqual(len(suites['benchmark']),4)
