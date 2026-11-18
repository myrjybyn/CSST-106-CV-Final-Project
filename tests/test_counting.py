"""Movement regressions; these synthetic sequences are not accuracy evidence."""
import unittest
from posture_check.counting import RepetitionCounter
from posture_check.temporal import TemporalAnalyzer
from test_temporal import sample


def hold(counter, features, seconds=.3, dt=1/30):
    return [counter.update(features,dt) for _ in range(round(seconds/dt))]


class CountingTests(unittest.TestCase):
    def test_short_endpoints_survive_independent_form_smoothing(self):
        for exercise in ('squat','pushup','jumping_jack'):
            a=TemporalAnalyzer(exercise,30)
            for lowered in (False,True,False):
                for _ in range(4):
                    result=a.update(sample(exercise,lowered))
            self.assertEqual(result['repetition_count'],1,exercise)

    def test_alternating_lunges_with_other_knee_remaining_bent(self):
        c=RepetitionCounter('lunge')
        def f(left,right):return {'left_knee_angle':left,'right_knee_angle':right}
        hold(c,f(170,120))
        hold(c,f(90,100))
        hold(c,f(170,120))
        self.assertEqual(c.count,1)
        hold(c,f(170,170))
        hold(c,f(115,90))
        self.assertEqual(c.active_leg,'right')
        hold(c,f(120,170))
        self.assertEqual(c.count,2)
        hold(c,f(120,170))
        self.assertEqual(c.count,2,'Holding a stance is not another rep')

    def test_both_lunge_knees_bending_count_only_once(self):
        c=RepetitionCounter('lunge')
        for l,r in [(170,170),(90,90),(170,170)]:
            hold(c,{'left_knee_angle':l,'right_knee_angle':r})
        self.assertEqual(c.count,1)

    def test_starting_lowered_never_counts_partial_rep(self):
        for mode in ('squat','pushup','lunge','jumping_jack'):
            c=RepetitionCounter(mode)
            hold(c,sample(mode,True)['features'])
            hold(c,sample(mode)['features'])
            self.assertEqual(c.count,0,mode)

    def test_hysteresis_preserves_dwell_near_an_endpoint(self):
        c=RepetitionCounter('pushup')
        f=sample('pushup')['features']
        for angle in (157,153,156,154):
            c.update(dict(f,elbow_angle=angle),1/30)
        self.assertEqual(c.stage,'bottom')
        hold(c,dict(f,elbow_angle=90))
        hold(c,f)
        self.assertEqual(c.count,1)

    def test_single_frame_spikes_and_transition_jitter_do_not_count(self):
        c=RepetitionCounter('pushup');f=sample('pushup')['features']
        hold(c,f)
        for _ in range(10):
            c.update(dict(f,elbow_angle=90),1/30)
            hold(c,dict(f,elbow_angle=120),.2)
        hold(c,f)
        self.assertEqual(c.count,0)

    def test_occlusion_stall_and_side_switch_discard_partial_cycles(self):
        for cause in ('occlusion','stall','side'):
            c=RepetitionCounter('pushup');f=sample('pushup')['features']
            hold(c,f);hold(c,sample('pushup',True)['features'])
            if cause=='occlusion':hold(c,None,.6)
            elif cause=='stall':c.update(f,.8)
            else:f=dict(f,side='right')
            hold(c,f)
            self.assertEqual(c.count,0,cause)

    def test_independent_counts_at_variable_cadence(self):
        for dt in (1/50,1/15,.08,.16):
            c=RepetitionCounter('jumping_jack')
            for lower in (False,True,False,True,False):
                hold(c,sample('jumping_jack',lower)['features'],.5,dt)
            self.assertEqual(c.count,2,dt)
