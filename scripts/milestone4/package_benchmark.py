"""Build a small code-only benchmark ZIP; model/videos stay on the user's laptop."""
from pathlib import Path
import zipfile
import shutil

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'docs/milestone4/PostureCheck_CP4_Benchmark_Code.zip'
INSTRUCTIONS='''POSTURE CHECK — CHECKPOINT 4 LAPTOP SPEED CHECK

This is a benchmark-only code package. It does not include videos, model weights,
or the interface logo. Extract into a separate folder before running it.

1. From your existing project, copy models/pose_landmarker_lite.task into this
   folder's models/ directory (create the directory if needed).
2. Copy your ORIGINAL four videos into data/raw/phase3_user/:
   push_up.mp4, squat.mp4, lunge.mp4, jumping_jacks.mp4.
   Do not re-encode or rename them. Checksums must match checkpoint 3.
3. Plug in the same laptop, close heavy applications, and use the same power mode
   as before (the earlier log recorded Balanced). Use the Python environment
   that successfully ran the earlier benchmark. From this extracted folder run:

   python src/evaluate.py --suite benchmark --runtime-label laptop --output docs/milestone4/laptop_benchmark.json

   If your working Python is in another project's .venv, replace python with its
   full executable path. PowerShell example (replace the example path):
   & "C:\\path\\to\\existing-project\\.venv\\Scripts\\python.exe" src/evaluate.py --suite benchmark --runtime-label laptop --output docs/milestone4/laptop_benchmark.json

4. WAIT for all four current-method runs and the final Completed message. Upload
   docs/milestone4/laptop_benchmark.json. That file must include completed_at_utc.
   If the script errors, send the terminal error. Results are never overwritten;
   choose a new output filename if rerunning.

The package verifies code, model, split-manifest and input checksums. Do not edit
src/ or the freeze file before the run. It records Python/dependency versions,
CPU/OS and (when available) Windows RAM and active power mode. If hardware capture
fails, provide CPU/RAM/power mode separately.

This benchmark measures inference + preprocessing + rules + counting. It excludes
preview rendering and video encoding, matching the processing-FPS scope used at
checkpoint 3. These four previously inspected clips are a speed/regression set,
not fresh held-out accuracy evidence. The 12-video held-out test is separate.
No checkpoint-3 git snapshot or Mendeley videos are needed for this speed run.
'''


def main():
    reference=ROOT/'docs/calibration/reference/uncalibrated_v2_code.zip'
    if reference.is_file():
        shutil.copyfile(reference,DEST)
        with zipfile.ZipFile(DEST) as archive:
            instructions=next(name for name in archive.namelist() if name.endswith('START_HERE.txt'))
            (DEST.parent/'LAPTOP_BENCHMARK.txt').write_bytes(archive.read(instructions))
        print('Restored historical v2 benchmark package. For calibrated current code use scripts/calibration/package_benchmark.py.')
        return
    files=sorted((ROOT/'src').rglob('*.py'))+[ROOT/'app.py',ROOT/'run.py',ROOT/'requirements.txt',ROOT/'docs/milestone4/evaluation_freeze.json']
    files+=sorted((ROOT/'data/prepared/mendeley').glob('*_videos.csv'))
    prefix='PostureCheck_CP4_Benchmark/'
    with zipfile.ZipFile(DEST,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,prefix+str(path.relative_to(ROOT)))
        archive.writestr(prefix+'START_HERE.txt',INSTRUCTIONS)
    with zipfile.ZipFile(DEST) as archive:
        assert archive.testzip() is None
        assert not any(name.endswith(('.mp4','.task')) for name in archive.namelist())
    (DEST.parent/'LAPTOP_BENCHMARK.txt').write_text(INSTRUCTIONS)
    print(DEST,'bytes',DEST.stat().st_size)


if __name__=='__main__':main()
