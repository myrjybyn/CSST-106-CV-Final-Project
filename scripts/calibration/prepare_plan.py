"""Reserve a new participant holdout before fitting; never rewrite source splits."""
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'docs/calibration/plan.json'
RESERVED=('mendeley_17','mendeley_19','mendeley_21','mendeley_23')


def main():
    if DEST.exists():raise ValueError('Calibration plan already exists')
    rows={}
    for split in ('train','val','test'):
        with (ROOT/f'data/prepared/mendeley/{split}_videos.csv').open(newline='') as f:
            rows[split]=[r for r in csv.DictReader(f) if '/side/' in r['relative_video_path'] and r['requires_review']=='NO' and r['exercise'] in ('squat','pushup')]
    selected={'fit':[r for r in rows['train'] if r['participant_id'] not in RESERVED],
              'validation':rows['val'], 'prospective':[r for r in rows['train'] if r['participant_id'] in RESERVED]}
    ids={s:{r['participant_id'] for r in rs} for s,rs in selected.items()}
    if any(ids[a]&ids[b] for a,b in (('fit','validation'),('fit','prospective'),('validation','prospective'))):raise ValueError('Participant leakage')
    for subject in RESERVED:
        pairs={(r['exercise'],r['form_label']) for r in selected['prospective'] if r['participant_id']==subject}
        if pairs!={(e,label) for e in ('squat','pushup') for label in ('correct','incorrect')}:raise ValueError('Incomplete prospective subject')
    plan={'created_at_utc':datetime.now(timezone.utc).isoformat(),
          'purpose':'Calibrate clip-level geometric form rules; preserve current pose, motion counts, and original reports.',
          'holdout_origin':'Prospectively reserved unused participants from original training inventory BEFORE feature extraction/fitting. No custom form model had previously been trained. Recorded development inference used Mendeley subject 001; other prior labelled runs used original validation/test participants. Inventory exposure is not model fitting.',
          'original_exposed_test_participants':sorted({r['participant_id'] for r in rows['test']}),
          'selection':'Four highest-numbered complete training participants with no documented development inference; subject 026 incomplete and excluded from holdout eligibility.',
          'search':{'model':'interpretable weighted-Gini decision tree on clip angle summaries','max_depth':[1,2],'min_leaf_clips':[4,6],'min_leaf_subjects':2,
                    'selection':'Leave-one-participant-out predictions on FIT only; maximize macro F1, then incorrect-form recall, then simpler model.',
                    'promotion':'Enable per exercise only if validation macro F1 strictly improves AND incorrect-form recall does not decrease AND fit-participant OOF macro F1 does not decrease. Otherwise retain uncalibrated rules.',
                    'untouched_test':'Run prospective only after model/source freeze; no post-test threshold/model selection.'},
          'scope':'Squat/push-up side views only. Whole-clip labels; no per-frame form supervision. Lunge/jack remain provisional.',
          'source_manifest_sha256':{},'partitions':{}}
    for split in rows:
        p=ROOT/f'data/prepared/mendeley/{split}_videos.csv';plan['source_manifest_sha256'][str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    for split,rs in selected.items():
        plan['partitions'][split]=[]
        for r in rs:
            relative='mendeley/'+r['relative_video_path'];p=ROOT/'data/raw'/relative
            plan['partitions'][split].append({'id':Path(relative).stem,'file':relative,'exercise':r['exercise'],'reference_form':r['form_label'],
                                              'participant':r['participant_id'],'original_split':r['split'],'partition':split,
                                              'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    DEST.write_text(json.dumps(plan,indent=2)+'\n')
    print('Plan fixed:',{s:len(r) for s,r in plan['partitions'].items()})


if __name__=='__main__':main()
