"""Update the supplied Sections 6-9 DOCX using the measured guided-rule results.

Requires python-docx (or the existing outputs/report_dependencies installation).
The input document is preserved; an updated copy is written inside the repository.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/report_dependencies'))
from docx import Document
from docx.shared import Pt
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement


def replace(paragraph, text):
    # Retain the original paragraph and first-run formatting.
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ''
    else:
        paragraph.add_run(text)


def cell_text(cell, text):
    replace(cell.paragraphs[0], text)
    for paragraph in cell.paragraphs[1:]:
        paragraph._element.getparent().remove(paragraph._element)


def new_row(table, texts):
    row = deepcopy(table.rows[-1]._tr)
    table._tbl.append(row)
    for cell, text in zip(table.rows[-1].cells, texts):
        cell_text(cell, text)
    return table.rows[-1]


def insert_paragraph(before, text, style='normal'):
    node = OxmlElement('w:p')
    before._p.addprevious(node)
    paragraph = Paragraph(node, before._parent)
    paragraph.style = style
    paragraph.add_run(text)
    return paragraph


def insert_table(before, template, rows):
    node = deepcopy(template._tbl)
    before._p.addprevious(node)
    table = Table(node, before._parent)
    while len(table.rows) > 2:
        table._tbl.remove(table.rows[-1]._tr)
    for cell, text in zip(table.rows[0].cells, rows[0]):
        cell_text(cell, text)
    for cell, text in zip(table.rows[1].cells, rows[1]):
        cell_text(cell, text)
    for row in rows[2:]:
        new_row(table, row)
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)
    return table


def update(source, destination):
    if source.resolve() == destination.resolve():
        raise ValueError('Preserve the original: choose a different output path')
    results_path = ROOT / 'docs/guided_evaluation/results.json'
    results = json.loads(results_path.read_text(encoding='utf-8'))
    audit = json.loads((results_path.parent / 'audit.json').read_text(encoding='utf-8'))
    if results['status'] != 'complete' or audit['status'] != 'passed':
        raise ValueError('A completed, audited evaluation is required')
    if hashlib.sha256(results_path.read_bytes()).hexdigest() != audit['result_sha256']:
        raise ValueError('Evaluation results changed after the audit')
    document = Document(source)
    paragraphs = list(document.paragraphs)
    tables = list(document.tables)
    if len(tables) != 17 or not paragraphs[27].text.startswith('There is no measured baseline'):
        raise ValueError('This updater expects the supplied original Sections 6-9 document')
    baseline = results['summary']['fixed_clip_rules']
    guided = results['summary']['guided_session_rules']
    percent = lambda value: f'{value:.2%}'
    score = lambda value: f'{value:.3f}'
    accuracy, macro, coverage = percent(guided['accuracy_all']), score(guided['macro_f1']), percent(guided['classification_coverage'])

    replacements = {
        3: 'Scope. This standalone addition contains Sections 6–9 only. The application source is based on commit 4551276. Updated 21 November 2026 with a frozen, audited comparison of the current guided-session rules and existing fixed clip rules. Historical CLI experiments remain separate because their decision rules and evaluation conditions differ. The new run is identified by docs/guided_evaluation/freeze.json and its source/model/input hashes, rather than by an uncommitted revision name.',
        27: 'The report now includes a matched comparison of the current guided-session assessor and existing uncalibrated fixed clip rules (E7). On 16 previously exposed squat/push-up videos, both methods scored ' + accuracy + ' accuracy and ' + macro + ' macro-F1, with ' + coverage + ' coverage. They agreed on every clip. Earlier rows below remain historical measurements; “calibrated CLI” is a different classifier, not the current guided final method. E7 assesses complete prerecorded clips, not target-based GUI stopping or live-camera performance.',
        32: 'Evidence: docs/results/mendeley_squat_side_validation.json; docs/phase3/reference_metrics.json; docs/milestone4/heldout_results.json; docs/calibration/prospective_results.json; docs/guided_evaluation/{freeze,results,audit}.json. The E7 breakdown and limitations appear in Section 7.7.',
        59: 'At commit 4551276, the existing 74 automated tests passed. The evaluation addition brings the suite to 77 passing tests, including three checks for abstention scoring, GUI-label mapping and agreement with direct assessor calls on shared timed records. Eleven original tests are dedicated session tests. They cover all four modes, form tips, count/form separation, tracking loss, idle lead-in, recording cadence, cleanup, target stop and countdown cancellation. These are software checks, separate from human-video classification measurements.',
        62: 'Evidence: docs/phase3/{reference_metrics,laptop_test_log}.json; docs/calibration/laptop_benchmark.json; tests/{test_session,test_guided_evaluation}.py; src/posture_check/{session,gui}.py. Synthetic examples are software evidence; the separate E7 video classification measurements are reported in Section 7.7.',
        84: 'Those findings have different scopes. Feature availability, classification correctness, repetition accuracy and interface behavior are separate outcomes. The original test shows why: usable-frame coverage rose while classification accuracy fell. E7 now directly measures the current guided assessor on 16 complete human-recorded clips, but finds no classification gain over the matched fixed-rule baseline: both score ' + accuracy + ' accuracy and ' + macro + ' macro-F1. Historical calibrated accuracy and count error still do not transfer to the guided application.',
        89: 'The measured datasets are small and their broad source labels are not an expert fault-by-fault reference. E7 provides a guided-rule measurement on previously exposed squat/push-up videos, not a new independent test. Balanced lunge and jumping-jack form evaluation is still missing. Pose coverage is not landmark localization accuracy because no joint-coordinate ground truth was scored. Target-truncated guided sessions, active-recording webcam speed, repetition-count accuracy and improvement-tip correctness still require separate measurements. Software-test success cannot replace those tests.',
        90: 'Evidence: docs/calibration/prospective_results.json; docs/guided_evaluation/{freeze,results,audit}.json; docs/phase3/failure_manifest.json; docs/GUIDED_SESSION.md; src/posture_check/session.py; docs/Project_Proposal.pdf.',
        93: 'Posture Check has progressed from image-processing feasibility to an integrated four-exercise guided desktop prototype. The evidence supports feature integration, reproducible historical experiments, and a new matched complete-clip assessment of the current guided rules. The guided assessor achieved ' + accuracy + ' accuracy and ' + macro + ' macro-F1 on 16 previously exposed squat/push-up clips, identical to its fixed-rule baseline. No classification improvement was demonstrated. The project has not demonstrated the original 80% accuracy target or the current application’s controlled live-camera performance target.',
        96: '1. Extend the initial guided-rule evaluation with independently reviewed data. E7 establishes a small source-labeled, previously exposed comparison, not an untouched final test. Obtain new form labels, fault descriptions and manual rep counts for all four modes, with review independent of predictions. Keep test participants separate from any threshold-development examples. Score macro-F1, incorrect recall, abstentions and count MAE on untouched inputs. Expected benefit: a more defensible estimate of guided-rule reliability.',
        97: '2. Improve failure mechanisms using separate development data. E7 missed six of eight source-incorrect clips, with no gain over the fixed rules. Investigate which labeled faults are outside the configured criteria; add per-repetition segmentation and fault-specific checks where supported by reviewed examples. Study viewpoint, cropping and confidence failures. Tune counting separately from form checks and retain abstention for weak evidence. Freeze changes before evaluation on new test clips; do not retune against E7 and call it independent validation.',
        99: 'Evidence: Original objectives and targets: docs/Project_Proposal.pdf. Current implementation: docs/GUIDED_SESSION.md and src/posture_check/session.py. New comparison: docs/guided_evaluation/{README.md,freeze.json,results.json,results.csv,audit.json}; scripts/evaluate_guided_rules.py. Quantitative conclusions remain version-specific. No predicted future gains are reported as achieved results.',
    }
    for index, text in replacements.items():
        replace(paragraphs[index], text)

    cell_text(tables[0].rows[1].cells[1], 'Pretrained pose landmarks and fixed per-frame geometry; no temporal repetition counter in the frame baseline. The early eight-clip squat result additionally aggregated measurements over whole videos; it was not single-frame classification.')
    cell_text(tables[0].rows[4].cells[1], 'Fixed guided-session-rules-v1; four exercise modes, target reps, countdown, automatic stop, video and summary. E7 evaluates its unmodified complete-clip assessor on squat/push-up videos; it does not load the historical calibration profile or measure the target-stop GUI workflow.')
    new_row(tables[0], ['E7 matched baseline', 'Existing summarize_for_exercise(..., calibrated=False) applied to all shared temporal records. This whole-clip fixed-rule baseline is distinct from the frame baseline and historical calibrated classifier.'])
    new_row(tables[1], ['E7 guided-rule evaluation', 'Windows 11 build 26200; Python 3.13.0; MediaPipe 1.2.0, NumPy 2.2.3, OpenCV-contrib 4.11.0.86, Pillow 11.1.0. One shared inference pass per clip. Classification only; no independent timing comparison or live webcam-speed claim.'])
    new_row(tables[2], ['E7: current guided-rule comparison', 'All 16 previously reserved E5 clips reused: participants 017, 019, 021, 023; 8 squat / 8 push-up; 8 source-correct / 8 source-incorrect.', 'Matched fixed-clip versus guided-session decisions on identical processed frames. Previously exposed data; not a new independent test. No threshold tuning or AI01 annotation use.'])
    cell_text(tables[5].rows[1].cells[0], '8-clip validation: early squat clip rules')
    new_row(tables[5], ['E7 reused 16: current guided rules', accuracy + ' (7/16)', macro, coverage + ' (15/16)'])
    for cell, text in zip(tables[5].rows[8].cells, ['E7 reused 16: fixed clip baseline', percent(baseline['accuracy_all']) + ' (7/16)', score(baseline['macro_f1']), percent(baseline['classification_coverage']) + ' (15/16)']):
        cell_text(cell, text)
    cell_text(tables[15].rows[1].cells[1], 'Historical calibrated CLI: accepted 4/8 incorrect and flagged 3/8 correct clips, with one correct abstention. Current E7 guided rules and matched fixed baseline: accepted 6/8 source-incorrect and flagged 2/8 source-correct clips, with one correct abstention. These are separate experiments. Broad source labels may encode faults outside the few configured 2D checks.')
    objective_updates = {
        2: 'All four selected modes have features, phase/count logic and session rules. Historical CLI tests and E7 guided complete-clip evaluation cover squat/push-up. E7 reuses exposed inputs; balanced guided evaluation for lunge/jumping jacks is missing.',
        3: 'Implemented as configured 2D checks with abstention. E7 guided accuracy is ' + accuracy + ', macro-F1 ' + macro + ', coverage ' + coverage + '; identical to the matched fixed baseline. Incorrect recall is 25%. The historical calibrated 50.0% result is separate.',
        5: 'Historical matrices, count errors and laptop processing logs exist. E7 adds frozen methods/inputs, 16 paired video decisions, per-class metrics and an artifact audit. Independently reviewed guided-session labels, manual count references, landmark scoring and end-to-end webcam timing remain pending.',
        6: '80% accuracy was not demonstrated: current guided E7 accuracy is ' + accuracy + ' on previously exposed source-labeled videos. Historical offline CLI throughput of 23.67 FPS does not verify the controlled guided-webcam ≥10-FPS target.',
    }
    for row, text in objective_updates.items():
        cell_text(tables[16].rows[row].cells[1], text)

    before = paragraphs[25]
    insert_paragraph(before, '6.6 Current guided-rule evaluation protocol (E7)', 'Heading 2')
    for text in [
        'E7 was run on 21 November 2026, Philippine time. Before inference, the evaluator froze the source, official MediaPipe Lite model and all 16 input hashes in docs/guided_evaluation/freeze.json. The entire historical reserved selection was retained without prediction-dependent filtering: four participants, eight side-view squats and eight side-view push-ups, with four source-correct and four source-incorrect clips per exercise. These videos had already been evaluated historically; E7 is a matched comparison on exposed data, not a fresh held-out result.',
        'The reference is one original Mendeley correct/incorrect label per whole video. These are broad dataset labels, not independently verified expert or per-fault annotations. The preliminary AI01 repetition annotations were not used. No new model training, threshold fitting, calibration promotion or post-result rule selection occurred.',
        'Baseline: the existing uncalibrated summarize_for_exercise(..., calibrated=False) over all temporal records. Final: unmodified ExerciseSession.add/assess, retaining initial-idle exclusion, a 15-frame lead-in and the 10-frame quality gate. The baseline retains its existing 30-frame gate. Both methods share one enhanced, tracked VIDEO pose pass and identical smoothed features. The GUI analyzer’s nominal 30-FPS configuration is retained, with dt_seconds=1/media_fps replacing live elapsed time; the guided counter is installed as in the application.',
        'Each video is processed to its end. The evaluation does not apply a target-repetition cutoff, countdown, preview or recording. Thus it measures complete-clip assessment, not automatic stopping, target-truncated session accuracy, live recording speed, count accuracy or tip correctness. Guided Good maps to correct, Bad to incorrect, and Unable to assess remains an abstention. Abstentions count as misses in all-clip accuracy and as false negatives for their source class in binary macro-F1.',
        'Reproduce after installing dependencies and obtaining the official model and Mendeley videos: python scripts/evaluate_guided_rules.py --output outputs/guided_rerun/results_rerun.json. Use a new output filename and stem. The command verifies frozen code/model/input hashes and saves JSON, CSV and Markdown results; the repository instructions describe paths and environment requirements.',
        'Evidence: scripts/evaluate_guided_rules.py; tests/test_guided_evaluation.py; docs/guided_evaluation/{README.md,freeze.json,results.json,results.csv,audit.json}.',
    ]:
        insert_paragraph(before, text)

    before = paragraphs[81]
    insert_paragraph(before, '7.7 Current guided rules versus matched fixed baseline (E7)', 'Heading 2')
    insert_paragraph(before, 'Both methods produced identical predictions for all 16 clips. Their accuracy was ' + accuracy + ' (7/16), macro-F1 ' + macro + ' and classification coverage ' + coverage + ' (15/16). Assessed-only accuracy was ' + percent(guided['accuracy_assessed']) + ' (7/15). The guided rules did not improve classification on this selection; this negative result is retained without changing thresholds.')
    rows = [['Method', 'Accuracy (all)', 'Macro-F1', 'Coverage']]
    for method, label in [('fixed_clip_rules', 'Fixed clip baseline'), ('guided_session_rules', 'Guided final assessor')]:
        metrics = results['summary'][method]
        rows.append([label, percent(metrics['accuracy_all']) + ' (7/16)', score(metrics['macro_f1']), percent(metrics['classification_coverage']) + ' (15/16)'])
    insert_table(before, tables[5], rows)
    insert_paragraph(before, 'Confusion matrix, shared by both methods. Rows are source labels and columns are predictions. Correct/incorrect correspond to guided Good/Bad; Unable to assess is retained explicitly.', 'Heading 3')
    matrix_rows = [['Reference', 'Correct', 'Incorrect', 'Unable to assess']]
    for truth, row in guided['confusion_matrix'].items():
        matrix_rows.append([truth.capitalize(), str(row['correct']), str(row['incorrect']), str(row['unassessable'])])
    insert_table(before, tables[5], matrix_rows)
    insert_paragraph(before, 'Per-class scores, shared by both methods', 'Heading 3')
    rows = [['Source class / support', 'Precision', 'Recall', 'F1']]
    for label, metrics in guided['per_class'].items():
        rows.append([label.capitalize() + ' / ' + str(metrics['support']), score(metrics['precision']), score(metrics['recall']), score(metrics['f1'])])
    insert_table(before, tables[5], rows)
    insert_paragraph(before, 'Exercise breakdown, shared by both methods', 'Heading 3')
    rows = [['Exercise / clips', 'Accuracy', 'Macro-F1', 'Coverage']]
    for exercise in ('squat', 'pushup'):
        metrics = results['by_exercise'][exercise]['guided_session_rules']
        rows.append([('Squat' if exercise == 'squat' else 'Push-up') + ' / 8', percent(metrics['accuracy_all']), score(metrics['macro_f1']), percent(metrics['classification_coverage'])])
    insert_table(before, tables[5], rows)
    for text in [
        'Both methods accepted six of eight source-incorrect clips, flagged two of eight source-correct clips and abstained on one source-correct squat. Incorrect-form recall was 25%. The abstention was insufficient observed movement, not a confirmed form fault. High assessment coverage therefore did not imply reliable classification.',
        'The matched methods share most squat/push-up form thresholds. Their different idle handling and minimum-frame gates did not change final labels on these clips. Broad source labels may describe faults outside the configured checks, but that mismatch was not independently adjudicated and does not invalidate or remove the observed errors.',
        'Do not treat the historical calibrated 50.0% score and current guided ' + accuracy + ' as a controlled improvement/regression comparison: the decision method and runtime differ. E7’s valid comparison is the two methods rerun here on shared features. It supplies no balanced guided evidence for lunge/jumping jacks, no manually referenced repetition error and no measurement of target-stop behavior or webcam speed.',
        'The completed run passed 160 post-run artifact checks, including source/model/input/evidence hashes, paired selection, decoded frame counts, replayed assessments, label mapping and independent metric recomputation. The software suite passed 77 tests. Neither artifact checks nor software tests establish expert-label validity or exercise safety.',
        'Evidence: docs/guided_evaluation/{freeze.json,results.json,results.csv,results.md,audit.json}; compressed shared frame records under outputs/guided_evaluation/results/. Runtime: Windows 11 build 26200, Python 3.13.0, MediaPipe 1.2.0, NumPy 2.2.3, OpenCV-contrib 4.11.0.86 and Pillow 11.1.0.',
    ]:
        insert_paragraph(before, text)

    document.core_properties.title = 'Posture Check — Final Report Sections 6–9 (Updated)'
    document.core_properties.subject = 'Historical experiments and measured current guided-rule evaluation'
    document.core_properties.comments = 'Updated from the supplied report using the completed frozen E7 evaluation. Original document and historical figures preserved.'
    destination.parent.mkdir(parents=True, exist_ok=True)
    document.save(destination)
    print('Updated report:', destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/reports/PostureCheck-FinalReport-Sections6-9-Updated.docx')
    args = parser.parse_args()
    update(args.input, args.output)
