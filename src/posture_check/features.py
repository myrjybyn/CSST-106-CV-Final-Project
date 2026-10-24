"""Visibility-gated, aspect-corrected 2D squat features (MediaPipe indices)."""
from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class Features:
    side: str
    knee_angle: float
    hip_angle: float
    trunk_lean: float
    min_confidence: float

    def to_dict(self):
        return asdict(self)


def angle(a, b, c):
    """Angle ABC in degrees; reject coincident or nonfinite points."""
    u = (a[0] - b[0], a[1] - b[1])
    v = (c[0] - b[0], c[1] - b[1])
    norm = math.hypot(*u) * math.hypot(*v)
    if not math.isfinite(norm) or norm < 1e-8:
        raise ValueError("Degenerate joint geometry")
    cosine = sum(x * y for x, y in zip(u, v)) / norm
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def extract(landmarks, width, height, confidence=0.5):
    """Pick the better-observed side; return None rather than assess hidden joints.

    Pixel scaling avoids distorting joint angles on nonsquare input. These are
    projected 2D features; side-view camera placement is a runtime requirement.
    """
    if len(landmarks) != 33 or width <= 0 or height <= 0:
        return None
    candidates = []
    for side, indices in (("left", (11, 23, 25, 27)), ("right", (12, 24, 26, 28))):
        joints = [landmarks[i] for i in indices]
        scores = [min(p.visibility, p.presence) for p in joints]
        if any(not math.isfinite(x) or x < confidence for x in scores):
            continue
        if any(not (0 <= p.x <= 1 and 0 <= p.y <= 1) for p in joints):
            continue
        shoulder, hip, knee, ankle = [(p.x * width, p.y * height) for p in joints]
        # The supported setup is a full-body subject filling the frame. The
        # observed equipment false detection had a tiny shoulder-to-ankle chain.
        chain = sum(math.dist(a, b) for a, b in zip(
            (shoulder, hip, knee), (hip, knee, ankle)))
        if chain < 0.35 * height:
            continue
        try:
            features = Features(
                side, angle(hip, knee, ankle), angle(shoulder, hip, knee),
                angle(shoulder, hip, (hip[0], hip[1] - height)), min(scores),
            )
        except ValueError:
            continue
        candidates.append(features)
    return max(candidates, key=lambda f: f.min_confidence, default=None)
