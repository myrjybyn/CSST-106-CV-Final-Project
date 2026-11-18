"""Build the single item-6 technical documentation draft from existing evidence.

Uses python-docx from outputs/report_dependencies when installed locally.
Does not run inference, change model/configuration, or create/move Git tags.
"""
from pathlib import Path
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/report_dependencies'))
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

CAL = ROOT / 'docs/calibration'
M4 = ROOT / 'docs/milestone4'
CP3 = ROOT / 'docs/phase3'
NAMES = {'pushup': 'Push-up', 'squat': 'Squat', 'lunge': 'Lunge', 'jumping_jack': 'Jumping jacks'}
SNAPSHOT = 'c5196f6b2778c892d4d459090780f6d0bc6685fb'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected):
    return math.isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-10)


def validate(log, freeze):
    checks = []

    def check(condition, description):
        require(condition, description)
        checks.append(description)

    check(bool(log.get('completed_at_utc')) and not log.get('error'), 'Completion timestamp present; no error')
    check(datetime.fromisoformat(log['completed_at_utc']) > datetime.fromisoformat(log['started_at_utc']), 'Completion follows start')
    check(log['suite'] == 'benchmark' and log['runtime']['location'] == 'laptop', 'Laptop benchmark suite')
    check(log['methods'] == ['current'], 'Only calibrated current method requested')
    check(log['source_sha256'] == freeze['source_sha256'], 'All 22 frozen source/profile/plan hashes match log')
    check(log['freeze_sha256'] == sha((CAL / 'evaluation_freeze.json').read_bytes()), 'Exact recorded evaluation-freeze checksum matches')
    check(log['model_sha256'] == freeze['model_sha256'] == sha((ROOT / 'models/pose_landmarker_lite.task').read_bytes()), 'Lite pose model checksum matches')
    check(log['checkpoint3_commit'] == freeze['checkpoint3_commit'], 'Checkpoint-three reference commit matches')
    for name, digest in freeze['source_sha256'].items():
        check(sha((ROOT / name).read_bytes()) == digest, 'Working file matches freeze: ' + name)
        data = subprocess.check_output(['git', 'show', SNAPSHOT + ':' + name], cwd=ROOT)
        check(sha(data) == digest, 'Submission commit matches freeze: ' + name)
    manifests = {}
    for name, digest in freeze['manifest_sha256'].items():
        check(sha((ROOT / name).read_bytes()) == digest, 'Dataset manifest matches: ' + name)
        manifests[name] = digest
    expected = {r['id']: r for r in freeze['suites']['benchmark']}
    check(len(log['runs']) == len(expected) == 4 and {r['id'] for r in log['runs']} == set(expected), 'Exactly four unique expected clip IDs')
    for row in log['runs']:
        ref = expected[row['id']]
        check(row['method'] == 'current' and row['exit_code'] == 0, row['id'] + ': successful current run')
        check(row['sha256'] == ref['sha256'] == sha((ROOT / 'data/raw' / ref['file']).read_bytes()), row['id'] + ': original input checksum')
        check(row['frames'] == ref['metadata_frames'] == row['metadata_frames'], row['id'] + ': complete decoded frame count')
        check(all(row[k] == ref[k] for k in ['file', 'exercise', 'reference_form', 'reference_reps', 'fps']), row['id'] + ': input metadata and references match')
        check(0 <= row['assessable_frames'] <= row['pose_frames'] <= row['frames'], row['id'] + ': valid coverage counts')
        check(row['processing_seconds'] > 0 and close(row['processing_fps'], row['frames'] / row['processing_seconds']), row['id'] + ': timing arithmetic')
        check(row['prediction'] == row['clip_assessment']['prediction'], row['id'] + ': consistent assessment')
    sys.path.insert(0, str(ROOT / 'src'))
    from posture_check.evaluation import summarize
    check(summarize(log['runs']) == log['summary']['current'], 'Entire aggregate summary recomputes exactly from runs')
    for ex in NAMES:
        check(summarize([r for r in log['runs'] if r['exercise'] == ex]) == log['by_exercise']['current'][ex], ex + ': per-exercise summary recomputes')
    with (CAL / 'laptop_benchmark.csv').open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    check(len(rows) == 4, 'CSV has four rows')
    for row, raw in zip(rows, log['runs']):
        check(all(str(raw.get(k)) == value for k, value in row.items()), raw['id'] + ': CSV agrees with JSON')
    squat = next(r for r in log['runs'] if r['exercise'] == 'squat')
    assessment = squat['clip_assessment']
    check(assessment.get('calibration_id') == 'form-rules-v1', 'Squat assessment explicitly records form-rules-v1')
    tag = subprocess.run(['git', 'rev-parse', '--verify', 'refs/tags/cp4-80^{commit}'], cwd=ROOT, capture_output=True, text=True)
    check(tag.returncode != 0 or tag.stdout.strip() == SNAPSHOT, 'Existing cp4-80 tag, if present, points to submission commit')
    return {
        'validated_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'PASS: complete log; exact calibrated frozen artifact match',
        'submission_commit': SNAPSHOT,
        'tag_status': 'absent locally; commit message identifies cp4-80; no tag created or moved' if tag.returncode else 'verified existing cp4-80 tag',
        'log_sha256': sha((CAL / 'laptop_benchmark.json').read_bytes()),
        'checks': checks,
        'run_portability_note': 'Before inference, CRLF text was restored to exact frozen LF bytes. The Python runner normalized source-hash dictionary keys from Windows backslashes to forward slashes. No checksum was bypassed; no evaluation algorithm or freeze was changed.',
        'hardware_caveat': 'Raw log CPU name is null and RAM is zero, explicitly marked incomplete. Separate post-run registry/GlobalMemoryStatusEx verification supplies CPU and RAM; it is not contemporaneous capture.',
        'physical_webcam_status': 'PENDING: recorded-file benchmark and virtual-desktop tests do not verify a physical webcam',
        'historical_measurements': 'Unchanged; current laptop measurement is a separate evidence file',
    }


