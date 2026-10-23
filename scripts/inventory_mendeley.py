#!/usr/bin/env python3
"""List squat/push-up MP4s from a downloaded Mendeley Subject-wise archive.

Never invent subject/quality labels. Unknown fields are explicitly flagged for manual review.
"""
import argparse
import csv
import re
from pathlib import Path

EXTENSIONS={".mp4", ".mov", ".avi", ".mkv", ".webm"}

def token(text, words):
    norm=re.sub(r"[^a-z0-9]+","_",text.lower()).strip("_")
    return any(re.search(rf"(^|_){re.escape(t)}($|_)",norm) for t in words)

def classify(p):
    text="/".join(p.parts)
    if token(text,["squat", "squats", "bodyweight_squat"]): ex="squat"
    elif token(text,["pushup","pushups", "push_up", "push_ups"]): ex="pushup"
    else: return None
    good=token(text,["good","correct","proper"])
    bad=token(text,["bad","incorrect","improper"])
    form=("correct" if good else "incorrect") if good != bad else "REVIEW"
    # Conservative participant ID inference; manual check expected for unknown naming patterns.
    subject="REVIEW"
    for part in p.parts:
        match=re.match(r"^(?:subject|participant|person|subj|sub|s)[_\- ]*0*(\d{1,4})$",part,re.I)
        if match:
            subject="mendeley_"+str(int(match.group(1)))
            break
    return {"relative_video_path":str(p).replace("\\","/"),"exercise":ex,"form_label":form,
            "participant_id":subject,"requires_review":"YES" if form=="REVIEW" or subject=="REVIEW" else "NO"}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,required=True,help="Folder extracted from the Mendeley Subject-wise ZIP")
    ap.add_argument("--output",type=Path,default=Path("data/prepared/mendeley_inventory.csv"))
    a=ap.parse_args()
    if not a.root.is_dir():ap.error("Dataset directory not found")
    rows=[]
    for file in sorted(a.root.rglob("*")):
        if file.is_file() and file.suffix.lower() in EXTENSIONS:
            entry=classify(file.relative_to(a.root))
            if entry:rows.append(entry)
    if not rows:ap.error("No squat/push-up videos found: inspect archive naming convention")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    review=sum(r["requires_review"]=="YES" for r in rows)
    print(f"[ok] {len(rows)} exercise videos inventoried; {review} rows require manual label/subject verification")
    print(f"[output] {a.output}")
    print("Do NOT create training splits until all participant IDs and quality labels are checked.")

if __name__=="__main__":main()
