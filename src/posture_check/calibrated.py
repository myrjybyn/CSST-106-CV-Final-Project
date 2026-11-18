"""Interpretable clip/session form classification, separately calibrated by mode.

Pose weights and instantaneous geometry cues are not trained by this module.
"""
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
from .form_features import COLUMNS,NAMES,summarize_angles

PROFILE=Path(__file__).resolve().parents[2]/'config/form_rules.json'


@lru_cache(maxsize=1)
def load_profile():
    if not PROFILE.is_file():return None
    profile=json.loads(PROFILE.read_text())
    if profile.get('schema_version')!=1:raise ValueError('Unsupported calibrated rule schema')
    for exercise,config in profile['exercises'].items():
        if exercise not in NAMES:raise ValueError('Unsupported calibrated exercise')
        if config['enabled']:
            _validate_tree(config['tree'],exercise)
    return profile


def _validate_tree(tree,exercise,depth=0):
    if depth>2:raise ValueError('Calibrated tree exceeds validated depth')
    if 'prediction' in tree:
        if tree['prediction'] not in ('correct','incorrect'):raise ValueError('Invalid leaf label')
        return
    if tree['feature'] not in NAMES[exercise] or not math.isfinite(tree['threshold']):raise ValueError('Invalid learned rule')
    _validate_tree(tree['left'],exercise,depth+1);_validate_tree(tree['right'],exercise,depth+1)


def predict_tree(tree,measurements):
    path=[]
    while 'prediction' not in tree:
        value=measurements[tree['feature']]
        if not math.isfinite(value):raise ValueError('Nonfinite calibration feature')
        left=value<=tree['threshold']
        path.append({'feature':tree['feature'],'value':value,'operator':'<=' if left else '>', 'threshold':tree['threshold']})
        tree=tree['left'] if left else tree['right']
    return tree['prediction'],path


def require_compatible_model(model,exercise):
    profile=load_profile()
    config=profile['exercises'].get(exercise) if profile else None
    if not config or not config['enabled'] or not Path(model).is_file():return
    if hashlib.sha256(Path(model).read_bytes()).hexdigest()!=profile['pose_model_sha256']:
        raise ValueError('The form rules require the pose model used for calibration; use the matching Lite model or recalibrate.')


def profile_identity():
    profile=load_profile()
    return {'id':profile['calibration_id'],'sha256':hashlib.sha256(PROFILE.read_bytes()).hexdigest()} if profile else None


def assess_summary(exercise,summary,profile=None):
    profile=load_profile() if profile is None else profile
    config=profile['exercises'].get(exercise) if profile else None
    if not config or not config['enabled']:return None
    result={'prediction':'unassessable','valid_frames':summary['valid_frames'],'valid_fraction':summary['valid_fraction'],
            'reasons':[],'measurements':summary['features'],'calibration_id':profile['calibration_id'],
            'scope':'clip-level rule prediction; live prefixes are provisional'}
    if not summary['eligible']:
        result['reasons']=[summary['reason']];return result
    prediction,path=predict_tree(config['tree'],summary['features'])
    result.update(prediction=prediction,decision_path=path)
    if prediction=='incorrect':result['reasons']=['calibrated_geometric_rule_flag']
    return result


def assess_clip(records,exercise):
    if exercise not in COLUMNS:return None
    # Do not retain images or assign the clip reference to these observations.
    vectors=[[r['features'][key] for key in COLUMNS[exercise]] for r in records if r.get('features') is not None]
    return assess_summary(exercise,summarize_angles(exercise,vectors,len(records)))
