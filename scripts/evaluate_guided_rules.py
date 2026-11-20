"""Matched complete-clip comparison of existing fixed and guided form rules."""
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import cv2
from posture_check.__main__ import process
from posture_check.evaluation import classification
from posture_check.exercises import summarize_for_exercise
from posture_check.pose import PoseEstimator
from posture_check.session import ExerciseSession, GuidedRepetitionCounter
from posture_check.temporal import TemporalAnalyzer

DEFAULT_FREEZE = ROOT / 'docs/guided_evaluation/freeze.json'
DEFAULT_OUTPUT = ROOT / 'docs/guided_evaluation/results.json'
METHODS = ('fixed_clip_rules', 'guided_session_rules')


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def source_hashes():
    paths = sorted((ROOT / 'src/posture_check').glob('*.py'))
    paths += [Path(__file__).resolve(), ROOT / 'requirements.txt']
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def prepare(path, model, data_root):
    if path.exists():
        raise ValueError('Freeze already exists; preserve it and choose a new path.')
    historical = ROOT / 'docs/calibration/evaluation_freeze.json'
    old = json.loads(historical.read_text(encoding='utf-8'))
    clips = old['suites']['prospective']
    # Use the complete pre-existing selection, never a prediction-dependent subset.
    if len(clips) != 16 or any(c['exercise'] not in ('squat', 'pushup') for c in clips):
        raise ValueError('Unexpected historical selection')
    for clip in clips:
        if sha(data_root / clip['file']) != clip['sha256']:
            raise ValueError('Input hash mismatch: ' + clip['id'])
    if sha(model) != old['model_sha256']:
        raise ValueError('Expected the existing official Lite model')
    freeze = {
        'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
        'selection_source': historical.relative_to(ROOT).as_posix(),
        'selection_source_sha256': sha(historical),
        'source_sha256': source_hashes(), 'model_sha256': sha(model),
        'methods': list(METHODS), 'clips': clips,
        'protocol': {
            'scope': 'Matched comparison on 16 previously exposed complete clips; not a fresh independent test.',
            'labels': 'Mendeley whole-clip source labels, not verified fault-level or expert labels. AI01 annotations are not used.',
            'baseline': 'Existing summarize_for_exercise(..., calibrated=False) on all shared temporal records.',
            'final': 'Unmodified ExerciseSession.add/assess; initial idle exclusion and quality gates retained.',
            'shared_processing': 'One tracked VIDEO pose pass per clip, enhanced=True, GUI temporal path with dt_seconds=1/media_fps and analyzer nominal FPS 30.',
            'stopping': 'Decode full clip; no target-based truncation, countdown, preview, or recording. Does not validate automatic stopping or webcam speed.',
            'mapping': 'Guided good -> correct; bad -> incorrect; unassessable retained.',
            'metrics': 'Accuracy on all clips; binary macro-F1 with abstentions as false negatives; coverage; assessed-only accuracy; per-class precision/recall/F1; confusion matrix.',
            'counts': 'Observed guided counts only. No manual rep references, so no count MAE or count-accuracy claim.',
            'tuning': 'No threshold fitting, calibration profile loading, or post-result selection. Preserve all outputs, including failures.',
        },
    }
    write_json(path, freeze)
    print('Prepared freeze:', path, flush=True)


def assess_records(exercise, records):
    session = ExerciseSession(exercise)
    for record in records:
        session.add(record)
    return {METHODS[0]: summarize_for_exercise(records, exercise, calibrated=False),
            METHODS[1]: session.assess()}


def canonical_prediction(assessment):
    prediction = assessment['prediction']
    return {'good': 'correct', 'bad': 'incorrect'}.get(prediction, prediction)


def collect(clip, model, data_root):
    source = data_root / clip['file']
    if sha(source) != clip['sha256']:
        raise ValueError('Input hash mismatch: ' + clip['id'])
    capture = cv2.VideoCapture(str(source))
    estimator = None
    try:
        if not capture.isOpened():
            raise ValueError('Cannot open ' + clip['id'])
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or not 0 < fps < 1000:
            raise ValueError('Invalid media FPS')
        estimator = PoseEstimator(model, video=True, fps=fps)
        analyzer = TemporalAnalyzer(clip['exercise'], 30)
        analyzer.counter = GuidedRepetitionCounter(clip['exercise'])
        records = []
        start = time.perf_counter()
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            _, raw = process(frame, estimator, clip['exercise'], enhanced=True)
            result = analyzer.update(raw, dt_seconds=1 / fps)
            records.append({key: result.get(key) for key in
                            ('features', 'raw_features', 'phase', 'instantaneous_phase', 'repetition_count')})
        elapsed = time.perf_counter() - start
        if len(records) != clip['metadata_frames'] or not records:
            raise ValueError('Decoded frame count does not match frozen input')
        if sha(source) != clip['sha256']:
            raise ValueError('Input changed during processing')
        return records, {'frames': len(records), 'media_fps': fps,
                         'guided_observed_reps': analyzer.count,
                         'shared_decode_and_processing_seconds': elapsed}
    finally:
        capture.release()
        if estimator is not None:
            estimator.close()


