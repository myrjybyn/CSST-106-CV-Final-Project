"""Human-reviewed label repair for POSTURE CHECK Milestone 1.

Step 1: python scripts/review_exercise_frames.py
        View outputs/review_lunge.png and outputs/review_jumping_jack.png.
Step 2: python scripts/review_exercise_frames.py --apply --lunge 3,7,11 --jumping-jack 1,4,30
        Replace the example indices with three *visually correct* candidates per exercise.

This tool corrects exercise-action labels only. It NEVER labels form as correct/incorrect.
Do not rerun prepare_data.py after applying, since it will overwrite your reviewed frames.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

# This script lives next to prepare_data.py in scripts/.
from prepare_data import ROOT, VIDEOS, SAMPLES, OUTPUTS

PREVIEW_DIR = OUTPUTS / 'review_candidates'
REPLACE = {'lunge': [1, 3, 5], 'jumping_jack': [2, 3, 4]}
CLIPS = {'lunge': ('lunge.webm', 8.0, 56.0, 47),
         'jumping_jack': ('jumping_jack.webm', 0.0, 13.5, 55)}


def get_font(size, bold=False):
    candidates = [
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def generate_preview(exercise):
    filename, start, end, count = CLIPS[exercise]
    video = VIDEOS / filename
    if not video.is_file():
        raise FileNotFoundError(f'Missing {video}. Keep your original downloaded video in data/videos/.')
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open video: {video}')
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = total_frames / fps if fps > 0 and total_frames > 0 else None
    if duration is not None:
        end = min(end, duration - 0.15)
    if end <= start:
        raise RuntimeError(f'Invalid time range for {video}: {start} to {end}')
    candidates_dir = PREVIEW_DIR / exercise
    candidates_dir.mkdir(parents=True, exist_ok=True)
    times = np.linspace(start, end, count)
    samples = []
    for j, time_sec in enumerate(times, 1):
        cap.set(cv2.CAP_PROP_POS_MSEC, float(time_sec * 1000))
        ok, image = cap.read()
        if not ok or image is None:
            print(f'[skip] {exercise} candidate {j} at {time_sec:.2f}s could not be decoded')
            continue
        height, width = image.shape[:2]
        scale = min(1.0, 960 / max(height, width))
        if scale < 1:
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        jpg = candidates_dir / f'{j:03}.jpg'
        if not cv2.imwrite(str(jpg), image, [cv2.IMWRITE_JPEG_QUALITY, 90]):
            raise RuntimeError(f'Cannot save {jpg}')
        # Recording the requested seek time is consistent with prepare_data.py.
        samples.append({'index': j, 'timestamp_s': round(float(time_sec), 3), 'file': str(jpg.relative_to(ROOT))})
    cap.release()
    if len(samples) < 3:
        raise RuntimeError(f'Only {len(samples)} candidate images could be extracted for {exercise}')
    manifest = PREVIEW_DIR / f'{exercise}.json'
    manifest.write_text(json.dumps(samples, indent=2), encoding='utf-8')

    cols = 5
    tilew, tileh, gap = 230, 177, 10
    margin, top = 20, 82
    rows = (len(samples) + cols - 1) // cols
    sheet = Image.new('RGB', (margin * 2 + cols * tilew + (cols - 1) * gap,
                              top + rows * (tileh + gap) + margin), '#0b1220')
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, 14), f'{exercise.replace("_", " ").upper()} - CANDIDATES',
              font=get_font(26, True), fill='white')
    draw.text((margin, 49), 'Select 3 candidate numbers showing the named exercise. Do not select unrelated movements.',
              font=get_font(13), fill='#cbd5e1')
    for k, item in enumerate(samples):
        rr, cc = divmod(k, cols)
        xx = margin + cc * (tilew + gap)
        yy = top + rr * (tileh + gap)
        draw.rounded_rectangle([xx, yy, xx + tilew, yy + tileh], radius=10, fill='#162238')
        with Image.open(ROOT / item['file']) as raw:
            pic = ImageOps.contain(raw.convert('RGB'), (tilew - 8, 142))
            sheet.paste(pic, (xx + (tilew - pic.width) // 2, yy + (147 - pic.height) // 2))
        draw.text((xx + 9, yy + 149),
                  f'#{item["index"]:03}    t={item["timestamp_s"]:.2f}s',
                  font=get_font(17, True), fill='white')
    out = OUTPUTS / f'review_{exercise}.png'
    sheet.save(out, optimize=True)
    print(f'[preview] {out} ({len(samples)} frames)')


def pick_three(s, exercise):
    if s is None:
        raise ValueError(f'Provide three indices: --{exercise.replace("_", "-")} 3,7,11')
    parts = [x.strip() for x in s.split(',')]
    try:
        nums = [int(x) for x in parts]
    except ValueError as exc:
        raise ValueError(f'Enter comma-separated numbers for {exercise}, e.g. 3,7,11') from exc
    if len(nums) != 3 or len(set(nums)) != 3:
        raise ValueError(f'{exercise}: select exactly THREE different candidate numbers.')
    manifest_file = PREVIEW_DIR / f'{exercise}.json'
    if not manifest_file.is_file():
        raise FileNotFoundError(f'Missing {manifest_file}: first run the script WITHOUT --apply.')
    options = {item['index']: item for item in json.loads(manifest_file.read_text(encoding='utf-8'))}
    for idx in nums:
        if idx not in options:
            raise ValueError(f'{exercise}: #{idx:03} was not generated; check the preview grid.')
        if not (ROOT / options[idx]['file']).is_file():
            raise FileNotFoundError(ROOT / options[idx]['file'])
    return [options[i] for i in nums]


def create_contact_sheet(rows):
    """Regenerate the original 5 x 4 sheet with push-up variant captions."""
    bg, tilebg, fg, muted = '#0b1220', '#162238', '#f8fafc', '#b8c7da'
    w, picture_h, caption_h, margin, title_h, cols, gap = 275, 180, 63, 24, 98, 5, 11
    nr = (len(rows) + cols - 1) // cols
    total_w = margin * 2 + cols * w + (cols - 1) * gap
    total_h = title_h + margin + nr * (picture_h + caption_h) + (nr - 1) * gap + margin + 45
    out = Image.new('RGB', (total_w, total_h), bg)
    draw = ImageDraw.Draw(out)
    draw.text((margin, 17), 'POSTURE CHECK  |  DATA EVIDENCE', font=get_font(28, True), fill=fg)
    draw.text((margin, 58), '20 genuine video frames  -  5 per exercise  -  exercise labels reviewed; form unverified',
              font=get_font(14), fill=muted)
    for j, row in enumerate(rows):
        rr, cc = divmod(j, cols)
        x, y = margin + cc * (w + gap), title_h + margin + rr * (picture_h + caption_h + gap)
        draw.rounded_rectangle((x, y, x + w, y + picture_h + caption_h), radius=12, fill=tilebg)
        path = SAMPLES / row['filename']
        with Image.open(path) as raw:
            img = ImageOps.contain(raw.convert('RGB'), (w - 12, picture_h - 12))
            out.paste(img, (x + (w - img.width) // 2, y + (picture_h - img.height) // 2))
        label = row['exercise_label'].replace('_', ' ').upper()
        variant = row.get('exercise_variant', '').strip().lower()
        if variant == 'wall':
            label = 'PUSH-UP (WALL)'
        elif variant == 'knee':
            label = 'PUSH-UP (KNEE)'
        draw.text((x + 11, y + picture_h + 5), f'{j + 1:02d}  {label}',
                  font=get_font(15, True), fill=fg)
        draw.text((x + 11, y + picture_h + 34),
                  f't={float(row["source_time_s"]):.1f}s  |  Form: UNVERIFIED',
                  font=get_font(12), fill=muted)
    draw.text((margin, total_h - 37),
              'Source video, licenses, timestamps, and variations: data/labels.csv',
              font=get_font(14), fill=muted)
    outfile = OUTPUTS / 'contact_sheet_20.png'
    out.save(outfile, optimize=True)
    return outfile


def apply(lunge: str, jumping_jack: str):
    selected = {'lunge': pick_three(lunge, 'lunge'),
                'jumping_jack': pick_three(jumping_jack, 'jumping_jack')}
    csvfile = ROOT / 'data' / 'labels.csv'
    if not csvfile.exists():
        raise FileNotFoundError('data/labels.csv is missing. Run prepare_data.py --no-download once first.')
    with csvfile.open(newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    expected = [f'{ex}_{i:02}.jpg' for ex in ('squat', 'pushup', 'lunge', 'jumping_jack') for i in range(1, 6)]
    by_file = {row['filename']: row for row in rows}
    if set(by_file) != set(expected) or len(rows) != 20:
        raise ValueError('Expected exactly 20 original samples named squat_01.jpg ... jumping_jack_05.jpg.')
    for file in expected:
        if not (SAMPLES / file).is_file():
            raise FileNotFoundError(SAMPLES / file)
    # Back up existing samples, labels, and sheet before overwriting any of them.
    backup = OUTPUTS / ('review_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(csvfile, backup / csvfile.name)
    if (OUTPUTS / 'contact_sheet_20.png').is_file():
        shutil.copy2(OUTPUTS / 'contact_sheet_20.png', backup / 'contact_sheet_20.png')
    for exercise, indices in REPLACE.items():
        for i in indices:
            original = SAMPLES / f'{exercise}_{i:02}.jpg'
            shutil.copy2(original, backup / original.name)
    for ex, new_samples in selected.items():
        for target_index, item in zip(REPLACE[ex], new_samples):
            name = f'{ex}_{target_index:02}.jpg'
            shutil.copy2(ROOT / item['file'], SAMPLES / name)
            by_file[name]['source_time_s'] = item['timestamp_s']
            by_file[name]['label_basis'] = 'manually selected frame depicting the stated exercise; form correctness not verified'
            print(f'[fixed] {name} from video time {item["timestamp_s"]:.2f}s')
    for i in range(1, 6):
        by_file[f'pushup_{i:02}.jpg']['exercise_variant'] = 'wall' if i <= 4 else 'knee'
    for name in expected:
        by_file[name].setdefault('exercise_variant', '')
        by_file[name]['form_correctness'] = 'UNVERIFIED'
    # Keep the original stable ordering in the contact sheet.
    ordered = [by_file[x] for x in expected]
    fields = list(ordered[0].keys())
    if 'exercise_variant' not in fields:
        fields.append('exercise_variant')
    with csvfile.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(ordered)
    final_image = create_contact_sheet(ordered)
    print(f'\n[done] Updated {csvfile} and {final_image}')
    print(f'[backup] Originals saved to {backup}')
    print('IMPORTANT: Open the final contact sheet and confirm EVERY visible action matches the label.')
    print('Do NOT rerun prepare_data.py, or it will overwrite the reviewed images.')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true', help='Apply human-reviewed candidate numbers and regenerate CSV + contact sheet')
    parser.add_argument('--lunge', help='3 candidate numbers (from outputs/review_lunge.png), e.g. 3,7,11')
    parser.add_argument('--jumping-jack', help='3 candidate numbers (from outputs/review_jumping_jack.png), e.g. 2,5,29')
    args = parser.parse_args()
    if args.apply:
        apply(args.lunge, args.jumping_jack)
    else:
        for name in ('lunge', 'jumping_jack'):
            generate_preview(name)
        print('\nOpen both preview PNGs. Choose THREE unmistakable exercise frames from each.')
        print('Then run: python scripts/review_exercise_frames.py --apply --lunge 3,7,11 --jumping-jack 1,5,29')
        print('Replace those six EXAMPLE numbers with the candidate numbers you actually choose!')


if __name__ == '__main__':
    main()
