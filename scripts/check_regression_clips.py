"""One-pass regression check on the previously inspected Phase 3 clips.

These known clips informed earlier failure analysis. This is NOT a fresh held-out
accuracy test. Do not adjust parameters after inspecting these results. Original
Phase 3 logs/reports remain historical and are never rewritten by this script.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
import time
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import cv2
from posture_check.__main__ import process
from posture_check.pose import PoseEstimator
from posture_check.temporal import TemporalAnalyzer
from posture_check.exercises import summarize_for_exercise


def source_hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'src/posture_check').glob('*.py'))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=ROOT,help='Checkout containing data/raw/phase3_user/')
    parser.add_argument('--model',type=Path,default=ROOT/'models/pose_landmarker_lite.task')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/development/phase3_regression.json')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'docs/phase3/test_manifest.json').read_text())
    annotations=json.loads((ROOT/'docs/phase3/reference_annotations.json').read_text())
    original=json.loads((ROOT/'docs/phase3/test_log.json').read_text())
    old={r['clip_id']:r for r in original['runs'] if r['method']=='main'}
    paths=[]
    for c in manifest:
        p=(args.source_root/c['file']).resolve()
        if not p.is_relative_to(args.source_root.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=c['sha256']:
            raise ValueError('Regression input mismatch: '+c['id'])
        paths.append(p)
    log={'purpose':'Previously inspected regression set; not independent held-out accuracy; no threshold tuning on these outputs.',
         'started_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':source_hashes(),
         'runtime':{'python':platform.python_version(),'platform':platform.platform(),'cpu':platform.processor(),'logical_cpus':os.cpu_count()},
         'model_sha256':hashlib.sha256(args.model.read_bytes()).hexdigest(),
         'reference_origin':annotations['source'],'reference_limitations':annotations['timing'],'runs':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for c,path in zip(manifest,paths):
        capture=cv2.VideoCapture(str(path));estimator=None
        try:
            if not capture.isOpened():raise ValueError('Cannot decode '+str(path))
            fps=capture.get(cv2.CAP_PROP_FPS)
            estimator=PoseEstimator(args.model,video=True,fps=fps)
            analyzer=TemporalAnalyzer(c['exercise'],fps)
            rows=[];padding=0;seconds=0.0;started=time.perf_counter()
            while True:
                ok,frame=capture.read()
                if not ok:break
                tick=time.perf_counter()
                _,raw=process(frame,estimator,c['exercise'],enhanced=True)
                padding+=int(raw['padding_removed'])
                rows.append(analyzer.update(raw));seconds+=time.perf_counter()-tick
            if len(rows)!=c['metadata_frames']:raise ValueError('Frame count mismatch')
            expected=annotations['clips'][c['id']]
            result={'clip_id':c['id'],'input_sha256':c['sha256'],'frames':len(rows),
                    'processing_seconds':seconds,'processing_fps':len(rows)/seconds,
                    'decode_and_processing_fps':len(rows)/(time.perf_counter()-started),
                    'timing_scope':'CPU inference, preprocessing, rules and counting; no drawing or encoding',
                    'reference_reps':expected['completed_reps'],'reference_form':expected['form_label'],
                    'previous_reps':old[c['id']]['repetition_count'],'estimated_reps':analyzer.count,
                    'previous_assessable_frames':old[c['id']]['assessable_frames'],
                    'assessable_frames':sum(r['features'] is not None for r in rows),
                    'padding_removed_frames':padding,'clip_assessment':summarize_for_exercise(rows,c['exercise']),
                    'previous_clip_prediction':old[c['id']]['clip_assessment']['prediction']}
            log['runs'].append(result)
            args.output.write_text(json.dumps(log,indent=2)+'\n')
            print(c['id'],'previous',result['previous_reps'],'candidate',analyzer.count,'reference',expected['completed_reps'],flush=True)
        finally:
            capture.release()
            if estimator is not None:estimator.close()
    if source_hashes()!=log['source_sha256']:raise ValueError('Source changed during regression evaluation')
    n=len(log['runs'])
    log['summary']={
        'processing_fps':sum(r['frames'] for r in log['runs'])/sum(r['processing_seconds'] for r in log['runs']),
        'previous_count_mae':sum(abs(r['previous_reps']-r['reference_reps']) for r in log['runs'])/n,
        'candidate_count_mae':sum(abs(r['estimated_reps']-r['reference_reps']) for r in log['runs'])/n,
        'previous_form_agreement':sum(r['previous_clip_prediction']==r['reference_form'] for r in log['runs'])/n,
        'candidate_form_agreement':sum(r['clip_assessment']['prediction']==r['reference_form'] for r in log['runs'])/n}
    log['completed_at_utc']=datetime.now(timezone.utc).isoformat()
    args.output.write_text(json.dumps(log,indent=2)+'\n')


if __name__=='__main__':
    main()
