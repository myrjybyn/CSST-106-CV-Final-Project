"""Exercise-specific geometric features and provisional posture rules.

The pose weights are shared pretrained MediaPipe weights, not an exercise classifier.
Squat behavior delegates to the existing baseline. New rules are uncalibrated and
require the selected exercise/view; they do not establish form accuracy.
"""
from dataclasses import asdict, dataclass
import math
import numpy as np
from .features import angle, extract as extract_squat
from .baseline import assess as assess_squat
from .clip import summarize as summarize_squat, RULES as SQUAT_RULES

SUPPORTED_EXERCISES = ('squat', 'pushup', 'lunge', 'jumping_jack')


@dataclass(frozen=True)
class PushupFeatures:
    side: str
    elbow_angle: float
    body_alignment: float
    body_inclination: float
    min_confidence: float

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class LungeFeatures:
    left_knee_angle: float
    right_knee_angle: float
    trunk_lean: float
    min_confidence: float

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class JackFeatures:
    left_arm_angle: float
    right_arm_angle: float
    ankle_width_ratio: float
    left_knee_angle: float
    right_knee_angle: float
    min_confidence: float

    def to_dict(self):
        return asdict(self)


def _points(landmarks, indices, width, height, confidence):
    if len(landmarks) != 33 or width <= 0 or height <= 0:
        return None
    selected = [landmarks[i] for i in indices]
    if any(not math.isfinite(p.visibility) or not math.isfinite(p.presence) for p in selected):
        return None
    scores = [min(p.visibility, p.presence) for p in selected]
    if any(not math.isfinite(s) or s < confidence for s in scores):
        return None
    if any(not (0 <= p.x <= 1 and 0 <= p.y <= 1) for p in selected):
        return None
    return {i: (p.x * width, p.y * height) for i, p in zip(indices, selected)}, min(scores)


def extract_pushup(landmarks, width, height, confidence=.5):
    candidates = []
    for side, ids in [('left', (11, 13, 15, 23, 27)), ('right', (12, 14, 16, 24, 28))]:
        found = _points(landmarks, ids, width, height, confidence)
        if found is None:
            continue
        points, score = found
        shoulder, elbow, wrist, hip, ankle = (points[i] for i in ids)
        if math.dist(shoulder, hip) + math.dist(hip, ankle) < .35 * max(width, height):
            continue
        try:
            inclination = angle(shoulder, hip, (hip[0], hip[1] - height))
            # Standard horizontal push-ups only; wall variants need separate rules.
            if not 55 <= inclination <= 125:
                continue
            candidates.append(PushupFeatures(side, angle(shoulder, elbow, wrist),
                                             angle(shoulder, hip, ankle), inclination, score))
        except ValueError:
            continue
    return max(candidates, key=lambda f: f.min_confidence, default=None)


def extract_lunge(landmarks, width, height, confidence=.5):
    ids = (11, 12, 23, 24, 25, 26, 27, 28)
    found = _points(landmarks, ids, width, height, confidence)
    if found is None:
        return None
    p, score = found
    chains = [math.dist(p[s], p[h]) + math.dist(p[h], p[k]) + math.dist(p[k], p[a])
              for s, h, k, a in [(11, 23, 25, 27), (12, 24, 26, 28)]]
    if min(chains) < .35 * height:
        return None
    shoulder = tuple((p[11][i] + p[12][i]) / 2 for i in (0, 1))
    hip = tuple((p[23][i] + p[24][i]) / 2 for i in (0, 1))
    try:
        return LungeFeatures(angle(p[23], p[25], p[27]), angle(p[24], p[26], p[28]),
                             angle(shoulder, hip, (hip[0], hip[1] - height)), score)
    except ValueError:
        return None


def extract_jack(landmarks, width, height, confidence=.5):
    ids = (11, 12, 15, 16, 23, 24, 25, 26, 27, 28)
    found = _points(landmarks, ids, width, height, confidence)
    if found is None:
        return None
    p, score = found
    shoulder_width = math.dist(p[11], p[12])
    # Jack rules require a front view with measurable shoulder separation.
    if shoulder_width < .04 * width:
        return None
    chains = [math.dist(p[s], p[h]) + math.dist(p[h], p[k]) + math.dist(p[k], p[a])
              for s, h, k, a in [(11, 23, 25, 27), (12, 24, 26, 28)]]
    if min(chains) < .35 * height:
        return None
    try:
        return JackFeatures(angle(p[23], p[11], p[15]), angle(p[24], p[12], p[16]),
                            math.dist(p[27], p[28]) / shoulder_width,
                            angle(p[23], p[25], p[27]), angle(p[24], p[26], p[28]), score)
    except ValueError:
        return None


def extract_for_exercise(landmarks, width, height, exercise='squat'):
    functions = {'squat': extract_squat, 'pushup': extract_pushup,
                 'lunge': extract_lunge, 'jumping_jack': extract_jack}
    if exercise not in functions:
        raise ValueError(f'Unsupported exercise: {exercise}')
    return functions[exercise](landmarks, width, height)


