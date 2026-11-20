"""Inventory existing source labels and prepare BLANK human-review worksheets.

Does not infer form labels, decode test media, or modify calibration artifacts.
Run from any directory: python scripts/calibration/prepare_label_review.py
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'docs/calibration/label_review'
SOURCE = 'https://data.mendeley.com/datasets/kgbb3yn47p/3'


def write_csv(path, rows, fields):
    with path.open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    # Refuse any overwrite: reviewers may have edited these worksheets.
    outputs = ['source_clips.csv', 'side_view_review_queue.csv',
               'rep_annotations.csv', 'new_recording_plan.csv', 'inventory.json']
    existing = [name for name in outputs if (DEST / name).exists()]
    if existing:
        raise SystemExit('Preserve existing review files; already present: ' + ', '.join(existing))
    plan = json.loads((ROOT / 'docs/calibration/plan.json').read_text(encoding='utf-8'))
    roles = {clip['id']: role for role, clips in plan['partitions'].items() for clip in clips}
    exposed = set(plan['original_exposed_test_participants'])
    with (ROOT / 'data/prepared/mendeley/all_videos.csv').open(encoding='utf-8-sig', newline='') as stream:
        records = list(csv.DictReader(stream))
    clips = []
    for row in records:
        relative = row['relative_video_path']
        path = ROOT / 'data/raw/mendeley' / relative
        clip_id = Path(relative).stem
        role = roles.get(clip_id, 'outside_side_view_calibration_plan')
        exposure = ('original_test_previously_inspected' if row['participant_id'] in exposed
                    else 'prior_prospective_test_now_exposed' if role == 'prospective'
                    else 'development_participant')
        clips.append(dict(
            clip_id=clip_id, exercise=row['exercise'], participant=row['participant_id'],
            view=Path(relative).parent.name, source_form_label=row['form_label'],
            label_scope='whole_clip_only', label_origin='published_source_good_bad',
            original_split=row['split'], prior_calibration_role=role,
            participant_exposure=exposure, fresh_final_test_eligible='NO',
            local_video_path=path.relative_to(ROOT).as_posix(),
            media_present='YES' if path.is_file() else 'NO', source_url=SOURCE,
            specific_fault_labels='NOT_PROVIDED', rep_boundaries='NOT_PROVIDED'))
    side = [row for row in clips if row['view'] == 'side']
    # Queue excludes source form labels so reviewers can work without seeing them.
    queue = [dict(clip_id=row['clip_id'], exercise=row['exercise'],
                  participant=row['participant'], video_path=row['local_video_path'],
                  media_present=row['media_present'], review_status='pending') for row in side]
    annotation_fields = ['clip_id', 'participant', 'exercise', 'rep_index',
                         'start_seconds', 'end_seconds', 'view', 'assessable',
                         'unassessable_reason', 'overall_form', 'limited_depth',
                         'incomplete_extension', 'trunk_alignment_issue',
                         'evidence_notes', 'reviewer_id', 'reviewer_qualification',
                         'reviewed_at', 'second_reviewer_id', 'adjudication_status']
    recordings = []
    for number in range(1, 9):
        participant = f'local_new_{number:03d}'
        split = 'development' if number <= 4 else 'validation' if number <= 6 else 'final_test'
        for exercise in ('squat', 'pushup'):
            for take in range(1, 4):
                recordings.append(dict(recording_id=f'{participant}_{exercise}_{take:02d}',
                                       participant=participant, exercise=exercise, view='side',
                                       reserved_split=split, target_completed_reps=3,
                                       recording_status='not_recorded',
                                       form_label='', label_status='unlabeled'))
    DEST.mkdir(parents=True, exist_ok=True)
    write_csv(DEST / outputs[0], clips, list(clips[0]))
    write_csv(DEST / outputs[1], queue, list(queue[0]))
    write_csv(DEST / outputs[2], [], annotation_fields)
    write_csv(DEST / outputs[3], recordings, list(recordings[0]))
    summary = dict(source_url=SOURCE, source_clip_count=len(clips),
                   side_view_clip_count=len(side),
                   side_view_labels=dict(Counter(f"{r['exercise']}:{r['source_form_label']}" for r in side)),
                   local_media_present=sum(r['media_present'] == 'YES' for r in clips),
                   new_recording_slots=len(recordings), actual_new_recordings=0,
                   reviewed_rep_annotations=0,
                   fresh_test_policy='All existing participants conservatively excluded from a fresh final test.',
                   status='Source labels inventoried; per-rep fault validation pending media and human review.')
    with (DEST / outputs[4]).open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, indent=2)
        stream.write('\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
