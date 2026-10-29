#!/usr/bin/env python3
"""Acquire REHAB24-6 annotation CSV and create participant-disjoint split manifests.

Does NOT download or produce RGB video/pose features. Grouped splitting uses person_id.
"""
import argparse
import csv
import itertools
import math
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

URLS = [
    "https://zenodo.org/records/13305826/files/Segmentation.csv?download=1",
    "https://raw.githubusercontent.com/YattaHab/REHAB24-6-Standardized-Training-Data/main/Segmentation.csv",
]
EXERCISES = {"3": "table_pushup", "5": "lunge", "6": "squat"}
REQUIRED = {"video_id", "person_id", "exercise_id", "repetition_number", "first_frame", "last_frame", "correctness"}


def acquire(target):
    if target.is_file():
        print(f"[existing] {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    for url in URLS:
        try:
            req = Request(url, headers={"User-Agent": "PostureCheckAcademicDatasetPrep/1.0 (research; compatible browser)"})
            with urlopen(req, timeout=35) as response:
                content = response.read(1_000_000)
            if not content.startswith(b"video_id;"):
                raise ValueError("Response is not the expected semicolon-delimited CSV")
            target.write_bytes(content)
            print(f"[downloaded] {target}\n[source] {url}")
            return
        except Exception as exc:
            failures.append(f"{url}: {exc}")
    raise SystemExit("Automatic metadata download failed. Download Segmentation.csv from the Zenodo page and save it at:\n"
                     + str(target) + "\nThen rerun this script. Errors:\n" + "\n".join(failures))


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("Unexpected annotation schema; expected columns: " + ", ".join(sorted(REQUIRED)))
        original_fields = list(reader.fieldnames)
        rows = []
        for r in reader:
            if r["exercise_id"] not in EXERCISES:
                continue
            if r["correctness"] not in ("0", "1"):
                raise ValueError(f"Unrecognized correctness label: {r['correctness']}")
            if not (r["person_id"] and r["video_id"]):
                raise ValueError("Missing subject or video identity")
            r = dict(r)
            r["exercise"] = EXERCISES[r["exercise_id"]]
            r["form_label"] = "correct" if r["correctness"] == "1" else "incorrect"
            r["dataset"] = "REHAB24-6"
            rows.append(r)
    return rows, original_fields + ["exercise", "form_label", "dataset"]


def choose_split(rows):
    subjects = sorted({r["person_id"] for r in rows})
    if len(subjects) < 6:
        raise ValueError("At least six distinct people required for a meaningful three-way subject split")
    by_person = {s: Counter((r["exercise"], r["form_label"]) for r in rows if r["person_id"] == s) for s in subjects}
    labels = sorted({(r["exercise"], r["form_label"]) for r in rows})
    total = Counter((r["exercise"], r["form_label"]) for r in rows)
    n = len(rows)
    target = {"train": .70, "val": .15, "test": .15}
    # Practical exhaustive search for 10 REHAB24-6 subjects; explore group counts near 70/15/15.
    nsub = len(subjects)
    sizes = [(t,v,nsub-t-v) for t in range(max(1,round(.60*nsub)),min(nsub-2,round(.75*nsub))+1)
             for v in range(max(1,round(.10*nsub)),min(nsub-t-1,round(.25*nsub))+1)]
    sizes = [s for s in sizes if s[2] >= 1]
    best = None
    for nt, nv, _ in sizes:
        for train in itertools.combinations(subjects, nt):
            remains = [s for s in subjects if s not in train]
            for val in itertools.combinations(remains, nv):
                test = tuple(s for s in remains if s not in val)
                split_subjects = {"train": train, "val": val, "test": test}
                breakdown = {split: sum((by_person[s] for s in people), Counter()) for split, people in split_subjects.items()}
                counts = {split: sum(x.values()) for split, x in breakdown.items()}
                score = sum(abs(counts[k] / n - target[k]) for k in target) * 4
                # Preserve relative exercise x correctness proportions where possible.
                for k in target:
                    for label in labels:
                        goal = target[k] * total[label]
                        got = breakdown[k][label]
                        score += abs(got - goal) / max(total[label],1) * .20
                        if got == 0:
                            score += 10 if k != "train" else 20
                key = (score, tuple(split_subjects[k] for k in ("train", "val", "test")))
                if best is None or key < best[0]:
                    best = (key, split_subjects)
    if best is None:
        raise ValueError("Could not produce subject-separated splits")
    return {subject: split for split, people in best[1].items() for subject in people}


def save_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def render_card(out, rows, split_map, raw_path):
    sub = Counter(r["person_id"] for r in rows)
    totals = Counter((r["exercise"],r["form_label"],r["split"]) for r in rows)
    categories = ["table_pushup", "lunge", "squat"]
    parts = ["# POSTURE CHECK — Milestone 2 Data Card (REHAB24-6 subset)", "",
        "**Data type:** repetition-level annotation manifests, **NOT image files or pose features**.",
        "**Source:** Černek et al. (2024), REHAB24-6: https://zenodo.org/records/13305826",
        "**License/conditions:** academic/non-profit, non-commercial research only; cite original publication. ",
        "**Subset:** Ex3 table-supported push-ups; Ex5 lunges; Ex6 squats. No jumping jacks.",
        "**Collection:** 10 participants overall, lab environment, two synchronized RGB viewpoints, 30 FPS; physiotherapist-supervised repetitions.",
        "**Annotation:** original Segmentation.csv, correctness 1=correct / 0=incorrect; temporal start/end frames and video IDs preserved.",
        "**Splitting:** grouped by person_id (all videos and repetitions for a person in one partition), targeting ~70/15/15; splits locked after assignment.",
        "**Preprocessing applied:** rows filtered to exercise IDs 3, 5, 6; exercise and form labels normalized. No video frames resized or pose features extracted.",
        "**Image sizes:** not applicable to annotation-only files. Verify per-video resolution after downloading videos.",
        "**Training assets:** Download original `videos.zip` (2.7 GB) for RGB input, OR `2d_joints.zip` (693.4 MB) for 2D joint-feature experiments; both not included here.",
        "**Gaps:** no jumping jacks; push-ups are table-supported; small participant pool; lab recording/mocap suits may not generalize to webcam usage.",
        "**Leakage warning:** No random frame-level splitting. Do not merge REHAB with other sources before reconciling landmark conventions and subject identities.",
        "", "## Repetition-level counts (ground-truth annotations)", "",
        "| Exercise | Form | Train | Validation | Test | Total |", "|---|---|---:|---:|---:|---:|"]
    for ex in categories:
        for label in ("correct","incorrect"):
            tr,va,te=(totals[ex,label,k] for k in ("train","val","test"))
            parts.append(f"| {ex} | {label} | {tr} | {va} | {te} | {tr+va+te} |")
    splits = Counter(r["split"] for r in rows)
    parts += ["", f"**Total:** {len(rows)} repetitions; train {splits['train']}, val {splits['val']}, test {splits['test']}.",
              f"**Participants represented:** {len(sub)}; " + ", ".join(f"{k}={len({r['person_id'] for r in rows if r['split']==k})}" for k in ("train","val","test")) + ".",
              "", "**Note:** This card describes annotation acquisition and splitting only. Mark media/landmark acquisition as pending until the corresponding ZIP is downloaded and validated.", ""]
    out.write_text("\n".join(parts),encoding="utf-8")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--metadata", type=Path,default=Path("data/raw/rehab24/Segmentation.csv"))
    p.add_argument("--output",type=Path,default=Path("data/prepared/rehab24"))
    p.add_argument("--data-card",type=Path,default=Path("docs/data_cards/DATA_CARD_REHAB24.md"))
    a=p.parse_args()
    acquire(a.metadata)
    rows, fields=read_rows(a.metadata)
    split_map=choose_split(rows)
    for r in rows:
        r["split"]=split_map[r["person_id"]]
    fields=fields+["split"]
    a.output.mkdir(parents=True, exist_ok=True)
    for split in ("train","val","test"):
        save_csv(a.output/f"{split}_repetitions.csv",[r for r in rows if r["split"]==split],fields)
    save_csv(a.output/"all_repetitions.csv",rows,fields)
    pmap=[{"person_id":sid,"split":spl} for sid,spl in sorted(split_map.items())]
    save_csv(a.output/"subject_assignments.csv",pmap,["person_id","split"])
    card=a.data_card
    card.parent.mkdir(parents=True,exist_ok=True)
    render_card(card,rows,split_map,a.metadata)
    print(f"[ok] {len(rows)} repetitions; {len(split_map)} participants, no cross-split subjects")
    for split in ("train","val","test"):
        print(f"  {split}: {sum(r['split']==split for r in rows)} reps")
    print(f"[card] {card}")
    print("NOTE: RGB/joint data NOT downloaded. These are annotation manifests ONLY.")

if __name__=="__main__":main()
