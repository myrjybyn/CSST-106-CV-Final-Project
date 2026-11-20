"""Verify the public archive, extract manifest videos, and build review assets.

Uses source labels only as existing clip-level metadata, never as per-rep truth.
No pose inference or tuning is performed. Human annotations are left untouched.
"""
import csv
import hashlib
import json
import random
import shutil
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / 'data/raw/mendeley'
PACK = ROOT / 'outputs/form_label_review'
DOCS = ROOT / 'docs/calibration/label_review'


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def save_csv(path, records):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    metadata = json.loads((MEDIA / 'source_files_2026-11-20.json').read_text(encoding='utf-8'))
    source = next(row for row in metadata if row['filename'] == 'Dataset Subject-wise.zip')
    expected = source['content_details']
    archive = MEDIA / source['filename']
    candidate = archive if archive.exists() else archive.with_suffix('.zip.part')
    if not candidate.exists() or candidate.stat().st_size != expected['size']:
        raise SystemExit('Archive download incomplete: size does not match publisher metadata.')
    archive_hash = digest(candidate)
    if archive_hash != expected['sha256_hash']:
        raise SystemExit('Archive checksum differs from publisher metadata; refusing extraction.')
    if candidate != archive:
        candidate.rename(archive)
    print('Archive size and SHA256 verified.', flush=True)
    with (DOCS / 'source_clips.csv').open(newline='', encoding='utf-8') as stream:
        records = list(csv.DictReader(stream))
    wanted = {PurePosixPath(row['local_video_path']).relative_to('data/raw/mendeley').as_posix(): row
              for row in records}
    extracted = []
    with zipfile.ZipFile(archive) as bundle:
        entries = {entry.filename: entry for entry in bundle.infolist()}
        missing = set(wanted) - entries.keys()
        if missing:
            raise SystemExit('Archive paths differ from manifests: ' + repr(sorted(missing)[:5]))
        # Validate every selected destination before writing anything.
        for name in wanted:
            path = PurePosixPath(name)
            target = (MEDIA / name).resolve()
            if path.is_absolute() or '..' in path.parts or not target.is_relative_to(MEDIA.resolve()):
                raise ValueError('Unsafe archive destination: ' + name)
            if stat.S_ISLNK(entries[name].external_attr >> 16):
                raise ValueError('Symlink archive entry rejected: ' + name)
        for number, (name, row) in enumerate(wanted.items(), 1):
            target = MEDIA / name
            target.parent.mkdir(parents=True, exist_ok=True)
            entry = entries[name]
            if target.exists():
                # Compare existing media to archive bytes without overwriting.
                with bundle.open(entry) as stream:
                    archived_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
                if digest(target) != archived_hash:
                    raise ValueError('Existing media differs; preserved: ' + str(target))
            else:
                partial = target.with_suffix('.mp4.extracting')
                with bundle.open(entry) as incoming, partial.open('wb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
                partial.rename(target)
            row['media_present'] = 'YES'
            extracted.append(dict(clip_id=row['clip_id'], size=target.stat().st_size, sha256=digest(target)))
            if number % 40 == 0:
                print(f'Extracted/verified {number}/{len(wanted)} manifest videos.', flush=True)
    expected_clips = {clip['id']: clip['sha256'] for clips in json.loads(
        (ROOT / 'docs/calibration/plan.json').read_text(encoding='utf-8'))['partitions'].values() for clip in clips}
    for row in extracted:
        if row['clip_id'] in expected_clips and row['sha256'] != expected_clips[row['clip_id']]:
            raise ValueError('Media differs from prior calibration input: ' + row['clip_id'])
    PACK.mkdir(parents=True, exist_ok=True)
    index, mapping = [], []
    # Never overwrite an earlier review pack; it could contain human annotations.
    if (PACK / 'reviewer_index.csv').exists():
        raise SystemExit('Review pack already exists; preserve it or use a separate destination.')
    review_records = [row for row in records if row['view'] == 'side']
    random.Random(20261120).shuffle(review_records)
    for number, row in enumerate(review_records, 1):
        alias = f'review_{number:03d}'
        path = ROOT / row['local_video_path']
        capture = cv2.VideoCapture(str(path))
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if not capture.isOpened() or fps <= 0 or frames < 6:
                raise ValueError('Unreadable video: ' + row['clip_id'])
            sheet = Image.new('RGB', (960, 610), 'white')
            drawing = ImageDraw.Draw(sheet)
            drawing.text((12, 8), f'{alias} | {row["exercise"]} | preview only; review the full video', fill='black')
            for cell, fraction in enumerate((.05, .23, .41, .59, .77, .95)):
                frame_number = min(frames - 1, int((frames - 1) * fraction))
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ok, frame = capture.read()
                if not ok:
                    raise ValueError(f'Frame decode failed: {alias} at {frame_number}')
                picture = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                picture.thumbnail((312, 258))
                x, y = (cell % 3) * 320, 36 + (cell // 3) * 282
                sheet.paste(picture, (x + (320 - picture.width) // 2, y))
                drawing.text((x + 8, y + 260), f'{frame_number / fps:.2f} seconds', fill='black')
            sheet.save(PACK / f'{alias}.jpg', quality=88)
        finally:
            capture.release()
        destination = PACK / f'{alias}.mp4'
        if destination.exists():
            if digest(destination) != digest(path):
                raise ValueError('Existing review video differs: ' + alias)
        else:
            shutil.copyfile(path, destination)
        index.append(dict(review_id=alias, exercise=row['exercise'], video=f'{alias}.mp4',
                          contact_sheet=f'{alias}.jpg', duration_seconds=round(frames / fps, 3),
                          fps=fps, frames=frames, review_status='pending'))
        mapping.append(dict(review_id=alias, clip_id=row['clip_id'], participant=row['participant'],
                            source_form_label=row['source_form_label'], sha256=digest(path)))
        if number % 10 == 0:
            print(f'Prepared {number}/98 numbered review videos and contact sheets.', flush=True)
    save_csv(PACK / 'reviewer_index.csv', index)
    # A separate blank worksheet uses aliases, not source filenames/labels.
    with (DOCS / 'rep_annotations.csv').open(newline='', encoding='utf-8') as stream:
        original_fields = csv.DictReader(stream).fieldnames
    review_fields = ['review_id'] + [field for field in original_fields
                                    if field not in ('clip_id', 'participant')]
    with (PACK / 'reviewer_rep_annotations.csv').open('x', newline='', encoding='utf-8') as stream:
        csv.writer(stream).writerow(review_fields)
    (PACK / 'START_HERE.txt').write_text(
        'Review numbered MP4 videos using reviewer_index.csv. JPG files are previews only.\n'
        'Add one row per complete repetition to reviewer_rep_annotations.csv.\n'
        'Use review_id from the index. Do not view source mappings or app predictions\n'
        'until independent labeling is complete. Read REVIEWER_GUIDE.txt in this\n'
        'folder for the workflow, column values and rubric preparation steps.\n'
        'No per-rep labels have been assigned. Finalize the rubric with a qualified\n'
        'reviewer, record qualifications, and use uncertain/unassessable when needed.\n'
        'Prior participant/test exposure remains; these are development/review assets.\n\n'
        'SOURCE AND ATTRIBUTION\n'
        'A Multi-View Raw Video Dataset of Seven Fitness Exercises with Good/Bad Form Labels, v3.\n'
        'Duddela Sai Prashanth, Priya Kamath, Rakshith Bhandary, S Ashlesh Pai,\n'
        'Pratham PN, Advith P, and Abhishek Mashetty. DOI: 10.17632/kgbb3yn47p.3\n'
        'https://data.mendeley.com/datasets/kgbb3yn47p/3\n'
        'CC BY 4.0: https://creativecommons.org/licenses/by/4.0/\n'
        'Changes: video copies renamed for independent review; JPG contact sheets\n'
        'sampled from source videos with review IDs and timestamps. No endorsement implied.\n',
        encoding='utf-8')
    shutil.copyfile(DOCS / 'REVIEWER_GUIDE.txt', PACK / 'REVIEWER_GUIDE.txt')
    save_csv(MEDIA / 'review_id_mapping.csv', mapping)
    save_csv(MEDIA / 'extracted_manifest_checksums.csv', extracted)
    # New dated snapshot; the original inventory and review queue remain unchanged.
    save_csv(DOCS / 'source_clips_available_2026-11-20.csv', records)
    report = dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),
                  source_url='https://data.mendeley.com/datasets/kgbb3yn47p/3',
                  archive_bytes=expected['size'], archive_sha256=archive_hash,
                  publisher_sha256_match=True, manifest_videos_verified=len(extracted),
                  prior_calibration_clip_hashes_matched=len(expected_clips),
                  review_videos_prepared=len(index), contact_sheets_prepared=len(index),
                  video_decode_check='Six sampled frames decoded per side-view video; not a full decode audit.',
                  reviewer_index='outputs/form_label_review/reviewer_index.csv',
                  private_source_mapping='data/raw/mendeley/review_id_mapping.csv',
                  human_rep_labels_created=0, validation_status='Awaiting independent human rep/fault review',
                  test_status='Prior test exposure retained; no fresh final-test claim.')
    (DOCS / 'acquisition_2026-11-20.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
