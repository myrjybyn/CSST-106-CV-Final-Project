"""Movement-only full-cycle counting, independent of smoothed form feedback.

Endpoint entry limits are inherited from the existing geometric rules. A five
 degree / 0.2 shoulder-width release margin supplies hysteresis, not a relaxed
form label. Missing input never supplies movement evidence.
"""
import math
from .exercises import SUPPORTED_EXERCISES

PARAMETERS = {'endpoint_dwell_seconds': .10, 'reset_after_missing_seconds': .50,
              'angle_release_margin_degrees': 5, 'jack_width_release_margin': .2}


class RepetitionCounter:
    def __init__(self, exercise):
        if exercise not in SUPPORTED_EXERCISES:
            raise ValueError(f'Unsupported exercise: {exercise}')
        self.exercise = exercise
        self.top_angle, self.bottom_angle = {
            'squat': (160, 100), 'pushup': (155, 100),
            'lunge': (160, 110), 'jumping_jack': (40, 140),
        }[exercise]
        self.closed_width, self.open_width = 1.3, 1.8
        self.count = 0
        self.reset()

    def reset(self):
        """Discard partial movement and identity; retain completed count."""
        self.stage = 'ready'
        self.endpoint = None
        self.candidate = None
        self.dwell = 0.0
        self.missing = 0.0
        self.side = None
        self.active_leg = None
        self.ready_legs = set()
        self.phase = 'unknown'

    def _endpoint(self, f):
        margin = PARAMETERS['angle_release_margin_degrees']
        if self.exercise in ('squat', 'pushup'):
            angle = f['knee_angle' if self.exercise == 'squat' else 'elbow_angle']
            top, bottom = self.top_angle, self.bottom_angle
            if angle >= top or (self.endpoint == 'ready' and angle >= top-margin):
                return 'ready'
            if angle <= bottom or (self.endpoint == 'bottom' and angle <= bottom+margin):
                return 'bottom'
        elif self.exercise == 'jumping_jack':
            low, high = sorted((f['left_arm_angle'],f['right_arm_angle']))
            width = f['ankle_width_ratio']
            width_margin = PARAMETERS['jack_width_release_margin']
            if ((high <= self.top_angle and width <= self.closed_width) or
                    (self.endpoint == 'ready' and high <= self.top_angle+margin and width <= self.closed_width+width_margin)):
                return 'ready'
            if ((low >= self.bottom_angle and width >= self.open_width) or
                    (self.endpoint == 'bottom' and low >= self.bottom_angle-margin and width >= self.open_width-width_margin)):
                return 'bottom'
        else:
            angles = {leg:f[f'{leg}_knee_angle'] for leg in ('left','right')}
            if self.active_leg is not None:
                value = angles[self.active_leg]
                if value >= self.top_angle or (self.endpoint == 'ready' and value >= self.top_angle-margin):
                    return 'ready'
                if value <= self.bottom_angle or (self.endpoint == 'bottom' and value <= self.bottom_angle+margin):
                    return 'bottom'
            else:
                # Only a leg observed straight during a confirmed ready stance
                # may initiate a rep. A rear knee already bent is not a new rep.
                candidates = [leg for leg in self.ready_legs if angles[leg] <= self.bottom_angle]
                if candidates and self.stage == 'bottom':
                    leg = min(candidates,key=lambda side:(angles[side],side))
                    return 'bottom:'+leg
                if max(angles.values()) >= self.top_angle:
                    return 'ready'
        return None

    def update(self, features, dt):
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('Counter elapsed time must be finite and positive')
        completed = False
        if dt >= PARAMETERS['reset_after_missing_seconds']:
            self.reset()
            # Do not count an unseen interval as endpoint dwell.
            dt = 0.0
        if features is None:
            self.missing += dt
            self.candidate, self.dwell, self.endpoint = None, 0.0, None
            self.phase = 'unknown'
            if self.missing >= PARAMETERS['reset_after_missing_seconds']:
                self.reset()
            return self._result(completed)
        self.missing = 0.0
        side = features.get('side')
        if self.side is not None and side != self.side:
            self.reset()
        self.side = side
        endpoint = self._endpoint(features)
        self.endpoint = endpoint
        self.phase = ('transition' if endpoint is None else
                      ('standing' if self.exercise in ('squat','lunge') else
                       'top' if self.exercise == 'pushup' else 'closed') if endpoint == 'ready' else
                      'open' if self.exercise == 'jumping_jack' else 'bottom')
        if endpoint is None:
            self.candidate, self.dwell = None, 0.0
            return self._result(completed)
        if endpoint != self.candidate:
            self.candidate, self.dwell = endpoint, 0.0
        self.dwell += dt
        if self.dwell + 1e-9 < PARAMETERS['endpoint_dwell_seconds']:
            return self._result(completed)
        if self.stage == 'ready' and endpoint == 'ready':
            self.stage = 'bottom'
        elif self.stage == 'bottom' and endpoint.startswith('bottom'):
            self.stage = 'return'
            if self.exercise == 'lunge':
                self.active_leg = endpoint.split(':')[1]
                self.endpoint = self.candidate = 'bottom'
        elif self.stage == 'return' and endpoint == 'ready':
            self.count += 1
            completed = True
            self.stage = 'bottom'
            self.active_leg = None
            self.ready_legs.clear()
        if self.exercise == 'lunge' and self.stage == 'bottom' and endpoint == 'ready':
            self.ready_legs.update(leg for leg in ('left','right') if features[f'{leg}_knee_angle'] >= self.top_angle)
        return self._result(completed)

    def _result(self, completed):
        return {'repetition_count':self.count, 'repetition_completed':completed,
                'movement_phase':self.phase, 'active_leg':self.active_leg}
