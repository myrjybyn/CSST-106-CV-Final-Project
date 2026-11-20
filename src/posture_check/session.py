"""Small, fixed-rule whole-session assessment for the classroom demo."""
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from .clip import RULES as SQUAT_RULES
from .counting import RepetitionCounter
from .exercises import NEW_RULES, SUPPORTED_EXERCISES

METHOD = 'guided-session-rules-v1'
MIN_VALID_FRAMES = 10
MIN_COVERAGE = .5
MIN_MOTION = 20
TIPS = {
    'limited_depth': 'Use a fuller lowering movement to reach the exercise depth target.',
    'incomplete_extension': 'Return fully to the starting position between repetitions.',
    'trunk_lean': 'Keep your torso steadier and reduce excessive forward lean.',
    'body_alignment': 'Keep your shoulders, hips and ankles in a straighter line during push-ups.',
    'arms_not_raised': 'Raise both arms fully during the open part of each jumping jack.',
    'feet_not_spread': 'Move your feet farther apart during the open part of each jumping jack.',
    'incomplete_close': 'Bring your arms down and feet together between jumping jacks.',
    'arm_asymmetry': 'Move both arms together through a similar range.',
}


class GuidedRepetitionCounter(RepetitionCounter):
    """Count recognizable movement even when it falls short of the form target."""
    def __init__(self, exercise):
        super().__init__(exercise)
        self.top_angle, self.bottom_angle = {
            'squat': (150, 130), 'pushup': (145, 125),
            'lunge': (150, 130), 'jumping_jack': (55, 110),
        }[exercise]
        self.closed_width, self.open_width = 1.4, 1.6


class ExerciseSession:
    """Keep numeric movement evidence, excluding the initial standing/setup wait."""
    def __init__(self, exercise):
        if exercise not in SUPPORTED_EXERCISES:
            raise ValueError('Unsupported exercise: ' + exercise)
        self.exercise = exercise
        self.records = []
        self.before_movement = deque(maxlen=15)
        self.started = False

    def add(self, record):
        item = {'features': record.get('features'),
                'phase': record.get('instantaneous_phase', record.get('phase', 'unknown'))}
        if not self.started:
            self.before_movement.append(item)
            if item['features'] is None or item['phase'] in ('standing', 'top', 'closed', 'unknown'):
                return
            self.started = True
            self.records.extend(self.before_movement)
            self.before_movement.clear()
        else:
            self.records.append(item)

    def assess(self):
        records = self.records
        valid = [r['features'] for r in records if r['features'] is not None]
        coverage = len(valid) / len(records) if records else 0
        result = dict(method=METHOD, prediction='unassessable', issues=[], tips=[],
                      valid_frames=len(valid), valid_fraction=coverage, measurements={},
                      scope='Fixed 2D exercise checks; school-project form estimate.')
        if not self.started and any(r['features'] is not None for r in self.before_movement):
            result['tips'] = ['Show a full lowering and return movement, then try again.']
            result['reason'] = 'insufficient_observed_movement'
            return result
        if len(valid) < MIN_VALID_FRAMES or coverage < MIN_COVERAGE:
            result['tips'] = ['Try again with your whole body visible and steady lighting.']
            result['reason'] = 'insufficient_pose_coverage'
            return result

        def percentile(key, percent):
            return float(np.percentile([f[key] for f in valid], percent))

        issues = result['issues']
        if self.exercise == 'jumping_jack':
            arms = [min(f['left_arm_angle'], f['right_arm_angle']) for f in valid]
            low, high = (float(v) for v in np.percentile(arms, [10, 90]))
            width_low, width_high = percentile('ankle_width_ratio', 10), percentile('ankle_width_ratio', 90)
            symmetry = sum(max(f['left_arm_angle'], f['right_arm_angle']) > 60
                           and abs(f['left_arm_angle'] - f['right_arm_angle']) > 35 for f in valid) / len(valid)
            result['measurements'] = dict(arm_p10=low, arm_p90=high,
                                          ankle_width_p10=width_low, ankle_width_p90=width_high,
                                          asymmetric_frame_fraction=symmetry)
            if high < 140: issues.append('arms_not_raised')
            if width_high < 1.8: issues.append('feet_not_spread')
            if low > 40 or width_low > 1.3: issues.append('incomplete_close')
            if symmetry > .2: issues.append('arm_asymmetry')
        else:
            key = 'elbow_angle' if self.exercise == 'pushup' else 'knee_angle'
            angles = ([min(f['left_knee_angle'], f['right_knee_angle']) for f in valid]
                      if self.exercise == 'lunge' else [f[key] for f in valid])
            low, high = (float(v) for v in np.percentile(angles, [10, 90]))
            rules = SQUAT_RULES if self.exercise == 'squat' else NEW_RULES[self.exercise]
            bottom = rules['max_bottom_elbow'] if self.exercise == 'pushup' else rules['max_bottom_knee_degrees' if self.exercise == 'squat' else 'max_bottom_knee']
            top = rules['min_top_elbow'] if self.exercise == 'pushup' else rules['min_top_knee_degrees' if self.exercise == 'squat' else 'min_top_knee']
            result['measurements'] = dict(angle_p10=low, angle_p90=high,
                                          depth_target_degrees=bottom, return_target_degrees=top)
            if low > bottom: issues.append('limited_depth')
            if high < top: issues.append('incomplete_extension')
            if self.exercise == 'pushup':
                alignment = percentile('body_alignment', 10)
                result['measurements']['body_alignment_p10'] = alignment
                if alignment < rules['min_body_alignment']: issues.append('body_alignment')
            else:
                active = [f['trunk_lean'] for f, angle in zip(valid, angles) if angle < 145]
                lean = float(np.percentile(active, 90)) if active else None
                result['measurements']['active_trunk_lean_p90'] = lean
                limit = rules['max_active_trunk_lean_degrees' if self.exercise == 'squat' else 'max_active_trunk_lean']
                if lean is not None and lean > limit: issues.append('trunk_lean')
        if high - low < MIN_MOTION:
            result.update(issues=[], tips=['Show a full lowering and return movement, then try again.'],
                          reason='insufficient_observed_movement')
            return result
        result['prediction'] = 'bad' if issues else 'good'
        result['tips'] = [TIPS[issue] for issue in issues] if issues else [
            'Keep the same range of movement and steady control for your next set.']
        return result


class SessionRecorder:
    """Write local MP4 with elapsed-time pacing despite variable inference FPS."""
    def __init__(self, path, frame, fps=20):
        self.path, self.fps = Path(path), fps
        height, width = frame.shape[:2]
        self.writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
        if not self.writer.isOpened():
            self.writer.release()
            raise RuntimeError('Cannot save the session recording. Check the output folder and available disk space.')
        self.frames = 0
        self.previous = frame.copy()

    def write(self, frame, elapsed):
        target = max(0, int(elapsed * self.fps))
        while self.frames < target:
            self.writer.write(self.previous)
            self.frames += 1
        if self.frames == target:
            self.writer.write(frame)
            self.frames += 1
        self.previous = frame.copy()

    def close(self):
        self.writer.release()
