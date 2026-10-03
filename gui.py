# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "customtkinter",
#     "yt-dlp",
#     "mlx-whisper",
# ]
# ///

import customtkinter as ctk
import yt_dlp
import mlx_whisper
import tempfile
import threading
from pathlib import Path
import tkinter as tk

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
AUDIO_FORMAT = "bestaudio/best"
AUDIO_CODEC = "wav"

RETRIES = 10
FRAGMENT_RETRIES = 10
EXTRACTOR_RETRIES = 5
SOCKET_TIMEOUT = 30

# yt-dlp needs a JS runtime plus this solver script to answer YouTube's "n"
# challenge. Fetching it can fail offline, but yt-dlp only warns and carries
# on, so it never turns into a hard failure.
REMOTE_COMPONENTS = ("ejs:github",)

# YouTube keeps pushing clients onto SABR streaming, which returns formats
# whose URLs cannot be fetched — surfacing as "HTTP Error 403: Forbidden".
# android_vr is in yt-dlp's default client set and is the one that most often
# breaks, so it is excluded from the first attempt; the later strategies fall
# back to older clients that still hand back plain CDN URLs.
# See https://github.com/yt-dlp/yt-dlp/issues/12482 and /issues/17456
DOWNLOAD_STRATEGIES = (
    ("default", ("default", "-android_vr")),
    ("tv_embedded", ("tv_embedded",)),
    ("android", ("android",)),
)

FORBIDDEN_HINTS = ("403", "forbidden")


class AudioDownloadError(RuntimeError):
    """Raised when every player-client strategy failed to fetch the audio."""

    def __init__(self, hint: str, details: str):
        super().__init__(hint)
        self.hint = hint
        self.details = details


def build_ydl_opts(tmp_dir: Path, clients) -> dict:
    """Build a fresh yt-dlp options mapping for a single download attempt."""
    return {
        "format": AUDIO_FORMAT,
        "outtmpl": str(tmp_dir / "%(title)s.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": AUDIO_CODEC}],
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "retries": RETRIES,
        "fragment_retries": FRAGMENT_RETRIES,
        "extractor_retries": EXTRACTOR_RETRIES,
        "socket_timeout": SOCKET_TIMEOUT,
        "remote_components": list(REMOTE_COMPONENTS),
        "extractor_args": {"youtube": {"player_client": list(clients)}},
    }


def describe_failure(errors) -> AudioDownloadError:
    """Turn per-strategy errors into an actionable, user-facing error."""
    details = "\n".join(errors)
    if any(hint in details.lower() for hint in FORBIDDEN_HINTS):
        hint = (
            "YouTube refused the audio download (HTTP 403). Update yt-dlp with "
            "'uv run --refresh-package yt-dlp gui.py' and try again; if it "
            "persists, sign in to YouTube in your browser first."
        )
    else:
        hint = "Could not download audio from YouTube. See the result box for details."
    return AudioDownloadError(hint, f"Download attempts:\n{details}")


def download_audio(url: str, tmp_dir: Path, on_attempt) -> Path:
    """Download `url` as WAV, trying each player-client strategy in turn."""
    errors = []
    for index, (label, clients) in enumerate(DOWNLOAD_STRATEGIES):
        on_attempt(label, index)
        try:
            with yt_dlp.YoutubeDL(build_ydl_opts(tmp_dir, clients)) as ydl:
                info = ydl.extract_info(url, download=True)
                expected = Path(ydl.prepare_filename(info)).with_suffix(f".{AUDIO_CODEC}")
            if expected.is_file():
                return expected
            produced = sorted(tmp_dir.glob(f"*.{AUDIO_CODEC}"))
            if produced:
                return produced[0]
            errors.append(f"[{label}] finished without producing an audio file")
        except Exception as exc:
            errors.append(f"[{label}] {exc}")

    raise describe_failure(errors)


