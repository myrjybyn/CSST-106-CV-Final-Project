"""Milestone-1 feasibility spike: read FIVE real frames, grayscale, blur, Canny edges.

This tests reproducible image loading and classical CV preprocessing, NOT posture accuracy.
Outputs a genuine five-panel results image, to use as a screenshot AFTER running on source data.
"""
from __future__ import annotations
import csv
from pathlib import Path
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT=Path(__file__).resolve().parents[1]
SAMPLES=ROOT/'data'/'samples'
OUT=ROOT/'outputs'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    labels=ROOT/'data'/'labels.csv'
    if not labels.is_file():
        raise FileNotFoundError('No data/labels.csv. First run: python scripts/prepare_data.py')
    with labels.open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    # Five images, covering all four exercise classes.
    picks=[]
    for exercise,i in [('squat',1),('pushup',1),('lunge',1),('jumping_jack',1),('squat',3)]:
        matching=[r for r in rows if r['exercise_label']==exercise]
        if len(matching)<i:raise ValueError(f'Insufficient images for {exercise}')
        picks.append(matching[i-1])
    images=[]
    for row in picks:
        src=SAMPLES/row['filename']
        frame=cv2.imread(str(src))
        if frame is None:raise RuntimeError(f'cv2.imread failed for {src}')
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        blurred=cv2.GaussianBlur(gray,(5,5),0)
        edges=cv2.Canny(blurred,50,150)
        dest=OUT/f'edges_{src.stem}.png'
        if not cv2.imwrite(str(dest),edges):raise RuntimeError(f'Cannot save {dest}')
        images.append((row,cv2.cvtColor(frame,cv2.COLOR_BGR2RGB),edges))
        print(f'{src.name}: {frame.shape[1]}x{frame.shape[0]}, edge pixels={(edges>0).sum()} -> {dest.name}')
    w=490; tile_h=415; margin=26; gap=12; title_h=83
    canvas=Image.new('RGB',(margin*2+5*w+4*gap,title_h+tile_h+margin+60),'#0b1220')
    d=ImageDraw.Draw(canvas)
    def font(n,bold=False):
        try:return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',n)
        except OSError:return ImageFont.load_default()
    d.text((margin,16),'FEASIBILITY SPIKE  |  FIVE REAL EXERCISE FRAMES',font=font(25,True),fill='white')
    d.text((margin,52),'INPUT (left)  →  Gaussian blur + Canny edge detection (right)',font=font(17),fill='#b8c7da')
    for i,(row,rgb,edges) in enumerate(images):
        x=margin+i*(w+gap); y=title_h
        d.rounded_rectangle((x,y,x+w,y+tile_h),radius=10,fill='#17253a')
        original=ImageOps.contain(Image.fromarray(rgb),(w//2-12,310))
        processed=ImageOps.contain(Image.fromarray(edges).convert('RGB'),(w//2-12,310))
        # Consistent split rendering across 5 inputs.
        canvas.paste(original,(x+6+(w//2-original.width)//2,y+10+(310-original.height)//2))
        canvas.paste(processed,(x+w//2+6+(w//2-processed.width)//2,y+10+(310-processed.height)//2))
        d.text((x+12,y+334),f'{i+1:02d}  {row["exercise_label"].replace("_"," ").title()}',font=font(19,True),fill='white')
        d.text((x+12,y+366),f'{row["filename"]}  |  {float(row["source_time_s"]):.1f}s',font=font(14),fill='#b8c7da')
    d.text((margin,title_h+tile_h+23),'Operation output only — does not classify exercise quality or measure pose estimation accuracy.',font=font(16),fill='#b8c7da')
    output=OUT/'feasibility_spike_screenshot.png'
    canvas.save(output,optimize=True)
    print(f'SUCCESS: {len(images)} inputs processed. Screenshot: {output}')

if __name__=='__main__':main()
