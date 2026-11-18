"""Clip/session angle summaries for supervised rule calibration.

Whole-clip labels are never copied onto frames. Coverage/motion gates are fixed,
not fitted to form labels. The same numeric summaries serve files and live-session
prefixes; prefix accuracy is not implied by whole-clip validation.
"""
from array import array
import numpy as np

COLUMNS={'squat':('knee_angle','hip_angle','trunk_lean'),
         'pushup':('elbow_angle','body_alignment','body_inclination')}
NAMES={
    'squat':('knee_p10','knee_p50','knee_p90','knee_range','hip_p10','hip_p50','hip_p90','hip_range','active_trunk_p50','active_trunk_p90','deep_fraction'),
    'pushup':('elbow_p10','elbow_p50','elbow_p90','elbow_range','alignment_p10','alignment_p50','inclination_p10','inclination_p50','inclination_p90','bent_fraction','misalignment_fraction'),
}
GATES={'min_valid_frames':30,'min_valid_fraction':.5,'min_motion_range_degrees':20}


def summarize_angles(exercise,vectors,frames):
    if exercise not in COLUMNS:raise ValueError('No calibrated feature schema for '+exercise)
    data=np.asarray(vectors,dtype=float)
    if not len(data):data=np.empty((0,len(COLUMNS[exercise])))
    if data.ndim!=2 or data.shape[1]!=len(COLUMNS[exercise]) or not np.isfinite(data).all():
        raise ValueError('Invalid angle vectors')
    if frames<len(data) or frames<0:raise ValueError('Invalid frame count')
    valid=len(data);coverage=valid/frames if frames else 0.
    result={'frames':frames,'valid_frames':valid,'valid_fraction':coverage,'eligible':False,'reason':None,'features':None}
    if valid<GATES['min_valid_frames'] or coverage<GATES['min_valid_fraction']:
        result['reason']='insufficient_pose_coverage';return result
    a,b,c=data.T
    low,middle,high=(float(x) for x in np.percentile(a,[10,50,90]));span=high-low
    if span<GATES['min_motion_range_degrees']:
        result['reason']='insufficient_observed_movement';return result
    if exercise=='squat':
        hip_low,hip_mid,hip_high=(float(x) for x in np.percentile(b,[10,50,90]))
        active=c[a<145]
        if not len(active):active=c
        values=(low,middle,high,span,hip_low,hip_mid,hip_high,hip_high-hip_low,
                float(np.percentile(active,50)),float(np.percentile(active,90)),float(np.mean(a<=100)))
    else:
        values=(low,middle,high,span,float(np.percentile(b,10)),float(np.percentile(b,50)),
                *[float(x) for x in np.percentile(c,[10,50,90])],float(np.mean(a<=100)),float(np.mean(b<155)))
    result.update(eligible=True,features=dict(zip(NAMES[exercise],values)))
    return result


class SessionAngles:
    """Retain only numeric angles in RAM: about 2.6 MB/hour at 30 FPS.

    No camera images or per-frame ground-truth labels are stored. Release this
    object when a session stops. Percentiles are exact, not histogram estimates.
    """
    def __init__(self,exercise):
        if exercise not in COLUMNS:raise ValueError('Unsupported calibrated session')
        self.exercise=exercise;self.values=array('d');self.frames=0

    def update(self,record):
        self.frames+=1
        features=record.get('features')
        if features is not None:self.values.extend(float(features[x]) for x in COLUMNS[self.exercise])

    def summary(self):
        vectors=np.frombuffer(self.values,dtype=np.float64).reshape((-1,len(COLUMNS[self.exercise])))
        return summarize_angles(self.exercise,vectors,self.frames)
