import unittest
import numpy as np
from posture_check.form_features import summarize_angles,SessionAngles
from posture_check.calibrated import predict_tree,assess_summary


class CalibratedTests(unittest.TestCase):
    def test_session_prefix_matches_clip_angle_summary(self):
        session=SessionAngles('pushup');vectors=[]
        for angle in [170]*25+[90]*25+[170]*25:
            f={'elbow_angle':angle,'body_alignment':175,'body_inclination':90}
            session.update({'features':f});vectors.append([angle,175,90])
        self.assertEqual(session.summary(),summarize_angles('pushup',vectors,len(vectors)))
        session.update({'features':None})
        self.assertEqual(session.summary()['frames'],76)

    def test_coverage_and_movement_not_relaxed_by_calibration(self):
        self.assertFalse(summarize_angles('squat',[[90,90,10]]*10,10)['eligible'])
        self.assertEqual(summarize_angles('squat',[[170,170,10]]*40,40)['reason'],'insufficient_observed_movement')
        self.assertEqual(summarize_angles('squat',[[90,90,10]]*40,100)['reason'],'insufficient_pose_coverage')

    def test_tree_decision_trace_and_unknown_frame_labels(self):
        tree={'feature':'alignment_p10','threshold':160,'left':{'prediction':'incorrect'},'right':{'prediction':'correct'}}
        label,path=predict_tree(tree,{'alignment_p10':150})
        self.assertEqual(label,'incorrect');self.assertEqual(path[0]['operator'],'<=')
        profile={'calibration_id':'test','exercises':{'pushup':{'enabled':True,'tree':tree}}}
        result=assess_summary('pushup',{'valid_frames':0,'valid_fraction':0,'features':None,'eligible':False,'reason':'insufficient_pose_coverage'},profile)
        self.assertEqual(result['prediction'],'unassessable')
        self.assertNotIn('confidence',result)

    def test_invalid_numeric_vectors_rejected(self):
        with self.assertRaises(ValueError):summarize_angles('pushup',[[np.nan,180,90]]*40,40)

class CalibrationProtocolTests(unittest.TestCase):
    def test_reserved_subjects_excluded_from_fit_and_validation(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        plan=json.loads((root/'docs/calibration/plan.json').read_text())
        groups={s:{r['participant'] for r in rs} for s,rs in plan['partitions'].items()}
        self.assertFalse(groups['fit']&groups['validation'])
        self.assertFalse(groups['prospective']&(groups['fit']|groups['validation']))
        self.assertFalse(groups['prospective']&set(plan['original_exposed_test_participants']))
        self.assertEqual(len(plan['partitions']['prospective']),16)

    def test_active_profile_passes_predeclared_validation_guards(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        results=json.loads((root/'docs/calibration/fitting_results.json').read_text())
        for item in results['exercises'].values():
            if item['enabled']:
                self.assertGreater(item['calibrated_validation']['macro_f1'],item['uncalibrated_validation']['macro_f1'])
                self.assertGreaterEqual(item['calibrated_validation']['per_class']['incorrect']['recall'],item['uncalibrated_validation']['per_class']['incorrect']['recall'])
                self.assertGreaterEqual(item['selected_fit_oof']['macro_f1'],item['uncalibrated_fit']['macro_f1'])

    def test_tree_learns_a_known_threshold_with_multi_subject_leaves(self):
        import importlib.util
        from pathlib import Path
        path=Path(__file__).resolve().parents[1]/'scripts/calibration/fit_rules.py'
        spec=importlib.util.spec_from_file_location('fit_rules_test',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        X=np.array([[10],[90]]*4);y=np.array([0,1]*4);groups=np.array(['a','a','b','b','c','c','d','d'])
        tree=module.fit_tree(X,y,groups,('hip_p10',),1,4)
        self.assertEqual(predict_tree(tree,{'hip_p10':10})[0],'correct')
        self.assertEqual(predict_tree(tree,{'hip_p10':90})[0],'incorrect')
        self.assertGreaterEqual(tree['left']['training_subjects'],2)
        self.assertGreaterEqual(tree['right']['training_subjects'],2)
