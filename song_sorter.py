"""
SongSorter — AI-Powered Instrumental vs Vocal Classifier  v2.0
Premium Gold Edition — Smooth animations, glassmorphism, golden UI
Uses Groq Whisper API to detect vocals in MP4 files.
Moves instrumental files to Instru folder, vocal files to Trash folder.
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import threading
import time
import math
import requests
import customtkinter as ctk
from tkinter import filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3-turbo"
SAMPLE_DURATION = 25          # seconds of audio to sample (keeps under 25MB)
SAMPLE_OFFSET_PERCENT = 0.3   # start sampling at 30% of the track (skip intros)
MAX_WORKERS = 4               # parallel API calls
VOCAL_WORD_THRESHOLD = 3      # minimum words to classify as vocal
INSTRUMENTAL_DIR = r"C:\Users\Crystal\OneDrive - SRc\YT\Instru"
TRASH_DIR = r"C:\Users\Crystal\OneDrive - SRc\YT\Trash"

# ─── Premium Gold Color Palette ──────────────────────────────────────────────
COLORS = {
    "bg_dark":       "#0c0c14",     # deep space black
    "bg_card":       "#12121e",     # card background
    "bg_header":     "#161625",     # header background
    "bg_controls":   "#0f0f1c",     # controls bar
    "bg_item":       "#16162a",     # list item
    "bg_item_hover": "#1e1e38",     # list item hover
    "bg_input":      "#0a0a16",     # input fields
    
    "gold":          "#d4a843",     # primary gold
    "gold_light":    "#f0d078",     # light gold / highlight
    "gold_dark":     "#a07830",     # dark gold
    "gold_glow":     "#e8c860",     # gold glow
    "gold_muted":    "#8a7040",     # muted gold for borders
    
    "accent_green":  "#4ade80",     # success green
    "accent_red":    "#f87171",     # error/vocal red
    "accent_blue":   "#60a5fa",     # info blue
    "accent_amber":  "#fbbf24",     # warning amber
    "accent_purple": "#a78bfa",     # purple accent
    "accent_cyan":   "#22d3ee",     # instrumental cyan
    
    "text_primary":  "#f0e6d0",     # warm white text
    "text_secondary":"#a09880",     # muted gold text
    "text_dim":      "#605848",     # very dim text
    "text_bright":   "#fff8e8",     # bright text
    
    "border":        "#2a2a40",     # subtle border
    "border_gold":   "#3d3520",     # gold border
    "gradient_start":"#1a1428",     # gradient purple-ish  
    "gradient_end":  "#0c0c14",     # gradient to dark
}

# ─── Core Logic ──────────────────────────────────────────────────────────────

def get_audio_duration(filepath):
    """Get duration of an audio/video file using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", filepath],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 120.0  # default 2 min if probe fails


