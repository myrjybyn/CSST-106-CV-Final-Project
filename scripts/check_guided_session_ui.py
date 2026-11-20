"""Brief desktop layout smoke test; never opens a camera."""
import json
from pathlib import Path
import sys
import time
import tkinter as tk
from unittest.mock import patch

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from posture_check.gui import PostureApp


def screenshot(window, path):
    window.update()
    # Let Windows finish its opening fade before grabbing the compositor image.
    time.sleep(.35)
    window.update()
    x, y = window.winfo_rootx(), window.winfo_rooty()
    bounds = (x, y, x + window.winfo_width(), y + window.winfo_height())
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        first = wintypes.POINT(bounds[0], bounds[1])
        last = wintypes.POINT(bounds[2], bounds[3])
        convert = ctypes.windll.user32.LogicalToPhysicalPointForPerMonitorDPI
        convert(window.winfo_id(), ctypes.byref(first))
        convert(window.winfo_id(), ctypes.byref(last))
        bounds = (first.x, first.y, last.x, last.y)
    ImageGrab.grab(bbox=bounds).save(path)


def main():
    output = ROOT / 'outputs/guided_session_smoke'
    output.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    root.withdraw()
    try:
        app = PostureApp(root, ROOT / 'models/pose_landmarker_lite.task')
        root.geometry('1000x640+40+40')
        app.show_workspace()
        root.deiconify()
        root.update()
        assert app.target_reps.get() == '5'
        assert app.target_input.winfo_ismapped()
        app.adjust_target(1)
        assert app.target_reps.get() == '6'
        app.target_reps.set('100')
        app.adjust_target(1)
        assert app.target_reps.get() == '100'
        app.target_reps.set('1')
        app.adjust_target(-1)
        assert app.target_reps.get() == '1'
        app.target_reps.set('5')
        app.active = True
        app.adjust_target(1)
        assert app.target_reps.get() == '5'
        app.active = False
        assert app.start_button.itemcget(app.start_button.caption, 'text') == 'Start Session'
        for child in app.menu.winfo_children():
            assert child.winfo_y() + child.winfo_height() <= app.menu.winfo_height(), 'Menu control clipped'
        for child in app.target_card.body.winfo_children():
            assert child.winfo_y() + child.winfo_height() <= app.target_card.body.winfo_height(), 'Rep goal control clipped'
        screenshot(root, output / 'setup.png')
        summary = dict(exercise='squat', target_reps=5, completed_reps=5,
                       end_reason='target_reached', video_path='outputs/sessions/example/recording.mp4',
                       report_path='outputs/sessions/example/summary.json',
                       assessment=dict(prediction='bad', tips=[
                           'Use a fuller lowering movement to reach the exercise depth target.',
                           'Keep your torso steadier and reduce excessive forward lean.']))
        app.finish_session(summary)
        app.dialog.geometry('+70+70')
        screenshot(app.dialog, output / 'results.png')
        assert 'Bad' in app.session_form.cget('text')
        assert app.reps.cget('text') == '5 / 5'
        app.dialog.destroy()
        app.dialog = None
        app.target_reps.set('0')
        with patch('posture_check.gui.messagebox.showerror') as error:
            app.start_camera()
            error.assert_called_once()
        assert app.worker is None
        result = dict(gui_created=True, minimum_window_layout_passed=True,
                      target_validation_passed=True, result_dialog_passed=True,
                      rep_stepper_bounds_and_session_lock_passed=True,
                      camera_opened=False, screenshots=['setup.png', 'results.png'])
        (output / 'gui_smoke.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2))
    finally:
        root.destroy()


if __name__ == '__main__':
    main()
