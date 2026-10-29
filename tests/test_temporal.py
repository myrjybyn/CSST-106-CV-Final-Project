import copy
import unittest
from posture_check.temporal import TemporalAnalyzer


def sample(exercise, lowered=False):
    common = {'min_confidence': .95}
    if exercise == 'squat':
        common.update(side='left', knee_angle=90 if lowered else 170, hip_angle=100, trunk_lean=20)
    elif exercise == 'pushup':
        common.update(side='left', elbow_angle=90 if lowered else 170,
                      body_alignment=180, body_inclination=90)
    elif exercise == 'lunge':
        common.update(left_knee_angle=90 if lowered else 170,
                      right_knee_angle=100 if lowered else 175, trunk_lean=10)
    else:
        common.update(left_arm_angle=165 if lowered else 10, right_arm_angle=165 if lowered else 10,
                      ankle_width_ratio=2.5 if lowered else .8, left_knee_angle=170, right_knee_angle=170)
    return {'features': common, 'status': 'rule_pass', 'phase': 'unknown',
            'feedback': 'raw', 'exercise': exercise, 'processing_seconds': .01,
            'pose_detected': True}


def feed(analyzer, record, frames=25):
    return [analyzer.update(copy.deepcopy(record)) for _ in range(frames)]


class TemporalTests(unittest.TestCase):
    def test_complete_cycles_count_once_for_every_exercise(self):
        for mode in ('squat', 'pushup', 'lunge', 'jumping_jack'):
            analyzer = TemporalAnalyzer(mode, 30)
            outputs = feed(analyzer, sample(mode))
            outputs += feed(analyzer, sample(mode, True))
            outputs += feed(analyzer, sample(mode))
            self.assertEqual(analyzer.count, 1, mode)
            self.assertEqual(sum(r['repetition_completed'] for r in outputs), 1)
            feed(analyzer, sample(mode), 25)
            self.assertEqual(analyzer.count, 1)
            feed(analyzer, sample(mode, True))
            feed(analyzer, sample(mode))
            self.assertEqual(analyzer.count, 2, mode)

    def test_starting_at_bottom_does_not_count_partial_repetition(self):
        analyzer = TemporalAnalyzer('squat', 30)
        feed(analyzer, sample('squat', True))
        feed(analyzer, sample('squat'))
        self.assertEqual(analyzer.count, 0)

    def test_short_jitter_cannot_make_a_repetition(self):
        analyzer = TemporalAnalyzer('jumping_jack', 30)
        feed(analyzer, sample('jumping_jack'))
        for _ in range(10):
            feed(analyzer, sample('jumping_jack', True), 1)
            feed(analyzer, sample('jumping_jack'), 5)
        self.assertEqual(analyzer.count, 0)

    def test_long_missing_gap_drops_partial_cycle_and_never_imputes_pose(self):
        analyzer = TemporalAnalyzer('lunge', 30)
        feed(analyzer, sample('lunge'))
        feed(analyzer, sample('lunge', True))
        missing = {'features': None, 'status': 'unassessable', 'phase': 'unknown',
                   'feedback': 'Show full body', 'pose_detected': False}
        outputs = feed(analyzer, missing, 20)
        self.assertTrue(all(r['features'] is None and r['phase'] == 'unknown' for r in outputs))
        feed(analyzer, sample('lunge'))
        self.assertEqual(analyzer.count, 0)

    def test_raw_features_are_not_modified_by_smoothing(self):
        analyzer = TemporalAnalyzer('squat', 30)
        feed(analyzer, sample('squat'))
        raw = sample('squat', True)
        before = copy.deepcopy(raw)
        result = analyzer.update(raw)
        self.assertEqual(raw, before)
        self.assertGreater(result['features']['knee_angle'], 90)
        self.assertLess(result['features']['knee_angle'], 170)
        self.assertEqual(result['raw_features']['knee_angle'], 90)

    def test_invalid_timing_or_mode_is_rejected(self):
        for fps in (0, -1, float('nan'), 1000):
            with self.assertRaises(ValueError):
                TemporalAnalyzer('squat', fps)
        with self.assertRaises(ValueError):
            TemporalAnalyzer('cycling', 30)


if __name__ == '__main__':
    unittest.main()