def pct(value):
    return f'{100 * value:.1f}%'


class Report:
    def __init__(self):
        self.doc = Document()
        self.md = []
        section = self.doc.sections[0]
        section.page_width, section.page_height = Inches(8.27), Inches(11.69)
        section.top_margin = section.bottom_margin = Inches(.65)
        section.left_margin = section.right_margin = Inches(.65)
        for name, size in [('Normal', 10), ('Title', 22), ('Heading 1', 14), ('Heading 2', 11)]:
            style = self.doc.styles[name]
            style.font.name, style.font.size = 'Arial', Pt(size)
            style.paragraph_format.space_after = Pt(6)
            if name != 'Normal':
                style.font.color.rgb = RGBColor.from_string('843B20')
        self.doc.core_properties.author = 'Posture Check project team'
        self.doc.core_properties.title = 'Posture Check: Draft Technical Documentation (Checkpoint 4, Item 6)'
        footer = section.footer.paragraphs[0]
        footer.add_run('POSTURE CHECK | Draft technical documentation | ')
        field = OxmlElement('w:fldSimple')
        field.set(qn('w:instr'), 'PAGE')
        footer._p.append(field)

    def heading(self, text, level=1):
        self.doc.add_heading(text, level)
        self.md.extend(['', '#' * (level + 1) + ' ' + text, ''])

    def p(self, text):
        self.doc.add_paragraph(text)
        self.md.extend([text, ''])

    def table(self, headers, rows):
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = 'Light Shading Accent 1'
        for cell, text in zip(table.rows[0].cells, headers):
            cell.text = str(text)
        trpr = table.rows[0]._tr.get_or_add_trPr()
        trpr.append(OxmlElement('w:tblHeader'))
        for values in rows:
            for cell, text in zip(table.add_row().cells, values):
                cell.text = str(text)
        for row in table.rows:
            row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(3)
                    for run in p.runs:
                        run.font.size = Pt(8)
        self.md.append('| ' + ' | '.join(headers) + ' |')
        self.md.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        self.md.extend('| ' + ' | '.join(str(x).replace('|', '/') .replace('\n', ' ') for x in row) + ' |' for row in rows)
        self.md.append('')

    def picture(self, path, caption):
        require(path.is_file(), 'Missing interface evidence: ' + str(path))
        self.doc.add_picture(str(path), width=Inches(6.5))
        self.p(caption)
        relative = Path(os.path.relpath(path, M4)).as_posix()
        self.md.extend(['![' + caption + '](' + relative + ')', ''])


