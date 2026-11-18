"""Padding, coordinate mapping and rejected-input checks."""
from types import SimpleNamespace
import unittest
import numpy as np
from posture_check.preprocessing import active_region, restore_landmarks
from posture_check.quality import explain
from posture_check.__main__ import process
from test_exercises import pushup, jack


class Estimator:
    def __init__(self, points):self.points=points
    def detect(self,frame):self.shape=frame.shape;return self.points


class RegionTests(unittest.TestCase):
    def test_paired_black_margins_removed_and_landmarks_restored(self):
        image=np.zeros((800,1600,3),np.uint8);image[100:700,300:1300]=80
        crop,box=active_region(image)
        self.assertEqual(box,(300,100,1300,700));self.assertEqual(crop.shape,(600,1000,3))
        p=SimpleNamespace(x=.2,y=.3,visibility=.9,presence=.9)
        restored=restore_landmarks([p],box,1600,800)[0]
        self.assertAlmostEqual(restored.x,500/1600);self.assertAlmostEqual(restored.y,280/800)
        self.assertEqual(p.x,.2);self.assertEqual(restored.presence,.9)

    def test_plain_dark_and_one_sided_borders_are_not_cropped(self):
        for image in (np.zeros((80,120,3),np.uint8),np.full((80,120,3),80,np.uint8)):
            self.assertEqual(active_region(image)[1],(0,0,120,80))
        image=np.full((80,120,3),80,np.uint8);image[:20]=0
        self.assertEqual(active_region(image)[1],(0,0,120,80))

    def test_small_luminous_region_does_not_create_fake_person_roi(self):
        image=np.zeros((100,100,3),np.uint8);image[40:50,40:50]=80
        self.assertEqual(active_region(image)[1],(0,0,100,100))

    def test_padding_no_longer_causes_pushup_size_rejection(self):
        # Identical valid geometry embedded in a wider padded canvas.
        frame=np.zeros((1000,2400,3),np.uint8);frame[:,700:1700]=80
        points=pushup()
        padded=[SimpleNamespace(x=(p.x*1000+700)/2400,y=p.y,visibility=p.visibility,presence=p.presence) for p in points]
        _,old=process(frame,Estimator(padded),'pushup')
        _,new=process(frame,Estimator(points),'pushup',enhanced=True)
        self.assertIsNone(old['features']);self.assertIsNotNone(new['features'])
        self.assertEqual(new['analysis_region'],[700,0,1700,1000])

    def test_crop_does_not_bypass_hidden_or_outside_joint_gates(self):
        frame=np.zeros((1000,2000,3),np.uint8);frame[:,500:1500]=80
        for reason,change in [('outside_frame',lambda p:setattr(p[15],'x',1.1)),
                              ('required_joints_not_visible',lambda p:setattr(p[15],'presence',.1))]:
            p=pushup();change(p)
            _,result=process(frame,Estimator(p),'pushup',enhanced=True)
            self.assertIsNone(result['features']);self.assertEqual(result['assessability_reason'],reason)

    def test_missing_pose_has_actionable_feedback(self):
        self.assertEqual(explain([], 'squat')[0],'no_pose')

    def test_jack_still_requires_both_visible_wrists(self):
        points=jack(True);points[16].presence=.1
        self.assertEqual(explain(points,'jumping_jack')[0],'required_joints_not_visible')


class ConfidenceRegressionTests(unittest.TestCase):
    def test_nan_presence_cannot_be_hidden_by_finite_visibility(self):
        from posture_check.features import extract
        points=[SimpleNamespace(x=.5,y=.5,visibility=.95,presence=float('nan')) for _ in range(33)]
        self.assertIsNone(extract(points,1000,1000))
