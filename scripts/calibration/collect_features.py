"""Extract tracked angle summaries from fit/validation only; resume per-clip caches."""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import cv2
from posture_check import __main__ as pipeline
from posture_check import exercises,features,baseline
from posture_check.pose import PoseEstimator
from posture_check.temporal import TemporalAnalyzer
from posture_check.form_features import COLUMNS,summarize_angles


def fingerprint():
    import posture_check.pose as pose,posture_check.temporal as temporal
    import posture_check.preprocessing as preprocessing,posture_check.quality as quality,posture_check.counting as counting
    objects=[pose.PoseEstimator,pipeline.process,features.angle,features.extract,baseline.assess,
             exercises.extract_for_exercise,exercises.extract_pushup,exercises.extract_lunge,exercises.extract_jack,exercises._points,
             exercises.assess_for_exercise,temporal.TemporalAnalyzer,preprocessing.active_region,preprocessing._paired_bounds,
             preprocessing.restore_landmarks,quality.explain,counting.RepetitionCounter,summarize_angles]
    return hashlib.sha256('\n'.join(inspect.getsource(x) for x in objects).encode()).hexdigest()


def collect(clip,model,cache_dir,pipeline_hash):
    source=ROOT/'data/raw'/clip['file'];cache=cache_dir/(clip['id']+'.json.gz')
    model_hash=hashlib.sha256(model.read_bytes()).hexdigest()
    if cache.exists():
        with gzip.open(cache,'rt') as f:r=json.load(f)
        if r['input_sha256']!=clip['sha256'] or r['pipeline_fingerprint']!=pipeline_hash or r['model_sha256']!=model_hash:raise ValueError('Stale feature cache')
        return r
    if hashlib.sha256(source.read_bytes()).hexdigest()!=clip['sha256']:raise ValueError('Input changed')
    capture=cv2.VideoCapture(str(source));estimator=None
    try:
        if not capture.isOpened():raise ValueError('Cannot decode '+clip['id'])
        fps=capture.get(cv2.CAP_PROP_FPS);expected=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        estimator=PoseEstimator(model,video=True,fps=fps);analyzer=TemporalAnalyzer(clip['exercise'],fps)
        rows=[];vectors=[];seconds=0.0;started=time.perf_counter()
        while True:
            ok,frame=capture.read()
            if not ok:break
            tick=time.perf_counter()
            _,raw=pipeline.process(frame,estimator,clip['exercise'],enhanced=True)
            r=analyzer.update(raw);rows.append(r);seconds+=time.perf_counter()-tick
            if r['features'] is not None:vectors.append([r['features'][x] for x in COLUMNS[clip['exercise']]])
        if len(rows)!=expected or not rows:raise ValueError('Frame count mismatch')
        data={**clip,'input_sha256':clip['sha256'],'model_sha256':model_hash,'pipeline_fingerprint':pipeline_hash,
              'fps':fps,'frames':len(rows),'processing_seconds':seconds,'processing_fps':len(rows)/seconds,
              'decode_and_processing_fps':len(rows)/(time.perf_counter()-started),'summary':summarize_angles(clip['exercise'],vectors,len(rows)),
              'uncalibrated_assessment':pipeline.summarize_for_exercise(rows,clip['exercise']),
              'estimated_reps':analyzer.count,'columns':list(COLUMNS[clip['exercise']]),'angle_vectors':vectors,
              'measured_at_utc':datetime.now(timezone.utc).isoformat()}
        cache_dir.mkdir(parents=True,exist_ok=True)
        temporary=cache.with_suffix('.tmp')
        with gzip.open(temporary,'wt') as f:json.dump(data,f)
        temporary.replace(cache);return data
    finally:
        capture.release()
        if estimator is not None:estimator.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise',choices=('squat','pushup'),required=True)
    args=parser.parse_args();plan=json.loads((ROOT/'docs/calibration/plan.json').read_text())
    clips=[r for split in ('fit','validation') for r in plan['partitions'][split] if r['exercise']==args.exercise]
    fp=fingerprint();results=[]
    for i,clip in enumerate(clips,1):
        r=collect(clip,ROOT/'models/pose_landmarker_lite.task',ROOT/'outputs/calibration/cache',fp)
        results.append({k:v for k,v in r.items() if k!='angle_vectors'})
        (ROOT/f'docs/calibration/{args.exercise}_features.json').write_text(json.dumps({'pipeline_fingerprint':fp,'clips':results},indent=2)+'\n')
        print(args.exercise,i,'/',len(clips),clip['id'],r['summary']['valid_frames'],'/',r['frames'],'eligible',r['summary']['eligible'],flush=True)
    print('COMPLETE',args.exercise,flush=True)


if __name__=='__main__':main()