def laptop_section(report, log, old, hardware, validation):
    current = log['summary']['current']
    previous = old['method_summary']['main']
    fps_change = 100 * (current['processing_fps'] / previous['processing_fps'] - 1)
    ms_change = 100 * (current['processing_ms_per_frame'] / previous['processing_ms_per_frame'] - 1)
    report.heading('4.4. Demo-laptop performance and checkpoint 3 comparison', 2)
    local = datetime.fromisoformat(log['completed_at_utc']).astimezone(timezone(timedelta(hours=8)))
    report.p('Benchmark completed ' + local.strftime('%d %B %Y, %H:%M:%S') + ' Asia/Manila. Four original known clips; 1,700 decoded frames; one sequential pass. Processing FPS = total frames / total processing seconds; milliseconds/frame = 1000 × total processing seconds / total frames. Per-clip FPS values are not averaged arithmetically.')
    report.table(['Laptop version', 'Frames', 'Processing FPS', 'ms/frame', 'Count MAE'], [
        ['Checkpoint 3 main (historical)', 1700, f"{previous['processing_fps']:.2f}", f"{previous['processing_ms_per_frame']:.2f}", '3.50'],
        ['Calibrated checkpoint 4 current', 1700, f"{current['processing_fps']:.2f}", f"{current['processing_ms_per_frame']:.2f}", f"{current['count_mae']:.2f}"],
    ])
    report.p(f"Observed change: {current['processing_fps'] - previous['processing_fps']:+.2f} FPS ({fps_change:+.1f}%; {current['processing_fps'] / previous['processing_fps']:.2f}× throughput); {current['processing_ms_per_frame'] - previous['processing_ms_per_frame']:+.2f} ms/frame ({ms_change:+.1f}%). Both logs contain the same four clip identities and frame counts. This is an observed comparison across runs, not a controlled estimate of code-only speedup.")
    older = {r['clip_id']: r for r in old['runs'] if r['method'] == 'main'}
    report.table(['Clip / frames', 'CP3 FPS / ms', 'Current FPS / ms', 'Reference / CP3 / current reps', 'Current form'], [
        [NAMES[r['exercise']] + f" / {r['frames']}", f"{older[r['id']]['processing_fps']:.2f} / {older[r['id']]['processing_ms_per_frame']:.2f}", f"{r['processing_fps']:.2f} / {1000 * r['processing_seconds'] / r['frames']:.2f}", f"{r['reference_reps']} / {older[r['id']]['repetition_count']} / {r['estimated_reps']}", r['prediction']]
        for r in log['runs']
    ])
    report.p('Timing scope: ' + log['timing_scope'] + ' It does not establish displayed webcam FPS, end-to-end GUI latency, or sustained physical-camera performance. CP3 full-run throughput includes output work; current decode-plus-processing throughput excludes output encoding, so those end-to-end fields are not compared.')
    runtime = log['runtime']
    report.table(['Environment field', 'Current laptop evidence'], [
        ['CPU / RAM (post-run verification)', f"{hardware['cpu']}; {hardware['ram_gib']:.2f} GiB"],
        ['OS / logical processors', f"{runtime['platform']}; {runtime['logical_cpus']} logical CPUs"],
        ['Power scheme captured during benchmark', runtime['windows_hardware']['power_scheme']],
        ['Python', runtime['python']],
        *[[name, value] for name, value in runtime['dependencies'].items()],
        ['Benchmark-time CPU/RAM capture', 'Incomplete: null CPU, RAM 0; raw log retained'],
    ])
    report.p('CPU model and RAM were checked after the run using the Windows registry and GlobalMemoryStatusEx, recorded in docs/calibration/laptop_environment_verification.json. They agree with the historical CP3 hardware (AMD Athlon Silver 3050U; 5.94 GiB). Windows build, Python 3.13.0, two logical CPUs and Balanced power also agree across logs. CP3 does not record dependency versions, so dependency parity cannot be verified. Plugged-in state, thermals and background workload were not logged. Current dependency names/versions above are exactly the reported distribution metadata, including mediapipe 1.2.0.')
    report.p('Known clips show 75% form agreement (three correct decisions, one jumping-jack abstention), count MAE 1.75 reps/clip, and one exact count. All four reference forms are correct and user-supplied after earlier predictions. These clips cannot establish incorrect-form recall or independent generalization. The squat row records calibration_id=form-rules-v1; push-up was not promoted, and lunge/jack form rules remain provisional.')
    report.p('Validation: ' + validation['status'] + '. All frozen source/profile/plan, model, manifests, clip hashes, frame counts, summaries and CSV values were checked. Submission source is byte-identical to commit ' + SNAPSHOT + '. Local tag status: ' + validation['tag_status'] + '.')
    report.p(validation['run_portability_note'])
    report.p('Physical webcam acceptance: PENDING. Camera open/start/stop/restart, release on Quit, lighting/occlusion behavior, and sustained displayed FPS on an actual camera require a separately recorded acceptance run.')


