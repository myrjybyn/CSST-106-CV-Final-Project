"""Capture the desktop UI and real sample inference; never opens a webcam.

Run --prepare first, then --capture on an interactive Windows desktop.
The screenshot index records which UI states are illustrative.
"""
import argparse
import copy
import csv
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import cv2
import numpy as np

from posture_check.__main__ import run, process, annotate, CONNECTIONS
from posture_check.pose import PoseEstimator
from posture_check.session import ExerciseSession, GuidedRepetitionCounter
from posture_check.temporal import TemporalAnalyzer

DEST = ROOT / 'screenshots'
DATA = ROOT / 'outputs/screenshot_samples'
MODEL = ROOT / 'models/pose_landmarker_lite.task'
MODES = {'squat': ('Squat', 'squat.mp4'), 'pushup': ('Push-up', 'push_up.mp4'),
         'lunge': ('Lunge', 'lunge.mp4'), 'jumping_jack': ('Jumping jack', 'jumping_jacks.mp4')}
entries = []


def record(name, description, provenance):
    entries.append(dict(filename=name, description=description, provenance=provenance))


def save_index():
    entries.sort(key=lambda item: item['filename'])
    with (DEST / 'index.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=['filename', 'description', 'provenance'])
        writer.writeheader()
        writer.writerows(entries)
    (DATA / 'index.json').write_text(json.dumps(entries, indent=2), encoding='utf-8')


def prepare():
    for source in sorted((ROOT / 'milestone1/posture_check/data/samples').glob('*.jpg')):
        exercise = source.stem.rsplit('_', 1)[0]
        name = f'40_sample_output_{source.stem}.png'
        report = run(source, DEST / name, MODEL, exercise)
        # Keep raw evidence together, outside the requested picture folder.
        evidence = DEST / (name + '.json')
        evidence.replace(DATA / evidence.name)
        record(name, f'Actual annotated image output: {exercise}; {report["records"][0]["status"]}',
               str(source.relative_to(ROOT)))
        print(name, flush=True)
    for exercise, (_, filename) in MODES.items():
        source = ROOT / 'data/raw/phase3_user' / filename
        cap = cv2.VideoCapture(str(source))
        fps = cap.get(cv2.CAP_PROP_FPS)
        estimator = PoseEstimator(MODEL, video=True, fps=fps)
        analyzer = TemporalAnalyzer(exercise, fps)
        analyzer.counter = GuidedRepetitionCounter(exercise)
        session = ExerciseSession(exercise)
        best = None
        best_score = (-1, -1)
        n = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                landmarks, raw = process(frame, estimator, exercise, enhanced=True)
                result = analyzer.update(raw)
                session.add(result)
                score = (int(result['features'] is not None), result['repetition_count'])
                if score > best_score:
                    best_score = score
                    overlay = frame.copy()
                    if landmarks and result['features'] is not None:
                        h, w = frame.shape[:2]
                        for a, b in CONNECTIONS:
                            if min(landmarks[a].visibility, landmarks[a].presence,
                                   landmarks[b].visibility, landmarks[b].presence) >= .5:
                                points = [(int(landmarks[i].x*w), int(landmarks[i].y*h)) for i in (a,b)]
                                cv2.line(overlay, *points, (95,112,255), 3, cv2.LINE_AA)
                                for point in points:
                                    cv2.circle(overlay, point, 4, (213,240,255), -1, cv2.LINE_AA)
                    best = (frame.copy(), overlay, copy.deepcopy(result), annotate(frame, landmarks, result), n)
                n += 1
        finally:
            cap.release()
            estimator.close()
        plain, overlay, result, annotated, frame_index = best
        np.savez_compressed(DATA / f'{exercise}_preview.npz', plain=plain, overlay=overlay)
        (DATA / f'{exercise}_frame.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        summary = dict(exercise=exercise, target_reps=max(5, analyzer.count + 1),
                       completed_reps=analyzer.count, end_reason='stopped_early',
                       duration_seconds=round(n/fps, 2), assessment=session.assess(),
                       video_path=str(source.relative_to(ROOT)),
                       report_path=f'outputs/screenshot_samples/{exercise}_summary.json')
        (DATA / f'{exercise}_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        name = f'41_sample_video_output_{exercise}.png'
        cv2.imwrite(str(DEST / name), annotated)
        record(name, f'Actual video inference, frame {frame_index}; guided rep counter; '
               f'full clip: {analyzer.count} reps, {summary["assessment"]["prediction"]}',
               str(source.relative_to(ROOT)))
        print(name, summary['completed_reps'], summary['assessment']['prediction'], flush=True)
    save_index()


def capture():
    import tkinter as tk
    from tkinter import messagebox
    from PIL import ImageGrab
    from posture_check.gui import PostureApp
    entries.extend(item for item in json.loads((DATA / 'index.json').read_text(encoding='utf-8'))
                   if item['filename'].startswith(('40_', '41_')))
    root = tk.Tk()
    root.withdraw()
    app = PostureApp(root, MODEL)
    # Fit the 1920x1080 desktop even at Windows' 150% display scaling.
    root.geometry('1200x640+20+20')
    root.deiconify()
    root.attributes('-topmost', True)

    def snap(name, description, provenance='Actual app UI; no webcam opened', window=None):
        window = window or root
        window.lift()
        window.update()
        time.sleep(.45)
        window.update()
        x, y = window.winfo_rootx(), window.winfo_rooty()
        bounds = (x, y, x+window.winfo_width(), y+window.winfo_height())
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            first, last = wintypes.POINT(*bounds[:2]), wintypes.POINT(*bounds[2:])
            convert = ctypes.windll.user32.LogicalToPhysicalPointForPerMonitorDPI
            convert(window.winfo_id(), ctypes.byref(first))
            convert(window.winfo_id(), ctypes.byref(last))
            bounds = (first.x, first.y, last.x, last.y)
        ImageGrab.grab(bbox=bounds).save(DEST / name)
        record(name, description, provenance)
        print(name, flush=True)

    def close_dialog():
        if app.dialog is not None:
            app.dialog.destroy()
            app.dialog = None

    def dialog_snap(name, description, provenance='Actual app dialog'):
        root.update()
        app.dialog.geometry('+380+65')
        snap(name, description, provenance)
        close_dialog()

    def show_frame(exercise, name, countdown=0, skeleton=True, mirror=True, override=None):
        app.exercise.set(MODES[exercise][0])
        app.show_workspace()
        data = np.load(DATA / f'{exercise}_preview.npz')
        frame = data['overlay' if skeleton else 'plain']
        if mirror:
            frame = cv2.flip(frame, 1)
        result = json.loads((DATA / f'{exercise}_frame.json').read_text())
        if override:
            result.update(override)
        result['countdown'] = countdown
        app.active = True
        target = json.loads((DATA / f'{exercise}_summary.json').read_text())['target_reps']
        if countdown or override:
            target = 5
        app.session_target = target
        app.target_reps.set(str(target))
        app.progress_goal = target
        app.set_target_enabled(False)
        app.start_button.set_text('End Session')
        root.update()
        app.mailbox.put(('frame', cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), result,
                         1/max(result['processing_seconds'], .001)))
        app.poll()
        provenance = f'Real {exercise} sample-video inference replayed through app.poll; no live webcam'
        if countdown or override:
            provenance += '; illustrative UI state override'
        snap(name, f'{MODES[exercise][0]} preview; skeleton={skeleton}, mirror={mirror}', provenance)
        app.active = False

    try:
        snap('01_home_menu.png', 'Home menu, default rep goal and navigation')
        app.choose_exercise()
        dialog_snap('02_choose_exercise.png', 'All four supported exercises and viewing guidance')
        app.settings()
        dialog_snap('03_settings_camera_mirror_skeleton.png', 'Camera index, mirror and skeleton settings; local-save information')
        app.target_reps.set('10')
        snap('04_custom_rep_goal.png', 'Editable repetition goal and minus/plus controls')
        app.target_reps.set('5')
        app.show_workspace()
        snap('05_session_workspace_ready.png', 'Session workspace before starting')
        show_frame('squat', '06_three_second_countdown_illustrative.png', countdown=3,
                   override=dict(repetition_count=0, movement_phase='get_ready',
                                 feedback='Get into position. Recording begins after the countdown.'))
        for number, exercise in enumerate(MODES, 7):
            show_frame(exercise, f'{number:02d}_{exercise}_tracking_sample_replay.png')
        show_frame('squat', '11_skeleton_disabled_sample_replay.png', skeleton=False)
        show_frame('squat', '12_mirroring_disabled_sample_replay.png', mirror=False)
        show_frame('squat', '13_rep_progress_illustrative.png',
                   override=dict(repetition_count=3, movement_phase='standing'))
        show_frame('squat', '14_missing_pose_feedback_illustrative.png', skeleton=False,
                   override=dict(status='unassessable', features=None, movement_phase='unknown',
                                 feedback='Keep your whole body visible and use a side view.'))
        app.set_target_enabled(True)
        for number, exercise in enumerate(MODES, 15):
            summary = json.loads((DATA / f'{exercise}_summary.json').read_text())
            app.finish_session(summary)
            dialog_snap(f'{number:02d}_{exercise}_actual_sample_results.png',
                        f'Actual complete-video assessment: {summary["assessment"]["prediction"]}; ended early',
                        'Actual guided analysis of local sample video; full file, no automatic target stop')
        # Explicit examples cover all result branches independent of sample content.
        from posture_check.session import TIPS
        for number, (prediction, tips) in enumerate([
            ('good', ['Keep the same range of movement and steady control for your next set.']),
            ('bad', [TIPS['limited_depth'], TIPS['trunk_lean']]),
            ('unassessable', ['Try again with your whole body visible and steady lighting.'])], 19):
            summary = dict(exercise='squat', target_reps=5, completed_reps=5 if prediction != 'unassessable' else 0,
                           end_reason='target_reached' if prediction != 'unassessable' else 'stopped_early',
                           video_path='outputs/sessions/example/recording.mp4',
                           report_path='outputs/sessions/example/summary.json',
                           assessment=dict(prediction=prediction, tips=tips))
            app.finish_session(summary)
            dialog_snap(f'{number:02d}_{prediction}_result_illustrative.png',
                        f'Illustrative {prediction} result, tips and saved-file paths',
                        'Illustrative summary fixture passed to actual app.finish_session; example paths')
        summary['end_reason'] = 'time_limit'
        app.finish_session(summary)
        dialog_snap('22_time_limit_result_illustrative.png', '10-minute time-limit result branch',
                    'Illustrative end_reason fixture; actual app result dialog')
        summary['end_reason'] = 'cancelled_before_recording'
        summary['video_path'] = summary['report_path'] = None
        app.finish_session(summary)
        snap('23_cancelled_before_recording_illustrative.png', 'Cancelled countdown with no recording',
             'Illustrative cancellation summary passed to actual app.finish_session')

        def capture_native_dialog(name, description, title):
            # Native messageboxes run their own Tk loop; capture and dismiss it there.
            def grab():
                try:
                    snap(name, description)
                finally:
                    if sys.platform == 'win32':
                        import ctypes
                        user32 = ctypes.windll.user32
                        user32.FindWindowW.restype = ctypes.c_void_p
                        user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                                       ctypes.c_size_t, ctypes.c_ssize_t]
                        handle = user32.FindWindowW(None, title)
                        if handle:
                            user32.PostMessageW(handle, 0x0111, 1, 0)  # WM_COMMAND, IDOK
                    else:
                        root.tk.call('event', 'generate', '.__tk__messagebox', '<KeyPress-Return>')
            root.after(700, grab)

        app.target_reps.set('0')
        capture_native_dialog('24_invalid_rep_goal_error.png', 'Actual validation for a goal outside 1-100', 'Invalid target')
        app.start_camera()
        app.target_reps.set('5')
        capture_native_dialog('25_camera_error_dialog.png', 'Camera failure message presentation; illustrative error event', 'Session unavailable')
        app.mailbox.put(('error', 'Cannot open this camera. Check camera permissions, close other camera apps, or choose another camera index in Settings.'))
        app.poll()

        # Use a real saved session as the example recording and JSON output.
        saved = sorted((ROOT / 'outputs/sessions').glob('*/summary.json'))[-1]
        saved_summary = json.loads(saved.read_text())
        app.finish_session(saved_summary)
        dialog_snap('26_saved_session_actual_results.png', 'Existing recorded session and saved-file paths',
                    str(saved.relative_to(ROOT)))
        cap = cv2.VideoCapture(str(saved.parent / 'recording.mp4'))
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / 2))
        ok, frame = cap.read()
        cap.release()
        if ok:
            name = '27_saved_recording_sample_frame.png'
            cv2.imwrite(str(DEST / name), frame)
            record(name, 'Actual middle frame of a locally saved recording, without preview overlays',
                   str((saved.parent / 'recording.mp4').relative_to(ROOT)))
        viewer = tk.Toplevel(root)
        viewer.transient(root)
        root.attributes('-topmost', False)
        viewer.attributes('-topmost', True)
        viewer.title('Saved session output: summary.json (file preview)')
        viewer.geometry('1000x640+40+30')
        text = tk.Text(viewer, font=('Consolas', 11), wrap='word', padx=18, pady=18)
        text.pack(fill='both', expand=True)
        text.insert('1.0', json.dumps(saved_summary, indent=2))
        text.configure(state='disabled')
        snap('28_saved_summary_json_output.png', 'Read-only file preview of actual saved summary.json',
             str(saved.relative_to(ROOT)) + '; separate file viewer, not an app feature', window=viewer)
        viewer.destroy()
        save_index()
        (DEST / 'READ_ME.txt').write_text(
            'POSTURE CHECK FEATURE SCREENSHOTS AND SAMPLE OUTPUTS\n\n'
            '01-28: desktop app features, result branches and saved outputs.\n'
            '40: all 20 bundled sample images processed by the actual CLI pipeline.\n'
            '41: actual annotated sample-video inference for all four exercises.\n\n'
            'See index.csv for every filename, description and source.\n'
            'Files marked illustrative show staged UI states, not measured webcam results.\n'
            'Tracking screenshots replay real local sample-video inference through the GUI.\n'
            'Actual sample result dialogs use complete-video guided assessment and an early-end label.\n'
            'The saved JSON screenshot is a separate file preview.\n'
            'No webcam was opened. No application source code was changed.\n'
            'Raw inference evidence is in outputs/screenshot_samples/.\n'
            'Reproduce: python scripts/capture_screenshots.py --prepare\n'
            'Then, on an interactive desktop: python scripts/capture_screenshots.py --capture\n',
            encoding='utf-8')
    finally:
        root.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    DEST.mkdir(exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    if args.prepare:
        prepare()
    if args.capture:
        capture()
