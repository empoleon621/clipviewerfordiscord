# ClipViewer for Discord

ClipViewer for Discord is a standalone desktop application for viewing, trimming, and converting Discord-shared video clips.  
It uses Python, Tkinter, VLC, and FFmpeg to provide a streamlined, cross-platform tool that runs without requiring any additional installations.

---

## Features

- Instant playback of Discord video URLs or local files.
- Integrated VLC backend for wide format and codec support (H.264, VP9, AV1, etc.).
- Built-in FFmpeg processing for:
  - Lossless video trimming
  - Format conversion (MP4, MKV, WEBM, GIF)
  - Resolution scaling and compression
- Drag-and-drop clip loading.
- Export presets optimized for Discord sharing.
- Distributed as a single executable file.

---

## Technical Details

- **GUI Development:** Implemented with Tkinter for a native, lightweight interface.
- **Video Playback:** Uses VLC Python bindings for real-time playback and previews.
- **Video Processing:** Integrates FFmpeg for high-performance encoding and decoding.
- **Threading:** Processing is handled in a separate thread to keep the UI responsive.
- **Packaging:** Built with PyInstaller, embedding VLC and FFmpeg binaries for portability.
- **Custom Build Script:** Uses a tailored `.spec` file to flatten VLC’s directory structure and package only necessary binaries.

---

## Installation

### Option 1 – Prebuilt Release
1. Download the latest release from the [Releases](../../releases) page.
2. Extract the `.zip` file.
3. Run `ClipViewer.exe`.

### Option 2 – Run from Source
```bash
# Clone the repository
git clone https://github.com/<your-username>/clipviewerfordiscord.git
cd clipviewerfordiscord

# Create and activate environment
conda env create -f environment.yml
conda activate tkvid

# Run the application
python main.py
