# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Execution & Development Commands

This project uses PEP 723 script metadata. `uv` is the recommended tool for execution.

- **Run Application:** `uv run gui.py`
- **Install Dependencies (Manual):** `pip install customtkinter yt-dlp mlx-whisper`
- **Run (Standard Python):** `python gui.py`

*Note: No dedicated test suite or linting configuration is currently present.*

## Code Architecture

The repository consists of a single-file application (`gui.py`) that implements a GUI for transcribing YouTube videos on Apple Silicon.

### Core Components
- **`TranscriberApp` (Class):** Inherits from `ctk.CTk`. Handles the UI layout using `customtkinter` and manages application state.
- **Background Processing:**
    - Transcription is performed in a separate `threading.Thread` to prevent blocking the GUI main loop (`start_click` -> `process_video`).
- **Audio Retrieval:** Uses `yt-dlp` with `FFmpegExtractAudio` post-processor to download and convert YouTube streams to WAV in a `tempfile.TemporaryDirectory`.
- **Inference:** Uses `mlx_whisper` with the `mlx-community/whisper-large-v3-turbo` model for optimized transcription on Apple Silicon.
- **UI Threading Safety:** Thread-safe UI updates are handled using `self.after(0, callback)` (see `update_status` and `set_result`).

## Development Patterns
- **Threading:** Always run long-running tasks (IO/ML) in a daemon thread.
- **UI Updates:** Use `self.after` when updating UI elements from worker threads to ensure main loop stability.
- **Temporary Files:** Use `tempfile.TemporaryDirectory` for downloading intermediate audio files.
