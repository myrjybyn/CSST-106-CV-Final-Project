"""Desktop interface for the selected-exercise live posture pipeline."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import queue
import threading
import time
import uuid
import tkinter as tk
from tkinter import ttk, messagebox

import cv2
from PIL import Image, ImageTk, ImageOps

from .__main__ import process, CONNECTIONS
from .pose import PoseEstimator
from .temporal import TemporalAnalyzer
from .session import ExerciseSession, SessionRecorder, GuidedRepetitionCounter

ROOT = Path(__file__).resolve().parents[2]
LOGO = ROOT / 'assets' / 'posture_check_logo.png'
EXERCISES = {'Squat': 'squat', 'Push-up': 'pushup', 'Lunge': 'lunge',
             'Jumping jack': 'jumping_jack'}
BG, PANEL, TEXT, MUTED, ACCENT = '#fff0e8', '#ffe0cf', '#3d241d', '#735046', '#8b3d23'
CORAL, BUTTON, BUTTON_HOVER = '#a63f30', '#f3bfa5', '#e9ac8c'
CONTROL, BORDER, DISABLED = '#fffaf6', '#c08b73', '#efd4c4'
SHADOW = '#ebc9b5'
PIXEL_FONT = 'Consolas'


def publish_latest(mailbox, item):
    """Bound memory and preview latency when inference outpaces rendering."""
    try:
        mailbox.put_nowait(item)
    except queue.Full:
        try:
            mailbox.get_nowait()
        except queue.Empty:
            pass
        mailbox.put_nowait(item)


def camera_worker(mailbox, stop, model, exercise, camera, mirror, skeleton,
                  target=5, output_root=None, countdown_seconds=3, max_seconds=600):
    """Own all native resources here; never access Tk from this thread."""
    capture = estimator = recorder = None
    session_path = None
    try:
        if isinstance(target, bool) or not isinstance(target, int) or not 1 <= target <= 100:
            raise ValueError('Choose a target between 1 and 100 repetitions.')
        capture = cv2.VideoCapture(camera)
        if not capture.isOpened():
            raise RuntimeError('Cannot open this camera. Check camera permissions, close other camera apps, or choose another camera index in Settings.')
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        estimator = PoseEstimator(model, video=True)
        analyzer = TemporalAnalyzer(exercise, 30)
        analyzer.counter = GuidedRepetitionCounter(exercise)
        session = ExerciseSession(exercise)
        ready_at = time.perf_counter() + countdown_seconds
        previous = time.perf_counter()
        began = None
        end_reason = 'stopped_early'
        elapsed = 0.0
        while not stop.is_set():
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError('The camera stopped sending frames. Reconnect it and try again.')
            landmarks, raw = process(frame, estimator, exercise, enhanced=True)
            now = time.perf_counter()
            dt = max(now - previous, .001)
            previous = now
            preparing = now < ready_at
            if preparing:
                result = dict(raw, repetition_count=0, movement_phase='get_ready',
                              feedback='Get into position. Recording begins after the countdown.',
                              countdown=max(1, math.ceil(ready_at - now)), recording=False)
            else:
                if began is None:
                    began = now
                    output = Path(output_root) if output_root is not None else ROOT / 'outputs/sessions'
                    name = datetime.now(timezone.utc).strftime('session_%Y%m%d_%H%M%SUTC_') + uuid.uuid4().hex[:6]
                    session_path = output / name
                    session_path.mkdir(parents=True, exist_ok=False)
                    recorder = SessionRecorder(session_path / 'recording.mp4', frame)
                    # Setup time must not contribute to a repetition's dwell.
                    dt = 1 / 30
                elapsed = now - began
                result = analyzer.update(raw, dt_seconds=dt)
                session.add(result)
                result.update(recording=True, countdown=0)
                # Record the original orientation before adding display overlays.
                recorder.write(frame, elapsed)
            if skeleton and landmarks and result['features'] is not None:
                h, w = frame.shape[:2]
                for a, b in CONNECTIONS:
                    if all(min(landmarks[i].visibility, landmarks[i].presence) >= .5 for i in (a, b)):
                        points = [(int(landmarks[i].x*w), int(landmarks[i].y*h)) for i in (a,b)]
                        cv2.line(frame, *points, (95, 112, 255), 3, cv2.LINE_AA)
                        for point in points:
                            cv2.circle(frame, point, 4, (213, 240, 255), -1, cv2.LINE_AA)
            # Analyze the original camera orientation; mirror only the display.
            if mirror:
                frame = cv2.flip(frame, 1)
            publish_latest(mailbox, ('frame', cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), result, 1/dt))
            if not preparing and analyzer.count >= target:
                end_reason = 'target_reached'
                break
            if began is not None and elapsed >= max_seconds:
                end_reason = 'time_limit'
                break
        if recorder is not None:
            recorder.close()
            recorder = None
        summary = dict(exercise=exercise, target_reps=target, completed_reps=analyzer.count,
                       end_reason=end_reason if began is not None else 'cancelled_before_recording',
                       duration_seconds=round(elapsed, 2), assessment=session.assess(),
                       video_path=str(session_path / 'recording.mp4') if session_path else None,
                       report_path=str(session_path / 'summary.json') if session_path else None,
                       recorded_at_utc=datetime.now(timezone.utc).isoformat())
        if session_path:
            (session_path / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        publish_latest(mailbox, ('complete', summary))
    except Exception as error:
        detail = str(error)
        if session_path:
            detail += f'\nAny partial recording is in {session_path}'
        publish_latest(mailbox, ('error', detail))
    finally:
        if recorder is not None:
            recorder.close()
        if capture is not None:
            capture.release()
        if estimator is not None:
            estimator.close()


class CloudPanel(tk.Frame):
    """A stepped, scalloped cloud border around an ordinary Tk content frame."""
    def __init__(self, parent, fill=PANEL, inset=22, **kwargs):
        super().__init__(parent, bg=parent.cget('bg'), **kwargs)
        self.inset = inset
        self.canvas = tk.Canvas(self, bg=self.cget('bg'), highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=fill)
        self.body.place(x=inset, y=inset, relwidth=1, relheight=1,
                        width=-2 * inset, height=-2 * inset)
        self.fill = fill
        self.bind('<Configure>', self._draw)

    def fit_content(self):
        self.update_idletasks()
        self.configure(width=self.body.winfo_reqwidth() + 2 * self.inset,
                       height=self.body.winfo_reqheight() + 2 * self.inset)

    def _draw(self, event):
        width, height = event.width - 4, event.height - 5
        if min(width, height) < 36:
            return
        # Repeated flat-topped lobes, drawn with right-angle pixel steps.
        def edge(length):
            count = max(2, round((length - 32) / 52))
            span = (length - 32) / count
            points = []
            for number in range(count):
                x = 16 + number * span
                for fraction, y in ((0, 16), (.12, 16), (.12, 10), (.28, 10),
                                    (.28, 5), (.72, 5), (.72, 10), (.88, 10),
                                    (.88, 16), (1, 16)):
                    points.append((round(x + fraction * span), y))
            return points
        top = edge(width)
        right = [(width - y, x) for x, y in edge(height)]
        bottom = [(width - x, height - y) for x, y in top]
        left = [(y, height - x) for x, y in edge(height)]
        points = top + right + bottom + left
        self.canvas.delete('cloud')
        self.canvas.create_polygon([v for x, y in points for v in (x + 3, y + 4)],
                                   fill=SHADOW, outline='', tags='cloud')
        self.canvas.create_polygon([v for point in points for v in point], fill=self.fill,
                                   outline=BORDER, width=2, joinstyle='miter', tags='cloud')


class RoundedButton(tk.Canvas):
    """Stepped pixel button with keyboard access and a small pressed offset."""
    def __init__(self, parent, text, command, primary=False):
        super().__init__(parent, height=44, bg=parent.cget('bg'),
                         highlightthickness=0, bd=0, cursor='hand2', takefocus=True)
        self.text, self.command, self.primary = text, command, primary
        self.enabled, self.hovered, self.pressed = True, False, False
        self.shadow = self.create_polygon(0, 0, 1, 1, fill=BORDER, outline='')
        self.fill = self.create_polygon(0, 0, 1, 1, smooth=False, outline=BORDER, width=1, tags='button')
        self.caption = self.create_text(18, 22, text=text, anchor='center',
            font=(PIXEL_FONT, 12, 'bold'), tags='button')
        self.bind('<Configure>', self._draw)
        self.bind('<Enter>', self._enter)
        self.bind('<Leave>', self._leave)
        self.bind('<ButtonPress-1>', self._press)
        self.bind('<ButtonRelease-1>', self._release)
        self.bind('<space>', self._activate)
        self.bind('<Return>', self._activate)
        self.bind('<FocusIn>', self._draw)
        self.bind('<FocusOut>', self._draw)
        self._draw()

    def _colors(self):
        if not self.enabled:
            return DISABLED, MUTED
        if self.primary:
            return (ACCENT if self.hovered or self.pressed else CORAL), CONTROL
        return (BUTTON_HOVER if self.hovered or self.pressed else BUTTON), TEXT

    def _draw(self, _event=None):
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        if width < 24 or height < 24:
            return
        points = [(9, 2), (width-11, 2), (width-11, 6), (width-6, 6),
                  (width-6, 11), (width-3, 11), (width-3, height-13),
                  (width-6, height-13), (width-6, height-8), (width-11, height-8),
                  (width-11, height-5), (9, height-5), (9, height-8),
                  (4, height-8), (4, height-13), (1, height-13), (1, 11),
                  (4, 11), (4, 6), (9, 6)]
        offset = 2 if self.pressed else 0
        fill, foreground = self._colors()
        self.coords(self.shadow, *[v for x, y in points for v in (x+2, y+3)])
        self.coords(self.fill, *[v for x, y in points for v in (x+offset, y+offset)])
        self.itemconfigure(self.fill, fill=fill,
                           outline=ACCENT if self.focus_get() == self else BORDER)
        self.itemconfigure(self.caption, fill=foreground)
        self.coords(self.caption, width / 2 + offset, (height - 3) / 2 + offset)

    def _enter(self, _event):
        self.hovered = True
        self._draw()

    def _leave(self, _event):
        self.hovered = self.pressed = False
        self._draw()

    def _press(self, _event):
        if self.enabled:
            self.pressed = True
            self.focus_set()
            self._draw()

    def _release(self, event):
        activate = self.enabled and self.pressed and 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self.pressed = False
        self._draw()
        if activate:
            self.command()

    def _activate(self, _event):
        if self.enabled:
            self.command()

    def set_text(self, text):
        self.itemconfigure(self.caption, text=text)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.configure(cursor='hand2' if enabled else 'arrow')
        self._draw()


class PostureApp:
    def __init__(self, root, model):
        self.root, self.model = root, model
        self.exercise = tk.StringVar(value='Squat')
        self.target_reps = tk.StringVar(value='5')
        self.camera = tk.IntVar(value=0)
        self.mirror = tk.BooleanVar(value=True)
        self.skeleton = tk.BooleanVar(value=True)
        self.mailbox = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.worker = None
        self.active = self.closing = False
        self.dialog = None
        self.last_summary = None
        root.title('Sparkling Pixel Posture Check')
        width = min(1200, max(1000, root.winfo_screenwidth() - 80))
        height = min(780, max(640, root.winfo_screenheight() - 100))
        root.geometry(f'{width}x{height}'); root.minsize(1000, 640)
        root.configure(bg=BG)
        root.protocol('WM_DELETE_WINDOW', self.quit)
        root.bind('<Escape>', lambda event: self.stop_camera() if self.active else None)
        style = ttk.Style(root); style.theme_use('clam')
        style.configure('TCombobox', padding=8, fieldbackground=CONTROL,
                        background=BUTTON, foreground=TEXT, arrowcolor=TEXT,
                        selectbackground=ACCENT, selectforeground=CONTROL)
        style.map('TCombobox', fieldbackground=[('readonly', CONTROL)],
                  foreground=[('readonly', TEXT)],
                  selectbackground=[('readonly', ACCENT)],
                  selectforeground=[('readonly', CONTROL)])
        self.shell = tk.Frame(root, bg=BG); self.shell.pack(fill='both', expand=True, padx=28, pady=28)
        self.menu_card = CloudPanel(self.shell, width=310)
        self.menu_card.place(relx=.5, rely=.5, anchor='center', width=410, height=min(700, height - 56))
        self.menu = self.menu_card.body
        self.menu.configure(padx=10, pady=5)
        self.logo_source = Image.open(LOGO).convert('RGBA')
        self.logo_label = tk.Label(self.menu, bg=PANEL, bd=0)
        self.logo_label.pack(pady=(0, 9))
        self.set_logo_width(160)
        self.label(self.menu, 'MOVE WITH INTENTION', 10, ACCENT, bold=True).pack(anchor='w')
        self.label(self.menu, 'Your movement. A clearer view.', 10, MUTED).pack(anchor='w', pady=(4,8))
        self.target_card = CloudPanel(self.menu, fill=CONTROL, inset=18, height=112)
        self.target_card.pack(fill='x', pady=(0, 8))
        target_body = self.target_card.body
        self.label(target_body, 'YOUR REP GOAL', 9, ACCENT, True).pack()
        target_row = tk.Frame(target_body, bg=CONTROL)
        target_row.pack(fill='x', pady=2)
        self.target_minus = self.button(target_row, '−', lambda: self.adjust_target(-1))
        self.target_minus.configure(width=36, height=34)
        self.target_minus.pack(side='left')
        self.target_plus = self.button(target_row, '+', lambda: self.adjust_target(1))
        self.target_plus.configure(width=36, height=34)
        self.target_plus.pack(side='right')
        self.target_input = tk.Entry(target_row, textvariable=self.target_reps,
                                     width=4, font=(PIXEL_FONT, 23, 'bold'), justify='center',
                                     bg=CONTROL, fg=ACCENT, insertbackground=TEXT,
                                     disabledbackground=CONTROL, disabledforeground=MUTED,
                                     selectbackground=ACCENT, selectforeground=CONTROL,
                                     relief='flat', bd=0, highlightthickness=0)
        self.target_input.pack(side='left', fill='x', expand=True)
        self.label(target_body, 'reps to your finish line', 8, MUTED).pack()
        self.start_button = self.button(self.menu, 'Start Session', self.toggle_camera, primary=True)
        self.start_button.pack(fill='x', pady=5)
        self.button(self.menu, 'Choose Exercise', self.choose_exercise).pack(fill='x', pady=5)
        self.button(self.menu, 'Settings', self.settings).pack(fill='x', pady=5)
        self.button(self.menu, 'Quit', self.quit).pack(fill='x', pady=5)
        self.mode_label = self.label(self.menu, '', 10, MUTED)
        self.mode_label.pack(anchor='w', pady=(12,0))
        self.exercise.trace_add('write', lambda *_: self.update_mode())
        self.update_mode()
        self.workspace = tk.Frame(self.shell, bg=BG)
        header = tk.Frame(self.workspace, bg=BG);header.pack(fill='x', pady=(0,14))
        self.label(header, 'LIVE SESSION', 11, ACCENT, bold=True).pack(side='left')
        self.camera_state = self.label(header, 'Camera off', 10, MUTED);self.camera_state.pack(side='right')
        self.preview_card = CloudPanel(self.workspace, fill=CONTROL)
        self.preview_card.pack(fill='both', expand=True)
        self.preview_area = self.preview_card.body
        self.preview = tk.Label(self.preview_area, bg=CONTROL, fg=MUTED,
                                text='Your next little win starts here.\nCamera preview', font=('Arial',12))
        self.preview.image = None
        self.preview_area.bind('<Configure>', self.resize_preview)
        self.stats_card = CloudPanel(self.workspace, height=98, inset=20)
        self.stats_card.pack(fill='x', pady=(10,0))
        stats = self.stats_card.body
        stats.configure(padx=5)
        self.reps = self.label(stats, '0', 32, ACCENT, bold=True);self.reps.pack(side='left')
        self.label(stats, '  REP TRACKER', 9, MUTED, True).pack(side='left', padx=(0,16))
        self.phase = self.label(stats, 'Waiting for movement', 12, TEXT);self.phase.pack(side='left')
        self.fps = self.label(stats, '— FPS', 10, MUTED);self.fps.pack(side='right')
        self.progress_count, self.progress_goal = 0, 5
        self.progress = tk.Canvas(self.workspace, bg=BG, height=10, highlightthickness=0)
        self.progress.pack(fill='x', pady=(5, 0))
        self.progress.bind('<Configure>', lambda _event: self.draw_progress())
        self.session_form = self.label(self.workspace, 'Set a target and start your session.', 11, MUTED)
        self.session_form.configure(wraplength=550, justify='left')
        self.session_form.pack(anchor='w', pady=(10, 0))
        self.feedback = self.label(self.workspace, 'Ready when you are.', 13, TEXT)
        self.feedback.configure(wraplength=550, justify='left');self.feedback.pack(anchor='w', pady=(16,4))
        self.guidance = self.label(self.workspace, '', 10, MUTED);self.guidance.pack(anchor='w')
        root.after(30, self.poll)

    @staticmethod
    def label(parent, text, size, color, bold=False):
        return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color,
                        font=(PIXEL_FONT if bold else 'Arial', size, 'bold' if bold else 'normal'), anchor='w')

    @staticmethod
    def button(parent, text, command, primary=False):
        return RoundedButton(parent, text, command, primary)

    def update_mode(self):
        self.mode_label.configure(text='Selected  /  '+self.exercise.get())
        if hasattr(self, 'session_form') and not self.active:
            self.session_form.configure(text='Set a target and start your session.', fg=MUTED)

    def adjust_target(self, difference):
        if self.active or (self.worker is not None and self.worker.is_alive()):
            return
        try:
            current = int(self.target_reps.get())
        except ValueError:
            current = 5
        self.target_reps.set(str(max(1, min(100, current + difference))))

    def set_target_enabled(self, enabled):
        self.target_input.configure(state='normal' if enabled else 'disabled')
        self.target_minus.set_enabled(enabled)
        self.target_plus.set_enabled(enabled)

    def draw_progress(self):
        width = self.progress.winfo_width()
        self.progress.delete('all')
        blocks = min(20, self.progress_goal)
        span = width / max(1, blocks)
        for number in range(blocks):
            filled = self.progress_count / max(1, self.progress_goal) >= (number + 1) / blocks
            self.progress.create_rectangle(number * span + 2, 2, (number + 1) * span - 2, 8,
                                           fill=CORAL if filled else SHADOW, outline='')

    def set_logo_width(self, width):
        logo_image = self.logo_source.copy()
        logo_image.thumbnail((width, 220), Image.Resampling.LANCZOS)
        logo_layer = Image.new('RGBA', logo_image.size, PANEL)
        logo_layer.alpha_composite(logo_image)
        self.logo_photo = ImageTk.PhotoImage(logo_layer.convert('RGB'))
        self.logo_label.configure(image=self.logo_photo)

    def resize_preview(self, event):
        # Keep a 16:9 preview capped at 640x360, centered in the remaining space.
        scale = min(1, max(1, event.width - 32) / 640, max(1, event.height - 32) / 360)
        width, height = int(640 * scale), int(360 * scale)
        self.preview.place(relx=.5, rely=.5, anchor='center', width=width, height=height)

    def show_workspace(self):
        self.menu_card.place_forget()
        self.menu_card.pack(side='left', fill='y', padx=(0,20));self.menu_card.pack_propagate(False)
        self.menu_card.configure(width=300)
        self.set_logo_width(145)
        self.workspace.pack(side='left', fill='both', expand=True)
        view = 'front' if self.exercise.get() == 'Jumping jack' else 'side'
        self.guidance.configure(text=f'{self.exercise.get()} | Use a {view} view. Keep your entire body visible.')

    def toggle_camera(self):
        if self.active:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        if self.worker is not None and self.worker.is_alive():
            return
        try:
            target = int(self.target_reps.get())
            if not 1 <= target <= 100:
                raise ValueError
        except ValueError:
            messagebox.showerror('Invalid target', 'Enter a whole number from 1 to 100 reps.', parent=self.root)
            return
        if self.dialog is not None:
            self.dialog.destroy();self.dialog = None
        self.show_workspace()
        self.stop = threading.Event()
        self.mailbox = queue.Queue(maxsize=1)
        self.active = True
        self.session_target = target
        self.reps.configure(text=f'0 / {target}');self.phase.configure(text='Get ready')
        self.session_form.configure(text='A 3-second countdown gives you time to get into position.', fg=MUTED)
        self.set_target_enabled(False)
        self.progress_count, self.progress_goal = 0, target
        self.draw_progress()
        self.feedback.configure(text='Opening camera…', fg=TEXT)
        self.camera_state.configure(text='Connecting…');self.start_button.set_text('End Session')
        self.worker = threading.Thread(target=camera_worker, args=(self.mailbox,self.stop,self.model,
            EXERCISES[self.exercise.get()],self.camera.get(),self.mirror.get(),self.skeleton.get(),target),daemon=True)
        self.worker.start()

    def stop_camera(self):
        self.active = False;self.stop.set()
        self.start_button.set_text('Stopping…');self.start_button.set_enabled(False)
        self.camera_state.configure(text='Finishing session…')
        self.feedback.configure(text='Saving the recording and checking your overall form…', fg=TEXT)

    def dialog_window(self, title):
        if self.worker is not None and self.worker.is_alive():
            messagebox.showinfo('Stop camera first', 'Stop the camera before changing exercise or settings.', parent=self.root)
            return None
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.lift();return None
        window = tk.Toplevel(self.root);self.dialog=window
        window.title(title);window.configure(bg=BG);window.resizable(False,False)
        window.transient(self.root)
        def close():
            window.destroy();self.dialog=None
        window.protocol('WM_DELETE_WINDOW',close)
        card = CloudPanel(window)
        card.pack(padx=10, pady=10)
        body = card.body
        body.configure(padx=14, pady=12)
        window.after_idle(card.fit_content)
        self.label(body,title,20,TEXT,True).pack(anchor='w',pady=(0,18))
        return body,close

    def choose_exercise(self):
        dialog=self.dialog_window('Choose exercise')
        if dialog is None:return
        body,close=dialog
        for name in EXERCISES:
            tk.Radiobutton(body,text=name,variable=self.exercise,value=name,bg=PANEL,fg=TEXT,
                selectcolor=CONTROL,activebackground=PANEL,activeforeground=ACCENT,
                font=('Arial',12),padx=8,pady=8).pack(anchor='w')
        self.label(body,'Side view for squat, push-up and lunge.\nFront view for jumping jacks.',10,MUTED).pack(pady=12)
        self.button(body,'Done',close,True).pack(fill='x')

    def settings(self):
        dialog=self.dialog_window('Settings')
        if dialog is None:return
        body,close=dialog
        self.label(body,'Camera index',11,TEXT).pack(anchor='w')
        selected=tk.StringVar(value=str(self.camera.get()))
        ttk.Combobox(body,textvariable=selected,values=[str(i) for i in range(6)],state='readonly',width=24).pack(pady=(6,16))
        for text,variable in [('Mirror preview',self.mirror),('Show pose skeleton',self.skeleton)]:
            tk.Checkbutton(body,text=text,variable=variable,bg=PANEL,fg=TEXT,selectcolor=CONTROL,
                activebackground=PANEL,activeforeground=TEXT,font=('Arial',11)).pack(anchor='w',pady=7)
        self.label(body,'Recordings and summaries are saved locally\nin outputs/sessions/. Sessions end at the target,\non End Session, or after 10 minutes.',10,MUTED).pack(pady=16)
        def save():
            self.camera.set(int(selected.get()));close()
        self.button(body,'Done',save,True).pack(fill='x')

    def finish_session(self, summary):
        self.active = False
        self.last_summary = summary
        self.camera_state.configure(text='Recording saved' if summary['video_path'] else 'Camera off')
        self.reps.configure(text=f'{summary["completed_reps"]} / {summary["target_reps"]}')
        self.progress_count, self.progress_goal = summary['completed_reps'], summary['target_reps']
        self.draw_progress()
        endings = {'target_reached': 'Target reached', 'stopped_early': 'Ended early',
                   'time_limit': 'Time limit reached', 'cancelled_before_recording': 'Cancelled'}
        ending = endings[summary['end_reason']]
        self.phase.configure(text=ending)
        assessment = summary['assessment']
        names = {'good': 'Good', 'bad': 'Bad — needs improvement', 'unassessable': 'Unable to assess — try again'}
        title = names[assessment['prediction']]
        color = ACCENT if assessment['prediction'] == 'good' else CORAL
        self.session_form.configure(text=f'Overall form: {title}', fg=color)
        self.feedback.configure(text='\n'.join('• ' + tip for tip in assessment['tips']), fg=TEXT)
        self.guidance.configure(text='Recording + summary saved in outputs/sessions/.' if summary['video_path']
                                else 'Recording was cancelled before the session began.')
        if summary['end_reason'] == 'cancelled_before_recording':
            return
        window = tk.Toplevel(self.root)
        self.dialog = window
        window.title('Session results')
        window.configure(bg=BG)
        window.transient(self.root)
        card = CloudPanel(window)
        card.pack(padx=10, pady=10)
        body = card.body
        body.configure(padx=14, pady=12)
        self.label(body, 'SESSION RESULTS', 12, ACCENT, True).pack(anchor='w')
        self.label(body, title, 22, color, True).pack(anchor='w', pady=(12, 6))
        exercise = summary['exercise'].replace('_', ' ').title()
        self.label(body, f'{exercise} | {summary["completed_reps"]} / {summary["target_reps"]} reps | {ending}',
                   11, TEXT).pack(anchor='w', pady=(0, 16))
        tips = self.label(body, '\n\n'.join('• ' + tip for tip in assessment['tips']), 12, TEXT)
        tips.configure(wraplength=520, justify='left')
        tips.pack(anchor='w')
        saved = self.label(body, f'Recording: {summary["video_path"]}\nSummary: {summary["report_path"]}', 9, MUTED)
        saved.configure(wraplength=520, justify='left')
        saved.pack(anchor='w', pady=(16, 16))
        def close():
            window.destroy()
            self.dialog = None
        window.protocol('WM_DELETE_WINDOW', close)
        self.button(body, 'Done', close, True).pack(fill='x')
        window.after_idle(card.fit_content)

    def poll(self):
        if self.closing:
            if self.worker is None or not self.worker.is_alive():
                self.root.destroy();return
            self.root.after(30,self.poll);return
        try:
            item=self.mailbox.get_nowait()
        except queue.Empty:
            item=None
        if item and item[0] == 'complete':
            self.finish_session(item[1])
        elif item and item[0] == 'error':
            self.active = False
            self.stop.set()
            self.camera_state.configure(text='Session error')
            self.feedback.configure(text=item[1], fg=CORAL)
            messagebox.showerror('Session unavailable', item[1], parent=self.root)
        elif self.active and item:
            if item[0] == 'frame':
                _,pixels,result,fps=item
                image=Image.fromarray(pixels)
                image=ImageOps.contain(image,(max(1,self.preview.winfo_width()),max(1,self.preview.winfo_height())))
                photo=ImageTk.PhotoImage(image)
                self.preview.configure(image=photo,text='');self.preview.image=photo
                countdown = result.get('countdown', 0)
                self.camera_state.configure(text=f'Starting in {countdown}…' if countdown else 'Recording')
                self.reps.configure(text=f'{result["repetition_count"]} / {self.session_target}')
                self.progress_count = result['repetition_count']
                self.draw_progress()
                self.phase.configure(text=result.get('movement_phase', result['phase']).replace('_',' ').capitalize())
                self.fps.configure(text=f'{fps:.1f} FPS')
                self.session_form.configure(text=f'Get ready: {countdown}' if countdown else
                                            'Complete your target. Overall form is checked when the recording ends.', fg=MUTED)
                status=result['status']
                title={'rule_pass':'No rule issue detected', 'rule_flag':'Check your movement',
                       'pending':'Checking movement', 'unassessable':'Adjust your position'}.get(status,status)
                color=ACCENT if status=='rule_pass' else CORAL if status=='rule_flag' else TEXT
                self.feedback.configure(text=title+' | '+result['feedback'],fg=color)
        if not self.active and (self.worker is None or not self.worker.is_alive()):
            self.start_button.set_text('Start Session');self.start_button.set_enabled(True)
            self.set_target_enabled(True)
        self.root.after(30,self.poll)

    def quit(self):
        self.closing=True;self.active=False;self.stop.set()
        self.root.withdraw()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,default=ROOT/'models/pose_landmarker_lite.task')
    args=parser.parse_args()
    try:
        root=tk.Tk()
    except tk.TclError as error:
        parser.exit(1,f'Desktop display unavailable: {error}\nRun this interface on your laptop with a graphical desktop.\n')
    PostureApp(root,args.model)
    root.mainloop()


if __name__=='__main__':
    main()
