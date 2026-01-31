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
            self, text="MLX YouTube Transcriber",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.header_label.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        # 2. Input Section
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.url_label = ctk.CTkLabel(
            self.input_frame, text="YouTube URL",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.url_label.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        self.url_entry = ctk.CTkEntry(
            self.input_frame, placeholder_text="https://www.youtube.com/watch?v=...",
            height=40
        )
        self.url_entry.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.start_button = ctk.CTkButton(
            self.input_frame, text="Start Transcription",
            font=ctk.CTkFont(weight="bold"),
            command=self.start_click, height=40
        )
        self.start_button.grid(row=1, column=1, padx=(0, 20), pady=(0, 20))

        # 3. Progress Section
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=2, column=0, padx=30, pady=10, sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.progress_frame, text="Status: Ready",
            font=ctk.CTkFont(slant="italic")
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
            self.result_frame, text="Transcription Result",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.result_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.copy_button = ctk.CTkButton(
            self.result_frame, text="Copy Text", width=100,
            command=self.copy_click
        )
        self.copy_button.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        self.result_textbox = ctk.CTkTextbox(
            self.result_frame, font=ctk.CTkFont(size=13),
            border_width=1
        )
        self.result_textbox.grid(
            row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew"
        )

    def update_status(self, msg: str, loading: bool = False):
        self.status_label.configure(text=f"Status: {msg}")
        if loading:
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            self.progress_bar.set(0)

    def copy_click(self):
        text = self.result_textbox.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_status("Copied to clipboard!")

    def process_video(self, url):
        try:
            self.update_status("Downloading audio...", True)
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": str(tmp_path / "%(title)s.%(ext)s"),
                    "postprocessors": [
                        {"key": "FFmpegExtractAudio", "preferredcodec": "wav"}
                    ],
                    "quiet": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    audio_path = Path(ydl.prepare_filename(info)).with_suffix(".wav")

                self.update_status("Transcribing (using MLX)...", True)
                result = mlx_whisper.transcribe(
                    str(audio_path),
                    path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                )

                self.result_textbox.delete("1.0", tk.END)
                self.result_textbox.insert("1.0", result["text"])
                self.update_status("Finished!", False)
        except Exception as e:
            self.update_status(f"Error: {str(e)}", False)
        finally:
            self.start_button.configure(state="normal")

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
