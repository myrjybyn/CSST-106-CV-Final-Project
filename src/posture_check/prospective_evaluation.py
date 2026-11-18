"""One frozen prospective evaluation; no fitting or parameter promotion here."""
import hashlib
import importlib.util
import json
from pathlib import Path
from datetime import datetime,timezone

from .calibrated import load_profile,assess_summary,require_compatible_model
from .evaluation import summarize


def evaluate(args,freeze,root,runtime,write_json,source_hashes):
    profile=load_profile()
    if not profile:raise ValueError('Calibrate and freeze a form profile first')
    plan_path=root/'docs/calibration/plan.json';plan=json.loads(plan_path.read_text())
    if profile['plan_sha256']!=hashlib.sha256(plan_path.read_bytes()).hexdigest():raise ValueError('Calibration allocation changed')
    clips=freeze['suites']['prospective']
    expected={r['id'] for r in plan['partitions']['prospective']}
    if {r['id'] for r in clips}!=expected:raise ValueError('Prospective input selection changed')
    reserved={r['participant'] for r in clips}
    for ex,config in profile['exercises'].items():
        if reserved&(set(config['fitting_participants'])|set(config['validation_participants'])):raise ValueError('Participant leakage into final test')
    if args.methods not in (None,['current']):raise ValueError('Prospective evaluation always compares uncalibrated/current decisions on shared features')
    if args.output.exists():raise ValueError('Preserve previous results; choose a new output filename')
    spec=importlib.util.spec_from_file_location('calibration_feature_collection',root/'scripts/calibration/collect_features.py')
    collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
    fp=collector.fingerprint()
    if any(c['pipeline_fingerprint']!=fp for c in profile['exercises'].values()):raise ValueError('Pose/angle pipeline differs from calibration')
    log={'started_at_utc':datetime.now(timezone.utc).isoformat(),'suite':'prospective',
         'protocol':'Four participants reserved from unused training inventory before calibration. Neither their features nor outcomes entered fitting, cross-validation or promotion. One frozen evaluation.',
         'holdout_origin':plan['holdout_origin'],'source_sha256':freeze['source_sha256'],
         'freeze_sha256':hashlib.sha256(args.freeze.read_bytes()).hexdigest(),'model_sha256':freeze['model_sha256'],
         'calibration_id':profile['calibration_id'],'runtime':runtime(args.runtime_label),
         'methods':['uncalibrated','current'],'shared_inference':True,'runs':[],
         'timing_scope':'One tracked feature pass per clip; both decision rules reuse identical features. Timing is common feature throughput, not an independent speed comparison.',
         'limitations':'16 clips / four participants, side-view squat/push-up only. Source whole-clip labels, not verified frame labels. No test-set repetition counts. Live session prefix accuracy not independently validated.'}
    write_json(args.output,log)
    for clip in clips:
        try:
            require_compatible_model(args.model,clip['exercise'])
            data=collector.collect(clip,args.model,root/'outputs/calibration/prospective_cache',fp)
            if data['frames']!=clip['metadata_frames']:raise ValueError('Decoded frame count mismatch')
            candidate=assess_summary(clip['exercise'],data['summary'],profile)
            if candidate is None:candidate=data['uncalibrated_assessment']
            for method,assessment in [('uncalibrated',data['uncalibrated_assessment']),('current',candidate)]:
                log['runs'].append({**clip,'method':method,'frames':data['frames'],
                    'assessable_frames':data['summary']['valid_frames'],'processing_seconds':data['processing_seconds'],
                    'processing_fps':data['processing_fps'],'estimated_reps':data['estimated_reps'],
                    'prediction':assessment['prediction'],'clip_assessment':assessment,
                    'source_reference':'Mendeley source whole-clip label','exit_code':0})
            write_json(args.output,log)
            print(clip['id'],'uncalibrated',data['uncalibrated_assessment']['prediction'],'current',candidate['prediction'],'reference',clip['reference_form'],flush=True)
        except Exception as e:
            log['error']={'clip_id':clip['id'],'message':str(e)};write_json(args.output,log);raise
    if source_hashes()!=freeze['source_sha256']:raise ValueError('Source/profile changed during test')
    log['summary']={m:summarize([r for r in log['runs'] if r['method']==m]) for m in log['methods']}
    log['by_exercise']={m:{ex:summarize([r for r in log['runs'] if r['method']==m and r['exercise']==ex]) for ex in ('squat','pushup')} for m in log['methods']}
    log['completed_at_utc']=datetime.now(timezone.utc).isoformat();write_json(args.output,log)
    import csv
    with args.output.with_suffix('.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');cols=['id','participant','method','exercise','reference_form','prediction','frames','assessable_frames','estimated_reps'];w.writerow(cols)
        for r in log['runs']:w.writerow([r[k] for k in cols])
    print('Completed prospective test:',args.output)