def assess_for_exercise(features, exercise='squat'):
    if exercise not in SUPPORTED_EXERCISES:
        raise ValueError(f'Unsupported exercise: {exercise}')
    if exercise == 'squat':
        return assess_squat(features)
    if features is None:
        view = 'front' if exercise == 'jumping_jack' else 'side'
        return {'status': 'unassessable', 'phase': 'unknown',
                'feedback': f'Show the required joints and full body in a {view} view.'}
    issues = []
    if exercise == 'pushup':
        phase = 'top' if features.elbow_angle >= 155 else 'bottom' if features.elbow_angle <= 100 else 'transition'
        if features.body_alignment < 155:
            issues.append('Review shoulder-hip-ankle alignment.')
    elif exercise == 'lunge':
        knee = min(features.left_knee_angle, features.right_knee_angle)
        phase = 'standing' if knee >= 160 else 'bottom' if knee <= 110 else 'transition'
        if phase != 'standing' and features.trunk_lean > 45:
            issues.append('Review projected trunk lean.')
    else:
        low, high = sorted((features.left_arm_angle, features.right_arm_angle))
        phase = ('open' if low >= 140 and features.ankle_width_ratio >= 1.8 else
                 'closed' if high <= 40 and features.ankle_width_ratio <= 1.3 else 'transition')
        if high > 60 and high - low > 35:
            issues.append('Review left-right arm symmetry.')
    return {'status': 'rule_flag' if issues else 'rule_pass', 'phase': phase,
            'feedback': ' '.join(issues) if issues else 'No baseline flag. This does not establish correct form.'}


NEW_RULES = {
    'pushup': {'min_valid_frames': 30, 'min_valid_fraction': .5, 'min_elbow_range': 20,
               'max_bottom_elbow': 100, 'min_top_elbow': 150, 'min_body_alignment': 155},
    'lunge': {'min_valid_frames': 30, 'min_valid_fraction': .5, 'min_knee_range': 20,
              'max_bottom_knee': 110, 'min_top_knee': 145, 'max_active_trunk_lean': 45},
    'jumping_jack': {'min_valid_frames': 30, 'min_valid_fraction': .5,
                     'min_open_frames': 3, 'min_closed_frames': 3},
}


def rules_for_exercise(exercise):
    if exercise not in SUPPORTED_EXERCISES:
        raise ValueError(f'Unsupported exercise: {exercise}')
    return SQUAT_RULES if exercise == 'squat' else NEW_RULES[exercise]


def summarize_for_exercise(records, exercise='squat'):
    if exercise == 'squat':
        return summarize_squat(records)
    rules = rules_for_exercise(exercise)
    valid = [r for r in records if r.get('features') is not None]
    result = {'prediction': 'unassessable', 'valid_frames': len(valid),
              'valid_fraction': len(valid) / len(records) if records else 0.0,
              'reasons': [], 'measurements': None}
    if len(valid) < rules['min_valid_frames'] or result['valid_fraction'] < rules['min_valid_fraction']:
        result['reasons'] = ['insufficient_pose_coverage']
        return result
    features = [r['features'] for r in valid]
    if exercise == 'jumping_jack':
        opened = sum(r['phase'] == 'open' for r in valid)
        closed = sum(r['phase'] == 'closed' for r in valid)
        result['measurements'] = {'open_frames': opened, 'closed_frames': closed}
        result['movement_observed'] = opened >= rules['min_open_frames'] and closed >= rules['min_closed_frames']
        result['reasons'] = ['form_classification_not_validated']
        # Motion evidence is separate from good/bad form, for which labels are absent.
        return result
    if exercise == 'pushup':
        angles = [f['elbow_angle'] for f in features]
        low, high = (float(v) for v in np.percentile(angles, [10, 90]))
        alignment = float(np.percentile([f['body_alignment'] for f in features], 10))
        result['measurements'] = {'elbow_p10': low, 'elbow_p90': high, 'body_alignment_p10': alignment}
        minimum_range = rules['min_elbow_range']
        if low > rules['max_bottom_elbow']:
            result['reasons'].append('limited_projected_elbow_flexion')
        if high < rules['min_top_elbow']:
            result['reasons'].append('limited_projected_elbow_extension')
        if alignment < rules['min_body_alignment']:
            result['reasons'].append('projected_body_misalignment')
    else:
        angles = [min(f['left_knee_angle'], f['right_knee_angle']) for f in features]
        low, high = (float(v) for v in np.percentile(angles, [10, 90]))
        active = [f['trunk_lean'] for f in features if min(f['left_knee_angle'], f['right_knee_angle']) < 145]
        lean = float(np.percentile(active, 90)) if active else None
        result['measurements'] = {'knee_p10': low, 'knee_p90': high, 'active_trunk_lean_p90': lean}
        minimum_range = rules['min_knee_range']
        if low > rules['max_bottom_knee']:
            result['reasons'].append('limited_projected_lunge_depth')
        if high < rules['min_top_knee']:
            result['reasons'].append('limited_projected_extension')
        if lean is not None and lean > rules['max_active_trunk_lean']:
            result['reasons'].append('large_projected_trunk_lean')
    if high - low < minimum_range:
        result['reasons'] = ['insufficient_observed_movement']
        return result
    result['prediction'] = 'incorrect' if result['reasons'] else 'correct'
    return result