def extract_audio_sample(filepath, output_path, duration=SAMPLE_DURATION, offset_pct=SAMPLE_OFFSET_PERCENT):
    """Extract a short audio sample from the middle of the track."""
    total_duration = get_audio_duration(filepath)
    
    start_time = max(0, total_duration * offset_pct)
    if start_time + duration > total_duration:
        start_time = max(0, total_duration - duration)
    actual_duration = min(duration, total_duration)
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", filepath,
        "-t", str(actual_duration),
        "-vn",                    # no video
        "-acodec", "libmp3lame",  # compress to mp3
        "-ar", "16000",           # 16kHz (Whisper optimal)
        "-ac", "1",               # mono
        "-b:a", "64k",            # low bitrate for speed
        "-loglevel", "error",
        output_path
    ]
    
    subprocess.run(cmd, capture_output=True, timeout=30,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    return output_path


def classify_with_groq(audio_path, api_key):
    """Send audio to Groq Whisper and classify based on transcription.
    Returns: (classification, detail_string, full_lyrics_text)
    """
    file_size = os.path.getsize(audio_path)
    if file_size > 25 * 1024 * 1024:
        return "error", "File too large for API (>25MB)", ""
    
    with open(audio_path, "rb") as f:
        response = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (os.path.basename(audio_path), f, "audio/mpeg")},
            data={
                "model": GROQ_MODEL,
                "response_format": "verbose_json",
                "language": "en"
            },
            timeout=60
        )
    
    if response.status_code == 429:
        time.sleep(3)
        with open(audio_path, "rb") as f:
            response = requests.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (os.path.basename(audio_path), f, "audio/mpeg")},
                data={
                    "model": GROQ_MODEL,
                    "response_format": "verbose_json",
                    "language": "en"
                },
                timeout=60
            )
    
    if response.status_code != 200:
        error_msg = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
        return "error", error_msg, ""
    
    data = response.json()
    text = data.get("text", "").strip()
    segments = data.get("segments", [])
    
    # Classification Logic
    clean_text = text
    for noise in ["[Music]", "[Applause]", "[Laughter]", "(Music)", 
                  "[music]", "...", "♪", "🎵", "[MUSIC]", "[ Music]",
                  "[BLANK_AUDIO]", "[silence]", "[Silence]"]:
        clean_text = clean_text.replace(noise, "")
    
    words = [w for w in clean_text.split() if len(w) > 1]
    word_count = len(words)
    
    avg_confidence = 0
    if segments:
        confidences = [s.get("avg_logprob", -1) for s in segments]
        avg_confidence = sum(confidences) / len(confidences)
    
    if word_count <= VOCAL_WORD_THRESHOLD:
        return "instrumental", f"Words: {word_count} | '{text[:60]}'", text
    elif word_count > VOCAL_WORD_THRESHOLD and avg_confidence > -1.0:
        return "vocal", f"Words: {word_count} | '{text[:60]}'", text
    elif word_count > VOCAL_WORD_THRESHOLD * 3:
        return "vocal", f"Words: {word_count} | '{text[:60]}'", text
    else:
        return "instrumental", f"Words: {word_count} (low conf) | '{text[:60]}'", text


def process_single_file(filepath, api_key, temp_dir):
    """Process one MP4 file: extract sample → classify → return result."""
    try:
        sample_path = os.path.join(temp_dir, f"sample_{hash(filepath) & 0xFFFFFFFF}.mp3")
        extract_audio_sample(filepath, sample_path)
        
        if not os.path.exists(sample_path) or os.path.getsize(sample_path) < 1000:
            return filepath, "error", "Failed to extract audio", "", ""
        
        classification, detail, lyrics_text = classify_with_groq(sample_path, api_key)
        
        if classification != "vocal":
            try:
                os.remove(sample_path)
            except:
                pass
            sample_path = ""
        
        return filepath, classification, detail, lyrics_text, sample_path
        
    except Exception as e:
        return filepath, "error", str(e), "", ""


def copy_file(filepath, classification):
    """Copy file to the appropriate directory."""
    filename = os.path.basename(filepath)
    
    if classification == "instrumental":
        dest_dir = INSTRUMENTAL_DIR
    elif classification == "vocal":
        dest_dir = TRASH_DIR
    else:
        return False, "Unknown classification"
    
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    
    if os.path.exists(dest_path):
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{name}_{counter}{ext}")
            counter += 1
    
    shutil.copy2(filepath, dest_path)
    return True, dest_path


# ─── Animated Widgets ────────────────────────────────────────────────────────

class PulsingDot(ctk.CTkFrame):
    """Small dot that pulses with a glow animation."""
    def __init__(self, parent, color=COLORS["gold"], size=8, **kwargs):
        super().__init__(parent, width=size, height=size, corner_radius=size//2,
                         fg_color=color, **kwargs)
        self._color = color
        self._size = size
        self._phase = 0
        self._animating = False
    
    def start(self):
        self._animating = True
        self._pulse()
    
    def stop(self):
        self._animating = False
        self.configure(fg_color=self._color)
    
    def _pulse(self):
        if not self._animating:
            return
        self._phase += 0.15
        alpha = (math.sin(self._phase) + 1) / 2  # 0 to 1
        # Interpolate between dim and bright
        r1, g1, b1 = 60, 48, 24
        r2, g2, b2 = 240, 208, 96
        r = int(r1 + (r2 - r1) * alpha)
        g = int(g1 + (g2 - g1) * alpha)
        b = int(b1 + (b2 - b1) * alpha)
        self.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")
        self.after(50, self._pulse)


