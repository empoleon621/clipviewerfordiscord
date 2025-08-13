# main.py
import os, sys, subprocess, tempfile, shutil, ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# -------- Robust VLC bootstrap (handles _internal\vlc\plugins and _internal\plugins) --------
import os, sys, ctypes
from pathlib import Path


def resource_path(rel: str) -> str:
    """Return absolute path to resource, working for dev and PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)           # _internal during runtime
    else:
        base = Path(__file__).resolve().parent
    return str((base / rel).resolve())


def exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

BASE = exe_dir()
INTERNAL = BASE / "_internal"
VENDOR = BASE / "vendor"

roots: list[Path] = []
if INTERNAL.exists():
    roots.append(INTERNAL)
roots.append(BASE)
if VENDOR.exists():
    roots.append(VENDOR)

VLC_DLL: Path | None = None
VLC_PLUGINS: Path | None = None

for r in roots:
    # A: dll in root, plugins in root/plugins or root/vlc/plugins
    dll_root = r / "libvlc.dll"
    if dll_root.exists():
        VLC_DLL = dll_root
        # two possible plugin layouts
        if (r / "plugins").exists():
            VLC_PLUGINS = r / "plugins"
        elif (r / "vlc" / "plugins").exists():
            VLC_PLUGINS = r / "vlc" / "plugins"
        break
    # B: dll under vlc/, plugins under vlc/plugins
    dll_nested = r / "vlc" / "libvlc.dll"
    if dll_nested.exists():
        VLC_DLL = dll_nested
        if (r / "vlc" / "plugins").exists():
            VLC_PLUGINS = r / "vlc" / "plugins"
        break

# Prepare environment and force-load DLL
if VLC_DLL:
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(VLC_DLL.parent))
        except Exception:
            pass
    os.environ["PATH"] = str(VLC_DLL.parent) + os.pathsep + os.environ.get("PATH", "")
else:
    print("⚠ libvlc.dll not found under _internal/, next to EXE, or vendor/. Will try system VLC if available.")

# Find ffmpeg tools too (used later)
def find_tool(name: str) -> str:
    candidates = [
        INTERNAL / "ffmpeg" / name,
        BASE / "ffmpeg" / name,
        VENDOR / "ffmpeg" / name,
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return name

FFMPEG  = find_tool("ffmpeg.exe")
FFPROBE = find_tool("ffprobe.exe")

# Now import python-vlc
import vlc

# Build list of candidate plugin paths to try
plugin_candidates = []
if VLC_PLUGINS:
    plugin_candidates.append(Path(VLC_PLUGINS))
# also try a folder named "plugins" next to the DLL (common requirement)
if VLC_DLL:
    plugin_candidates.append(VLC_DLL.parent / "plugins")

# De-duplicate while preserving order
seen = set()
clean_candidates = []
for c in plugin_candidates:
    p = c.resolve()
    if p not in seen and p.exists():
        clean_candidates.append(p)
        seen.add(p)

# Try initializing libVLC with several arg styles and plugin paths
_instance = None
for cand in clean_candidates + [None]:  # final None = try with no explicit plugin path
    args = ["--no-video-title-show"]
    if cand is not None:
        args.append(f"--plugin-path={cand}")
        os.environ["VLC_PLUGIN_PATH"] = str(cand)               # env for libvlc
        os.environ["PYTHON_VLC_MODULE_PATH"] = str(cand)        # env some python-vlc versions read
    try:
        # ensure DLL is actually loadable (bitness problems would raise here)
        if VLC_DLL:
            ctypes.CDLL(str(VLC_DLL))
        _instance = vlc.Instance(*args)
    except Exception:
        _instance = None
    if _instance is not None:
        break

if _instance is None:
    raise RuntimeError(
        "Failed to create VLC instance (vlc.Instance() returned None).\n"
        f"Searched for libvlc.dll under:\n"
        f"  {INTERNAL}\n  {BASE}\n  {VENDOR/'vlc'}\n"
        "Make sure libvlc.dll is 64-bit and that a 'plugins' folder exists.\n"
        "Tip: If plugins are inside '\\vlc\\plugins', try moving/copying them to a folder named just 'plugins' next to libvlc.dll."
    )

# Now import python-vlc
import vlc

# Build list of candidate plugin paths to try
plugin_candidates = []
if VLC_PLUGINS:
    plugin_candidates.append(Path(VLC_PLUGINS))
# also try a folder named "plugins" next to the DLL (common requirement)
if VLC_DLL:
    plugin_candidates.append(VLC_DLL.parent / "plugins")

# De-duplicate while preserving order
seen = set()
clean_candidates = []
for c in plugin_candidates:
    p = c.resolve()
    if p not in seen and p.exists():
        clean_candidates.append(p)
        seen.add(p)

# Try initializing libVLC with several arg styles and plugin paths
_instance = None
for cand in clean_candidates + [None]:  # final None = try with no explicit plugin path
    args = ["--no-video-title-show"]
    if cand is not None:
        args.append(f"--plugin-path={cand}")
        os.environ["VLC_PLUGIN_PATH"] = str(cand)               # env for libvlc
        os.environ["PYTHON_VLC_MODULE_PATH"] = str(cand)        # env some python-vlc versions read
    try:
        # ensure DLL is actually loadable (bitness problems would raise here)
        if VLC_DLL:
            ctypes.CDLL(str(VLC_DLL))
        _instance = vlc.Instance(*args)
    except Exception:
        _instance = None
    if _instance is not None:
        break

if _instance is None:
    raise RuntimeError(
        "Failed to create VLC instance (vlc.Instance() returned None).\n"
        f"Searched for libvlc.dll under:\n"
        f"  {INTERNAL}\n  {BASE}\n  {VENDOR/'vlc'}\n"
        "Make sure libvlc.dll is 64-bit and that a 'plugins' folder exists.\n"
        "Tip: If plugins are inside '\\vlc\\plugins', try moving/copying them to a folder named just 'plugins' next to libvlc.dll."
    )

# Safe to import vlc now
import vlc

# Create a libVLC instance with explicit plugin path (when we know it)
def _debug(msg: str):
    try:
        print(msg)
    except Exception:
        pass

# Make sure python-vlc sees both the DLL and plugins
if VLC_DLL:
    os.environ["PYTHON_VLC_LIB_PATH"] = str(VLC_DLL)
if VLC_PLUGINS:
    # python-vlc older/newer env names + VLC native arg
    os.environ["VLC_PLUGIN_PATH"] = str(VLC_PLUGINS)
    os.environ["PYTHON_VLC_MODULE_PATH"] = str(VLC_PLUGINS)

# Also help Windows loader
if VLC_DLL and hasattr(os, "add_dll_directory"):
    try:
        os.add_dll_directory(str(VLC_DLL.parent))
    except Exception as e:
        _debug(f"add_dll_directory failed: {e}")

# Show what we detected
_debug(f"[VLC] DLL: {VLC_DLL}")
_debug(f"[VLC] PLUGINS: {VLC_PLUGINS}")

# Try several init styles
_instance = None
attempts = []

# 1) Explicit plugin path
if VLC_PLUGINS:
    attempts.append((f"--plugin-path={VLC_PLUGINS}",))

# 2) Minimal args
attempts.append(("--no-video-title-show",))

# 3) No args at all
attempts.append(tuple())

for args in attempts:
    try:
        _debug(f"[VLC] Trying vlc.Instance{args} ...")
        _instance = vlc.Instance(*args)
    except Exception as e:
        _debug(f"[VLC] Instance error: {e}")
        _instance = None
    if _instance is not None:
        break

if _instance is None:
    # Extra hint: print folder contents so we know what PyInstaller packed
    try:
        from glob import glob
        _debug("[VLC] Listing DLL dir:")
        _debug("\n".join(glob(str((VLC_DLL.parent if VLC_DLL else Path('.')) / "*.dll"))))
        _debug("[VLC] Listing plugins dir:")
        if VLC_PLUGINS:
            _debug("\n".join(glob(str(Path(VLC_PLUGINS) / "**" / "*.dll"), recursive=True)[:20]) + "\n... (truncated)")
    except Exception:
        pass

    raise RuntimeError(
        "Failed to create VLC instance (vlc.Instance() returned None).\n"
        f"Searched for libvlc.dll under:\n"
        f"  {INTERNAL}\n  {BASE}\n  {VENDOR/'vlc'}\n"
        "Make sure libvlc.dll is 64-bit and a 'plugins' folder exists.\n"
        "Tip: your build currently has VLC under: "
        f"{(INTERNAL/'vlc') if (INTERNAL/'vlc').exists() else '(not found)'}"
    )

# ============================================================
# App logic
# ============================================================
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm", ".m4v"}
DISCORD_SOFT_LIMIT = 10_000_000  # 10 MB
DISCORD_TARGET     = 9_500_000   # ~9.5 MB target

def fmt_time(ms: int | None) -> str:
    if ms is None or ms < 0:
        return "00:00"
    s = int(ms // 1000)
    return f"{s//60:02d}:{s%60:02d}"

class ClipViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        
        #set icon
        try:
            icon_file = resource_path('discordlogo.ico')   # because we targeted '.' in datas
            self.iconbitmap(default=icon_file)
        except Exception as e:
            print("Icon load failed:", e)  # won't crash if missing, just logs        
        
        
        
        self.title("Video Player")
        self.geometry("960x640")

        # state
        self.folder: Path | None = None
        self.files: list[Path] = []
        self.index = -1
        self.seeking = False
        self.after_id = None
        self._temp_dir = Path(tempfile.mkdtemp(prefix="clipviewer_"))
        self._compressed_cache: dict[str, Path] = {}

        # layout
        self.video_frame = tk.Frame(self, bg="black")
        self.video_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        controls = tk.Frame(self)
        controls.pack(side=tk.BOTTOM, fill=tk.X)

        # row 1
        self.btn_open = tk.Button(controls, text="Choose Folder", width=14, command=self.open_folder)
        self.btn_prev = tk.Button(controls, text="Prev", width=10, command=self.prev_video, state=tk.DISABLED)
        self.btn_play = tk.Button(controls, text="Play", width=12, command=self.toggle_play, state=tk.DISABLED)
        self.btn_next = tk.Button(controls, text="Next", width=10, command=self.next_video, state=tk.DISABLED)
        self.btn_copy = tk.Button(controls, text="Download (Copy)", width=16, command=self.copy_current_to_clipboard, state=tk.DISABLED)

        self.btn_open.grid(row=0, column=0, padx=6, pady=(10,4))
        self.btn_prev.grid(row=0, column=1, padx=6, pady=(10,4))
        self.btn_play.grid(row=0, column=2, padx=6, pady=(10,4))
        self.btn_next.grid(row=0, column=3, padx=6, pady=(10,4))
        self.btn_copy.grid(row=0, column=4, padx=6, pady=(10,4))

        # row 2: seek + time
        self.pos_var = tk.DoubleVar(value=0.0)
        self.pos_slider = tk.Scale(
            controls, variable=self.pos_var, from_=0, to=1000,
            orient=tk.HORIZONTAL, length=700, showvalue=0,
            command=self._on_seek_drag_start
        )
        self.pos_slider.grid(row=1, column=0, columnspan=5, sticky="ew", padx=12, pady=(0,8))
        controls.grid_columnconfigure(2, weight=1)

        self.time_label = tk.Label(controls, text="00:00 / 00:00", width=16)
        self.time_label.grid(row=1, column=5, padx=8)

        # row 3: volume
        tk.Label(controls, text="Volume").grid(row=2, column=0, sticky="e", padx=(12,4))
        self.vol_var = tk.IntVar(value=80)
        self.vol_slider = tk.Scale(
            controls, variable=self.vol_var, from_=0, to=100,
            orient=tk.HORIZONTAL, length=200, command=lambda _=None: self._set_volume()
        )
        self.vol_slider.grid(row=2, column=1, columnspan=2, sticky="w", pady=(0,10))

        # VLC player setup — use the instance we created above
        self.instance = _instance
        self.player = self.instance.media_player_new()
        if self.player is None:
            raise RuntimeError("libVLC returned None for media_player_new — check VLC files and plugins directory.")

        # attach video to Tk frame (Windows)
        self.update_idletasks()
        handle = self.video_frame.winfo_id()
        if sys.platform.startswith("win"):
            self.player.set_hwnd(handle)  # type: ignore[attr-defined]

        self.pos_slider.bind("<ButtonRelease-1>", self._on_seek_commit)

        # cleanup
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._tick()

    # ---------- UI Actions ----------
    def open_folder(self):
        path = filedialog.askdirectory(initialdir="C:/", title="Select your video folder")
        if not path:
            return
        folder = Path(path)
        files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        if not files:
            messagebox.showinfo("No videos", "No supported video files in this folder.")
            return

        self.folder = folder
        self.files = files
        self.index = 0
        self._load_current(start_play=True)
        self._refresh_nav_buttons()
        self._set_volume()

    def _load_current(self, start_play=False):
        if not (0 <= self.index < len(self.files)):
            return
        current = self.files[self.index].resolve()
        media = self.instance.media_new(str(current))
        self.player.set_media(media)
        self.title(f"Video Player — {current.name}  ({self.index+1}/{len(self.files)})")
        if start_play:
            self.player.play()
            self.btn_play.config(text="Pause")
        self.btn_play.config(state=tk.NORMAL)
        self.btn_copy.config(state=tk.NORMAL)

    def toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.config(text="Play")
        else:
            self.player.play()
            self.btn_play.config(text="Pause")

    def next_video(self):
        if self.index < len(self.files) - 1:
            self.index += 1
            self._load_current(start_play=True)
        self._refresh_nav_buttons()

    def prev_video(self):
        if self.index > 0:
            self.index -= 1
            self._load_current(start_play=True)
        self._refresh_nav_buttons()

    def _refresh_nav_buttons(self):
        self.btn_prev.config(state=(tk.NORMAL if self.index > 0 else tk.DISABLED))
        self.btn_next.config(state=(tk.NORMAL if self.index < len(self.files) - 1 else tk.DISABLED))

    # ---------- Clipboard (with auto-compress >10MB) ----------
    def copy_current_to_clipboard(self):
        if not (0 <= self.index < len(self.files)):
            return
        src = self.files[self.index].resolve()
        try:
            if src.stat().st_size > DISCORD_SOFT_LIMIT:
                dst = self._compress_for_discord(src)
                path_to_copy = str(dst)
                label = f"{dst.name} (compressed)"
            else:
                path_to_copy = str(src)
                label = src.name

            safe_path = path_to_copy.replace("'", "''")
            ps = f"Set-Clipboard -Path '{safe_path}'"
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                check=True, capture_output=True, text=True
            )
            #self._toast(f"Copied to clipboard:\n{label}")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Clipboard error", e.stderr or e.stdout or str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _compress_for_discord(self, src: Path) -> Path:
        key = str(src)
        if key in self._compressed_cache and self._compressed_cache[key].exists():
            return self._compressed_cache[key]

        duration = self._probe_duration(src)
        out = Path(self._temp_dir) / (src.stem + "_dc9p5mb.mp4")

        if duration and duration > 0:
            target_bits_total = DISCORD_TARGET * 8
            audio_kbps = 96
            video_kbps = max(150, int((target_bits_total / duration) / 1000 - audio_kbps))
            cmd = [
                FFMPEG, "-y", "-i", str(src),
                "-c:v", "libx264", "-preset", "veryfast",
                "-b:v", f"{video_kbps}k", "-maxrate", f"{video_kbps}k", "-bufsize", f"{video_kbps*2}k",
                "-c:a", "aac", "-b:a", f"{audio_kbps}k",
                "-movflags", "+faststart",
                str(out)
            ]
        else:
            cmd = [
                FFMPEG, "-y", "-i", str(src),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                "-c:a", "aac", "-b:a", "96k",
                "-movflags", "+faststart",
                "-fs", str(DISCORD_TARGET),
                str(out)
            ]

        self._run_ffmpeg(cmd)

        if out.exists() and out.stat().st_size > DISCORD_TARGET and duration and duration > 0:
            try_kbps = max(120, int(self._extract_bitrate_kbps(cmd) * 0.85))
            cmd2 = [
                FFMPEG, "-y", "-i", str(src),
                "-c:v", "libx264", "-preset", "veryfast",
                "-b:v", f"{try_kbps}k", "-maxrate", f"{try_kbps}k", "-bufsize", f"{try_kbps*2}k",
                "-c:a", "aac", "-b:a", "96k",
                "-movflags", "+faststart",
                str(out)
            ]
            self._run_ffmpeg(cmd2)

        if not out.exists():
            raise RuntimeError("ffmpeg did not produce output.")
        self._compressed_cache[key] = out
        return out

    @staticmethod
    def _extract_bitrate_kbps(cmd: list[str]) -> int:
        if "-b:v" in cmd:
            i = cmd.index("-b:v")
            try:
                return int(cmd[i+1].rstrip("k"))
            except Exception:
                return 800
        return 800

    @staticmethod
    def _run_ffmpeg(cmd: list[str]):
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            out = (e.stderr or b"").decode(errors="ignore")
            raise RuntimeError(f"ffmpeg failed:\n{out}") from e

    @staticmethod
    def _probe_duration(path: Path) -> float | None:
        try:
            r = subprocess.run(
                [FFPROBE, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                check=True, capture_output=True, text=True
            )
            return float(r.stdout.strip())
        except Exception:
            return None

    # ---------- Sliders & UI updates ----------
    def _tick(self):
        try:
            length_ms = self.player.get_length()
            time_ms = self.player.get_time()
            self.time_label.config(text=f"{fmt_time(time_ms)} / {fmt_time(length_ms)}")

            if not self.seeking and length_ms and length_ms > 0 and time_ms >= 0:
                pos = max(0, min(1000, int(1000 * time_ms / length_ms)))
                self.pos_var.set(pos)

            if length_ms and time_ms >= 0 and (length_ms - time_ms) < 250 and self.player.get_state() == vlc.State.Ended:
                if self.index < len(self.files) - 1:
                    self.index += 1
                    self._load_current(start_play=True)
                    self._refresh_nav_buttons()
                else:
                    self.btn_play.config(text="Play")
        except Exception:
            pass

        self.after_id = self.after(200, self._tick)

    def _on_seek_drag_start(self, _value):
        self.seeking = True

    def _on_seek_commit(self, _evt):
        length = self.player.get_length()
        if length and length > 0:
            pos = self.pos_var.get() / 1000.0
            self.player.set_time(int(length * pos))
        self.seeking = False

    def _set_volume(self):
        vol = int(self.vol_var.get())  # 0..100
        self.player.audio_set_volume(vol)

    # ---------- Helpers ----------
    def _toast(self, msg: str):
        top = tk.Toplevel(self)
        top.title("✓")
        top.attributes("-topmost", True)
        tk.Label(top, text=msg, padx=14, pady=10).pack()
        self.after(1200, top.destroy)

    def _on_close(self):
        try:
            if self.after_id:
                self.after_cancel(self.after_id)
        except Exception:
            pass
        try:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        finally:
            self.destroy()

if __name__ == "__main__":
    app = ClipViewer()
    app.mainloop()
