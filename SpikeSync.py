import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Label
import numpy as np
import pandas as pd
import cv2
from moviepy.editor import VideoFileClip, AudioFileClip
import soundfile as sf
import tempfile
import os
import re
import sys
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import time
import sounddevice as sd

SAMPLE_RATE = 30000

def readTrodesExtractedDataFile(filename):
    with open(filename, 'rb') as f:
        if f.readline().decode('ascii').strip() != '<Start settings>':
            raise Exception("Settings format not supported")

        fields = True
        fieldsText = {}
        for line in f:
            if fields:
                line = line.decode('ascii').strip()
                if line != '<End settings>':
                    vals = line.split(': ')
                    fieldsText.update({vals[0].lower(): vals[1]})
                else:
                    fields = False
                    dt = parseFields(fieldsText['fields'])
                    fieldsText['data'] = np.zeros([1], dtype=dt)
                    break

        dt = parseFields(fieldsText['fields'])
        data = np.fromfile(f, dt)
        fieldsText.update({'data': data})
        return fieldsText

def parseFields(fieldstr):
    sep = re.split(r'\s+', re.sub(r"[<>]", ' ', fieldstr).strip())
    typearr = []
    for i in range(0, len(sep), 2):
        fieldname = sep[i]
        repeats = 1
        ftype = 'uint32'
        if '*' in sep[i+1]:
            temptypes = re.split(r'\*', sep[i+1])
            ftype = temptypes[0] if temptypes[0].isalpha() else temptypes[1]
            repeats = int(temptypes[0]) if temptypes[0].isdigit() else int(temptypes[1])
        else:
            ftype = sep[i+1]

        try:
            fieldtype = getattr(np, ftype)
        except AttributeError:
            print(ftype + " is not a valid field type.")
            sys.exit(1)
        else:
            typearr.append((str(fieldname), fieldtype, repeats))
    return np.dtype(typearr)

def align_timestamp_and_rawdata(df_ts, df_rd):
    min_len = min(len(df_ts), len(df_rd))
    return pd.concat([df_ts.iloc[:min_len].reset_index(drop=True),
                      df_rd.iloc[:min_len].reset_index(drop=True)], axis=1)

class DataAlignerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SpikeSync")
        self.root.configure(bg='black')

        self.timestamp_file = None
        self.rawdata_file = None
        self.video_file = None
        self.aligned_data = None
        self.video_clip = None
        self.video_fps = None
        self.raw_segment = None
        self.sample_start_idx = 0
        self.sample_end_idx = 0
        self.start_sec = 0

        self.is_playing = False
        self.is_muted = True
        self.playback_thread = None

        # Left panel
        left_frame = tk.Frame(root, bg='black')
        left_frame.pack(side='left', fill='y', padx=10, pady=10)

        btn_font = ('Arial', 10)
        entry_bg = '#333333'
        fg = 'white'

        tk.Button(left_frame, text="Upload Timestamp File", command=self.load_timestamp, font=btn_font, bg=entry_bg, fg=fg).pack(fill='x', pady=5)
        tk.Button(left_frame, text="Upload Raw Data File", command=self.load_rawdata, font=btn_font, bg=entry_bg, fg=fg).pack(fill='x', pady=5)
        tk.Button(left_frame, text="Upload Video File", command=self.load_video, font=btn_font, bg=entry_bg, fg=fg).pack(fill='x', pady=5)

        tk.Label(left_frame, text="Start Time (HH:MM:SS):", bg='black', fg='white').pack()
        self.start_entry = tk.Entry(left_frame, bg=entry_bg, fg=fg)
        self.start_entry.pack(fill='x')

        tk.Label(left_frame, text="End Time (HH:MM:SS):", bg='black', fg='white').pack()
        self.end_entry = tk.Entry(left_frame, bg=entry_bg, fg=fg)
        self.end_entry.pack(fill='x')

        tk.Button(left_frame, text="Align and Export", command=self.run_alignment, font=btn_font, bg='#444444', fg=fg).pack(fill='x', pady=10)
        tk.Button(left_frame, text="Segment Info", command=self.show_segment_info, font=btn_font, bg='#555555', fg=fg).pack(fill='x', pady=5)
        tk.Button(left_frame, text="Save Aligned CSV", command=self.save_aligned_csv, font=btn_font, bg='#666666', fg=fg).pack(fill='x', pady=5)

        # Right panel
        self.right_frame = tk.Frame(root, bg='black')
        self.right_frame.pack(side='right', fill='both', expand=True)

        self.canvas_label = tk.Label(self.right_frame, text="Video Preview", bg='black', fg='white')
        self.canvas_label.pack()
        self.video_canvas = tk.Label(self.right_frame)
        self.video_canvas.pack()

        self.graph_label = tk.Label(self.right_frame, text="Signal Visualization", bg='black', fg='white')
        self.graph_label.pack()
        self.fig, self.ax = plt.subplots(figsize=(6, 2))
        self.ax.set_facecolor('black')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.fig.patch.set_facecolor('black')
        self.line, = self.ax.plot([], [], color='lime')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        control_frame = tk.Frame(self.right_frame, bg='black')
        control_frame.pack(pady=10)

        self.play_btn = tk.Button(control_frame, text="▶️ Play", command=self.toggle_playback, bg='#333', fg='white')
        self.play_btn.pack(side='left', padx=5)

        self.mute_btn = tk.Button(control_frame, text="🔇 Mute", command=self.toggle_mute, bg='#333', fg='white')
        self.mute_btn.pack(side='left', padx=5)

    def load_timestamp(self):
        self.timestamp_file = filedialog.askopenfilename(title="Select timestamp .dat file")

    def load_rawdata(self):
        self.rawdata_file = filedialog.askopenfilename(title="Select spikeband .dat file")

    def load_video(self):
        self.video_file = filedialog.askopenfilename(title="Select video file")

    def run_alignment(self):
        threading.Thread(target=self._run_alignment).start()

    def _run_alignment(self):
        try:
            ts_data = readTrodesExtractedDataFile(self.timestamp_file)
            rd_data = readTrodesExtractedDataFile(self.rawdata_file)
            df_ts = pd.DataFrame.from_records(ts_data['data'])
            df_rd = pd.DataFrame.from_records(rd_data['data'])
            df_aligned = align_timestamp_and_rawdata(df_ts, df_rd)
            self.aligned_data = df_aligned

            start = self.start_entry.get().strip()
            end = self.end_entry.get().strip()
            self.start_sec = self.hms_to_seconds(start)
            end_sec = self.hms_to_seconds(end)
            duration = end_sec - self.start_sec
            if self.start_sec >= end_sec:
                raise ValueError("Start time must be less than end time.")

            self.video_clip = VideoFileClip(self.video_file).subclip(self.start_sec, end_sec)
            self.video_fps = self.video_clip.fps

            self.sample_start_idx = int(self.start_sec * SAMPLE_RATE)
            self.sample_end_idx = int(end_sec * SAMPLE_RATE)

            audio_col = next((col for col in df_aligned.columns if df_aligned[col].dtype in [np.int16, np.float32, np.int32]), None)
            if not audio_col:
                raise ValueError("No valid audio channel found.")

            self.raw_segment = df_aligned[audio_col].values[self.sample_start_idx:self.sample_end_idx].astype(np.float32)
            self.raw_segment /= np.max(np.abs(self.raw_segment))

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                sf.write(tmp_wav.name, self.raw_segment, SAMPLE_RATE)
                tmp_audio = tmp_wav.name

            clip_with_audio = self.video_clip.set_audio(AudioFileClip(tmp_audio))
            output_path = filedialog.asksaveasfilename(defaultextension=".mp4", title="Save Final Video As")
            if output_path:
                clip_with_audio.write_videofile(output_path, codec='libx264', audio_codec='aac')

            os.remove(tmp_audio)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def toggle_playback(self):
        if self.is_playing:
            self.is_playing = False
            self.play_btn.config(text="▶️ Play")
            sd.stop()
        else:
            self.is_playing = True
            self.play_btn.config(text="⏸️ Pause")
            if self.playback_thread is None or not self.playback_thread.is_alive():
                self.playback_thread = threading.Thread(target=self.play_preview_and_visualize)
                self.playback_thread.start()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.mute_btn.config(text="🔇 Mute" if self.is_muted else "🔊 Unmute")

    def play_preview_and_visualize(self):
        frames = list(self.video_clip.iter_frames(fps=self.video_fps))
        frame_interval = 1 / self.video_fps
        samples_per_frame = int(SAMPLE_RATE / self.video_fps)

        if not self.is_muted:
            sd.play(self.raw_segment, samplerate=SAMPLE_RATE, blocking=False)

        for idx, frame in enumerate(frames):
            if not self.is_playing:
                break

            img = Image.fromarray(frame)
            img = img.resize((320, 240))
            img_tk = ImageTk.PhotoImage(image=img)
            self.video_canvas.configure(image=img_tk)
            self.video_canvas.image = img_tk

            start_idx = idx * samples_per_frame
            end_idx = start_idx + samples_per_frame
            signal_chunk = self.raw_segment[start_idx:end_idx]
            self.line.set_data(np.arange(len(signal_chunk)), signal_chunk)
            self.ax.set_xlim(0, len(signal_chunk))
            self.ax.set_ylim(-1.1, 1.1)
            self.canvas.draw()

            time.sleep(frame_interval)

        self.is_playing = False
        self.play_btn.config(text="▶️ Play")
        sd.stop()

    def show_segment_info(self):
        if self.raw_segment is None:
            messagebox.showinfo("No Segment", "You must run alignment first.")
            return

        frames = int((self.sample_end_idx - self.sample_start_idx) / (SAMPLE_RATE / self.video_fps))
        seconds = (self.sample_end_idx - self.sample_start_idx) / SAMPLE_RATE
        total_samples = self.sample_end_idx - self.sample_start_idx

        popup = Toplevel(self.root)
        popup.title("Segment Info")
        popup.configure(bg='black')
        Label(popup, text=f"Segment Duration: {seconds:.2f} seconds", bg='black', fg='white').pack(pady=2)
        Label(popup, text=f"Total Frames: {frames}", bg='black', fg='white').pack(pady=2)
        Label(popup, text=f"Total Samples: {total_samples}", bg='black', fg='white').pack(pady=2)
        Label(popup, text=f"Video FPS: {self.video_fps}", bg='black', fg='white').pack(pady=2)
        Label(popup, text=f"Sample Rate: {SAMPLE_RATE}", bg='black', fg='white').pack(pady=2)

    def save_aligned_csv(self):
        if self.aligned_data is None:
            messagebox.showerror("Error", "Run alignment first.")
            return

        audio_col = next((col for col in self.aligned_data.columns if self.aligned_data[col].dtype in [np.int16, np.float32, np.int32]), None)
        timestamps = self.aligned_data['time'].values[self.sample_start_idx:self.sample_end_idx]
        voltages = self.aligned_data[audio_col].values[self.sample_start_idx:self.sample_end_idx]

        seconds = np.arange(self.sample_start_idx, self.sample_end_idx) // SAMPLE_RATE
        frames = ((np.arange(self.sample_start_idx, self.sample_end_idx) - self.sample_start_idx) / (SAMPLE_RATE / self.video_fps)).astype(int)

        df = pd.DataFrame({
            'time': timestamps,
            'voltage': voltages,
            'frame': frames,
            'second': seconds
        })

        path = filedialog.asksaveasfilename(defaultextension=".csv", title="Save CSV File")
        if path:
            df.to_csv(path, index=False)
            messagebox.showinfo("Saved", f"CSV saved to {path}")

    def hms_to_seconds(self, hms):
        h, m, s = map(int, hms.strip().split(":"))
        return h * 3600 + m * 60 + s

if __name__ == '__main__':
    root = tk.Tk()
    app = DataAlignerApp(root)
    root.mainloop()
