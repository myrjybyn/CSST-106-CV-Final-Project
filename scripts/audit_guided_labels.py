"""Audit conflicting byte-identical labels and rescore preserved guided results.

No inference, training, threshold changes, relabeling, or original-result edits.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from posture_check.evaluation import classification


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def conflicting_groups(clips):
    groups = defaultdict(list)
    for clip in clips:
        groups[clip['sha256']].append(clip)
    return [group for group in groups.values()
            if len({clip['reference_form'] for clip in group}) > 1]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def run(source, freeze_path, data_root, archive_path, output):
    destinations = [output.with_suffix(ext) for ext in ('.json', '.csv', '.md')]
    audit_path = output.with_name(output.stem + '_label_audit.json')
    if any(p.exists() for p in [*destinations, audit_path]):
        raise ValueError('Preserve previous analyses; choose a new --output filename')
    original = json.loads(source.read_text(encoding='utf-8'))
    freeze = json.loads(freeze_path.read_text(encoding='utf-8'))
    if original['status'] != 'complete' or sha(freeze_path) != original['freeze_sha256']:
        raise ValueError('Completed results and their exact original freeze are required')
    clips = freeze['clips']
    if len({c['id'] for c in clips}) != len(clips):
        raise ValueError('Duplicate clip IDs')
    methods = freeze['methods']
    if len(original['runs']) != len(clips) * len(methods):
        raise ValueError('Incomplete paired results')
    for clip in clips:
        if sha(data_root / clip['file']) != clip['sha256']:
            raise ValueError('Input bytes differ: ' + clip['id'])
        paired = [r for r in original['runs'] if r['id'] == clip['id']]
        if len(paired) != len(methods) or {r['method'] for r in paired} != set(methods):
            raise ValueError('Unpaired clip: ' + clip['id'])
        for row in paired:
            if any(row[key] != clip[key] for key in ('sha256', 'exercise', 'reference_form', 'file')):
                raise ValueError('Results disagree with input manifest: ' + clip['id'])
    for method in methods:
        if classification([r for r in original['runs'] if r['method'] == method]) != original['summary'][method]:
            raise ValueError('Original summary does not match predictions')
    groups = conflicting_groups(clips)
    excluded = {clip['id'] for group in groups for clip in group}
    # Verify contradictions in the downloaded ZIP, rather than assuming a local
    # extraction/copy mistake. All members are excluded regardless of predictions.
    archive_evidence = []
    with ZipFile(archive_path) as archive:
        for group in groups:
            members = []
            for clip in group:
                entry = Path(clip['file']).relative_to('mendeley').as_posix()
                with archive.open(entry) as handle:
                    digest = hashlib.file_digest(handle, 'sha256').hexdigest()
                if digest != clip['sha256']:
                    raise ValueError('Downloaded archive differs: ' + entry)
                members.append({'id': clip['id'], 'label': clip['reference_form'],
                                'archive_entry': entry, 'sha256': digest})
            archive_evidence.append({'sha256': group[0]['sha256'], 'members': members,
                                     'decision': 'exclude every member; contradictory source labels'})
    retained = [c for c in clips if c['id'] not in excluded]
    runs = [r for r in original['runs'] if r['id'] not in excluded]
    if not retained:
        raise ValueError('No clips remain after exclusions')
    summary = {m: classification([r for r in runs if r['method'] == m]) for m in methods}
    exercises = sorted({r['exercise'] for r in runs})
    by_exercise = {ex: {m: classification([r for r in runs if r['method'] == m and r['exercise'] == ex])
                        for m in methods} for ex in exercises}
    protocol = {
        'type': 'Post-hoc data-quality sensitivity analysis, not a new independent test.',
        'exclusion_rule': 'Exclude ALL members of each byte-identical input group carrying conflicting source form labels, regardless of either prediction.',
        'preservation': 'Original freeze, predictions, labels and results remain unchanged. Retained rows reuse the exact original inference outputs.',
        'scope': 'Complete-clip squat/push-up classification only. No retraining, threshold tuning, relabeling, target stopping, rep-count accuracy or live-speed measurement.',
        'limitations': 'Source labels remaining after duplicate removal are not independently reviewed expert labels. Exact-byte audit does not detect re-encoded/near duplicates or other labeling mistakes. Previously exposed clips remain exposed.',
        'metrics': 'Same binary class metrics as the original run; abstentions remain misses in all-clip accuracy and false negatives for their true class.',
    }
    audit = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
             'source_results_sha256': sha(source), 'source_freeze_sha256': sha(freeze_path),
             'audit_script_sha256': sha(Path(__file__).resolve()),
             'input_files_verified': len(clips), 'original_archive': str(archive_path),
             'conflicting_groups': archive_evidence, 'excluded_ids': sorted(excluded),
             'original_clips': len(clips), 'retained_clips': len(retained),
             'protocol': protocol}
    result = {'status': 'complete', 'created_at_utc': audit['created_at_utc'],
              'source_results_sha256': audit['source_results_sha256'],
              'source_freeze_sha256': audit['source_freeze_sha256'],
              'runtime': original['runtime'], 'protocol': protocol,
              'excluded_ids': sorted(excluded), 'retained_ids': [c['id'] for c in retained],
              'summary': summary, 'by_exercise': by_exercise, 'runs': runs}
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(audit_path, audit)
    write_json(output, result)
    with output.with_suffix('.csv').open('w', newline='', encoding='utf-8') as handle:
        fields = ['id', 'exercise', 'participant', 'reference_form', 'method', 'prediction']
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(runs)
    lines = ['# Guided evaluation: dataset correction', '',
             'Two byte-identical video pairs have opposite source labels. Both copies of each pair '
             'were verified in the original downloaded ZIP and excluded from this separate post-hoc analysis. '
             'Original 16-clip results are preserved unchanged.', '',
             '## Excluded inputs', '', '| Exercise | Contradictory pair |', '| --- | --- |']
    for group in groups:
        lines.append('| ' + group[0]['exercise'] + ' | ' + ' / '.join(c['id'] for c in group) + ' |')
    lines += ['', f'## Results on {len(retained)} retained clips', '',
              '| Set | Method | Accuracy | Macro-F1 | Coverage | Assessed accuracy |',
              '| --- | --- | ---: | ---: | ---: | ---: |']
    for subset, metrics_by_method in [('All retained clips', summary), *by_exercise.items()]:
        for method, metrics in metrics_by_method.items():
            macro = f"{metrics['macro_f1']:.3f}" if metrics['macro_f1'] is not None else 'N/A'
            conditional = f"{metrics['accuracy_assessed']:.2%}" if metrics['accuracy_assessed'] is not None else 'N/A'
            lines.append(f"| {subset} | {method} | {metrics['accuracy_all']:.2%} | {macro} | "
                         f"{metrics['classification_coverage']:.2%} | {conditional} |")
    for method, metrics in summary.items():
        lines += ['', '## ' + method, '', '| Source label | Correct | Incorrect | Unable to assess |',
                  '| --- | ---: | ---: | ---: |']
        for truth, row in metrics['confusion_matrix'].items():
            lines.append(f"| {truth} | {row['correct']} | {row['incorrect']} | {row['unassessable']} |")
    lines += ['', '## Interpretation and report correction', '',
              'Duplicate removal fixes contradictory evaluation inputs; it does not fix the form classifier. '
              'The original 43.75% accuracy / 0.430 macro-F1 is the unfiltered result and must remain labeled as such. '
              'Report the cleaned analysis alongside it, not as a new untouched test or an accuracy improvement.', '',
              'Both methods still agree on every retained clip. The guided rules show no measured classification '
              'gain over the matched fixed rules. Remaining source labels may describe faults outside the configured '
              'checks and have not been independently adjudicated.', '',
              'The original 160-check audit validated artifacts and arithmetic, not label consistency. '
              'This additional audit detects exact-byte label conflicts and verifies them in the downloaded archive; '
              'it is not expert label validation or a near-duplicate search.', '',
              'No human labels were invented or changed. Rules, source videos and original results are unchanged. '
              'The remaining squat tracking/movement abstention is retained. Lunge/jumping-jack accuracy, '
              'count accuracy, tip correctness and live target stopping remain untested.', '']
    output.with_suffix('.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    print(json.dumps({'excluded_ids': sorted(excluded), 'retained_clips': len(retained), 'summary': summary}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'docs/guided_evaluation/results.json')
    parser.add_argument('--freeze', type=Path, default=ROOT / 'docs/guided_evaluation/freeze.json')
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data/raw')
    parser.add_argument('--archive', type=Path, default=ROOT / 'data/raw/mendeley/Dataset Subject-wise.zip')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/guided_evaluation/cleaned_results.json')
    args = parser.parse_args()
    run(args.source, args.freeze, args.data_root, args.archive, args.output)
