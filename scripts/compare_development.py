"""Compare frozen old/new main methods using training-only development media.

This does not choose parameters, write over Phase 3 results, or use test clips.
Run from the repository root; no installation or PYTHONPATH export required.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import cv2
from posture_check.__main__ import process
from posture_check.pose import PoseEstimator
from posture_check.temporal import TemporalAnalyzer
from posture_check.exercises import summarize_for_exercise


def source_at(ref, name):
    return subprocess.check_output(['git','show',f'{ref}:{name}'],cwd=ROOT,text=True)


def reference_methods(ref):
    temporal = {'__package__':'posture_check', '__name__':'reference_temporal'}
    exec(source_at(ref,'src/posture_check/temporal.py'),temporal)
    pipeline = {'__package__':'posture_check', '__name__':'reference_pipeline'}
    exec(source_at(ref,'src/posture_check/__main__.py'),pipeline)
    return pipeline['process'],temporal['TemporalAnalyzer']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--media-root',type=Path,required=True,help='Directory containing mendeley/ and rehab24/')
    parser.add_argument('--model',type=Path,default=ROOT/'models/pose_landmarker_lite.task')
    parser.add_argument('--manifest',type=Path,default=ROOT/'docs/development/pose_counting_manifest.json')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/development/pose_counting_comparison.json')
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text())
    if not manifest['clips'] or any(c['split']!='train' for c in manifest['clips']):
        raise ValueError('Only nonempty training-manifest development inputs are permitted')
    paths=[]
    for clip in manifest['clips']:
        path=(args.media_root/clip['file']).resolve()
        if not path.is_relative_to(args.media_root.resolve()) or not path.is_file():
            raise ValueError('Invalid or missing development media: '+clip['file'])
        paths.append(path)
    # Lock input/code identity before inference and retain the original reference.
    reference=subprocess.check_output(['git','rev-parse',manifest['reference_ref']],cwd=ROOT,text=True).strip()
    old_process,old_analyzer=reference_methods(reference)
    log={'started_at_utc':datetime.now(timezone.utc).isoformat(),'purpose':manifest['purpose'],
         'manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
         'reference_commit':reference, 'model_sha256':hashlib.sha256(args.model.read_bytes()).hexdigest(),
         'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src/posture_check').glob('*.py'))},
         'inputs':[{**c,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for c,p in zip(manifest['clips'],paths)],
         'limitations':manifest['limitations'],'runs':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for clip,path in zip(manifest['clips'],paths):
        for version in ('reference','candidate'):
            capture=cv2.VideoCapture(str(path));estimator=None
            try:
                if not capture.isOpened():raise ValueError('Cannot decode '+str(path))
                fps=capture.get(cv2.CAP_PROP_FPS)
                analyzer=(old_analyzer if version=='reference' else TemporalAnalyzer)(clip['exercise'],fps)
                estimator=PoseEstimator(args.model,video=version=='candidate',fps=fps if version=='candidate' else None)
                rows=[];seconds=0.;reasons=Counter();padding=0
                started=time.perf_counter()
                while True:
                    ok,frame=capture.read()
                    if not ok:break
                    tick=time.perf_counter()
                    if version=='reference':_,raw=old_process(frame,estimator,clip['exercise'])
                    else:_,raw=process(frame,estimator,clip['exercise'],enhanced=True)
                    rows.append(analyzer.update(raw));seconds+=time.perf_counter()-tick
                    reasons[raw.get('assessability_reason','not_recorded')]+=1
                    padding+=int(raw.get('padding_removed',False))
                elapsed=time.perf_counter()-started
                if not rows:raise ValueError('No decoded frames')
                result={'clip_id':clip['id'],'exercise':clip['exercise'],'version':version,
                        'frames':len(rows),'assessable_frames':sum(r['features'] is not None for r in rows),
                        'pose_frames':sum(r['pose_detected'] for r in rows),'estimated_reps':analyzer.count,
                        'reference_form':clip['reference_form'],'clip_assessment':summarize_for_exercise(rows,clip['exercise']),
                        'padding_removed_frames':padding,'assessability_reasons':dict(reasons),
                        'processing_fps':len(rows)/seconds,'decode_and_processing_fps':len(rows)/elapsed}
                log['runs'].append(result)
                args.output.write_text(json.dumps(log,indent=2)+'\n')
                print(clip['id'],version,'coverage',f"{result['assessable_frames']}/{len(rows)}",'reps',analyzer.count,'prediction',result['clip_assessment']['prediction'],flush=True)
            finally:
                capture.release()
                if estimator is not None:estimator.close()
    log['completed_at_utc']=datetime.now(timezone.utc).isoformat()
    args.output.write_text(json.dumps(log,indent=2)+'\n')


if __name__=='__main__':
    main()
