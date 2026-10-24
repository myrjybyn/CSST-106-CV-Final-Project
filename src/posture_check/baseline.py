"""Provisional single-frame squat rules, independent of inference and rendering."""


def assess(features):
    if features is None:
        return {"status": "unassessable", "phase": "unknown",
                "feedback": "Show shoulder, hip, knee and ankle in a side view."}
    knee = features.knee_angle
    phase = "standing" if knee >= 160 else "bottom" if knee <= 100 else "transition"
    if phase != "standing" and features.trunk_lean > 60:
        return {"status": "rule_flag", "phase": phase,
                "feedback": "Large projected trunk lean; review the side-view recording."}
    return {"status": "rule_pass", "phase": phase,
            "feedback": "No baseline flag. This does not establish correct form."}
