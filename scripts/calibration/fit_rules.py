"""Fit deterministic shallow rule trees using FIT only; validation gates adoption."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from posture_check.form_features import NAMES
from posture_check.calibrated import predict_tree
from posture_check.evaluation import classification


def fit_tree(X,y,groups,names,depth,min_leaf,min_subjects=2):
    counts=np.bincount(y,minlength=2)
    if not all(counts):raise ValueError('Both form classes required to fit rules')
    weights=np.array([.5/counts[v] for v in y])
    def impurity(indices):
        w=weights[indices];mass=w.sum()
        if not mass:return 0.
        p=w[y[indices]==1].sum()/mass;return 2*p*(1-p)
    def build(indices,remaining):
        positive=weights[indices][y[indices]==1].sum();negative=weights[indices][y[indices]==0].sum()
        leaf={'prediction':'incorrect' if positive>=negative else 'correct',
              'class_counts':{'correct':int(np.sum(y[indices]==0)),'incorrect':int(np.sum(y[indices]==1))},
              'training_subjects':len(set(groups[indices]))}
        if not remaining or len(indices)<2*min_leaf or len(set(y[indices]))<2:return leaf
        best=None;gain_best=1e-12;parent=impurity(indices);total=weights[indices].sum()
        for column,name in enumerate(names):
            values=np.unique(X[indices,column])
            for threshold in (values[:-1]+values[1:])/2:
                left=indices[X[indices,column]<=threshold];right=indices[X[indices,column]>threshold]
                if min(len(left),len(right))<min_leaf:continue
                if min(len(set(groups[left])),len(set(groups[right])))<min_subjects:continue
                gain=parent-(weights[left].sum()*impurity(left)+weights[right].sum()*impurity(right))/total
                if gain>gain_best+1e-12:
                    gain_best=gain;best=(name,float(threshold),left,right)
        if best is None:return leaf
        name,threshold,left,right=best
        return {'feature':name,'threshold':threshold,'left':build(left,remaining-1),'right':build(right,remaining-1)}
    return build(np.arange(len(y)),depth)


def metrics(rows,predictions):
    return classification([{'reference_form':r['reference_form'],'prediction':p} for r,p in zip(rows,predictions)])


def infer(tree,row):
    summary=row['summary']
    return predict_tree(tree,summary['features'])[0] if summary['eligible'] else 'unassessable'


def default_metrics(rows):return metrics(rows,[r['uncalibrated_assessment']['prediction'] for r in rows])


def train(rows,exercise,depth,min_leaf):
    eligible=[r for r in rows if r['summary']['eligible']]
    if len({r['participant'] for r in eligible})<6:raise ValueError('Fewer than six usable fitting participants')
    names=NAMES[exercise]
    X=np.array([[r['summary']['features'][n] for n in names] for r in eligible]);y=np.array([int(r['reference_form']=='incorrect') for r in eligible])
    groups=np.array([r['participant'] for r in eligible])
    return fit_tree(X,y,groups,names,depth,min_leaf)


def main():
    plan_path=ROOT/'docs/calibration/plan.json';plan=json.loads(plan_path.read_text())
    if (ROOT/'config/form_rules.json').exists():raise ValueError('Profile already exists; preserve it and use a new version')
    expected={r['id']:r for split in ('fit','validation') for r in plan['partitions'][split]}
    profile={'schema_version':1,'calibration_id':'form-rules-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
             'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),
             'label_scope':'Whole-clip source labels only; no calibrated frame-level probability.',
             'exercises':{}}
    report={'plan_sha256':profile['plan_sha256'],'exercises':{}}
    for exercise in ('squat','pushup'):
        data=json.loads((ROOT/f'docs/calibration/{exercise}_features.json').read_text())
        rows=data['clips']
        if {r['id'] for r in rows}!={key for key,r in expected.items() if r['exercise']==exercise}:raise ValueError('Incomplete or unexpected calibration inputs')
        if any(any(r[k]!=expected[r['id']][k] for k in ('participant','reference_form','exercise','partition')) or r['input_sha256']!=expected[r['id']]['sha256'] for r in rows):raise ValueError('Calibration data identity mismatch')
        if any(r['pipeline_fingerprint']!=data['pipeline_fingerprint'] for r in rows):raise ValueError('Mixed feature pipelines')
        model_hashes={r['model_sha256'] for r in rows}
        if len(model_hashes)!=1:raise ValueError('Mixed pose models')
        model_hash=next(iter(model_hashes))
        if 'pose_model_sha256' in profile and profile['pose_model_sha256']!=model_hash:raise ValueError('Different models across exercises')
        profile['pose_model_sha256']=model_hash
        fit=[r for r in rows if r['partition']=='fit'];validation=[r for r in rows if r['partition']=='validation']
        if {r['participant'] for r in fit}&{r['participant'] for r in validation}:raise ValueError('Participant leakage')
        trials=[]
        for depth in plan['search']['max_depth']:
            for min_leaf in plan['search']['min_leaf_clips']:
                predictions={};folds=[]
                for subject in sorted({r['participant'] for r in fit}):
                    training=[r for r in fit if r['participant']!=subject];held=[r for r in fit if r['participant']==subject]
                    assert subject not in {r['participant'] for r in training}
                    tree=train(training,exercise,depth,min_leaf)
                    predictions.update({r['id']:infer(tree,r) for r in held})
                    folds.append({'held_out_participant':subject,'fit_participants':sorted({r['participant'] for r in training})})
                score=metrics(fit,[predictions[r['id']] for r in fit])
                trials.append({'max_depth':depth,'min_leaf':min_leaf,'oof_metrics':score,'folds':folds,'oof_predictions':predictions})
        best=max(trials,key=lambda t:(t['oof_metrics']['macro_f1'],t['oof_metrics']['per_class']['incorrect']['recall'],-t['max_depth'],t['min_leaf']))
        tree=train(fit,exercise,best['max_depth'],best['min_leaf'])
        proposed=metrics(validation,[infer(tree,r) for r in validation]);baseline=default_metrics(validation)
        baseline_oof=default_metrics(fit)
        enabled=(proposed['macro_f1']>baseline['macro_f1']+1e-12
                 and proposed['per_class']['incorrect']['recall']>=baseline['per_class']['incorrect']['recall']
                 and best['oof_metrics']['macro_f1']>=baseline_oof['macro_f1'])
        config={'enabled':bool(enabled),'tree':tree,'feature_names':list(NAMES[exercise]),
                'selected_parameters':{'max_depth':best['max_depth'],'min_leaf_clips':best['min_leaf'],'min_leaf_subjects':2},
                'pipeline_fingerprint':data['pipeline_fingerprint'],'fitting_participants':sorted({r['participant'] for r in fit}),
                'validation_participants':sorted({r['participant'] for r in validation}),
                'prospective_participants':sorted({r['participant'] for r in plan['partitions']['prospective']}),
                'promotion_reason':'Validation macro F1 improved without lowering incorrect recall; fitting OOF guard passed.' if enabled else 'Promotion guard failed; retain uncalibrated rules.'}
        profile['exercises'][exercise]=config
        report['exercises'][exercise]={'enabled':bool(enabled),'uncalibrated_fit':baseline_oof,'selected_fit_oof':best['oof_metrics'],
                    'uncalibrated_validation':baseline,'calibrated_validation':proposed,'search':trials,'tree':tree,
                    'validation_predictions':[{**{k:r[k] for k in ('id','participant','reference_form')},'uncalibrated':r['uncalibrated_assessment']['prediction'],'calibrated':infer(tree,r)} for r in validation]}
        print(exercise,'OOF',best['oof_metrics']['macro_f1'],'validation',baseline['macro_f1'],'->',proposed['macro_f1'],'ENABLED',enabled,flush=True)
    target=ROOT/'config/form_rules.json';temporary=target.with_suffix('.tmp')
    temporary.write_text(json.dumps(profile,indent=2)+'\n');temporary.replace(target)
    report['profile_sha256']=hashlib.sha256((ROOT/'config/form_rules.json').read_bytes()).hexdigest()
    report['completed_at_utc']=datetime.now(timezone.utc).isoformat()
    (ROOT/'docs/calibration/fitting_results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
