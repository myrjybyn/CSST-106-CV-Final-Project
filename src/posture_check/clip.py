"""Fixed, provisional side-view squat clip rules; no frame-level label inference.

Thresholds were specified before the new validation run. A pass is a baseline
prediction for comparison with source labels, not a verified form judgement.
"""
import numpy as np

RULES = {
    "min_valid_frames": 30, "min_valid_fraction": 0.5,
    "min_knee_range_degrees": 20, "max_bottom_knee_degrees": 100,
    "min_top_knee_degrees": 145, "max_active_trunk_lean_degrees": 60,
    "min_body_chain_image_height_fraction": 0.35,
}


def summarize(records):
    features = [r["features"] for r in records if r.get("features") is not None]
    coverage = len(features) / len(records) if records else 0.0
    result = {"prediction": "unassessable", "valid_frames": len(features),
              "valid_fraction": coverage, "reasons": [], "measurements": None}
    if len(features) < RULES["min_valid_frames"] or coverage < RULES["min_valid_fraction"]:
        result["reasons"] = ["insufficient_pose_coverage"]
        return result
    knees = np.array([f["knee_angle"] for f in features])
    bottom, top = (float(x) for x in np.percentile(knees, [10, 90]))
    active = [f["trunk_lean"] for f in features if f["knee_angle"] < 145]
    lean = float(np.percentile(active, 90)) if active else None
    result["measurements"] = {"knee_p10": bottom, "knee_p90": top,
                              "active_trunk_lean_p90": lean}
    if top - bottom < RULES["min_knee_range_degrees"]:
        result["reasons"] = ["insufficient_observed_movement"]
        return result
    if bottom > RULES["max_bottom_knee_degrees"]:
        result["reasons"].append("limited_projected_depth")
    if top < RULES["min_top_knee_degrees"]:
        result["reasons"].append("limited_projected_extension")
    if lean is not None and lean > RULES["max_active_trunk_lean_degrees"]:
        result["reasons"].append("large_projected_trunk_lean")
    result["prediction"] = "incorrect" if result["reasons"] else "correct"
    return result


def classification_metrics(rows):
    """Count abstentions as misses in overall accuracy and class recall/F1."""
    if not rows:
        raise ValueError("No classified clips")
    labels = ("correct", "incorrect")
    matrix = {label: {pred: 0 for pred in (*labels, "unassessable")} for label in labels}
    for row in rows:
        matrix[row["ground_truth"]][row["clip_assessment"]["prediction"]] += 1
    matched = sum(matrix[label][label] for label in labels)
    assessed = sum(sum(matrix[label][pred] for pred in labels) for label in labels)
    f1 = {}
    for label in labels:
        tp = matrix[label][label]
        fn = sum(matrix[label].values()) - tp
        fp = sum(matrix[other][label] for other in labels if other != label)
        f1[label] = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    return {"clips": len(rows), "assessed_clips": assessed,
            "abstained_clips": len(rows) - assessed, "accuracy_all_clips": matched / len(rows),
            "accuracy_assessed_clips": matched / assessed if assessed else None,
            "macro_f1_with_abstentions_as_misses": sum(f1.values()) / len(labels),
            "per_class_f1": f1, "confusion_matrix": matrix}
