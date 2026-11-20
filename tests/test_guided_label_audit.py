"""Regression checks for prediction-independent conflicting-label exclusion."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from posture_check.evaluation import classification

SPEC = importlib.util.spec_from_file_location(
    'audit_guided_labels', Path(__file__).resolve().parents[1] / 'scripts/audit_guided_labels.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class GuidedLabelAuditTests(unittest.TestCase):
    def test_all_conflicting_copies_are_selected_regardless_of_prediction(self):
        clips = [dict(id='a', sha256='same', reference_form='correct', prediction='correct'),
                 dict(id='b', sha256='same', reference_form='incorrect', prediction='correct'),
                 dict(id='c', sha256='same', reference_form='correct', prediction='incorrect'),
                 dict(id='d', sha256='other', reference_form='correct')]
        self.assertEqual({c['id'] for g in audit.conflicting_groups(clips) for c in g}, {'a', 'b', 'c'})
        self.assertEqual(audit.conflicting_groups([dict(sha256='same', reference_form='correct')] * 2), [])

    def fixture(self, folder):
        clips, runs = [], []
        model_methods = ['baseline', 'guided']
        archive_path = folder / 'dataset.zip'
        with ZipFile(archive_path, 'w') as archive:
            for index, (content, label, prediction) in enumerate([
                    (b'duplicate', 'correct', 'correct'), (b'duplicate', 'incorrect', 'correct'),
                    (b'unique-good', 'correct', 'unassessable'), (b'unique-bad', 'incorrect', 'incorrect')]):
                name = f'mendeley/clip{index}.mp4'
                path = folder / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                archive.writestr(f'clip{index}.mp4', content)
                clip = dict(id=str(index), file=name, exercise='squat', participant='p',
                            reference_form=label, sha256=hashlib.sha256(content).hexdigest())
                clips.append(clip)
                runs.extend(dict(**clip, method=method, prediction=prediction) for method in model_methods)
        freeze = folder / 'freeze.json'
        audit.write_json(freeze, dict(clips=clips, methods=model_methods))
        source = folder / 'results.json'
        audit.write_json(source, dict(status='complete', freeze_sha256=audit.sha(freeze), runs=runs,
                                      runtime={}, summary={method: classification([r for r in runs if r['method'] == method])
                                                           for method in model_methods}))
        return source, freeze, archive_path

    def test_cleaned_analysis_keeps_abstention_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            source, freeze, archive = self.fixture(folder)
            original_hash = audit.sha(source)
            output = folder / 'cleaned.json'
            with redirect_stdout(io.StringIO()):
                audit.run(source, freeze, folder, archive, output)
            result = json.loads(output.read_text())
            self.assertEqual(result['excluded_ids'], ['0', '1'])
            self.assertEqual(result['retained_ids'], ['2', '3'])
            self.assertEqual(result['summary']['guided']['accuracy_all'], .5)
            self.assertEqual(result['summary']['guided']['classification_coverage'], .5)
            self.assertEqual(result['summary']['guided']['abstentions'], 1)
            self.assertEqual(audit.sha(source), original_hash)
            with self.assertRaises(ValueError):
                audit.run(source, freeze, folder, archive, output)

    def test_changed_input_is_rejected_before_any_results_are_written(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            source, freeze, archive = self.fixture(folder)
            (folder / 'mendeley/clip0.mp4').write_bytes(b'changed')
            output = folder / 'cleaned.json'
            with self.assertRaisesRegex(ValueError, 'Input bytes differ'):
                audit.run(source, freeze, folder, archive, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
