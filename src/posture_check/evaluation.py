"""Clip-level evaluation; abstentions count as misses, unknown labels stay unknown."""
from contextlib import contextmanager
import hashlib
import importlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile


def classification(rows):
    labels=('correct','incorrect')
    labelled=[r for r in rows if r.get('reference_form') in labels]
    matrix={label:{prediction:0 for prediction in (*labels,'unassessable')} for label in labels}
    for r in labelled:matrix[r['reference_form']][r['prediction']]+=1
    support={label:sum(matrix[label].values()) for label in labels}
    per_class={}
    for label in labels:
        tp=matrix[label][label]
        predicted=sum(matrix[truth][label] for truth in labels)
        fp=predicted-tp;fn=support[label]-tp
        per_class[label]={'support':support[label], 'precision':tp/predicted if predicted else None,
                          'recall':tp/support[label] if support[label] else None,
                          'f1':2*tp/(2*tp+fp+fn) if support[label] else None}
    n=len(labelled);assessed=sum(r['prediction']!='unassessable' for r in labelled)
    matched=sum(matrix[label][label] for label in labels)
    return {'labelled_clips':n,'assessed_clips':assessed,'abstentions':n-assessed,
            'accuracy_all':matched/n if n else None,
            'accuracy_assessed':matched/assessed if assessed else None,
            'classification_coverage':assessed/n if n else None,
            'macro_f1':sum(per_class[x]['f1'] for x in labels)/2 if all(support.values()) else None,
            'per_class':per_class,'confusion_matrix':matrix}


def summarize(rows):
    frames=sum(r['frames'] for r in rows)
    seconds=sum(r['processing_seconds'] for r in rows)
    counted=[r for r in rows if r.get('reference_reps') is not None]
    return {'videos':len(rows),'frames':frames,'classification':classification(rows),
            'feature_coverage':sum(r['assessable_frames'] for r in rows)/frames if frames else None,
            'processing_fps':frames/seconds if seconds else None,
            'processing_ms_per_frame':1000*seconds/frames if frames else None,
            'count_labelled_clips':len(counted),
            'count_mae':sum(abs(r['estimated_reps']-r['reference_reps']) for r in counted)/len(counted) if counted else None,
            'count_exact_matches':sum(r['estimated_reps']==r['reference_reps'] for r in counted) if counted else None}


@contextmanager
def checkpoint3(root, expected_commit):
    """Load all original modules in an isolated package, without shared new rules."""
    commit=subprocess.check_output(['git','rev-parse','cp3-core^{commit}'],cwd=root,text=True).strip()
    if commit!=expected_commit:raise ValueError('Checkpoint 3 tag changed')
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'src/posture_check'],cwd=root,text=True).splitlines()
    package_name='_posture_checkpoint3'
    try:
        with tempfile.TemporaryDirectory(prefix='posture-cp3-') as folder:
            package=Path(folder)/package_name;package.mkdir()
            hashes={}
            for name in names:
                if not name.endswith('.py'):continue
                data=subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=root)
                (package/Path(name).name).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            spec=importlib.util.spec_from_file_location(package_name,package/'__init__.py',submodule_search_locations=[str(package)])
            module=importlib.util.module_from_spec(spec);sys.modules[package_name]=module;spec.loader.exec_module(module)
            pipeline=importlib.import_module(package_name+'.__main__')
            yield pipeline,hashes
    finally:
        for name in list(sys.modules):
            if name==package_name or name.startswith(package_name+'.'):sys.modules.pop(name,None)
