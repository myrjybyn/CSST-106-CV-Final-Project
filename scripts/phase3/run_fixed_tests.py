"""Run frozen selected-mode baseline and main pipelines on supplied test clips.

This evaluates no labels implicitly. Unknown ground truth remains unknown.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import cv2

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'docs/phase3/test_manifest.json')
    parser.add_argument('--freeze', type=Path, default=ROOT / 'docs/phase3/frozen_configuration.json')
    parser.add_argument('--results', type=Path, default=ROOT / 'docs/phase3/test_log.json')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs/phase3')
    parser.add_argument('--runtime-label', choices=('cloud', 'laptop'), default='cloud')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    freeze = json.loads(args.freeze.read_text())
    for name, expected in freeze['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen source changed: ' + name)
    model = ROOT / 'models/pose_landmarker_lite.task'
    if hashlib.sha256(model.read_bytes()).hexdigest() != freeze['model_sha256']:
        raise ValueError('Frozen model changed')
    for clip in manifest:
        if hashlib.sha256((ROOT / clip['file']).read_bytes()).hexdigest() != clip['sha256']:
            raise ValueError('Input changed: ' + clip['file'])
    cpu_text = Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists() else ''
    cpu = next((line.split(':',1)[1].strip() for line in cpu_text.splitlines()
                if line.startswith('model name')), platform.processor())
    log = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
           'runtime': {'location': args.runtime_label, 'python': platform.python_version(), 'platform': platform.platform(),
                       'cpu': cpu, 'logical_cpus': os.cpu_count(), 'laptop_fps': None},
           'freeze': str(args.freeze), 'manifest': str(args.manifest), 'runs': []}
    if platform.system() == 'Windows':
        # Collect only benchmark-relevant hardware, never usernames or serials.
        query = ("$c=Get-CimInstance Win32_Processor | Select-Object -First 1; "
                 "$m=Get-CimInstance Win32_ComputerSystem; "
                 "$o=Get-CimInstance Win32_OperatingSystem; "
                 "[pscustomobject]@{cpu=$c.Name;ram_gib=[math]::Round($m.TotalPhysicalMemory/1GB,2);"
                 "os=$o.Caption;power_scheme=(powercfg /getactivescheme | Out-String).Trim()} | ConvertTo-Json")
        try:
            hardware = subprocess.run(['powershell', '-NoProfile', '-Command', query],
                                      capture_output=True, text=True, timeout=20, check=True)
            log['runtime']['windows_hardware'] = json.loads(hardware.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            log['runtime']['windows_hardware'] = 'Automatic capture unavailable; supply CPU/RAM/power mode separately.'
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.results.parent.mkdir(parents=True, exist_ok=True)
    for clip in manifest:
        for method in ('baseline', 'main'):
            output = args.output_dir / f"{clip['id']}_{method}.mp4"
            stderr = args.output_dir / f"{clip['id']}_{method}.stderr.log"
            cmd = [sys.executable, str(ROOT/'run.py'), '--exercise', clip['exercise'], '--method', method,
                   '--input', str(ROOT/clip['file']), '--output', str(output), '--model', str(model)]
            start = time.perf_counter()
            env = dict(os.environ)
            env['MPLCONFIGDIR'] = str(ROOT / '.venv/matplotlib')
            with stderr.open('w') as err:
                process = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=err, text=True)
            elapsed = time.perf_counter() - start
            result = {'clip_id': clip['id'], 'exercise': clip['exercise'], 'method': method,
                      'command': cmd, 'exit_code': process.returncode, 'elapsed_seconds': elapsed,
                      'stdout': process.stdout.strip(), 'stderr_log': str(stderr),
                      'output': str(output), 'ground_truth_form': clip['ground_truth_form'],
                      'ground_truth_reps': clip['ground_truth_reps']}
            if process.returncode == 0:
                report = json.loads(output.with_suffix('.mp4.json').read_text())
                capture = cv2.VideoCapture(str(output)); decoded = 0
                while capture.read()[0]: decoded += 1
                capture.release()
                if decoded != report['frames'] or decoded != clip['metadata_frames']:
                    raise ValueError('Frame count mismatch: '+str(output))
                rows = report['records']; n = len(rows)
                switches = sum(a['status'] != b['status'] for a,b in zip(rows, rows[1:]))
                phase_switches = sum(a['phase'] != b['phase'] for a,b in zip(rows, rows[1:]))
                result.update(frames=n, decoded_output_frames=decoded,
                              processing_fps=report['processing_fps'],
                              processing_ms_per_frame=1000/report['processing_fps'],
                              end_to_end_fps=n/elapsed, model_pose_outputs=sum(r['pose_detected'] for r in rows),
                              assessable_frames=sum(r['features'] is not None for r in rows),
                              unassessable_frames=sum(r['status']=='unassessable' for r in rows),
                              pending_frames=sum(r['status']=='pending' for r in rows),
                              status_changes=switches, phase_changes=phase_switches,
                              repetition_count=report['repetition_count'], clip_assessment=report['clip_assessment'])
            log['runs'].append(result)
            args.results.write_text(json.dumps(log, indent=2))
            print(clip['id'], method, 'exit', process.returncode,
                  'frames',result.get('frames'), 'FPS',round(result.get('processing_fps',0),2),
                  'assessable',result.get('assessable_frames'),'reps',result.get('repetition_count'), flush=True)
            if process.returncode != 0:
                raise RuntimeError('Pipeline failed; inspect '+str(stderr))
    log['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
    log['method_summary'] = {}
    for method in ('baseline', 'main'):
        selected = [r for r in log['runs'] if r['method'] == method]
        frames = sum(r['frames'] for r in selected)
        seconds = sum(r['frames'] / r['processing_fps'] for r in selected)
        wall = sum(r['elapsed_seconds'] for r in selected)
        log['method_summary'][method] = {'frames': frames,
            'processing_fps': frames / seconds, 'processing_ms_per_frame': 1000 * seconds / frames,
            'end_to_end_fps': frames / wall}
    if args.runtime_label == 'laptop':
        log['runtime']['laptop_fps'] = {method: row['processing_fps']
                                      for method, row in log['method_summary'].items()}
    args.results.write_text(json.dumps(log, indent=2))


if __name__ == '__main__':
    main()
