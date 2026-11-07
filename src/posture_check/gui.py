"""Desktop interface for the selected-exercise live posture pipeline."""
import argparse
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import cv2
from PIL import Image, ImageTk, ImageOps

from .__main__ import process, CONNECTIONS
from .pose import PoseEstimator
from .temporal import TemporalAnalyzer

ROOT = Path(__file__).resolve().parents[2]
EXERCISES = {'Squat': 'squat', 'Push-up': 'pushup', 'Lunge': 'lunge',
             'Jumping jack': 'jumping_jack'}
BG, PANEL, TEXT, MUTED, ACCENT = '#101719', '#1b2528', '#edf3ec', '#9aaba6', '#c6ed91'


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


def camera_worker(mailbox, stop, model, exercise, camera, mirror, skeleton):
    """Own all native resources here; never access Tk from this thread."""
    capture = estimator = None
    try:
        capture = cv2.VideoCapture(camera)
        if not capture.isOpened():
            raise RuntimeError('Cannot open this camera. Check camera permissions, close other camera apps, or choose another camera index in Settings.')
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        estimator = PoseEstimator(model)
        analyzer = TemporalAnalyzer(exercise, 30)
        previous = time.perf_counter()
        while not stop.is_set():
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError('The camera stopped sending frames. Reconnect it and try again.')
            landmarks, raw = process(frame, estimator, exercise)
            now = time.perf_counter()
            dt = max(now - previous, .001)
            previous = now
            result = analyzer.update(raw, dt_seconds=dt)
            if skeleton and landmarks and result['features'] is not None:
                h, w = frame.shape[:2]
                for a, b in CONNECTIONS:
                    if all(min(landmarks[i].visibility, landmarks[i].presence) >= .5 for i in (a, b)):
                        points = [(int(landmarks[i].x*w), int(landmarks[i].y*h)) for i in (a,b)]
                        cv2.line(frame, *points, (145, 237, 198), 3, cv2.LINE_AA)
                        for point in points:
                            cv2.circle(frame, point, 4, (245, 250, 245), -1, cv2.LINE_AA)
            # Analyze the original camera orientation; mirror only the display.
            if mirror:
                frame = cv2.flip(frame, 1)
            publish_latest(mailbox, ('frame', cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), result, 1/dt))
    except Exception as error:
        publish_latest(mailbox, ('error', str(error)))
    finally:
        if capture is not None:
            capture.release()
        if estimator is not None:
            estimator.close()