def transcribe_audio(audio_path: Path) -> str:
    """Transcribe a WAV file with MLX Whisper and join the segments."""
    result = mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo=WHISPER_MODEL,
        task="transcribe",
        temperature=0.0,
        condition_on_previous_text=False,
        word_timestamps=True,
        no_speech_threshold=0.5,
        language=None,
        suppress_tokens="",  # Don't suppress anything (empty = no suppression)
        suppress_blank=False,  # Don't suppress blank outputs either
    )
    segments = result.get("segments") or []
    return "\n".join(segment["text"].strip() for segment in segments)


class TranscriberApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MLX YouTube Transcriber")
        self.geometry("800x700")
        self.minsize(600, 500)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Main grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Result frame expands

        # 1. Header
        self.header_label = ctk.CTkLabel(
            self,
            text="MLX YouTube Transcriber",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.header_label.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        # 2. Input Section
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.url_label = ctk.CTkLabel(
            self.input_frame,
            text="YouTube URL",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.url_label.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.url_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=40,
        )
        self.url_entry.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.start_button = ctk.CTkButton(
            self.input_frame,
            text="Start Transcription",
            font=ctk.CTkFont(weight="bold"),
            command=self.start_click,
            height=40,
        )
        self.start_button.grid(row=1, column=1, padx=(0, 20), pady=(0, 20))

        # 3. Progress Section
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=2, column=0, padx=30, pady=10, sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.progress_frame, text="Status: Ready", font=ctk.CTkFont(slant="italic")
        )
        self.status_label.grid(row=0, column=0, padx=5, pady=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=5, pady=10, sticky="ew")
        self.progress_bar.set(0)
        self.progress_bar.configure(mode="indeterminate")

        # 4. Result Section
        self.result_frame = ctk.CTkFrame(self)
        self.result_frame.grid(row=4, column=0, padx=30, pady=(10, 30), sticky="nsew")
        self.result_frame.grid_columnconfigure(0, weight=1)
        self.result_frame.grid_rowconfigure(1, weight=1)

        self.result_label = ctk.CTkLabel(
            self.result_frame,
            text="Transcription Result",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.result_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.copy_button = ctk.CTkButton(
            self.result_frame, text="Copy Text", width=100, command=self.copy_click
        )
        self.copy_button.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        self.result_textbox = ctk.CTkTextbox(
            self.result_frame, font=ctk.CTkFont(size=13), border_width=1
        )
        self.result_textbox.grid(
            row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew"
        )

    def update_status(self, msg: str, loading: bool = False):
        def _update():
            self.status_label.configure(text=f"Status: {msg}")
            if loading:
                self.progress_bar.start()
            else:
                self.progress_bar.stop()
                self.progress_bar.set(0)

        self.after(0, _update)

    def set_result(self, text: str):
        def _set():
            self.result_textbox.delete("1.0", tk.END)
            self.result_textbox.insert("1.0", text)

        self.after(0, _set)

    def copy_click(self):
        text = self.result_textbox.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_status("Copied to clipboard!")

    def on_download_attempt(self, label: str, index: int):
        """Surface which player client is being tried, on retries."""
        if index > 0:
            self.update_status(f"Retrying download (client: {label})...", True)

    def process_video(self, url):
        try:
            self.update_status("Downloading audio...", True)
            with tempfile.TemporaryDirectory() as tmp_dir:
                audio_path = download_audio(url, Path(tmp_dir), self.on_download_attempt)

                self.update_status("Transcribing (using MLX)...", True)
                self.set_result(transcribe_audio(audio_path))
                self.update_status("Finished!", False)
        except AudioDownloadError as exc:
            self.set_result(exc.details)
            self.update_status(f"Error: {exc.hint}", False)
        except Exception as exc:
            self.update_status(f"Error: {exc}", False)
        finally:
            self.after(0, lambda: self.start_button.configure(state="normal"))

    def start_click(self):
        url = self.url_entry.get()
        if not url:
            self.update_status("Please enter a URL")
            return

        self.start_button.configure(state="disabled")
        threading.Thread(target=self.process_video, args=(url,), daemon=True).start()


if __name__ == "__main__":
    app = TranscriberApp()
    app.mainloop()
