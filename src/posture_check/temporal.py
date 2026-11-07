"""Main method: feature EMA, dwell-confirmed feedback/phases, full-cycle counts.

Requires sequential frames at the supplied FPS. Missing poses are never imputed.
Counters are movement estimates, not verified exercise-form classifications.
"""
import math
from .features import Features
from .exercises import (SUPPORTED_EXERCISES, PushupFeatures, LungeFeatures,
                        JackFeatures, assess_for_exercise)

FEATURE_TYPES = {'squat': Features, 'pushup': PushupFeatures,
                 'lunge': LungeFeatures, 'jumping_jack': JackFeatures}
PARAMETERS = {'ema_time_constant_seconds': .12, 'phase_dwell_seconds': .10,
              'feedback_dwell_seconds': .15, 'reset_after_missing_seconds': .5}
ENDPOINTS = {'squat': ('standing', 'bottom'), 'pushup': ('top', 'bottom'),
             'lunge': ('standing', 'bottom'), 'jumping_jack': ('closed', 'open')}


class TemporalAnalyzer:
    def __init__(self, exercise, fps):
        if exercise not in SUPPORTED_EXERCISES:
            raise ValueError(f'Unsupported exercise: {exercise}')
        if not math.isfinite(fps) or not 0 < fps < 1000:
            raise ValueError('Valid frame rate required for temporal analysis')
        self.exercise, self.fps = exercise, fps
        self.alpha = 1 - math.exp(-1 / (fps * PARAMETERS['ema_time_constant_seconds']))
        self.phase_frames = max(1, math.ceil(fps * PARAMETERS['phase_dwell_seconds']))
        self.feedback_frames = max(1, math.ceil(fps * PARAMETERS['feedback_dwell_seconds']))
        self.reset_frames = max(1, math.ceil(fps * PARAMETERS['reset_after_missing_seconds']))
        self.elapsed = 0.0
        self.missing_seconds = self.phase_seconds = self.feedback_seconds = 0.0
        self.count = 0
        self.index = -1
        self.missing = 0
        self.smoothed = None
        self.side = None
        self.phase_candidate = None
        self.phase_run = 0
        self.phase = 'unknown'
        self.status_candidate = None
        self.status_run = 0
        self.status = 'pending'
        self.feedback = 'Checking movement consistency.'
        self.armed = self.bottom_seen = False

    def update(self, raw, *, dt_seconds=None):
        # File inference retains the original frame-based behavior. Live cameras
        # use elapsed time because capture/inference cadence varies by hardware.
        if dt_seconds is not None and (not math.isfinite(dt_seconds) or dt_seconds <= 0):
            raise ValueError('Elapsed frame time must be finite and positive')
        dt = 1 / self.fps if dt_seconds is None else dt_seconds
        timed = dt_seconds is not None
        self.elapsed += dt
        self.index += 1
        result = dict(raw)
        result.update(method='main', temporal_available=True,
                      raw_features=raw.get('features'), timestamp_seconds=self.index / self.fps,
                      repetition_completed=False)
        if timed:
            result['timestamp_seconds'] = self.elapsed
            if dt >= PARAMETERS['reset_after_missing_seconds']:
                self.smoothed = None
                self.armed = self.bottom_seen = False
                self.phase_candidate = self.status_candidate = None
                self.phase_run = self.status_run = 0
                self.phase_seconds = self.feedback_seconds = 0.0
                self.phase, self.status = 'unknown', 'pending'
                self.feedback = 'Checking movement consistency.'
                # A resumed frame does not prove the pose held during the stall.
                dt = 1 / self.fps
        features = raw.get('features')
        if features is None:
            self.missing += 1
            self.missing_seconds += dt
            self.phase_seconds = self.feedback_seconds = 0.0
            self.phase_candidate = self.status_candidate = None
            self.phase_run = self.status_run = 0
            self.phase = 'unknown'
            self.status = 'pending'
            self.feedback = 'Checking movement consistency.'
            if (self.missing_seconds >= PARAMETERS['reset_after_missing_seconds'] if timed else self.missing >= self.reset_frames):
                self.smoothed = None
                self.armed = self.bottom_seen = False
            result.update(status='unassessable', phase='unknown',
                          repetition_count=self.count)
            return result
        self.missing = 0
        self.missing_seconds = 0.0
        side = features.get('side')
        if self.smoothed is None or side != self.side:
            self.smoothed = dict(features)
            self.phase_candidate = None
            self.phase_run = 0
            self.phase_seconds = 0.0
        else:
            for key, value in features.items():
                if isinstance(value, (int, float)) and key != 'min_confidence':
                    alpha = 1 - math.exp(-dt / PARAMETERS['ema_time_constant_seconds']) if timed else self.alpha
                    self.smoothed[key] += alpha * (value - self.smoothed[key])
                else:
                    self.smoothed[key] = value
        self.side = side
        assessed = assess_for_exercise(FEATURE_TYPES[self.exercise](**self.smoothed), self.exercise)
        new_phase, new_status = assessed['phase'], assessed['status']
        if new_phase == self.phase_candidate:
            self.phase_run += 1
            self.phase_seconds += dt
        else:
            self.phase_candidate, self.phase_run = new_phase, 1
            self.phase_seconds = dt
        if (self.phase_seconds >= PARAMETERS['phase_dwell_seconds'] if timed else self.phase_run >= self.phase_frames):
            self.phase = new_phase
            ready, lowered = ENDPOINTS[self.exercise]
            if self.phase == ready:
                if self.armed and self.bottom_seen:
                    self.count += 1
                    result['repetition_completed'] = True
                self.armed, self.bottom_seen = True, False
            elif self.phase == lowered and self.armed:
                self.bottom_seen = True
        # Confirm the issue text as well as status so one issue cannot inherit
        # another issue's dwell time in exercises with multiple feedback messages.
        candidate = (new_status, assessed['feedback'])
        if candidate == self.status_candidate:
            self.status_run += 1
            self.feedback_seconds += dt
        else:
            self.status_candidate, self.status_run = candidate, 1
            self.feedback_seconds = dt
        if (self.feedback_seconds >= PARAMETERS['feedback_dwell_seconds'] if timed else self.status_run >= self.feedback_frames):
            self.status, self.feedback = candidate
        result.update(features=dict(self.smoothed), status=self.status, phase=self.phase,
                      instantaneous_phase=new_phase, feedback=self.feedback,
                      repetition_count=self.count)
        return result
