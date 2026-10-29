"""Extract real rejection examples without changing the frozen methods."""
from collections import Counter
from pathlib import Path
import json,math,sys
import cv2
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from posture_check.pose import PoseEstimator
from posture_check.features import angle


def diagnose(points, mode, width, height):
    if not points:
        return 'No pose output', 'MediaPipe returned no landmarks; no anatomical assessment possible.'
    groups={'pushup':[(11,13,15,23,27),(12,14,16,24,28)],
            'lunge':[(11,12,23,24,25,26,27,28)],
            'jumping_jack':[(11,12,15,16,23,24,25,26,27,28)]}[mode]
    reasons=[]
    for ids in groups:
        selected=[points[i] for i in ids]
        if any(not math.isfinite(p.visibility) or not math.isfinite(p.presence) or min(p.visibility,p.presence)<.5 for p in selected):
            reasons.append('Joint confidence');continue
        if any(not(0<=p.x<=1 and 0<=p.y<=1) for p in selected):
            reasons.append('Outside image');continue
        p={i:(points[i].x*width,points[i].y*height) for i in ids}
        if mode=='pushup':
            s,e,w,h,a=(p[i] for i in ids)
            if math.dist(s,h)+math.dist(h,a)<.35*max(width,height):
                reasons.append('Body-size gate');continue
            try:inc=angle(s,h,(h[0],h[1]-height))
            except ValueError:reasons.append('Degenerate geometry');continue
            if not 55<=inc<=125:reasons.append('Orientation gate');continue
        else:
            chains=[math.dist(p[s],p[h])+math.dist(p[h],p[k])+math.dist(p[k],p[a]) for s,h,k,a in [(11,23,25,27),(12,24,26,28)]]
            if mode=='jumping_jack' and math.dist(p[11],p[12])<.04*width:
                reasons.append('Shoulder-width gate');continue
            if min(chains)<.35*height:
                reasons.append('Body-size gate');continue
        reasons.append('Geometry/other gate')
    if all(reason=='Joint confidence' for reason in reasons):
        return 'Joint confidence', 'Required joints below 0.5 visibility/presence; inferred occlusion, cropping or small subject may contribute.'
    if all(reason=='Body-size gate' for reason in reasons):
        return 'Body-size gate', 'Projected body chain below the fixed minimum relative to full frame; padding/zoom may affect this ratio.'
    if all(reason=='Outside image' for reason in reasons):
        return 'Out-of-frame joints', 'Required predicted joints lie outside the image. Cropping or erroneous localization may contribute.'
    if 'Body-size gate' in reasons and 'Joint confidence' in reasons:
        return 'Size/confidence gates', 'One side fails required-joint confidence and the other fails the body-size gate. Padding/subject scale are candidate causes.'
    return 'Mixed geometric gates', 'Per-side/group rejection: '+', '.join(reasons)+'. Exact visibility and framing cause requires manual review.'


def main():
    folder=ROOT/'reports/phase3';manifest=json.loads((folder/'test_manifest.json').read_text());log=json.loads((folder/'test_log.json').read_text())
    if 'completed_at_utc' not in log:raise ValueError('Wait for all test runs')
    derived=[]
    for run in log['runs']:
        report=json.loads(Path(run['output']).with_suffix('.mp4.json').read_text())
        rows=report['records'];actions={'rule_pass','rule_flag'}
        item=dict(run)
        item['actionable_status_flips']=sum(a['status'] in actions and b['status'] in actions and a['status']!=b['status'] for a,b in zip(rows,rows[1:]))
        derived.append(item)
    (folder/'comparison_summary.json').write_text(json.dumps(derived,indent=2))
    gallery=folder/'failures';gallery.mkdir(exist_ok=True)
    examples=[];estimator=PoseEstimator(ROOT/'models/pose_landmarker_lite.task')
    try:
        for clip in manifest:
            if clip['exercise']=='squat':continue
            mode=clip['exercise'];run=next(r for r in log['runs'] if r['clip_id']==clip['id'] and r['method']=='main')
            records=json.loads(Path(run['output']).with_suffix('.mp4.json').read_text())['records']
            failed=[i for i,r in enumerate(records) if r['status']=='unassessable']
            quota=4 if mode=='pushup' else 3
            chosen=[]
            for k in range(quota):
                candidate=failed[round(k*(len(failed)-1)/max(quota-1,1))]
                if candidate not in chosen:chosen.append(candidate)
            source=cv2.VideoCapture(str(ROOT/clip['file']));output=cv2.VideoCapture(run['output'])
            for index in chosen:
                source.set(cv2.CAP_PROP_POS_FRAMES,index);ok,frame=source.read();assert ok
                output.set(cv2.CAP_PROP_POS_FRAMES,index);ok,annotated=output.read();assert ok
                points=estimator.detect(frame)
                cause,description=diagnose(points,mode,frame.shape[1],frame.shape[0])
                if bool(points)!=records[index]['pose_detected']:
                    cause,description='Pose instability','Post-hoc replay differs from original run; original rejection is recorded, root cause uncertain.'
                number=len(examples)+1;path=gallery/f'failure_{number:02d}.jpg'
                assert cv2.imwrite(str(path),annotated,[cv2.IMWRITE_JPEG_QUALITY,90])
                examples.append({'id':number,'clip':mode,'frame_index':index,'time_seconds':index/clip['fps'],'category':cause,'description':description,'original_status':records[index]['status'],'original_pose_output':records[index]['pose_detected'],'file':str(path.relative_to(folder))})
            source.release();output.release()
    finally:estimator.close()
    if len(examples)<10:raise ValueError('Fewer than ten genuine rejection frames; do not fabricate examples')
    examples.sort(key=lambda r:(r['category'],r['clip'],r['frame_index']))
    (folder/'failure_manifest.json').write_text(json.dumps({'definition':'Ten observed technical rejection frames, not ten independent clips or proven classification errors. Original main-run outputs are shown; causes use post-hoc landmark gate checks.','examples':examples},indent=2))
    print('Failure groups:',dict(Counter(r['category'] for r in examples)))
    sheet=Image.new('RGB',(1200,math.ceil(len(examples)/3)*245),'white');draw=ImageDraw.Draw(sheet)
    for slot,row in enumerate(examples):
        image=Image.open(folder/row['file']);image.thumbnail((390,200));x=(slot%3)*400;y=(slot//3)*245
        sheet.paste(image,(x,y+38));draw.text((x+4,y+2),f"F{row['id']:02d}: {row['clip']} {row['time_seconds']:.2f}s",fill='black')
        draw.text((x+4,y+19),row['category'],fill='black')
    sheet.save(folder/'failure_contact_sheet.jpg')
    for row in derived:print(row['clip_id'],row['method'],'FPS',round(row['processing_fps'],2),'state changes',row['status_changes'],'actionable flips',row['actionable_status_flips'],'phase changes',row['phase_changes'],'reps',row['repetition_count'])

if __name__=='__main__':main()
