"""Editable calibration supplement; original checkpoint-four measurements stay intact."""
from pathlib import Path
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'docs/calibration'


def pct(value):return f'{100*value:.1f}%'


def main():
    plan=json.loads((FOLDER/'plan.json').read_text());fit=json.loads((FOLDER/'fitting_results.json').read_text())
    final=json.loads((FOLDER/'prospective_results.json').read_text());profile=json.loads((ROOT/'config/form_rules.json').read_text())
    if 'completed_at_utc' not in final:raise ValueError('Prospective test incomplete')
    doc=Document();section=doc.sections[0]
    section.page_width=Inches(8.27);section.page_height=Inches(11.69)
    section.top_margin=section.bottom_margin=Inches(.6);section.left_margin=section.right_margin=Inches(.65)
    normal=doc.styles['Normal'];normal.font.name='Arial';normal.font.size=Pt(10)
    normal.paragraph_format.space_after=Pt(5)
    for style,size in [('Title',19),('Heading 1',14),('Heading 2',11)]:
        doc.styles[style].font.name='Arial';doc.styles[style].font.size=Pt(size);doc.styles[style].font.color.rgb=RGBColor.from_string('843B20')
    footer=section.footer.paragraphs[0];footer.alignment=2;footer.add_run('POSTURE CHECK | Form calibration | ').font.size=Pt(8)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    doc.core_properties.title='Posture Check — calibrated form rules and prospective evaluation'
    doc.core_properties.author='Posture Check project team'
    def p(text,bold=False,size=None):
        r=doc.add_paragraph().add_run(text);r.bold=bold
        if size:r.font.size=Pt(size)
    def table(headers,rows,size=9):
        t=doc.add_table(rows=1,cols=len(headers));t.style='Light Shading Accent 1'
        for cell,x in zip(t.rows[0].cells,headers):cell.text=str(x)
        for row in rows:
            for cell,x in zip(t.add_row().cells,row):cell.text=str(x)
        for row in t.rows:
            row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_after=Pt(3)
                    for r in paragraph.runs:r.font.size=Pt(size)
    date=datetime.fromisoformat(final['completed_at_utc']).astimezone(ZoneInfo('Asia/Manila'))
    doc.add_heading('POSTURE CHECK',0);p('Form-rule calibration and prospective evaluation',True,13)
    p(date.strftime('%d %B %Y, %I:%M %p')+' (Asia/Manila)',size=9)
    doc.add_heading('1. What was calibrated and how data was separated',1)
    p('The geometric form rules were recalibrated using Mendeley whole-clip labels for side-view squat and push-up. MediaPipe Lite pose weights, pose visibility gates, preprocessing, temporal angle smoothing and movement counting are unchanged. No per-frame form labels were invented.')
    p('The original 12 side-view test clips had already been inspected, so they were excluded from fitting, validation promotion and the new final evaluation. A new prospective holdout was reserved before feature extraction: participants 017, 019, 021 and 023, with one correct and one incorrect side-view clip per exercise. These clips came from the original training inventory, not a newly collected dataset. Recorded runs showed no prior model-development use of these participants; no custom form classifier had previously been trained.')
    table(['Partition','Clips','Participants','Use'],[
        ['Fitting',54,'14 total; 13 with push-up clips','Fit thresholds; participant-held-out cross-validation'],
        ['Validation',16,'4 original validation participants','Promotion guard only; no rule refitting on these labels'],
        ['Prospective test',16,'4 reserved participants','Single frozen evaluation after fitting/promotion'],
        ['Original exposed test',12,'018 / 020 / 022','Excluded from this calibration and final evaluation']
    ],size=9)
    p('The original source CSV splits are preserved. docs/calibration/plan.json records the new participant allocation and input hashes before fitting. No participant overlaps the fitting, validation and prospective partitions. Source whole-clip labels describe entire recordings, not every frame or every repetition.',size=9)
    doc.add_heading('Learning and promotion policy',2)
    p('Numeric features summarize joint-angle distributions: knee/hip/trunk statistics for squat, elbow/alignment/inclination statistics for push-up. Subject identity, filenames, camera quality, FPS and clip duration are not classifier inputs. Fixed coverage/motion gates require at least 30 valid frames, 50% valid coverage and 20° movement range.')
    p('A small deterministic weighted-Gini rule tree learns thresholds from fitting participants. Candidate depths are 1 or 2; minimum leaf sizes are 4 or 6 clips with at least two subjects. Hyperparameters are selected by leave-one-fitting-participant-out macro F1, then incorrect-form recall and simplicity. Promotion requires strictly better validation macro F1, no lower validation incorrect-form recall, and no lower fitting OOF macro F1 than the old fixed rules. The final test does not influence this decision.',size=9)

    doc.add_page_break();doc.add_heading('2. Fitting, validation and deployed rules',1)
    rows=[]
    for ex,d in fit['exercises'].items():
        rows.append([ex.capitalize(),f"{d['uncalibrated_fit']['macro_f1']:.3f} → {d['selected_fit_oof']['macro_f1']:.3f}",f"{d['uncalibrated_validation']['macro_f1']:.3f} → {d['calibrated_validation']['macro_f1']:.3f}",pct(d['uncalibrated_validation']['per_class']['incorrect']['recall'])+' → '+pct(d['calibrated_validation']['per_class']['incorrect']['recall']),'Enabled' if d['enabled'] else 'Not promoted'])
    table(['Exercise','Fit OOF macro F1*','Validation macro F1','Validation incorrect recall','Decision'],rows,size=8)
    p('*The old fixed-rule fitting score is compared with out-of-participant predictions from the newly fitted candidate; it is a development diagnostic, not independent test accuracy.',size=8)
    p('Squat: the promoted one-split rule uses the 10th percentile of projected hip angle. It predicts source-correct at or below '+f"{profile['exercises']['squat']['tree']['threshold']:.2f}°"+' and source-incorrect above it, after the fixed coverage/motion gates. This is a dataset-fitted statistical decision, not a universal recommended hip angle. Validation accuracy stays 4/8; macro F1 improves by detecting more incorrect examples at the cost of additional false flags.')
    p('Push-up: the candidate ties the old validation macro F1 (0.619) while incorrect-form recall falls from 75% to 50%. It is not deployed. The existing push-up rules remain active. Lunge and jumping-jack form rules are not calibrated because a suitable paired side-view/front-view labelled development set was not available for this step.')
    doc.add_heading('Application integration',2)
    p('config/form_rules.json contains the learned rules, enablement decisions, participant provenance and pose-model checksum. The main CLI uses the approved rule for the final clip assessment and writes the calibration ID/decision path to JSON. The baseline path retains the original fixed rules. The calibrated mode requires the matching Lite pose weights.')
    p('The desktop adds a provisional session-form estimate, updated about once per second from cumulative numeric angles. It does not record camera images. Instantaneous geometric cues remain separate and uncalibrated at the frame level; whole-clip training does not establish the accuracy of partial live-session prefixes. Start/Stop resets the session state.')
    p('Verification: 63 automated software tests pass. Actual calibrated video inference, annotated encoding and decoded frame counts were checked on a validation clip; its final decision matched the cached validation features. The desktop session-estimate update, capture release and Quit were tested on a virtual desktop using a validation video in place of a webcam. This is not a physical laptop-camera test.',size=9)
    image=FOLDER/'evidence/session_estimate.png'
    if image.exists():
        doc.add_picture(str(image),width=Inches(5.8))
        p('Actual session-estimate UI during the validation-video integration check; no new live-accuracy claim.',size=8)

    doc.add_page_break();doc.add_heading('3. Frozen prospective test results',1)
    old=final['summary']['uncalibrated'];new=final['summary']['current']
    p('All 16 reserved clips were evaluated after the rule/profile/source freeze. Both old and deployed form decisions use exactly the same tracked feature stream; there is one feature-inference pass per clip. Only the approved form decision changes. The source/profile checksums still match after testing; no parameter or promotion decision was changed in response to test results.')
    table(['Same prospective set','Uncalibrated tracked rules','Deployed calibrated version'],[
        ['Videos / unique frames',f"16 / {old['frames']:,}",f"16 / {new['frames']:,}"],
        ['Accuracy, abstention = miss',pct(old['classification']['accuracy_all']),pct(new['classification']['accuracy_all'])],
        ['Macro F1',f"{old['classification']['macro_f1']:.3f}",f"{new['classification']['macro_f1']:.3f}"],
        ['Assessed / abstained clips','15 / 1','15 / 1'],
        ['Incorrect-form recall',pct(old['classification']['per_class']['incorrect']['recall']),pct(new['classification']['per_class']['incorrect']['recall'])],
        ['Correct-form recall',pct(old['classification']['per_class']['correct']['recall']),pct(new['classification']['per_class']['correct']['recall'])]
    ],size=9)
    for method,title in [('uncalibrated','Uncalibrated'),('current','Deployed')]:
        m=final['summary'][method]['classification']['confusion_matrix']
        p(title+' confusion matrix (rows: reference; columns: prediction)',True,size=9)
        table(['Reference','Correct','Incorrect','Abstain'],[[label,m[label]['correct'],m[label]['incorrect'],m[label]['unassessable']] for label in ('correct','incorrect')],size=8)
    table(['Exercise / 8 clips each','Accuracy before → after','Macro F1 before → after'],[[ex.capitalize(),pct(final['by_exercise']['uncalibrated'][ex]['classification']['accuracy_all'])+' → '+pct(final['by_exercise']['current'][ex]['classification']['accuracy_all']),f"{final['by_exercise']['uncalibrated'][ex]['classification']['macro_f1']:.3f} → {final['by_exercise']['current'][ex]['classification']['macro_f1']:.3f}"] for ex in ('squat','pushup')],size=9)
    p('The gain is one additional correct clip overall (7/16 → 8/16). Squat incorrect-form recall improves from 1/4 to 3/4; one additional correct squat is falsely flagged. Push-up is unchanged at 3/8 correct because its candidate was not promoted. The outcome is a modest improvement, not reliable general form recognition.',True,size=9)
    p('Do not compare 50.0% here directly with 41.7% in the earlier checkpoint report: those scores use different participants and test sets. The valid calibration comparison on this new set is 43.8% → 50.0%. The earlier checkpoint report and its exposed-test results remain unchanged.',size=9)

    doc.add_page_break();doc.add_heading('4. Per-clip outcomes, limitations and remaining work',1)
    before={r['id']:r for r in final['runs'] if r['method']=='uncalibrated'}
    cases=[]
    for r in final['runs']:
        if r['method']!='current':continue
        name=r['id'].replace('subject_','S').replace('_push_up_',' push-up ').replace('_squat_',' squat ').replace('_side','')
        cases.append([name,r['reference_form'],before[r['id']]['prediction'],r['prediction'],'PASS' if r['reference_form']==r['prediction'] else 'FAIL'])
    table(['Prospective input','Reference','Before','Deployed','Result'],cases,size=7.5)
    p('Accuracy remains low: four source-incorrect clips are still accepted and three source-correct clips are flagged, with one abstention. There are only four final-test participants. Source labels cover multiple possible faults; projected 2D angles may not capture all of them, and no independent landmark-position ground truth was collected. Exact causes still need per-fault/landmark annotation.',size=9)
    p('The prospective participants were reserved from previously unused training inventory, not obtained from a new external source. This is a transparent revised evaluation split for a newly fitted form classifier. The set is now exposed; further model changes require another independent test, not repeated tuning on these 16 outcomes.',size=9)
    p('No new held-out repetition labels or current laptop speed were measured here. Motion counting is unchanged. Use the calibrated-version benchmark package for new laptop measurements; the earlier checkpoint-4 package intentionally measures the older v2 source. Physical webcam acceptance and live-prefix form validation remain pending.',size=9)
    p('Next: collect independently labelled fault examples and repetition boundaries for push-up/lunge/jacks, inspect projected landmark failures, calibrate only on development participants, then evaluate a new class-balanced participant-separated test. Retain honest abstention for unsupported/hidden joints and views.',size=9)
    p('Reproducibility: plan.json; fitting_results.json; squat_features.json/pushup_features.json (numeric clip summaries, no per-frame labels); config/form_rules.json; evaluation_freeze.json; prospective_results.json/csv; validation_smoke.json; gui_smoke.json. The original v2 code is preserved in reference/uncalibrated_v2_code.zip and the previous working checkout.',size=8)
    p('Checkpoint-four submission snapshot: cp4-80. Previous checkpoint tags and historical results are preserved; current laptop speed remains pending.',size=8)
    output=FOLDER/'Calibrated_Form_Results.docx';doc.save(output);print(output)


if __name__=='__main__':main()
