"""Frozen checkpoint-four evaluation: held-out side views or known laptop clips.

Prepare once before evaluation, then run without changing thresholds. A laptop
run uses the four known clips solely for matching checkpoint 3's speed workload.
"""
import argparse
from contextlib import ExitStack
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import platform
import subprocess
import time

import cv2
from posture_check import __main__ as current
from posture_check.evaluation import checkpoint3, summarize

ROOT=Path(__file__).resolve().parents[1]
SUITES=('prospective','heldout','benchmark')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');temporary.replace(path)


def source_hashes():
    paths=sorted((ROOT/'src').rglob('*.py'))+[ROOT/'run.py',ROOT/'app.py',ROOT/'requirements.txt']
    paths += [p for p in (ROOT/'config/form_rules.json', ROOT/'docs/calibration/plan.json') if p.is_file()]
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}


def suite_rows():
    folder=ROOT/'data/prepared/mendeley'
    partitions={}
    for split in ('train','val','test'):
        with (folder/f'{split}_videos.csv').open(newline='',encoding='utf-8') as stream:
            partitions[split]=list(csv.DictReader(stream))
    ids={s:{r['participant_id'] for r in rows} for s,rows in partitions.items()}
    if any(ids[a]&ids[b] for a,b in (('train','val'),('train','test'),('val','test'))):
        raise ValueError('Participant leakage across partitions')
    heldout=[]
    for r in partitions['test']:
        if r['split']!='test':raise ValueError('Test manifest contains a non-test row')
        if r['exercise'] not in ('squat','pushup') or '/side/' not in r['relative_video_path']:continue
        if r['requires_review']!='NO':raise ValueError('Unreviewed test label')
        heldout.append({'id':Path(r['relative_video_path']).stem,'file':'mendeley/'+r['relative_video_path'],
                        'exercise':r['exercise'],'participant':r['participant_id'],'split':'test',
                        'condition':'source side view; full original video','reference_form':r['form_label'],
                        'reference_reps':None,'reference_source':'Mendeley source whole-clip label'})
    benchmark=[]
    manifest=json.loads((ROOT/'docs/phase3/test_manifest.json').read_text())
    for r in manifest:
        relative=Path(r['file']).relative_to('data/raw')
        benchmark.append({'id':r['id'],'file':str(relative),'exercise':r['exercise'],'split':'known_regression',
                          'reference_form':r['ground_truth_form'],'reference_reps':r['ground_truth_reps'],
                          'sha256':r['sha256'],'condition':'previously inspected YouTube excerpt',
                          'reference_source':'User-supplied after checkpoint 3 predictions; not independently expert verified'})
    if not heldout or len({r['file'] for r in heldout})!=len(heldout):raise ValueError('Invalid held-out selection')
    prospective=[]
    plan_path=ROOT/'docs/calibration/plan.json'
    if plan_path.is_file():
        plan=json.loads(plan_path.read_text())
        prospective=[{**r,'split':'prospective_reserved','condition':'side view; prospective participant holdout','reference_reps':None,'reference_source':'Mendeley source whole-clip label'} for r in plan['partitions']['prospective']]
    return {'heldout':heldout,'benchmark':benchmark,'prospective':prospective}


def checked_path(data_root,relative):
    path=(data_root/relative).resolve()
    if not path.is_relative_to(data_root.resolve()) or not path.is_file():
        raise ValueError('Missing or invalid input: '+relative)
    return path