class PostureApp:
    def __init__(self, root, model):
        self.root, self.model = root, model
        self.exercise = tk.StringVar(value='Squat')
        self.camera = tk.IntVar(value=0)
        self.mirror = tk.BooleanVar(value=True)
        self.skeleton = tk.BooleanVar(value=True)
        self.mailbox = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.worker = None
        self.active = self.closing = False
        self.dialog = None
        root.title('Posture Check')
        width = min(1200, max(1000, root.winfo_screenwidth() - 80))
        height = min(780, max(640, root.winfo_screenheight() - 100))
        root.geometry(f'{width}x{height}'); root.minsize(1000, 640)
        root.configure(bg=BG)
        root.protocol('WM_DELETE_WINDOW', self.quit)
        root.bind('<Escape>', lambda event: self.stop_camera() if self.active else None)
        style = ttk.Style(root); style.theme_use('clam')
        style.configure('TCombobox', padding=8)
        self.shell = tk.Frame(root, bg=BG); self.shell.pack(fill='both', expand=True, padx=28, pady=28)
        self.menu = tk.Frame(self.shell, bg=PANEL, padx=32, pady=30, width=310)
        self.menu.place(relx=.5, rely=.5, anchor='center', width=390, height=min(650, height - 56))
        self.label(self.menu, 'MOVE WITH INTENTION', 10, MUTED).pack(anchor='w')
        self.label(self.menu, 'Posture\nCheck', 42, TEXT, bold=True).pack(anchor='w', pady=(18,10))
        self.label(self.menu, 'Your movement. A clearer view.', 11, MUTED).pack(anchor='w', pady=(0,24))
        self.start_button = self.button(self.menu, 'Start Camera', self.toggle_camera, primary=True)
        self.start_button.pack(fill='x', pady=5)
        self.button(self.menu, 'Choose Exercise', self.choose_exercise).pack(fill='x', pady=5)
        self.button(self.menu, 'Settings', self.settings).pack(fill='x', pady=5)
        self.button(self.menu, 'Quit', self.quit).pack(fill='x', pady=5)
        self.mode_label = self.label(self.menu, '', 10, MUTED)
        self.mode_label.pack(anchor='w', pady=(20,0))
        self.exercise.trace_add('write', lambda *_: self.update_mode())
        self.update_mode()
        self.workspace = tk.Frame(self.shell, bg=BG)
        header = tk.Frame(self.workspace, bg=BG);header.pack(fill='x', pady=(0,14))
        self.label(header, 'LIVE SESSION', 11, ACCENT, bold=True).pack(side='left')
        self.camera_state = self.label(header, 'Camera off', 10, MUTED);self.camera_state.pack(side='right')
        self.preview = tk.Label(self.workspace, bg='#080d0f', fg=MUTED,
                                text='Your camera preview will appear here', font=('Arial',12))
        self.preview.image = None
        self.preview.pack(fill='both', expand=True)
        stats = tk.Frame(self.workspace, bg=PANEL, padx=20, pady=15);stats.pack(fill='x', pady=(14,0))
        self.reps = self.label(stats, '0', 32, ACCENT, bold=True);self.reps.pack(side='left')
        self.label(stats, '  ESTIMATED REPS', 10, MUTED).pack(side='left', padx=(0,25))
        self.phase = self.label(stats, 'Waiting for movement', 12, TEXT);self.phase.pack(side='left')
        self.fps = self.label(stats, '— FPS', 10, MUTED);self.fps.pack(side='right')
        self.feedback = self.label(self.workspace, 'Ready when you are.', 13, TEXT)
        self.feedback.configure(wraplength=550, justify='left');self.feedback.pack(anchor='w', pady=(16,4))
        self.guidance = self.label(self.workspace, '', 10, MUTED);self.guidance.pack(anchor='w')
        self.label(self.workspace, 'Experimental feedback | Counts estimate movement, not form quality.', 9, MUTED).pack(anchor='w', pady=(10,0))
        root.after(30, self.poll)

    @staticmethod
    def label(parent, text, size, color, bold=False):
        return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color,
                        font=('Arial', size, 'bold' if bold else 'normal'), anchor='w')

    @staticmethod
    def button(parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, font=('Arial',12,'bold'),
                         bg=ACCENT if primary else '#2a3639', fg=BG if primary else TEXT,
                         activebackground='#b4dc7e' if primary else '#3a484b', activeforeground=TEXT,
                         relief='flat', bd=0, padx=18, pady=12, anchor='w', cursor='hand2')

    def update_mode(self):
        self.mode_label.configure(text='Selected  /  '+self.exercise.get())

    def show_workspace(self):
        self.menu.place_forget()
        self.menu.pack(side='left', fill='y', padx=(0,24));self.menu.pack_propagate(False)
        self.menu.configure(width=300)
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
        if self.dialog is not None:
            self.dialog.destroy();self.dialog = None
        self.show_workspace()
        self.stop = threading.Event()
        self.mailbox = queue.Queue(maxsize=1)
        self.active = True
        self.reps.configure(text='0');self.phase.configure(text='Waiting for movement')
        self.feedback.configure(text='Opening camera…', fg=TEXT)
        self.camera_state.configure(text='Connecting…');self.start_button.configure(text='Stop Camera')
        self.worker = threading.Thread(target=camera_worker, args=(self.mailbox,self.stop,self.model,
            EXERCISES[self.exercise.get()],self.camera.get(),self.mirror.get(),self.skeleton.get()),daemon=True)
        self.worker.start()

    def stop_camera(self):
        self.active = False;self.stop.set()
        self.start_button.configure(text='Stopping…', state='disabled')
        self.camera_state.configure(text='Camera off')
        self.preview.configure(image='', text='Camera stopped');self.preview.image = None
        self.feedback.configure(text='Session stopped. Start Camera begins a new count.', fg=TEXT)

    def dialog_window(self, title):
        if self.worker is not None and self.worker.is_alive():
            messagebox.showinfo('Stop camera first', 'Stop the camera before changing exercise or settings.', parent=self.root)
            return None
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.lift();return None
        window = tk.Toplevel(self.root);self.dialog=window
        window.title(title);window.configure(bg=PANEL);window.resizable(False,False)
        window.transient(self.root)
        def close():
            window.destroy();self.dialog=None
        window.protocol('WM_DELETE_WINDOW',close)
        body=tk.Frame(window,bg=PANEL,padx=28,pady=24);body.pack()
        self.label(body,title,20,TEXT,True).pack(anchor='w',pady=(0,18))
        return body,close

    def choose_exercise(self):
        dialog=self.dialog_window('Choose exercise')
        if dialog is None:return
        body,close=dialog
        for name in EXERCISES:
            tk.Radiobutton(body,text=name,variable=self.exercise,value=name,bg=PANEL,fg=TEXT,
                selectcolor='#34443a',activebackground=PANEL,activeforeground=ACCENT,
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
            tk.Checkbutton(body,text=text,variable=variable,bg=PANEL,fg=TEXT,selectcolor='#34443a',
                activebackground=PANEL,activeforeground=TEXT,font=('Arial',11)).pack(anchor='w',pady=7)
        self.label(body,'Video stays on this device.\nLive sessions are not recorded.',10,MUTED).pack(pady=16)
        def save():
            self.camera.set(int(selected.get()));close()
        self.button(body,'Done',save,True).pack(fill='x')

    def poll(self):
        if self.closing:
            if self.worker is None or not self.worker.is_alive():
                self.root.destroy();return
            self.root.after(30,self.poll);return
        try:
            item=self.mailbox.get_nowait()
        except queue.Empty:
            item=None
        if self.active and item:
            if item[0]=='error':
                self.stop_camera()
                self.feedback.configure(text=item[1],fg='#ffbb9c')
                messagebox.showerror('Camera unavailable',item[1],parent=self.root)
            else:
                _,pixels,result,fps=item
                image=Image.fromarray(pixels)
                image=ImageOps.contain(image,(max(1,self.preview.winfo_width()),max(1,self.preview.winfo_height())))
                photo=ImageTk.PhotoImage(image)
                self.preview.configure(image=photo,text='');self.preview.image=photo
                self.camera_state.configure(text='Camera on')
                self.reps.configure(text=str(result['repetition_count']))
                self.phase.configure(text=result['phase'].replace('_',' ').capitalize())
                self.fps.configure(text=f'{fps:.1f} FPS')
                status=result['status']
                title={'rule_pass':'No rule issue detected', 'rule_flag':'Check your movement',
                       'pending':'Checking movement', 'unassessable':'Adjust your position'}.get(status,status)
                color=ACCENT if status=='rule_pass' else '#ffbb9c' if status=='rule_flag' else TEXT
                self.feedback.configure(text=title+' | '+result['feedback'],fg=color)
        if not self.active and (self.worker is None or not self.worker.is_alive()):
            self.start_button.configure(text='Start Camera',state='normal')
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
