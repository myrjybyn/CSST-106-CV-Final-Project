"""Score stored predictions against user-supplied post-run manual references.

No inference, parameter tuning or modification of the original test log.
"""
from datetime import datetime, timezone
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/'docs/phase3'
REFERENCES={'pushup':('correct',4),'squat':('correct',4),
            'lunge':('correct',3),'jumping_jack':('correct',10)}


def main():
    references={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
                'source':'User-supplied manual labels and counts in chat',
                'timing':'Supplied after predictions were reported; not independently expert-verified.',
                'policy':'Score saved predictions without rerunning or tuning the methods.',
                'clips':{key:{'form_label':form,'completed_reps':count} for key,(form,count) in REFERENCES.items()}}
    (FOLDER/'reference_annotations.json').write_text(json.dumps(references,indent=2))
    manifest=json.loads((FOLDER/'test_manifest.json').read_text())
    for clip in manifest:
        form,count=REFERENCES[clip['id']]
        clip.update(ground_truth_form=form,ground_truth_reps=count,
                    reference_label_status='User-supplied manual reference after original test run; not independently expert-verified')
    (FOLDER/'test_manifest.json').write_text(json.dumps(manifest,indent=2))
    runs=json.loads((FOLDER/'comparison_summary.json').read_text())
    for run in runs:
        form,count=REFERENCES[run['clip_id']]
        run.update(ground_truth_form=form,ground_truth_reps=count,
                   reference_source='reference_annotations.json; post-run user-supplied manual labels')
        pred=run['repetition_count']
        run['count_signed_error']=pred-count if pred is not None else None
        run['count_absolute_error']=abs(pred-count) if pred is not None else None
    (FOLDER/'comparison_summary.json').write_text(json.dumps(runs,indent=2))
    scores={}
    for method in ('baseline','main'):
        selected=[r for r in runs if r['method']==method]
        matrix={label:{p:0 for p in ('correct','incorrect','unassessable')}
                for label in ('correct','incorrect')}
        for row in selected:matrix[row['ground_truth_form']][row['clip_assessment']['prediction']]+=1
        hits=sum(matrix[label][label] for label in matrix)
        assessed=sum(sum(matrix[label][p] for p in ('correct','incorrect')) for label in matrix)
        errors=[r['count_absolute_error'] for r in selected if r['count_absolute_error'] is not None]
        scores[method]={'clips':len(selected),'reference_class_support':{'correct':4,'incorrect':0},
                        'accuracy_all_clips':hits/len(selected),'accuracy_assessed_clips':hits/assessed if assessed else None,
                        'assessed_clips':assessed,'abstentions':len(selected)-assessed,'confusion_matrix':matrix,
                        'count_mae':sum(errors)/len(errors) if errors else None,
                        'exact_count_matches':sum(error==0 for error in errors) if errors else None,
                        'count_scored_clips':len(errors),'binary_macro_f1':None,
                        'limitation':'Correct-only sample; incorrect-form detection, false accepts and balanced performance cannot be estimated. References are user-supplied after predictions.'}
    (FOLDER/'reference_metrics.json').write_text(json.dumps(scores,indent=2))
    print(json.dumps(scores,indent=2))

if __name__=='__main__':main()