def prepare(args):
    suites=suite_rows()
    if args.suite=='prospective' and not (ROOT/'config/form_rules.json').is_file():
        raise ValueError('Fit and validation-gate the profile before preparing the final test freeze')
    for rows in suites.values():
        for row in rows:
            path=checked_path(args.data_root,row['file'])
            digest=sha(path)
            if row.get('sha256',digest)!=digest:raise ValueError('Known clip checksum changed')
            row['sha256']=digest
            capture=cv2.VideoCapture(str(path))
            try:
                if not capture.isOpened():raise ValueError('Cannot open '+str(path))
                row['metadata_frames']=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
                row['fps']=capture.get(cv2.CAP_PROP_FPS)
            finally:capture.release()
    commit=subprocess.check_output(['git','rev-parse','cp3-core^{commit}'],cwd=ROOT,text=True).strip()
    with checkpoint3(ROOT,commit) as (_,reference_hashes):pass
    freeze={'prepared_at_utc':datetime.now(timezone.utc).isoformat(),
            'protocol':'Supported side-view subject-separated Mendeley test clips. No tuning after evaluation. Known Phase 3 clips are a separate regression/speed workload.',
            'source_sha256':source_hashes(),'model_sha256':sha(args.model),
            'checkpoint3_commit':commit,'checkpoint3_source_sha256':reference_hashes,'suites':suites,
            'manifest_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'data/prepared/mendeley').glob('*_videos.csv'))}}
    if args.freeze.exists():raise ValueError('Freeze already exists; use a new path to preserve provenance')
    write_json(args.freeze,freeze)
    print('Prepared freeze:',args.freeze,'held-out clips:',len(suites['heldout']))


def runtime(label):
    info={'location':label,'python':platform.python_version(),'platform':platform.platform(),
          'cpu':platform.processor(),'logical_cpus':os.cpu_count(),'dependencies':{}}
    cpu_path=Path('/proc/cpuinfo')
    if cpu_path.exists():
        info['cpu']=next((r.split(':',1)[1].strip() for r in cpu_path.read_text().splitlines() if r.startswith('model name')),info['cpu'])
    for name in ('mediapipe','numpy','opencv-contrib-python','pillow'):
        try:info['dependencies'][name]=version(name)
        except PackageNotFoundError:info['dependencies'][name]=None
    if platform.system()=='Windows':
        query=("$c=Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1; "
               "$m=Get-CimInstance -ClassName Win32_ComputerSystem; "
               "[pscustomobject]@{cpu=$c.Name;ram_gib=[math]::Round($m.TotalPhysicalMemory/1GB,2);"
               "power_scheme=(powercfg /getactivescheme | Out-String).Trim()} | ConvertTo-Json")
        try:
            response=subprocess.run(['powershell','-NoProfile','-Command',query],capture_output=True,text=True,timeout=20,check=True)
            info['windows_hardware']=json.loads(response.stdout)
            if not info['windows_hardware'].get('cpu') or not info['windows_hardware'].get('ram_gib'):
                info['hardware_capture_status']='incomplete; supply CPU/RAM manually'
        except (OSError,ValueError,subprocess.SubprocessError):info['hardware_capture_status']='unavailable; supply CPU/RAM/power mode manually'
    return info


def evaluate(args):
    freeze=json.loads(args.freeze.read_text())
    if source_hashes()!=freeze['source_sha256']:raise ValueError('Evaluation source changed since freeze')
    if sha(args.model)!=freeze['model_sha256']:raise ValueError('Model checksum changed')
    for name,digest in freeze['manifest_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Dataset split manifest changed')
    clips=freeze['suites'][args.suite]
    if args.suite=='prospective':
        for c in clips:
            if sha(checked_path(args.data_root,c['file']))!=c['sha256']:raise ValueError('Prospective input checksum changed')
        from posture_check.prospective_evaluation import evaluate as evaluate_prospective
        return evaluate_prospective(args,freeze,ROOT,runtime,write_json,source_hashes)
    methods=args.methods or (['cp3','current'] if args.suite=='heldout' else ['current'])
    if len(methods)!=len(set(methods)):raise ValueError('Duplicate methods')
    for c in clips:
        if sha(checked_path(args.data_root,c['file']))!=c['sha256']:raise ValueError('Input checksum changed')
    if args.output.exists():raise ValueError('Result already exists; use a new output path')
    log={'started_at_utc':datetime.now(timezone.utc).isoformat(),'suite':args.suite,'runtime':runtime(args.runtime_label),
         'freeze_sha256':sha(args.freeze),'source_sha256':freeze['source_sha256'],'model_sha256':freeze['model_sha256'],
         'checkpoint3_commit':freeze['checkpoint3_commit'],'methods':methods,'runs':[],
         'timing_scope':'CPU pose inference, preprocessing, rules and temporal updates; excludes decoding, drawing, encoding and model initialization. Decode-plus-processing throughput logged separately.',
         'limitations':'Side-view squat and push-up only. The original heldout suite has already been exposed and is now regression data; prospective is the new reserved participant test. Whole-clip form labels are not frame labels. Repetition references unavailable for held-out videos. Known benchmark clips are not new held-out evidence. Single timing pass.'}
    write_json(args.output,log)
    with ExitStack() as stack:
        reference=None
        if 'cp3' in methods:
            reference,hashes=stack.enter_context(checkpoint3(ROOT,freeze['checkpoint3_commit']))
            if hashes!=freeze['checkpoint3_source_sha256']:raise ValueError('Checkpoint 3 snapshot mismatch')
        for clip in clips:
            for method in methods:
                capture=cv2.VideoCapture(str(checked_path(args.data_root,clip['file'])));estimator=None
                try:
                    if not capture.isOpened():raise ValueError('Cannot decode '+clip['id'])
                    fps=capture.get(cv2.CAP_PROP_FPS)
                    if not 0<fps<1000:raise ValueError('Invalid FPS')
                    pipeline=current if method=='current' else reference
                    started=time.perf_counter()
                    estimator=(pipeline.PoseEstimator(args.model,video=True,fps=fps) if method=='current' else pipeline.PoseEstimator(args.model))
                    initialization=time.perf_counter()-started
                    analyzer=pipeline.TemporalAnalyzer(clip['exercise'],fps)
                    rows=[];seconds=0.;started=time.perf_counter()
                    while True:
                        ok,frame=capture.read()
                        if not ok:break
                        tick=time.perf_counter()
                        if method=='current':_,raw=pipeline.process(frame,estimator,clip['exercise'],enhanced=True)
                        else:_,raw=pipeline.process(frame,estimator,clip['exercise'])
                        rows.append(analyzer.update(raw));seconds+=time.perf_counter()-tick
                    elapsed=time.perf_counter()-started
                    if not rows or len(rows)!=clip['metadata_frames']:raise ValueError('Decoded frame count mismatch: '+clip['id'])
                    assessment=(pipeline.summarize_for_exercise(rows,clip['exercise'],calibrated=True) if method=='current' else pipeline.summarize_for_exercise(rows,clip['exercise']))
                    result={**clip,'method':method,'frames':len(rows),'assessable_frames':sum(r['features'] is not None for r in rows),
                            'pose_frames':sum(r['pose_detected'] for r in rows),'prediction':assessment['prediction'],
                            'clip_assessment':assessment,'estimated_reps':analyzer.count,'processing_seconds':seconds,
                            'processing_fps':len(rows)/seconds,'decode_and_processing_fps':len(rows)/elapsed,
                            'model_initialization_seconds':initialization,'exit_code':0}
                    log['runs'].append(result);write_json(args.output,log)
                    print(clip['id'],method,assessment['prediction'],f"coverage {result['assessable_frames']}/{len(rows)}",'reps',analyzer.count,flush=True)
                except Exception as error:
                    log['error']={'clip_id':clip['id'],'method':method,'message':str(error)};write_json(args.output,log);raise
                finally:
                    capture.release()
                    if estimator is not None:estimator.close()
    if source_hashes()!=freeze['source_sha256']:raise ValueError('Source changed during evaluation')
    log['summary']={method:summarize([r for r in log['runs'] if r['method']==method]) for method in methods}
    log['by_exercise']={method:{exercise:summarize([r for r in log['runs'] if r['method']==method and r['exercise']==exercise]) for exercise in sorted({c['exercise'] for c in clips})} for method in methods}
    log['completed_at_utc']=datetime.now(timezone.utc).isoformat();write_json(args.output,log)
    csv_path=args.output.with_suffix('.csv')
    with csv_path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream,lineterminator='\n');columns=['id','method','exercise','reference_form','prediction','frames','assessable_frames','estimated_reps','reference_reps','processing_fps']
        writer.writerow(columns);writer.writerows([[r.get(c) for c in columns] for r in log['runs']])
    print('Completed:',args.output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--suite',choices=SUITES,default='prospective')
    parser.add_argument('--methods',nargs='+',choices=('cp3','current'))
    parser.add_argument('--data-root',type=Path,default=ROOT/'data/raw')
    parser.add_argument('--model',type=Path,default=ROOT/'models/pose_landmarker_lite.task')
    parser.add_argument('--freeze',type=Path,default=ROOT/'docs/calibration/evaluation_freeze.json')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/calibration/prospective_results.json')
    parser.add_argument('--runtime-label',choices=('cloud','laptop'),default='cloud')
    args=parser.parse_args()
    try:
        if args.prepare:prepare(args)
        else:evaluate(args)
    except (ValueError,FileNotFoundError,RuntimeError,subprocess.CalledProcessError) as error:parser.exit(1,f'Error: {error}\n')


if __name__=='__main__':main()
