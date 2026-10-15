"""Download four documented exercise clips, sample 20 REAL video frames, and label them.

Labels describe exercise action only, NOT correctness of form.
Use --no-download after manually putting the files in data/videos/.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / 'data' / 'videos'
SAMPLES = ROOT / 'data' / 'samples'
OUTPUTS = ROOT / 'outputs'

# All licenses checked via each Wikimedia Commons description page on 2026-10-15.
SOURCES = [
    {'exercise':'squat', 'filename':'squat.webm',
     'commons_filename':'Squat - exercise demonstration video.webm',
     'author':'FitnessScape', 'license':'CC BY 3.0', 'start':1.0, 'end':6.0},
    {'exercise':'pushup', 'filename':'pushup.webm',
     'commons_filename':'Muscle Strengthening at Home - Push-ups.webm',
     'author':'Centers for Disease Control and Prevention', 'license':'Public domain (US federal government work)', 'start':15.0, 'end':50.0},
    {'exercise':'lunge', 'filename':'lunge.webm',
     'commons_filename':'Forward lunge training.webm',
     'author':'Skhulile Mthiyane', 'license':'CC BY-SA 4.0', 'start':8.0, 'end':56.0},
    {'exercise':'jumping_jack', 'filename':'jumping_jack.webm',
     'commons_filename':'Jumping jacks and burpees.webm',
     'author':'Taco fleur', 'license':'CC BY-SA 4.0', 'start':2.0, 'end':12.0},
]


def fetch_video(src):
    from urllib.parse import quote
    VIDEOS.mkdir(parents=True, exist_ok=True)
    path = VIDEOS / src['filename']
    if path.exists() and path.stat().st_size > 4096:
        print(f'[cached] {path.name}: {path.stat().st_size} bytes')
        return path
    url = 'https://commons.wikimedia.org/wiki/Special:Redirect/file/' + quote(src['commons_filename'], safe='')
    print(f'[downloading] {src["exercise"]} from {url}', flush=True)
    try:
        with requests.get(url, headers={'User-Agent': 'AcademicExerciseCVSpike/1.0 (student research; contact via Wikimedia Commons)'},
                          stream=True, timeout=(20, 120)) as r:
            r.raise_for_status()
            if 'text/html' in r.headers.get('content-type','').lower():
                raise RuntimeError('Server returned HTML instead of video. Download manually from source page.')
            tmp = path.with_suffix('.part')
            with tmp.open('wb') as f:
                for chunk in r.iter_content(1024 * 128):
                    if chunk: f.write(chunk)
            if tmp.stat().st_size < 4096:
                raise RuntimeError('Downloaded file too small to contain video')
            tmp.replace(path)
    except Exception as e:
        raise RuntimeError(f'Could not download {src["exercise"]}. Open https://commons.wikimedia.org/wiki/File:{quote(src["commons_filename"].replace(" ","_"))} and manually save the ORIGINAL video as {path}. Underlying error: {e}') from e
    return path


def extract(src, path, count=5):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f'OpenCV could not read {path}; check WebM/VP9 codec support, or convert it to MP4/H.264.')
    fps = cap.get(cv2.CAP_PROP_FPS)
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = (nframes / fps) if (fps > 0 and nframes > 0) else None
    start, end = src['start'], src['end']
    if duration:
        end = min(end, max(0.2, duration - 0.2))
        start = min(start, end * .4)
    if end <= start:
        cap.release()
        raise RuntimeError(f'Bad video time range: {path}, duration={duration}')
    times = np.linspace(start, end, count)
    rows = []
    for i, t in enumerate(times, start=1):
        cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000)
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.release()
            raise RuntimeError(f'Cannot extract {path} at t={t:.2f}s. Re-encode the clip as MP4/H.264.')
        imgpath = SAMPLES / f'{src["exercise"]}_{i:02}.jpg'
        # No hallucinated posture labels: these are coarse action/video labels.
        h, w = frame.shape[:2]
        scale = min(1.0, 960.0 / max(h, w))
        if scale < 1: frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        if not cv2.imwrite(str(imgpath), frame, [cv2.IMWRITE_JPEG_QUALITY, 89]):
            raise RuntimeError(f'Could not save {imgpath}')
        rows.append({'filename': imgpath.name, 'exercise_label':src['exercise'],
             'form_correctness':'UNVERIFIED', 'source_video':src['filename'],
             'source_time_s':round(float(t),3),
             'source_page':'https://commons.wikimedia.org/wiki/File:' + src['commons_filename'].replace(' ','_'),
             'author':src['author'], 'license':src['license'],
             'label_basis':'video action/topic; manual visual review still required'})
    cap.release()
    return rows


def contact_sheet(rows):
    bg='#0b1220'; tilebg='#162238'; main='#f8fafc'; muted='#b8c7da'
    w=275; picture_h=180; caption_h=63; margin=24; title_h=98; cols=5; nrows=4; gap=11
    width=margin*2 + cols*w + (cols-1)*gap
    height=title_h + margin + nrows*(picture_h+caption_h) + (nrows-1)*gap + margin+45
    out=Image.new('RGB', (width,height), bg)
    draw=ImageDraw.Draw(out)
    def font(size, bold=False):
        paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
        for p in paths:
            try:return ImageFont.truetype(p,size)
            except OSError:pass
        return ImageFont.load_default()
    draw.text((margin,17),'POSTURE CHECK  |  DATA EVIDENCE',font=font(29,True),fill=main)
    draw.text((margin,58),'20 genuine extracted video frames  •  5 per exercise  •  action labels only',font=font(16),fill=muted)
    for j,row in enumerate(rows):
        r,c=divmod(j,cols)
        x=margin+c*(w+gap); y=title_h+margin+r*(picture_h+caption_h+gap)
        draw.rounded_rectangle((x,y,x+w,y+picture_h+caption_h), radius=12,fill=tilebg)
        with Image.open(SAMPLES / row['filename']) as raw:
            img=ImageOps.contain(raw.convert('RGB'),(w-12,picture_h-12),method=Image.Resampling.LANCZOS)
            px=x+(w-img.width)//2;py=y+(picture_h-img.height)//2
            out.paste(img,(px,py))
        lab=row['exercise_label'].replace('_',' ').upper()
        draw.text((x+11,y+picture_h+5),f'{j+1:02d}  {lab}',font=font(16,True),fill=main)
        draw.text((x+11,y+picture_h+33),f't={row["source_time_s"]:.1f}s  •  Form: UNVERIFIED',font=font(12),fill=muted)
    draw.text((margin,height-37),'Sources + licenses + per-frame timestamps: data/labels.csv  |  Review every frame before submission.',font=font(13),fill=muted)
    path=OUTPUTS/'contact_sheet_20.png'
    out.save(path, optimize=True)
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-download', action='store_true', help='Use videos already present in data/videos instead of downloading')
    args=parser.parse_args()
    for folder in [VIDEOS,SAMPLES,OUTPUTS]:folder.mkdir(exist_ok=True,parents=True)
    rows=[]
    for src in SOURCES:
        path=(VIDEOS/src['filename']) if args.no_download else fetch_video(src)
        if not path.exists():
            raise FileNotFoundError(f'Missing video: {path} (download from its Wikimedia Commons source page)')
        rows += extract(src,path,5)
        print(f'[frames] {src["exercise"]}: 5 saved')
    assert len(rows)==20
    with (ROOT/'data'/'labels.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    sheet=contact_sheet(rows)
    print(f'SUCCESS: {len(rows)} frame samples; labels.csv; {sheet}')
    print('NEXT: open the sheet to visually check every action label, and replace any off-action frames.')

if __name__=='__main__': main()