class AnimatedProgressBar(ctk.CTkFrame):
    """Custom progress bar with golden glow animation."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=6, corner_radius=3,
                         fg_color=COLORS["bg_card"], **kwargs)
        self._progress = 0
        self._bar = ctk.CTkFrame(self, height=6, corner_radius=3,
                                  fg_color=COLORS["gold"])
        self._bar.place(relx=0, rely=0, relheight=1, relwidth=0)
        self._glow_phase = 0
        self._animating = False
    
    def set(self, value):
        """Set progress 0.0 to 1.0"""
        self._progress = max(0, min(1, value))
        self._bar.place(relx=0, rely=0, relheight=1, relwidth=self._progress)
        # Animate color based on progress
        if self._progress >= 1.0:
            self._bar.configure(fg_color=COLORS["accent_green"])
        elif self._progress > 0:
            self._bar.configure(fg_color=COLORS["gold_glow"])
    
    def start_glow(self):
        self._animating = True
        self._glow()
    
    def stop_glow(self):
        self._animating = False
        self._bar.configure(fg_color=COLORS["gold"])
    
    def _glow(self):
        if not self._animating:
            return
        self._glow_phase += 0.1
        alpha = (math.sin(self._glow_phase) + 1) / 2
        r = int(160 + 80 * alpha)
        g = int(120 + 88 * alpha)
        b = int(48 + 48 * alpha)
        self._bar.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")
        self.after(50, self._glow)


class GoldButton(ctk.CTkButton):
    """Premium gold-themed button with hover glow."""
    def __init__(self, parent, text, command=None, style="primary", **kwargs):
        styles = {
            "primary": {
                "fg_color": COLORS["gold_dark"],
                "hover_color": COLORS["gold"],
                "text_color": COLORS["bg_dark"],
                "border_color": COLORS["gold_muted"],
            },
            "secondary": {
                "fg_color": COLORS["bg_card"],
                "hover_color": COLORS["bg_item"],
                "text_color": COLORS["gold_light"],
                "border_color": COLORS["border_gold"],
            },
            "danger": {
                "fg_color": "#3d1515",
                "hover_color": "#5d2020",
                "text_color": COLORS["accent_red"],
                "border_color": "#4d2020",
            },
            "success": {
                "fg_color": "#153d20",
                "hover_color": "#205d30",
                "text_color": COLORS["accent_green"],
                "border_color": "#204d30",
            },
            "action": {
                "fg_color": COLORS["gold"],
                "hover_color": COLORS["gold_light"],
                "text_color": COLORS["bg_dark"],
                "border_color": COLORS["gold_glow"],
            },
        }
        s = styles.get(style, styles["primary"])
        
        # Allow callers to override font via kwargs
        btn_font = kwargs.pop("font", ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
        
        super().__init__(
            parent, text=text, command=command,
            fg_color=s["fg_color"],
            hover_color=s["hover_color"],
            text_color=s["text_color"],
            border_color=s["border_color"],
            border_width=1,
            corner_radius=8,
            font=btn_font,
            **kwargs
        )


# ─── GUI Application ─────────────────────────────────────────────────────────

class SongSorterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("SongSorter — AI Music Classifier")
        self.geometry("960x780")
        self.minsize(860, 660)
        
        ctk.set_appearance_mode("dark")
        
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.files = []
        self.processing = False
        self.results = {}
        self.preview_process = None
        self.preview_window = None
        self.temp_dir = None
        
        # Animation state
        self._header_phase = 0
        self._particle_dots = []
        
        self.configure(fg_color=COLORS["bg_dark"])
        self._build_ui()
        self._start_ambient_animation()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _build_ui(self):
        # ─── Header with animated gold accent ─────────────────────
        self._build_header()
        # ─── Controls Bar ─────────────────────────────────────────
        self._build_controls()
        # ─── Destination Info ─────────────────────────────────────
        self._build_destination_bar()
        # ─── File List ────────────────────────────────────────────
        self._build_file_list()
        # ─── Progress Section ─────────────────────────────────────
        self._build_progress()
    
    def _build_header(self):
        # Main header container
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_header"], corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Gold accent line at top
        accent_line = ctk.CTkFrame(self, fg_color=COLORS["gold"], corner_radius=0, height=2)
        accent_line.pack(fill="x")
        self._accent_line = accent_line
        
        # Inner content
        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=24)
        
        # Left side - Title
        title_frame = ctk.CTkFrame(inner, fg_color="transparent")
        title_frame.pack(side="left", fill="y")
        
        # App icon and name row
        top_row = ctk.CTkFrame(title_frame, fg_color="transparent")
        top_row.pack(anchor="w", pady=(18, 0))
        
        ctk.CTkLabel(
            top_row, text="♪",
            font=ctk.CTkFont(size=32),
            text_color=COLORS["gold"]
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            top_row, text="SongSorter",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=COLORS["gold_light"]
        ).pack(side="left")
        
        # Version badge
        badge = ctk.CTkFrame(top_row, fg_color=COLORS["gold_dark"], corner_radius=10,
                             width=50, height=22)
        badge.pack(side="left", padx=(10, 0))
        badge.pack_propagate(False)
        ctk.CTkLabel(
            badge, text="v2.0",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["bg_dark"]
        ).pack(expand=True)
        
        # Subtitle
        ctk.CTkLabel(
            title_frame, text="AI-Powered Instrumental vs Vocal Classifier  ·  Groq Whisper",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(4, 0))
        
        # Right side - Status indicator
        status_frame = ctk.CTkFrame(inner, fg_color="transparent")
        status_frame.pack(side="right", fill="y")
        
        status_inner = ctk.CTkFrame(status_frame, fg_color=COLORS["bg_card"],
                                     corner_radius=12, border_width=1,
                                     border_color=COLORS["border_gold"])
        status_inner.pack(expand=True, padx=10, pady=20)
        
        self._status_dot = PulsingDot(status_inner, color=COLORS["accent_green"], size=8)
        self._status_dot.pack(side="left", padx=(12, 6), pady=10)
        
        self._header_status = ctk.CTkLabel(
            status_inner, text="Ready",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["accent_green"]
        )
        self._header_status.pack(side="left", padx=(0, 12), pady=10)
    
    def _build_controls(self):
        controls = ctk.CTkFrame(self, fg_color=COLORS["bg_controls"], corner_radius=0)
        controls.pack(fill="x")
        
        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.pack(pady=14, padx=24, fill="x")
        
        # Left buttons
        left_btns = ctk.CTkFrame(btn_frame, fg_color="transparent")
        left_btns.pack(side="left")
        
        self.btn_add_files = GoldButton(
            left_btns, text="  📁  Add Files  ", style="primary",
            command=self._add_files, height=40, width=140
        )
        self.btn_add_files.pack(side="left", padx=(0, 8))
        
        self.btn_add_folder = GoldButton(
            left_btns, text="  📂  Add Folder  ", style="primary",
            command=self._add_folder, height=40, width=150
        )
        self.btn_add_folder.pack(side="left", padx=(0, 8))
        
        self.btn_clear = GoldButton(
            left_btns, text="  🗑  Clear  ", style="danger",
            command=self._clear_files, height=40, width=110
        )
        self.btn_clear.pack(side="left", padx=(0, 8))
        
        # Right side
        right_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        right_frame.pack(side="right")
        
        self.file_count_label = ctk.CTkLabel(
            right_frame, text="0 files loaded",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"]
        )
        self.file_count_label.pack(side="left", padx=(0, 16))
        
        self.btn_sort = GoldButton(
            right_frame, text="  ⚡  SORT NOW  ", style="action",
            command=self._start_sorting, height=44, width=180,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        )
        self.btn_sort.pack(side="right")
    
    def _build_destination_bar(self):
        dest_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=10,
                                   border_width=1, border_color=COLORS["border_gold"])
        dest_frame.pack(fill="x", padx=20, pady=(12, 6))
        
        dest_inner = ctk.CTkFrame(dest_frame, fg_color="transparent")
        dest_inner.pack(pady=10, padx=18, fill="x")
        
        # Instrumental destination
        instr_frame = ctk.CTkFrame(dest_inner, fg_color="transparent")
        instr_frame.pack(side="left")
        
        ctk.CTkLabel(
            instr_frame, text="🎹",
            font=ctk.CTkFont(size=16)
        ).pack(side="left", padx=(0, 6))
        
        ctk.CTkLabel(
            instr_frame, text="Instrumental →",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["accent_cyan"]
        ).pack(side="left")
        
        ctk.CTkLabel(
            instr_frame, text=INSTRUMENTAL_DIR,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"]
        ).pack(side="left", padx=(8, 0))
        
        # Separator
        sep = ctk.CTkFrame(dest_inner, fg_color=COLORS["gold_muted"], width=1)
        sep.pack(side="left", fill="y", padx=24, pady=2)
        
        # Vocal destination
        vocal_frame = ctk.CTkFrame(dest_inner, fg_color="transparent")
        vocal_frame.pack(side="left")
        
        ctk.CTkLabel(
            vocal_frame, text="🎤",
            font=ctk.CTkFont(size=16)
        ).pack(side="left", padx=(0, 6))
        
        ctk.CTkLabel(
            vocal_frame, text="Vocal →",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["accent_red"]
        ).pack(side="left")
        
        ctk.CTkLabel(
            vocal_frame, text=TRASH_DIR,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"]
        ).pack(side="left", padx=(8, 0))
    
    def _build_file_list(self):
        # Main list container
        list_container = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12,
                                       border_width=1, border_color=COLORS["border"])
        list_container.pack(fill="both", expand=True, padx=20, pady=6)
        
        # Column header
        header_row = ctk.CTkFrame(list_container, fg_color=COLORS["bg_header"], corner_radius=8)
        header_row.pack(fill="x", padx=10, pady=(10, 4))
        
        cols = [
            ("", 30),      # index
            ("File", 350),
            ("Status", 140),
            ("Result", 320),
        ]
        for text, width in cols:
            ctk.CTkLabel(
                header_row, text=text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS["gold"],
                width=width, anchor="w"
            ).pack(side="left", padx=(10 if text == "" else 4, 4), pady=8)
        
        # Scrollable file list
        self.file_list = ctk.CTkScrollableFrame(
            list_container, fg_color=COLORS["bg_dark"], corner_radius=8,
            scrollbar_button_color=COLORS["gold_dark"],
            scrollbar_button_hover_color=COLORS["gold"]
        )
        self.file_list.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        
        # Empty state label
        self._empty_label = ctk.CTkLabel(
            self.file_list,
            text="✦  Drop MP4 files here or click 'Add Files' to begin  ✦",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_dim"]
        )
        self._empty_label.pack(expand=True, pady=60)
        
        self.file_rows = {}
        self._file_index = 0
    
    def _build_progress(self):
        progress_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=12,
                                       border_width=1, border_color=COLORS["border_gold"])
        progress_frame.pack(fill="x", padx=20, pady=(6, 14))
        
        # Top row: label + stats
        top_row = ctk.CTkFrame(progress_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=18, pady=(12, 6))
        
        self.progress_label = ctk.CTkLabel(
            top_row, text="✦  Ready — Add MP4 files to begin",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"]
        )
        self.progress_label.pack(side="left")
        
        self.stats_label = ctk.CTkLabel(
            top_row, text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["gold"]
        )
        self.stats_label.pack(side="right")
        
        # Progress bar
        self.progress_bar = AnimatedProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=18, pady=(0, 12))
    
    # ─── Ambient Animation ───────────────────────────────────────
    def _start_ambient_animation(self):
        self._animate_accent_line()
    
    def _animate_accent_line(self):
        self._header_phase += 0.04
        alpha = (math.sin(self._header_phase) + 1) / 2
        
        r = int(160 + 80 * alpha)
        g = int(130 + 78 * alpha)
        b = int(50 + 30 * alpha)
        
        try:
            self._accent_line.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")
        except:
            return
        
        self.after(60, self._animate_accent_line)
    
    # ─── File Management ─────────────────────────────────────────
    def _add_files(self):
        if self.processing:
            return
        files = filedialog.askopenfilenames(
            title="Select MP4 Files",
            filetypes=[("MP4 files", "*.mp4"), ("All video", "*.mp4;*.mkv;*.avi;*.webm")]
        )
        self._load_files(files)
    
    def _add_folder(self):
        if self.processing:
            return
        folder = filedialog.askdirectory(title="Select Folder with MP4 Files")
        if folder:
            files = []
            for f in os.listdir(folder):
                if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm')):
                    files.append(os.path.join(folder, f))
            self._load_files(files)
    
    def _load_files(self, files):
        if self._empty_label.winfo_exists():
            self._empty_label.destroy()
        
        new_count = 0
        for f in files:
            if f not in self.files:
                self.files.append(f)
                self._file_index += 1
                self._add_file_row(f, self._file_index)
                new_count += 1
        
        self.file_count_label.configure(text=f"{len(self.files)} files loaded")
        
        if new_count > 0:
            self._flash_count_label()
    
    def _flash_count_label(self):
        """Quick flash animation on the count label."""
        self.file_count_label.configure(text_color=COLORS["gold_light"])
        self.after(300, lambda: self.file_count_label.configure(text_color=COLORS["gold"]))
        self.after(600, lambda: self.file_count_label.configure(text_color=COLORS["text_secondary"]))
    
    def _add_file_row(self, filepath, index):
        # Animated row entrance
        row = ctk.CTkFrame(self.file_list, fg_color=COLORS["bg_item"], corner_radius=6,
                           height=42, border_width=1, border_color=COLORS["border"])
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)
        
        # Hover effect
        def on_enter(e):
            row.configure(fg_color=COLORS["bg_item_hover"], border_color=COLORS["gold_muted"])
        def on_leave(e):
            if filepath in self.file_rows:
                current_color = self.file_rows[filepath].get("bg_override", COLORS["bg_item"])
                row.configure(fg_color=current_color, border_color=COLORS["border"])
        
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)
        
        # Index number
        idx_label = ctk.CTkLabel(
            row, text=f"  {index}", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["gold_dark"], width=30, anchor="w"
        )
        idx_label.pack(side="left", padx=(8, 4))
        
        # Filename
        name = os.path.basename(filepath)
        display_name = name if len(name) < 45 else name[:42] + "..."
        name_label = ctk.CTkLabel(
            row, text=display_name,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"], width=340, anchor="w"
        )
        name_label.pack(side="left", padx=4)
        
        # Status
        status_label = ctk.CTkLabel(
            row, text="⏳ Waiting",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"], width=130, anchor="center"
        )
        status_label.pack(side="left", padx=4)
        
        # Preview button (hidden initially)
        preview_btn = GoldButton(
            row, text="▶ Preview", style="success",
            command=lambda fp=filepath: self._preview_lyrics(fp),
            height=28, width=90,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        
        # Result
        result_label = ctk.CTkLabel(
            row, text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"], width=280, anchor="w"
        )
        result_label.pack(side="left", padx=4)
        
        self.file_rows[filepath] = {
            "row": row,
            "index": idx_label,
            "name": name_label,
            "status": status_label,
            "result": result_label,
            "preview_btn": preview_btn,
            "bg_override": COLORS["bg_item"],
        }
    
    def _clear_files(self):
        if self.processing:
            return
        self._stop_preview()
        self.files.clear()
        self.file_rows.clear()
        self.results.clear()
        self._file_index = 0
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None
        for widget in self.file_list.winfo_children():
            widget.destroy()
        
        # Re-add empty label
        self._empty_label = ctk.CTkLabel(
            self.file_list,
            text="✦  Drop MP4 files here or click 'Add Files' to begin  ✦",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_dim"]
        )
        self._empty_label.pack(expand=True, pady=60)
        
        self.file_count_label.configure(text="0 files loaded")
        self.progress_bar.set(0)
        self.progress_label.configure(text="✦  Ready — Add MP4 files to begin")
        self.stats_label.configure(text="")
    
    def _update_row(self, filepath, status_text, status_color, result_text="", row_color=None, show_preview=False):
        """Thread-safe row update with subtle animation."""
        def update():
            if filepath in self.file_rows:
                row_data = self.file_rows[filepath]
                row_data["status"].configure(text=status_text, text_color=status_color)
                if result_text:
                    row_data["result"].configure(text=result_text)
                if row_color:
                    row_data["row"].configure(fg_color=row_color)
                    row_data["bg_override"] = row_color
                if show_preview:
                    row_data["preview_btn"].pack(side="right", padx=(4, 10))
        self.after(0, update)
    
    # ─── Preview ─────────────────────────────────────────────────
    def _preview_lyrics(self, filepath):
        if filepath not in self.results:
            return
        
        info = self.results[filepath]
        lyrics = info.get("lyrics", "(no lyrics detected)")
        sample_path = info.get("sample_path", "")
        filename = os.path.basename(filepath)
        
        self._stop_preview()
        
        # Create Premium Preview Window
        self.preview_window = ctk.CTkToplevel(self)
        self.preview_window.title(f"Preview — {filename}")
        self.preview_window.geometry("560x480")
        self.preview_window.attributes("-topmost", True)
        self.preview_window.configure(fg_color=COLORS["bg_dark"])
        self.preview_window.after(100, lambda: self.preview_window.focus_force())
        
        # Gold accent line
        ctk.CTkFrame(self.preview_window, fg_color=COLORS["gold"], height=2,
                     corner_radius=0).pack(fill="x")
        
        # Header
        header = ctk.CTkFrame(self.preview_window, fg_color=COLORS["bg_header"],
                              corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header, text=f"🎤  {filename}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["gold_light"]
        ).pack(expand=True)
        
        # Lyrics area
        lyrics_container = ctk.CTkFrame(self.preview_window, fg_color=COLORS["bg_card"],
                                         corner_radius=12, border_width=1,
                                         border_color=COLORS["border_gold"])
        lyrics_container.pack(fill="both", expand=True, padx=18, pady=12)
        
        ctk.CTkLabel(
            lyrics_container, text="✦  Detected Lyrics",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["gold"]
        ).pack(anchor="w", padx=16, pady=(12, 6))
        
        lyrics_box = ctk.CTkTextbox(
            lyrics_container, fg_color=COLORS["bg_item"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=13), corner_radius=8,
            wrap="word", border_width=1, border_color=COLORS["border"]
        )
        lyrics_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        lyrics_box.insert("1.0", lyrics if lyrics else "(no text detected)")
        lyrics_box.configure(state="disabled")
        
        # Controls
        control_frame = ctk.CTkFrame(self.preview_window, fg_color=COLORS["bg_header"],
                                      corner_radius=12, border_width=1,
                                      border_color=COLORS["border"])
        control_frame.pack(fill="x", padx=18, pady=(0, 18))
        
        btn_row = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_row.pack(pady=12)
        
        if sample_path and os.path.exists(sample_path):
            GoldButton(
                btn_row, text="  ▶  Play Sample  ", style="success",
                command=lambda: self._play_sample(sample_path),
                height=36, width=160
            ).pack(side="left", padx=6)
            
            GoldButton(
                btn_row, text="  ⏹  Stop  ", style="secondary",
                command=self._stop_preview,
                height=36, width=100
            ).pack(side="left", padx=6)
        else:
            ctk.CTkLabel(
                btn_row, text="⚠ Audio sample not available",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["accent_amber"]
            ).pack(padx=10)
        
        GoldButton(
            btn_row, text="  ✕  Close  ", style="danger",
            command=self._close_preview,
            height=36, width=100
        ).pack(side="left", padx=6)
    
    def _play_sample(self, sample_path):
        self._stop_preview()
        try:
            self.preview_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", sample_path],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except FileNotFoundError:
            messagebox.showwarning("Playback Error", "ffplay not found. Make sure ffmpeg is installed.")
    
    def _stop_preview(self):
        if self.preview_process:
            try:
                self.preview_process.terminate()
                self.preview_process.wait(timeout=2)
            except:
                try:
                    self.preview_process.kill()
                except:
                    pass
            self.preview_process = None
    
    def _close_preview(self):
        self._stop_preview()
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None
    
    def _on_close(self):
        self._stop_preview()
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.destroy()
    
    # ─── Sorting ─────────────────────────────────────────────────
    def _start_sorting(self):
        if self.processing:
            return
        if not self.files:
            messagebox.showwarning("No Files", "Add MP4 files first!")
            return
        
        self.processing = True
        self.btn_sort.configure(state="disabled", text="  ⏳  Processing...  ")
        self.btn_add_files.configure(state="disabled")
        self.btn_add_folder.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        
        # Update header status
        self._header_status.configure(text="Processing...", text_color=COLORS["accent_amber"])
        self._status_dot.configure(fg_color=COLORS["accent_amber"])
        self._status_dot.start()
        
        # Start progress glow
        self.progress_bar.start_glow()
        
        thread = threading.Thread(target=self._sort_worker, daemon=True)
        thread.start()
    
    def _sort_worker(self):
        total = len(self.files)
        completed = 0
        instrumental_count = 0
        vocal_count = 0
        error_count = 0
        start_time = time.time()
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir = tempfile.mkdtemp(prefix="songsort_")
        temp_dir = self.temp_dir
        
        try:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {}
                
                for filepath in self.files:
                    self._update_row(filepath, "🔄 Extracting...", COLORS["accent_amber"])
                    future = executor.submit(process_single_file, filepath, self.api_key, temp_dir)
                    futures[future] = filepath
                
                for future in as_completed(futures):
                    filepath, classification, detail, lyrics_text, sample_path = future.result()
                    completed += 1
                    
                    self.results[filepath] = {
                        "classification": classification,
                        "detail": detail,
                        "lyrics": lyrics_text,
                        "sample_path": sample_path
                    }
                    
                    progress = completed / total
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (total - completed) / rate if rate > 0 else 0
                    
                    self.after(0, lambda p=progress: self.progress_bar.set(p))
                    self.after(0, lambda c=completed, t=total, e=eta: 
                        self.progress_label.configure(
                            text=f"✦  Processing {c}/{t}  —  ETA: {int(e)}s"
                        ))
                    
                    if classification == "instrumental":
                        instrumental_count += 1
                        success, dest = copy_file(filepath, classification)
                        self._update_row(
                            filepath, "🎹 Instrumental", COLORS["accent_cyan"],
                            f"→ Instru  ·  {detail}", "#0a1520"
                        )
                    elif classification == "vocal":
                        vocal_count += 1
                        success, dest = copy_file(filepath, classification)
                        self._update_row(
                            filepath, "🎤 Vocal", COLORS["accent_red"],
                            f"→ Trash  ·  {detail}", "#200a0a",
                            show_preview=True
                        )
                    else:
                        error_count += 1
                        self._update_row(
                            filepath, "❌ Error", COLORS["accent_red"],
                            detail, "#1a0a0a"
                        )
                    
                    self.after(0, lambda i=instrumental_count, v=vocal_count, e=error_count:
                        self.stats_label.configure(
                            text=f"🎹 {i}  ·  🎤 {v}  ·  ❌ {e}"
                        ))
        
        except Exception as e:
            self.after(0, lambda err=str(e): self.progress_label.configure(
                text=f"❌ Error: {err}"
            ))
        
        elapsed = time.time() - start_time
        
        # Done!
        self.after(0, lambda: self._on_sort_complete(total, elapsed))
    
    def _on_sort_complete(self, total, elapsed):
        self.progress_label.configure(
            text=f"✅  Done!  {total} files sorted in {elapsed:.1f}s"
        )
        self.progress_bar.set(1.0)
        self.progress_bar.stop_glow()
        
        self.btn_sort.configure(state="normal", text="  ⚡  SORT NOW  ")
        self.btn_add_files.configure(state="normal")
        self.btn_add_folder.configure(state="normal")
        self.btn_clear.configure(state="normal")
        
        self._header_status.configure(text="Complete", text_color=COLORS["accent_green"])
        self._status_dot.stop()
        self._status_dot.configure(fg_color=COLORS["accent_green"])
        
        self.processing = False


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = SongSorterApp()
    app.mainloop()