def export(log, output):
    with output.with_suffix('.csv').open('w', newline='', encoding='utf-8') as handle:
        columns = ['id', 'participant', 'exercise', 'reference_form', 'method', 'prediction',
                   'frames', 'valid_frames', 'valid_fraction', 'guided_observed_reps', 'issues']
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        for row in log['runs']:
            assessment = row['assessment']
            item = {key: row.get(key) for key in columns}
            item.update(valid_frames=assessment['valid_frames'], valid_fraction=assessment['valid_fraction'],
                        issues=';'.join(assessment.get('issues') or assessment.get('reasons') or []))
            writer.writerow(item)
    lines = ['# Guided-rule evaluation results', '',
             'Matched comparison on previously exposed Mendeley source-labeled clips. '
             'This is not a new independent test or a webcam/automatic-stop benchmark.', '',
             '| Set | Method | Accuracy (all clips) | Macro-F1 | Coverage | Assessed accuracy |',
             '| --- | --- | ---: | ---: | ---: | ---: |']
    for subset, summaries in [('All 16', log['summary']), *log['by_exercise'].items()]:
        for method, metrics in summaries.items():
            conditional = metrics['accuracy_assessed']
            lines.append(f"| {subset} | {method} | {metrics['accuracy_all']:.1%} | "
                         f"{metrics['macro_f1']:.3f} | {metrics['classification_coverage']:.1%} | "
                         f"{conditional:.1%} |" if conditional is not None else
                         f'| {subset} | {method} | 0% | 0.000 | 0% | N/A |')
    for method, metrics in log['summary'].items():
        lines += ['', f'## {method}', '', 'Rows are source labels; columns are predictions.', '',
                  '| Reference | Correct | Incorrect | Unable to assess |', '| --- | ---: | ---: | ---: |']
        for truth, row in metrics['confusion_matrix'].items():
            lines.append(f"| {truth} | {row['correct']} | {row['incorrect']} | {row['unassessable']} |")
    lines += ['', '## Interpretation limits', '',
              '- Eight squat and eight push-up clips, four participants, balanced source form labels.',
              '- Source correct/incorrect labels may cover faults outside the configured checks; they are not expert fault annotations.',
              '- The same people/clips appeared in earlier experiments. No new generalization claim is supported.',
              '- Only complete-clip form decisions are scored. Lunge, jumping jacks, rep-count accuracy, feedback-tip accuracy, target stopping, and live speed are not scored.',
              '- Both methods reuse identical smoothed pose features. Guided initial-idle exclusion and its 10-frame gate differ from the baseline 30-frame gate.',
              '- Abstentions remain misses in overall accuracy and class recall/F1; assessed-only accuracy must be read with coverage.',
              '- No rules were changed for this evaluation. Historical calibrated CLI numbers belong to a different version/environment.', '',
              'See results.json for per-class metrics, complete assessments, runtime, and provenance; '
              'results.csv contains per-clip predictions. freeze.json records the protocol and hashes.', '']
    output.with_suffix('.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, default=DEFAULT_FREEZE)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--model', type=Path, default=ROOT / 'models/pose_landmarker_lite.task')
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data/raw')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.prepare_only:
        prepare(args.freeze, args.model, args.data_root)
        return
    freeze = json.loads(args.freeze.read_text(encoding='utf-8'))
    if source_hashes() != freeze['source_sha256'] or sha(args.model) != freeze['model_sha256']:
        raise ValueError('Code or model differs from the frozen evaluation')
    if any(args.output.with_suffix(ext).exists() for ext in ('.json', '.csv', '.md')):
        raise ValueError('Preserve existing results; use a new --output filename')
    # Validate every input before starting any inference.
    for clip in freeze['clips']:
        if sha(args.data_root / clip['file']) != clip['sha256']:
            raise ValueError('Input hash mismatch: ' + clip['id'])
    log = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'running',
           'freeze_sha256': sha(args.freeze), 'freeze_file': str(args.freeze),
           'source_sha256': freeze['source_sha256'], 'model_sha256': freeze['model_sha256'],
           'protocol': freeze['protocol'],
           'runtime': {'python': platform.python_version(), 'platform': platform.platform(),
                       'dependencies': {name: importlib.metadata.version(name) for name in
                                        ('mediapipe', 'numpy', 'opencv-contrib-python', 'pillow')}},
           'runs': []}
    write_json(args.output, log)
    try:
        for index, clip in enumerate(freeze['clips'], 1):
            records, metadata = collect(clip, args.model, args.data_root)
            evidence = ROOT / 'outputs/guided_evaluation' / args.output.stem / (clip['id'] + '.json.gz')
            if evidence.exists():
                raise ValueError('Evidence exists; choose a unique output stem')
            evidence.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(evidence, 'wt', encoding='utf-8') as handle:
                json.dump(records, handle, allow_nan=False)
            assessments = assess_records(clip['exercise'], records)
            for method, assessment in assessments.items():
                log['runs'].append({**clip, **metadata, 'method': method,
                                    'prediction': canonical_prediction(assessment), 'assessment': assessment,
                                    'evidence_file': evidence.relative_to(ROOT).as_posix(),
                                    'evidence_sha256': sha(evidence)})
            write_json(args.output, log)
            print(f"{index}/16 {clip['id']} reference={clip['reference_form']} " +
                  ' '.join(f'{method}={canonical_prediction(value)}' for method, value in assessments.items()), flush=True)
        if source_hashes() != freeze['source_sha256'] or sha(args.model) != freeze['model_sha256']:
            raise ValueError('Code or model changed during evaluation')
        log['summary'] = {m: classification([r for r in log['runs'] if r['method'] == m]) for m in METHODS}
        log['by_exercise'] = {ex: {m: classification([r for r in log['runs'] if r['method'] == m and r['exercise'] == ex])
                                  for m in METHODS} for ex in ('squat', 'pushup')}
        log['status'] = 'complete'
        log['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(args.output, log)
        export(log, args.output)
        print('Completed:', args.output, flush=True)
    except Exception as error:
        log.update(status='failed', error=str(error))
        write_json(args.output, log)
        raise


if __name__ == '__main__':
    main()
