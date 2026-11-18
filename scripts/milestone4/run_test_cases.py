"""Executable functional cases with IDs, expected/actual values and pass/fail.

Synthetic traces test software behavior, not real-video posture accuracy. Native
image/video cases use actual MediaPipe inference and OpenCV codecs.
"""
import argparse
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
import cv2
import numpy as np
from posture_check.__main__ import run, process
from posture_check.counting import RepetitionCounter
from posture_check.gui import camera_worker


def features(exercise,lower=False):
    f={'min_confidence':.95}
    if exercise=='squat':f.update(side='left',knee_angle=90 if lower else 170,hip_angle=100,trunk_lean=20)
    elif exercise=='pushup':f.update(side='left',elbow_angle=90 if lower else 170,body_alignment=180,body_inclination=90)
    elif exercise=='lunge':f.update(left_knee_angle=90 if lower else 170,right_knee_angle=100 if lower else 175,trunk_lean=10)
    else:f.update(left_arm_angle=165 if lower else 10,right_arm_angle=165 if lower else 10,ankle_width_ratio=2.5 if lower else .8,left_knee_angle=170,right_knee_angle=170)
    return f


def hold(counter,f,n=12):
    for _ in range(n):counter.update(f,1/30)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,default=ROOT/'models/pose_landmarker_lite.task')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/milestone4/functional_test_cases.json')
    args=parser.parse_args();cases=[]
    def check(id,input,condition,expected,function,hard=False,kind='synthetic movement trace'):
        try:actual=function();status='PASS' if actual==expected else 'FAIL'
        except Exception as e:actual={'exception':type(e).__name__,'message':str(e)};status='FAIL'
        cases.append({'id':id,'input':input,'condition':condition,'expected':expected,'actual':actual,'status':status,'hard_or_edge':hard,'kind':kind})
        print(id,status,flush=True)
    for i,exercise in enumerate(('squat','pushup','lunge','jumping_jack'),1):
        def cycle(exercise=exercise):
            c=RepetitionCounter(exercise)
            for lower in (False,True,False):hold(c,features(exercise,lower))
            return {'reps':c.count}
        check(f'F{i:02d}',exercise+' endpoint trace','Observed ready → lowered/open → ready, 12 frames each at 30 FPS',{'reps':1},cycle)
    def partial():
        c=RepetitionCounter('squat');hold(c,features('squat',True));hold(c,features('squat'));return {'reps':c.count}
    check('F05','squat starting at bottom','Partial starting repetition must not count',{'reps':0},partial,True)
    def gap():
        c=RepetitionCounter('pushup');hold(c,features('pushup'));hold(c,features('pushup',True));c.update(None,.8);hold(c,features('pushup'));return {'reps':c.count}
    check('F06','push-up trace with 0.8-second gap','Discard partial cycle across missing data',{'reps':0},gap,True)
    def occlusion():
        points=[SimpleNamespace(x=.5,y=.5,visibility=0.,presence=0.) for _ in range(33)]
        for index,(x,y) in {11:(.2,.3),13:(.3,.4),15:(.4,.3),23:(.5,.3),27:(.9,.3)}.items():
            points[index]=SimpleNamespace(x=x,y=y,visibility=.95,presence=.95)
        points[15].presence=.1
        estimator=SimpleNamespace(detect=lambda frame:points)
        _,r=process(np.full((1000,1000,3),80,np.uint8),estimator,'pushup',enhanced=True)
        return {'status':r['status'],'features':r['features']}
    check('F07','known push-up landmarks; wrist presence 0.1','Occluded required wrist must cause abstention',{'status':'unassessable','features':None},occlusion,True,'synthetic landmarks through frame pipeline')
    def no_camera():
        q=queue.Queue(maxsize=1)
        with patch('posture_check.gui.cv2.VideoCapture') as factory:
            factory.return_value.isOpened.return_value=False
            camera_worker(q,threading.Event(),args.model,'squat',0,True,True)
            message=q.get_nowait()
            return {'message_type':message[0],'capture_released':factory.return_value.release.call_count==1}
    check('F08','camera-open failure stub','Show camera error and release capture',{'message_type':'error','capture_released':True},no_camera,True,'camera resource integration with mocked unavailable device')
    with tempfile.TemporaryDirectory(prefix='posture-m4-cases-') as folder:
        folder=Path(folder)
        def missing():
            try:run(folder/'missing.mp4',folder/'missing_output.mp4',args.model)
            except FileNotFoundError:return {'error':'FileNotFoundError','output_exists':(folder/'missing_output.mp4').exists()}
        check('F09','nonexistent missing.mp4','Reject missing input without writing an output',{'error':'FileNotFoundError','output_exists':False},missing,True,'file pipeline')
        image=folder/'black.png';cv2.imwrite(str(image),np.zeros((160,240,3),np.uint8))
        def image_case():
            output=folder/'image_output.png';report=run(image,output,args.model)
            return {'decoded':cv2.imread(str(output)) is not None,'frames':report['frames'],'status':report['records'][0]['status'],'reps':report['repetition_count']}
        check('F10','uniform black 240×160 PNG','No person; annotated output and JSON, no form pass or invented count',{'decoded':True,'frames':1,'status':'unassessable','reps':None},image_case,True,'actual MediaPipe image inference and codec')
        def video_case():
            source=folder/'black.mp4';output=folder/'video_output.mp4'
            writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),15,(240,160))
            if not writer.isOpened():raise RuntimeError('Cannot initialize test encoder')
            for _ in range(3):writer.write(np.zeros((160,240,3),np.uint8))
            writer.release();report=run(source,output,args.model)
            capture=cv2.VideoCapture(str(output));n=0
            while capture.read()[0]:n+=1
            capture.release()
            return {'decoded_frames':n,'reps':report['repetition_count'],'all_unassessable':all(r['status']=='unassessable' for r in report['records'])}
        check('F11','three-frame black MP4 at 15 FPS','Tracked main method preserves output frames and does not invent a person/rep',{'decoded_frames':3,'reps':0,'all_unassessable':True},video_case,True,'actual MediaPipe VIDEO inference and codec')
        def same_path():
            before=hashlib.sha256(image.read_bytes()).hexdigest()
            try:run(image,image,args.model)
            except ValueError:return {'error':'ValueError','input_unchanged':hashlib.sha256(image.read_bytes()).hexdigest()==before}
        check('F12','same PNG as input and output','Protect source file against overwrite',{'error':'ValueError','input_unchanged':True},same_path,True,'file pipeline')
    result={'completed_at_utc':datetime.now(timezone.utc).isoformat(),'cases':cases,
            'limitations':'Synthetic movement/landmark cases verify software contracts, not posture accuracy. Camera availability is mocked. Physical laptop webcam acceptance is pending.',
            'passed':sum(c['status']=='PASS' for c in cases),'total':len(cases)}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    with args.output.with_suffix('.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f,lineterminator='\n');fields=['id','input','condition','expected','actual','status','hard_or_edge','kind'];writer.writerow(fields)
        for c in cases:writer.writerow([json.dumps(c[k]) if isinstance(c[k],dict) else c[k] for k in fields])
    if result['passed']!=len(cases):raise SystemExit(1)


if __name__=='__main__':main()
