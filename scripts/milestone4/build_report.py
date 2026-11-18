"""Build the editable checkpoint-four report from completed measured logs.

Run in the report-only environment containing python-docx. A new laptop log is
optional; absence is shown as pending, never filled using cloud measurements.
"""
import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'docs/milestone4'
NAMES={'pushup':'Push-up','squat':'Squat','lunge':'Lunge','jumping_jack':'Jumping jacks'}


def read_completed(path):
    data=json.loads(path.read_text())
    if 'completed_at_utc' not in data or data.get('error'):raise ValueError('Incomplete/error log: '+str(path))
    return data


def percent(value):return 'N/A' if value is None else f'{100*value:.1f}%'


def build_cases(heldout,functional,gui):
    cases=[]
    for i,r in enumerate([r for r in heldout['runs'] if r['method']=='current'],1):
        cases.append({'id':f'H{i:02d}','input':r['file'],'condition':r['condition'],
                      'expected':r['reference_form'],'actual':r['prediction'],
                      'status':'PASS' if r['prediction']==r['reference_form'] else 'FAIL',
                      'hard_or_edge':False,'kind':'real held-out clip classification; source label'})
    cases.extend(functional['cases'])
    cases.append({'id':'UI01','input':gui['input'],'condition':gui['condition'],
                  'expected':gui['expected'],'actual':gui['actual'],'status':gui['status'],
                  'hard_or_edge':False,'kind':'actual GUI/pose integration; video substituted for camera'})
    result={'cases':cases,'total':len(cases),'passed':sum(c['status']=='PASS' for c in cases),
            'failed':sum(c['status']=='FAIL' for c in cases),'hard_or_edge':sum(c['hard_or_edge'] for c in cases),
            'interpretation':'Real clip classification failures are distinct from functional software failures. Synthetic and mocked cases do not measure posture accuracy.'}
    (FOLDER/'test_cases.json').write_text(json.dumps(result,indent=2)+'\n')
    with (FOLDER/'test_cases.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream,lineterminator='\n');fields=['id','input','condition','expected','actual','status','hard_or_edge','kind'];writer.writerow(fields)
        for c in cases:writer.writerow([json.dumps(c[k]) if isinstance(c[k],dict) else c[k] for k in fields])
    return result


def compact(value):
    if not isinstance(value,dict):return str(value)
    if list(value)==['reps']:return f"{value['reps']} reps"
    if 'input_unchanged' in value:return 'ValueError; input intact'
    if 'output_exists' in value:return 'Missing-file error; no output'
    if 'message_type' in value:return 'Camera error; released'
    if 'features' in value:return 'Unassessable; no features'
    if 'decoded_frames' in value:return '3 frames; 0 reps; abstain'
    if 'decoded' in value:return 'PNG saved; abstain; reps N/A'
    return json.dumps(value)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--laptop-log',type=Path,default=FOLDER/'laptop_benchmark.json')
    args=parser.parse_args()
    heldout=read_completed(FOLDER/'heldout_results.json')
    known=read_completed(FOLDER/'known_clip_results.json')
    functional=read_completed(FOLDER/'functional_test_cases.json')
    gui=read_completed(FOLDER/'evidence/gui_test_log.json')
    freeze=json.loads((FOLDER/'evaluation_freeze.json').read_text())
    old_laptop=read_completed(ROOT/'docs/phase3/laptop_test_log.json')
    historical=json.loads((ROOT/'docs/phase3/comparison_summary.json').read_text())
    cp3_known=[r for r in historical if r['method']=='main']
    laptop=None
    if args.laptop_log.exists():
        laptop=read_completed(args.laptop_log)
        expected={r['id'] for r in freeze['suites']['benchmark']}
        if (laptop.get('suite')!='benchmark' or laptop['runtime']['location']!='laptop'
                or laptop['source_sha256']!=freeze['source_sha256'] or laptop['model_sha256']!=freeze['model_sha256']
                or len(laptop['runs'])!=4 or {r['id'] for r in laptop['runs']}!=expected
                or any(r['method']!='current' or r['exit_code']!=0 for r in laptop['runs'])):
            raise ValueError('Laptop log does not match the complete frozen current benchmark')
        expected_rows={r['id']:r for r in freeze['suites']['benchmark']}
        for row in laptop['runs']:
            reference=expected_rows[row['id']]
            if (row['sha256']!=reference['sha256'] or row['frames']!=reference['metadata_frames']
                    or row['processing_seconds']<=0):
                raise ValueError('Laptop input identity/frame count/timing mismatch')
        weighted_fps=sum(r['frames'] for r in laptop['runs'])/sum(r['processing_seconds'] for r in laptop['runs'])
        if not math.isclose(weighted_fps,laptop['summary']['current']['processing_fps'],rel_tol=1e-8):
            raise ValueError('Laptop aggregate timing does not match per-clip measurements')
    cases=build_cases(heldout,functional,gui)
    old=heldout['summary']['cp3'];new=heldout['summary']['current'];labels=new['classification']
    doc=Document();section=doc.sections[0]
    section.page_width=Inches(8.27);section.page_height=Inches(11.69)
    section.top_margin=section.bottom_margin=Inches(.6);section.left_margin=section.right_margin=Inches(.65)
    style=doc.styles['Normal'];style.font.name='Arial';style.font.size=Pt(10)
    style.paragraph_format.space_after=Pt(5);style.paragraph_format.line_spacing=1.02
    for name,size in [('Title',20),('Heading 1',14),('Heading 2',11)]:
        doc.styles[name].font.name='Arial';doc.styles[name].font.size=Pt(size);doc.styles[name].font.color.rgb=RGBColor.from_string('843B20')
    doc.core_properties.title='Posture Check — Checkpoint 4 application and testing report'
    doc.core_properties.author='Posture Check project team'
    footer=section.footer.paragraphs[0];footer.alignment=2
    footer.add_run('POSTURE CHECK | Checkpoint 4 | ').font.size=Pt(8)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    def p(text,bold=False,size=None):
        paragraph=doc.add_paragraph();r=paragraph.add_run(text);r.bold=bold
        if size:r.font.size=Pt(size)
        return paragraph
    def table(headers,rows,size=9):
        t=doc.add_table(rows=1,cols=len(headers));t.style='Light Shading Accent 1'
        for cell,text in zip(t.rows[0].cells,headers):cell.text=str(text)
        for values in rows:
            for cell,text in zip(t.add_row().cells,values):cell.text=str(text)
        for row in t.rows:
            row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_after=Pt(3)
                    for run in paragraph.runs:run.font.size=Pt(size)
        return t
    date=datetime.fromisoformat(heldout['completed_at_utc']).astimezone(ZoneInfo('Asia/Manila'))
    doc.add_heading('POSTURE CHECK',0)
    p('Checkpoint 4 — Nearly Complete Application & Testing',True,13)
    p('Evaluation completed '+date.strftime('%d %B %Y, %I:%M %p')+' (Asia/Manila)',size=9)
    doc.add_heading('1. Integrated application and interface',1)
    p('The desktop application integrates selected-exercise webcam input, MediaPipe Lite VIDEO tracking, conservative black-border removal, confidence/geometry gates, rule feedback, temporal smoothing and movement counting. The operator selects squat, push-up, lunge or jumping jacks. Exercise recognition and camera-view recognition are not automatic.')
    p('The custom home screen/logo and rounded menu are preserved. Start Camera moves the menu into a sidebar; the live view shows pose lines, feedback, movement phase, estimated reps and FPS. Settings select camera index, mirror preview and skeleton display. Stop/Start begins a new session; Quit releases capture. File inputs are supported through the CLI, including annotated output and JSON.')
    table(['Requirement','Evidence / status'],[
        ['1–2. Application and interface','Integrated desktop webcam pipeline; CLI image/video pipeline; actual GUI integration tested using recorded video in place of a webcam.'],
        ['3. Test results and laptop speed','Held-out and checkpoint-3 comparison completed by src/evaluate.py. '+('Current laptop speed log supplied.' if laptop else 'New current-version laptop run remains pending; old measurement retained.')],
        ['4–5. Analysis and test cases',f'Limitations below; {cases["total"]} recorded cases, including {cases["hard_or_edge"]} edge cases. Classification failures are retained.']
    ],size=9)
    doc.add_picture(str(FOLDER/'evidence/live.png'),width=Inches(6.65))
    p('Actual custom interface during cloud integration testing: recorded videos substituted for camera input; not a physical laptop-webcam acceptance test. Home screenshot and provenance are in evidence/.',size=8)
    p('Launch: python app.py | File prototype: python run.py --exercise squat --method main --input input.mp4 --output output.mp4',size=8)

    doc.add_page_break();doc.add_heading('2. Held-out evaluation produced by src/evaluate.py',1)
    p('The fixed supported subset contains 12 full side-view Mendeley test videos from participants 018, 020 and 022: six source-correct and six source-incorrect clips, split evenly between squat and push-up. Test participants are disjoint from train/validation. The remaining 24 front/diagonal test videos are excluded because the current rules require a side view. No labels are copied onto frames.')
    p('Model, code, input and split-manifest hashes were frozen before inference. All original checkpoint-3 source modules were loaded in an isolated package from cp3-core (3a568d7); current and checkpoint-3 main methods were rerun on exactly the same 12 clips. This is a new matched comparison, not a claim that checkpoint 3 originally measured this set. No parameters were adjusted after seeing these results.',size=9)
    table(['Metric, same held-out set','Checkpoint 3 rerun','Current'],[
        ['Clips / decoded frames per method',f"12 / {old['frames']:,}",f"12 / {new['frames']:,}"],
        ['Form accuracy (abstention = miss)',percent(old['classification']['accuracy_all']),percent(labels['accuracy_all'])],
        ['Macro F1',f"{old['classification']['macro_f1']:.3f}",f"{labels['macro_f1']:.3f}"],
        ['Assessed clips / abstentions','12 / 0','12 / 0'],
        ['Usable-pose frame coverage',percent(old['feature_coverage']),percent(new['feature_coverage'])],
        ['Cloud processing FPS',f"{old['processing_fps']:.2f}",f"{new['processing_fps']:.2f}"],
        ['Cloud processing ms/frame',f"{old['processing_ms_per_frame']:.2f}",f"{new['processing_ms_per_frame']:.2f}"]
    ],size=9)
    p(f"Accuracy changed by {100*(labels['accuracy_all']-old['classification']['accuracy_all']):+.1f} percentage points. More usable poses did not produce better form classification. Coverage measures accepted geometry, not landmark accuracy.",True,size=9)
    for method,title in [('cp3','Checkpoint 3'),('current','Current')]:
        matrix=heldout['summary'][method]['classification']['confusion_matrix']
        p(title+' confusion matrix (rows: source label; columns: predicted label)',True,size=9)
        table(['Reference','Correct','Incorrect','Abstain'],[[label.capitalize(),matrix[label]['correct'],matrix[label]['incorrect'],matrix[label]['unassessable']] for label in ('correct','incorrect')],size=8)
    table(['Current class','Support','Precision','Recall','F1'],[[label.capitalize(),r['support'],percent(r['precision']),percent(r['recall']),f"{r['f1']:.3f}"] for label,r in labels['per_class'].items()],size=8)
    table(['Exercise','CP3 accuracy / macro F1','Current accuracy / macro F1'],[[NAMES[ex],percent(heldout['by_exercise']['cp3'][ex]['classification']['accuracy_all'])+f" / {heldout['by_exercise']['cp3'][ex]['classification']['macro_f1']:.3f}",percent(heldout['by_exercise']['current'][ex]['classification']['accuracy_all'])+f" / {heldout['by_exercise']['current'][ex]['classification']['macro_f1']:.3f}"] for ex in ('pushup','squat')],size=8)
    p('Held-out repetition references are unavailable, so no held-out count MAE is invented. There is no equivalent held-out jumping-jack set; lunge/jack claims below use known regression clips only.',size=8)

    doc.add_page_break();doc.add_heading('3. Changes since checkpoint 3 and demo-laptop speed',1)
    p('Since checkpoint 3, the main pipeline adds tracked video inference, border-aware input handling, separate movement endpoints with dwell/hysteresis, lunge-leg tracking, clearer rejection guidance and the desktop interface. The same pretrained Lite weights are retained; no custom weight training is claimed.')
    p('Known-clip regression, measured again by src/evaluate.py:',True)
    previous={r['clip_id']:r for r in cp3_known}
    table(['Known clip','User reference reps','CP3 count','Current count'],[[NAMES[r['exercise']],r['reference_reps'],previous[r['id']]['repetition_count'],r['estimated_reps']] for r in known['runs']],size=9)
    count_mae=sum(abs(r['repetition_count']-r['ground_truth_reps']) for r in cp3_known)/4
    p(f"Count MAE: {count_mae:.2f} → {known['summary']['current']['count_mae']:.2f} reps/clip. Form agreement on these four clips remains {percent(known['summary']['current']['classification']['accuracy_all'])}. The excerpts were inspected during previous failure analysis; they are regression data, not fresh held-out evidence. All four form references are user-labelled correct and were supplied after original predictions; incorrect-form detection cannot be evaluated from this set.",size=9)
    old_speed=old_laptop['method_summary']['main']
    rows=[['Checkpoint 3 main',f"{old_speed['processing_fps']:.2f}",f"{old_speed['processing_ms_per_frame']:.2f}",'Measured laptop log'],
          ['Current main',f"{laptop['summary']['current']['processing_fps']:.2f}" if laptop else 'PENDING',f"{laptop['summary']['current']['processing_ms_per_frame']:.2f}" if laptop else 'PENDING','Measured laptop log' if laptop else 'Must run on demo laptop']]
    table(['Same four-clip speed workload','Processing FPS','ms/frame','Status'],rows,size=9)
    hw=old_laptop['runtime']['windows_hardware']
    p(f"Original demo laptop: {str(hw['cpu']).strip()}, {hw['ram_gib']} GiB reported RAM, Windows 11, two logical CPUs, Balanced power scheme, Python {old_laptop['runtime']['python']}. Processing FPS excludes startup, decoding, drawing and encoding. The current evaluator logs versions/hardware and the same timing scope; rendering/encoding speed is separate.",size=9)
    if laptop:
        s=laptop['summary']['current'];delta=s['processing_fps']-old_speed['processing_fps']
        p(f"Current measured laptop change: {delta:+.2f} processing FPS ({100*delta/old_speed['processing_fps']:+.1f}%). Check hardware, power mode and dependency-version differences in both logs before attributing the change to code alone.",True)
        p('Current runtime: '+json.dumps(laptop['runtime'],ensure_ascii=False),size=8)
    else:
        p('The current-version laptop speed and its change since checkpoint 3 are not yet measured. Cloud FPS cannot fill this field. Run the provided small benchmark package on the same laptop and supply the completed JSON log.',True)
    p('Laptop command (use the Python environment that ran the earlier benchmark):',True,size=9)
    p('python src/evaluate.py --suite benchmark --runtime-label laptop --output docs/milestone4/laptop_benchmark.json',size=8)
    p('The code-only ZIP excludes model/videos. Copy the existing pose model and four original clips as explained in START_HERE.txt. The report generator accepts the new laptop log and rebuilds this DOCX without rerunning the held-out set.',size=9)
    runtime=heldout['runtime']
    p(f"Cloud timing context: {runtime['cpu']}, {runtime['logical_cpus']} visible logical CPUs, Python {runtime['python']}. Single sequential timing passes on a shared cloud environment; brief validation jobs may overlap. These are not controlled speed experiments or laptop measurements.",size=8)

    doc.add_page_break();doc.add_heading('4. Real held-out classification test cases',1)
    p('Expected values are source whole-clip form labels. PASS means the one clip prediction matched its label; FAIL includes misclassification or abstention. All cases use complete source side-view videos; input paths, condition, expected, actual and pass/fail are also in test_cases.csv/json. No failed case was removed.',size=9)
    real=[c for c in cases['cases'] if c['id'].startswith('H')]
    real_rows=[]
    for c in real:
        filename=Path(c['input']).stem.replace('subject_','S').replace('_push_up_',' push-up ').replace('_squat_',' squat ').replace('_side','')
        real_rows.append([c['id'],filename,'Side view',c['expected'],c['actual'],c['status']])
    table(['ID','Input','Condition','Expected','Actual','Result'],real_rows,size=8)
    p(f"Current classification cases: {sum(c['status']=='PASS' for c in real)}/12 PASS; {sum(c['status']=='FAIL' for c in real)}/12 FAIL. These outcomes must not be merged with functional-case passes to describe model accuracy.",True,size=9)
    p('Observed failure pattern: four source-incorrect clips are accepted as correct; three source-correct clips are flagged incorrect. All three incorrect-squat clips are accepted, giving incorrect-squat recall 0/3 on this small set. The current pose gates cover more frames, yet the unchanged form rules still miss source-labelled faults.',size=9)
    p('Three false flags have explicit rule reasons: limited elbow extension (subject 020 push-up), limited projected depth (subject 020 squat), and limited elbow flexion (subject 022 push-up). The false accepts have no configured fault reason. Those are observed decision paths; they do not prove which anatomical fault or landmark error caused the source-label mismatch.',size=9)

    doc.add_page_break();doc.add_heading('5. Functional and hard/edge test cases',1)
    p('The following cases test software behavior. Synthetic movement traces and mocked device failures are labelled as such; they are not real-video posture-accuracy evidence. Native image/video rows run actual MediaPipe inference and codecs.',size=9)
    input_short={
        'F01':'Squat trace','F02':'Push-up trace','F03':'Lunge trace','F04':'Jack trace',
        'F05':'Bottom-start trace','F06':'Trace + 0.8 s gap','F07':'Hidden-wrist landmarks',
        'F08':'Unavailable camera stub','F09':'Missing MP4','F10':'Black PNG','F11':'3-frame black MP4','F12':'Same input/output PNG'}
    condition_short={
        'F01':'Full cycle','F02':'Full cycle','F03':'Full cycle','F04':'Full cycle',
        'F05':'Partial start [edge]','F06':'Missing data [edge]','F07':'Occlusion [edge]',
        'F08':'Device error [edge]','F09':'Missing file [edge]','F10':'No person [edge]',
        'F11':'No person / short video [edge]','F12':'Overwrite attempt [edge]'}
    table(['ID','Input','Condition','Expected','Actual','Result'],[[c['id'],input_short[c['id']],condition_short[c['id']],compact(c['expected']),compact(c['actual']),c['status']] for c in functional['cases']],size=7.5)
    p(f"Functional cases: {functional['passed']}/{functional['total']} PASS, including eight explicit hard/edge cases. Full structured expected/actual values are preserved in functional_test_cases.json and the combined CSV.",True,size=9)
    p('UI01 — Desktop integration: PASS. Actual tracked inference rendered the home and live views, stopping released capture, Start became available again, and Quit closed the window. This used recorded videos substituted for camera capture on a virtual desktop; physical laptop-camera acceptance remains pending.',size=9)
    p(f"Combined inventory: {cases['total']} cases, {cases['passed']} PASS and {cases['failed']} FAIL. The seven failures are retained real-video classification failures; functional success does not cancel them. Separately, all 56 automated software tests passed.",size=9)
    p('Vision hard-case coverage remains limited: black/no-person and synthetic wrist occlusion do not establish performance on dimly lit people, real motion blur, clutter, strong occlusion or multiple people. Those conditions need a separately labelled fixed visual test set.',size=9)

    doc.add_page_break();doc.add_heading('6. Performance analysis, limits and remaining work',1)
    table(['Where it works / fails','Evidence and explanation'],[
        ['Works: integrated application and motion pipeline','Four selected modes, local webcam preview and CLI annotated output are connected. Functional failure handling is exercised; known squat count stays 4/4.'],
        ['Improves: pose coverage and known movement counts','Held-out usable coverage rises 82.0%→95.5%; known count MAE falls 3.50→1.75. This does not verify landmark positions or form quality.'],
        ['Fails: form-label generalization','Current held-out accuracy is 5/12 (41.7%), below CP3 7/12 (58.3%). Four false accepts and three false flags remain. All three incorrect-squat labels are missed.'],
        ['Why: changed measurements, incomplete fixed rules','Tracking/preprocessing change the measurement distribution while the form thresholds remain fixed. A rule can pass despite faults outside its configured projected-angle checks. Landmark and fault annotations are needed to identify exact causes; no controlled ablation was performed.'],
        ['Fails / unknown: counting and robustness','Known push-up remains 2/4; lunge 2/3; jacks 6/10. Held-out count labels are absent. Camera edits, occlusion and strict endpoints can lose cycles; contributions are hypotheses until annotated.']
    ],size=9)
    p('Not designed for: automatic exercise/view identification, clinical assessment, unsupported exercise variants (including wall/table push-ups under the standard push-up mode), multiple-person identity management, cropped bodies or reliable classification from an unsuitable camera view. Side views are required for squat/push-up/lunge and front view for jacks. Low light, blur and clutter are not adequately validated. Jack whole-clip form classification deliberately abstains.',size=9)
    doc.add_heading('Next changes tied to measured failures',2)
    table(['Priority','Action and expected purpose'],[
        ['1. Form calibration','Label specific faults and landmark quality on development participants; calibrate projected-angle checks using train/validation only. Target the four false accepts and three false flags without fitting to this exposed test set.'],
        ['2. Count references and subject continuity','Independently annotate repetition boundaries for all four modes, including partial cycles and camera edits. Validate active-leg and endpoint handling; measure MAE and exact-count rate on a new fixed set.'],
        ['3. Broader validation and laptop acceptance','Add participant-separated lunge/jack and realistic hard-case recordings. Run the unchanged current benchmark and physical camera on the demo laptop; record power mode and dependency versions.']
    ],size=8)
    p('Current submission status: application features, interface evidence, held-out evaluation, checkpoint comparison, analysis and case inventory are prepared. '+('A current laptop benchmark is included; physical camera acceptance still needs confirmation.' if laptop else 'Current demo-laptop FPS/change and physical camera acceptance remain pending. Do not describe the performance hand-in as complete until the new laptop log is supplied.'),True,size=9)
    p('Reproducibility: evaluation_freeze.json locks inputs/model/source/splits; heldout_results.json/csv contains the matched test runs; known_clip_results.json/csv contains the separate regression workload; test_cases.json/csv and functional_test_cases.json/csv hold expectations and outcomes; evidence/ holds actual UI captures and test provenance. Original checkpoint-3 reports and tags are preserved.',size=8)
    output=FOLDER/'Checkpoint4_Application_Testing_Report.docx';doc.save(output)
    print(output)
    print('Cases:',cases['total'],'PASS',cases['passed'],'FAIL',cases['failed'],'LAPTOP',bool(laptop))


if __name__=='__main__':main()
