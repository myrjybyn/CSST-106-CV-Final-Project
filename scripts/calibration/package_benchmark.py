"""Package current calibrated benchmark code; exclude existing model/videos."""
from pathlib import Path
import json
import zipfile
import hashlib

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'docs/calibration/PostureCheck_Calibrated_Benchmark_Code.zip'
TEXT='''POSTURE CHECK — CALIBRATED VERSION LAPTOP BENCHMARK

This is a benchmark-only package for the new form-rules-v1 application. It does
not include the model, videos or interface artwork. Extract to a separate folder.
The older checkpoint-4 package measures the older uncalibrated version.

1. Copy models/pose_landmarker_lite.task from your existing project into models/.
2. Copy the ORIGINAL four clips into data/raw/phase3_user/:
   push_up.mp4, squat.mp4, lunge.mp4, jumping_jacks.mp4.
3. Use the same working Python environment and demo laptop as before. Keep the
   power mode the same (the original log recorded Balanced), plug in the laptop,
   close heavy apps, then run from this extracted folder:

   python src/evaluate.py --suite benchmark --runtime-label laptop --output docs/calibration/laptop_benchmark.json

   If needed, replace python with the full path of your working .venv Python.
   In PowerShell put & before a quoted executable path.
4. Wait for all FOUR current-method runs and Completed. Return the resulting
   docs/calibration/laptop_benchmark.json. It must contain completed_at_utc.
   If it fails, send the terminal error. Use a new output filename when rerunning.

Code, model, input and split hashes are checked. Do not edit src/, config/, the
plan or freeze. The learned form profile is included; pose weights are unchanged.
This measures the current pipeline on KNOWN clips for speed/regression only,
not a fresh test. The prospective participant test is already recorded separately.
The model and input hashes match the original clips; no git history is needed.
'''


def main():
    freeze=ROOT/'docs/calibration/evaluation_freeze.json'
    data=json.loads(freeze.read_text())
    for name,digest in data['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Current source/profile changed since final evaluation')
    paths=sorted((ROOT/'src').rglob('*.py'))+[ROOT/'run.py',ROOT/'app.py',ROOT/'requirements.txt',freeze,ROOT/'config/form_rules.json',ROOT/'docs/calibration/plan.json']
    paths+=sorted((ROOT/'data/prepared/mendeley').glob('*_videos.csv'))
    prefix='PostureCheck_Calibrated_Benchmark/'
    with zipfile.ZipFile(DEST,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for path in paths:z.write(path,prefix+str(path.relative_to(ROOT)))
        z.writestr(prefix+'START_HERE.txt',TEXT)
    with zipfile.ZipFile(DEST) as z:assert z.testzip() is None
    (DEST.parent/'LAPTOP_BENCHMARK.txt').write_text(TEXT)
    print(DEST,DEST.stat().st_size,'bytes')


if __name__=='__main__':main()