def archive_superseded():
    """Keep prior versions under history; leave one current submission DOCX."""
    sources = [M4 / 'Checkpoint4_Application_Testing_Report.docx',
               CAL / 'Calibrated_Form_Results.docx',
               M4 / 'Checkpoint4_Current_Technical_Report.docx',
               M4 / 'Checkpoint4_Current_Technical_Report.md']
    archived = []
    for path in sources:
        if not path.exists():
            continue
        destination = path.parent / 'history' / path.name
        require(path.resolve().is_relative_to(ROOT.resolve()), 'Archive source outside project')
        require(destination.resolve().is_relative_to(ROOT.resolve()), 'Archive target outside project')
        destination.parent.mkdir(parents=True, exist_ok=True)
        require(not destination.exists(), 'Archive already exists: ' + str(destination))
        shutil.move(str(path), str(destination))
        archived.append(destination)
    return archived


def main():
    log = load(CAL / 'laptop_benchmark.json')
    freeze = load(CAL / 'evaluation_freeze.json')
    validation = validate(log, freeze)
    save_json(CAL / 'laptop_benchmark_validation.json', validation)
    old = load(CP3 / 'laptop_test_log.json')
    hardware = load(CAL / 'laptop_environment_verification.json')
    heldout = load(M4 / 'heldout_results.json')
    known = load(M4 / 'known_clip_results.json')
    final = load(CAL / 'prospective_results.json')
    fit = load(CAL / 'fitting_results.json')
    plan = load(CAL / 'plan.json')
    cases = load(M4 / 'test_cases.json')
    manifest = {r['id']: r for r in load(CP3 / 'test_manifest.json')}
    require(all(manifest[r['id']]['sha256'] == r['sha256'] for r in log['runs']), 'CP3 workload identity mismatch')
    require(len([r for r in old['runs'] if r['method'] == 'main']) == 4, 'Incomplete CP3 comparison')
    for row in log['runs']:
        previous = next(r for r in old['runs'] if r['method'] == 'main' and r['clip_id'] == row['id'])
        require(previous['frames'] == row['frames'] and previous['exit_code'] == 0, 'CP3 workload frames/failure mismatch')
    for name in ['fit', 'validation', 'prospective']:
        participants = {r['participant'] for r in plan['partitions'][name]}
        for other in ['fit', 'validation', 'prospective']:
            if other != name:
                require(not participants & {r['participant'] for r in plan['partitions'][other]}, 'Calibration participant leakage')

    report = Report()
    report.heading('POSTURE CHECK', 0)
    report.p('Draft Technical Documentation: Checkpoint 4, Hand-in Item 6')
    report.p('19 November 2026 (Asia/Manila). Introduction, data, method and experiments. This is the single current documentation draft; it documents the application and testing already completed for items 1-5.')
    report.heading('1. Introduction')
    report.p('Posture Check is a computer-vision application that estimates exercise movement and gives provisional form feedback from a standard camera or recorded media. Its purpose is to make pose, movement phase, repetition estimates and rule-based feedback visible in one desktop interface. The project investigates whether pretrained pose landmarks and interpretable angle rules can support this workflow without training new pose-estimation weights.')
    report.p('The implemented scope is operator-selected squat, push-up, lunge and jumping jacks. The system combines MediaPipe Lite pose tracking with geometry checks, temporal movement analysis and a calibrated clip/session decision for squat. Push-up retains its existing rules because its fitted candidate did not satisfy promotion requirements. Lunge and jumping-jack form assessment remains provisional.')
    report.p('This draft explains the data allocation, processing method and completed experiments, including comparison with checkpoint 3 and the measured demo-laptop speed. The original 12-clip test, new 16-clip prospective evaluation and four known speed/regression clips serve different purposes and are reported separately. The results support a working prototype with limited form accuracy; physical webcam acceptance remains pending.')
    report.heading('2. Data')
    report.table(['Set', 'Clips / people', 'Purpose'], [
        ['Original exposed side-view test', '12 / 3 (018, 020, 022)', 'Historical CP3 vs pre-calibration v2 comparison; excluded from calibration'],
        ['Calibration fitting', '54 / 14 overall; 13 push-up', 'Fit candidates; leave-one-fitting-participant-out selection'],
        ['Calibration validation', '16 / 4 (004, 006, 011, 024)', 'Promotion guard; no test tuning'],
        ['New prospective test', '16 / 4 (017, 019, 021, 023)', 'Reserved from unused original training inventory before extraction'],
        ['Known four clips', '4; user-supplied excerpts', 'Speed/regression only; previously inspected'],
    ])
    report.p('Fitting, validation and prospective participants are disjoint in plan.json; the original CSV split files remain as historical inventory. The prospective set is a revised split, not newly acquired external data. Whole-clip source labels do not label every frame or repetition. Both exposed test sets now require replacement for any future parameter tuning.')
    report.heading('3. Method')
    report.heading('3.1. Integrated application and processing pipeline', 2)
    report.p('The desktop app integrates a selected-exercise MediaPipe Lite VIDEO pipeline, conservative black-border removal, confidence and geometry gates, temporal smoothing, movement counting, per-frame geometry feedback and a cumulative session-form estimate. Users select squat, push-up, lunge or jumping jacks; automatic exercise recognition is not implemented. File images/videos use the CLI. Launch the GUI with python app.py.')
    report.p('Start Camera moves the home menu into a sidebar. The preview shows skeleton lines, feedback, movement phase, estimated reps and FPS. Settings select camera index, mirror preview and skeleton display. Stop/Start starts a new session; Quit releases capture. Session form updates about once per second from cumulative angle summaries. Whole-clip calibration does not establish frame-level or live-prefix form accuracy. The GUI does not save camera frames.')
    report.picture(M4 / 'evidence/home.png', 'Home interface from historical cloud GUI integration; recorded input, not physical webcam evidence.')
    report.picture(M4 / 'evidence/live.png', 'Accepted preview with pose, feedback and counters during historical video-substitution integration.')
    report.picture(CAL / 'evidence/session_estimate.png', 'Calibrated session estimate during the validation-video GUI smoke test. Capture release and window closure passed; no physical-camera claim.')
    report.heading('3.2. Calibration procedure and deployment decisions', 2)
    report.p('Candidate rules use numerical angle distributions only. Filenames, subject IDs, recording length, FPS, quality and per-frame form labels are excluded from classifier inputs. Fixed gates require 30 valid frames, 50% coverage and 20 degrees of movement. Depth 1/2 and minimum leaves 4/6 are selected using participant-held-out predictions; leaves require at least two subjects. Promotion requires higher validation macro F1 with no loss of incorrect-form recall or fitting OOF macro F1.')
    report.table(['Exercise', 'Fit OOF macro F1', 'Validation macro F1 before / candidate', 'Decision'], [
        [NAMES[ex], f"{value['selected_fit_oof']['macro_f1']:.3f}", f"{value['uncalibrated_validation']['macro_f1']:.3f} / {value['calibrated_validation']['macro_f1']:.3f}", 'Enabled' if value['enabled'] else 'Not promoted']
        for ex, value in fit['exercises'].items()
    ])
    report.p('Squat uses the fitted hip-angle p10 split at 71.15 degrees, a dataset-derived decision threshold rather than a universal recommended angle. Validation incorrect-squat recall increases from 0% to 50% while accuracy stays 4/8. Push-up ties validation macro F1 at 0.619 and lowers incorrect-form recall from 75% to 50%, so it is not promoted. Lunge/jack form rules remain provisional. Pose weights, preprocessing, motion counting and geometry gates were not calibrated.')
    report.heading('4. Experiments and results')
    report.p('The following experiments were completed before this documentation revision. No new inference or parameter tuning was performed to prepare this draft. Source logs produced by src/evaluate.py are retained as the measured evidence.')
    report.heading('4.1. Experimental setup and version verification', 2)
    report.p('The complete laptop log matches the calibrated evaluation freeze, including 22 source/profile/plan hashes, the Lite model checksum, all four input hashes, four split manifests, 1,700 decoded frames and recomputed aggregate/per-exercise summaries. JSON and CSV agree. The same 22 files in submission commit ' + SNAPSHOT + ' match the freeze byte for byte. Tag verification: ' + validation['tag_status'] + '. No application/model parameters, decision thresholds, freeze files or tags were modified for this report.')
    report.p('Machine-readable audit: docs/calibration/laptop_benchmark_validation.json. Raw log: docs/calibration/laptop_benchmark.json; completion 2026-11-18T15:51:50.929943+00:00. Exact log checksum is ' + validation['log_sha256'] + '.')
    report.heading('4.2. Evaluation metrics and comparison design', 2)
    report.p('Whole-clip form accuracy is the number of predictions matching source labels divided by all labelled clips; an abstention counts as a miss. Per-class precision, recall and F1 describe class-specific errors; macro F1 averages the correct/incorrect class F1 scores. Coverage is the fraction of accepted frames or assessed clips and does not establish landmark accuracy. Repetition-count MAE is the average absolute difference from available reference counts and is reported only for the known four clips. Processing FPS and milliseconds per frame use total decoded frames and summed processing time, excluding decoding, rendering, encoding and model initialization.')
    report.p('The historical experiment reran checkpoint 3 and pre-calibration v2 on the same 12 original test clips. The new prospective experiment compares uncalibrated and deployed decisions on the same 16 reserved clips and the same single tracked inference stream. This isolates the form-decision change but does not provide two independent speed runs. The demo-laptop comparison uses the same four known excerpts as checkpoint 3; these are a regression workload rather than a new held-out accuracy test.')
    report.heading('4.3. Test results on two distinct sets', 2)
    report.table(['Set / metric', 'Reference method', 'Compared method'], [
        ['Original 12: accuracy', pct(heldout['summary']['cp3']['classification']['accuracy_all']), pct(heldout['summary']['current']['classification']['accuracy_all'])],
        ['Original 12: macro F1', '0.556 (CP3 rerun)', '0.413 (pre-calibration v2)'],
        ['Original 12: usable-pose coverage', pct(heldout['summary']['cp3']['feature_coverage']), pct(heldout['summary']['current']['feature_coverage'])],
        ['New prospective 16: accuracy', '43.8% (7/16; uncalibrated tracked)', '50.0% (8/16; deployed calibrated)'],
        ['New prospective 16: macro F1', '0.430', '0.517'],
        ['New prospective 16: incorrect-form recall', '25.0%', '50.0%'],
        ['New prospective 16: correct-form recall', '62.5%', '50.0%'],
        ['New prospective 16: assessed / abstained', '15 / 1', '15 / 1'],
    ])
    report.p('The historical 41.7% and prospective 50.0% use different subjects and cannot be presented as a matched improvement. The valid calibration comparison is 43.8% to 50.0% on the same 16 prospective clips and shared tracked features. The original historical evaluation compared reconstructed CP3 source and v2 on the same 12 clips; it does not evaluate calibrated v3 on those clips. Coverage is accepted geometry, not independently measured landmark accuracy.')
    report.table(['Prospective exercise (8 each)', 'Accuracy before / after', 'Macro F1 before / after'], [
        [NAMES[ex], pct(final['by_exercise']['uncalibrated'][ex]['classification']['accuracy_all']) + ' / ' + pct(final['by_exercise']['current'][ex]['classification']['accuracy_all']), f"{final['by_exercise']['uncalibrated'][ex]['classification']['macro_f1']:.3f} / {final['by_exercise']['current'][ex]['classification']['macro_f1']:.3f}"] for ex in ['squat', 'pushup']
    ])
    for method in ['uncalibrated', 'current']:
        matrix = final['summary'][method]['classification']['confusion_matrix']
        report.table(['Prospective ' + method + ' reference', 'Predicted correct', 'Incorrect', 'Abstain'], [[label, matrix[label]['correct'], matrix[label]['incorrect'], matrix[label]['unassessable']] for label in ['correct', 'incorrect']])
    report.p('Deployed prospective outcomes retain four false accepts, three false flags and one abstention. Incorrect-squat recall improves from 1/4 to 3/4; one more correct squat is falsely flagged. Push-up remains 3/8. Repetition-reference labels are unavailable on both Mendeley evaluation sets, so no held-out count MAE is reported.')
    laptop_section(report, log, old, hardware, validation)
    report.heading('4.5. Historical cloud timing', 2)
    report.table(['Cloud workload / version', 'Clips / frames', 'FPS', 'ms/frame'], [
        ['Original 12-clip test: CP3 rerun', '12 / 4,124', f"{heldout['summary']['cp3']['processing_fps']:.2f}", f"{heldout['summary']['cp3']['processing_ms_per_frame']:.2f}"],
        ['Original 12-clip test: pre-calibration v2', '12 / 4,124', f"{heldout['summary']['current']['processing_fps']:.2f}", f"{heldout['summary']['current']['processing_ms_per_frame']:.2f}"],
        ['Four known clips: pre-calibration v2', '4 / 1,700', f"{known['summary']['current']['processing_fps']:.2f}", f"{known['summary']['current']['processing_ms_per_frame']:.2f}"],
        ['Prospective shared feature pass: calibrated v3', '16 / 4,517', f"{final['summary']['current']['processing_fps']:.2f}", f"{final['summary']['current']['processing_ms_per_frame']:.2f}"],
    ])
    report.p('Cloud environment: ' + json.dumps(final['runtime'], ensure_ascii=False) + '. Shared cloud CPU scheduling and different Python/dependency versions prevent attribution of cloud/laptop differences to code. Prospective uncalibrated/current decisions reuse the same inference stream; the duplicated timing summaries are not two independent speed measurements.')
    report.heading('5. Discussion and limitations')
    report.p('Evidence covers only four prospective participants and two calibrated-candidate exercise modes. Source labels combine faults that projected 2D angles may not distinguish; no independent landmark ground truth was collected. Side-view assumptions, hidden joints, unsupported variations and view ambiguity limit assessment. Lunge/jacks lack a suitable paired independent form set; incorrect-form performance cannot be inferred from four all-correct regression references. The session estimate is provisional and is not medical guidance or validated live coaching.')
    report.p('Timing is a single sequential pass, with unmatched dependency provenance between historical/current laptop runs and incomplete benchmark-time CPU/RAM capture. Hardware verification is post-run. No repeated-run variance, physical-camera throughput, plugged-in state or thermal controls were recorded. Preserve abstention and collect new independently annotated faults, rep boundaries and participants before further tuning or stronger claims.')
    report.heading('Appendix A. Recorded test cases and integration evidence')
    report.p(f"Historical v2 inventory: {cases['total']} cases, {cases['passed']} PASS, {cases['failed']} FAIL, {cases['hard_or_edge']} hard/edge cases. The 12 real classification cases remain separate from 12 functional passes and one GUI integration pass. These tests were not rerun for this documentation update. Prior reports record 56 software tests for v2 and 63 for calibrated v3; those are recorded run claims, not new execution results.")
    report.table(['ID', 'Input', 'Condition', 'Expected', 'Actual', 'Pass/fail'], [[c['id'], c['input'], c['condition'], json.dumps(c['expected'], ensure_ascii=False) if isinstance(c['expected'], dict) else c['expected'], json.dumps(c['actual'], ensure_ascii=False) if isinstance(c['actual'], dict) else c['actual'], c['status']] for c in cases['cases']])
    report.p('Functional traces/landmarks are synthetic; camera-open failure is mocked; black PNG/three-frame video checks exercise actual MediaPipe/codecs. Neither mocked devices nor recorded-video GUI substitution verifies physical camera acceptance. Classification PASS/FAIL values are not combined with software tests to calculate accuracy.')
    before = {r['id']: r for r in final['runs'] if r['method'] == 'uncalibrated'}
    report.table(['Prospective input', 'Reference', 'Uncalibrated', 'Deployed', 'Status'], [[r['id'], r['reference_form'], before[r['id']]['prediction'], r['prediction'], 'PASS' if r['prediction'] == r['reference_form'] else 'FAIL'] for r in final['runs'] if r['method'] == 'current'])
    report.table(['Integration / acceptance check', 'Recorded result / scope'], [
        ['Calibrated validation video / codec', 'PASS: 435 frames; incorrect; form-rules-v1; validation_smoke.json'],
        ['Calibrated session UI', 'PASS: review technique; capture released; window closed; gui_smoke.json; validation video substituted'],
        ['Current laptop file benchmark', 'PASS: four complete runs / 1,700 frames; exact hash/summary validation'],
        ['Actual physical webcam open/start/stop/restart/Quit', 'PENDING — no physical-camera evidence'],
        ['Actual camera lighting / occlusion / view feedback', 'PENDING — recorded/synthetic evidence only'],
        ['Sustained physical-camera displayed FPS / latency', 'PENDING — processing throughput is not a GUI camera measurement'],
        ['Live-prefix / per-frame form accuracy', 'PENDING — no independently labelled live-prefix evaluation'],
    ])
    report.heading('Appendix B. Evidence and reproduction')
    report.p('Authoritative current files: config/form_rules.json; docs/calibration/plan.json, fitting_results.json, evaluation_freeze.json, prospective_results.json/csv, laptop_benchmark.json/csv, laptop_environment_verification.json, laptop_benchmark_validation.json, validation_smoke.json and gui_smoke.json. Historical measurements remain under docs/phase3 and docs/milestone4. The old v2 source ZIP remains docs/calibration/reference/uncalibrated_v2_code.zip.')
    report.p('Rebuild this single draft with python scripts/milestone4/update_current_report.py (report-only python-docx; outputs/report_dependencies is supported). Prior report versions are archived in history/ folders. Raw measurements, frozen model/profile parameters and checkpoint references are preserved. No test-set inference is rerun by the builder.')
    output = M4 / 'Checkpoint4_Technical_Documentation_Draft.docx'
    report.doc.save(output)
    (M4 / 'Checkpoint4_Technical_Documentation_Draft.md').write_text('\n'.join(report.md), encoding='utf-8')
    with zipfile.ZipFile(output) as archive:
        require(archive.testzip() is None, 'Invalid DOCX archive')
    Document(output)
    archives = archive_superseded()
    print(output.relative_to(ROOT))
    for path in archives:
        print('Archived:', path.relative_to(ROOT))
    print(f'PASS: {len(validation["checks"])} evidence checks; single item-6 DOCX reopens; no new inference/model/tag changes')


if __name__ == '__main__':
    main()
