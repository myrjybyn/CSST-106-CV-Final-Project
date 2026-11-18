"""Explain existing confidence/in-frame gates without inventing missing joints."""
import math

GROUPS = {
    'squat': ((11,23,25,27),(12,24,26,28)),
    'pushup': ((11,13,15,23,27),(12,14,16,24,28)),
    'lunge': ((11,12,23,24,25,26,27,28),),
    'jumping_jack': ((11,12,15,16,23,24,25,26,27,28),),
}


def explain(landmarks, exercise):
    """Diagnose rejected features; a valid chain can still fail geometry gates."""
    view = 'front' if exercise == 'jumping_jack' else 'side'
    if len(landmarks) != 33:
        return 'no_pose', 'Step into view and keep your whole body visible.'
    visible_groups = []
    for ids in GROUPS[exercise]:
        points = [landmarks[i] for i in ids]
        if all(math.isfinite(p.visibility) and math.isfinite(p.presence)
               and min(p.visibility,p.presence) >= .5 for p in points):
            visible_groups.append(points)
    if not visible_groups:
        return 'required_joints_not_visible', f'Keep the required joints visible in a {view} view; improve lighting or remove occlusion.'
    if not any(all(0 <= p.x <= 1 and 0 <= p.y <= 1 for p in points) for points in visible_groups):
        return 'outside_frame', 'Step back so your whole body fits inside the camera view.'
    return 'unsupported_geometry_or_scale', f'Use a {view} view and move closer while keeping your whole body visible.'
