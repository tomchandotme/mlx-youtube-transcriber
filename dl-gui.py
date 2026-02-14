# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "customtkinter",
#     "yt-dlp",
# ]
# ///

import customtkinter as ctk
import yt_dlp
import threading
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

SETTINGS_FILE = Path("settings.json")

class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Video Downloader")
        self.geometry("700x500")
        self.minsize(600, 400)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Load settings
        self.settings = self.load_settings()
        self.save_path = Path(self.settings.get("save_path", str(Path.home() / "Downloads")))

        # Main grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 1. Header
        self.header_label = ctk.CTkLabel(
            self,
            text="YouTube Video Downloader",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.header_label.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")

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

        # 3. Settings Section
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=2, column=0, padx=30, pady=10, sticky="ew")
        self.settings_frame.grid_columnconfigure(1, weight=1)

        self.path_label = ctk.CTkLabel(
            self.settings_frame,
            text="Save to:",
            font=ctk.CTkFont(weight="bold"),
        )
        self.path_label.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="w")

        self.path_display = ctk.CTkEntry(
            self.settings_frame,
            height=30,
        )
        self.path_display.insert(0, str(self.save_path))
        self.path_display.configure(state="readonly")
        self.path_display.grid(row=0, column=1, padx=10, pady=20, sticky="ew")

        self.browse_button = ctk.CTkButton(
            self.settings_frame,
            text="Browse",
            width=100,
            command=self.browse_click,
        )
        self.browse_button.grid(row=0, column=2, padx=(10, 20), pady=20)

        # 4. Actions & Progress
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=3, column=0, padx=30, pady=20, sticky="nsew")
        self.action_frame.grid_columnconfigure(0, weight=1)

        self.download_button = ctk.CTkButton(
            self.action_frame,
            text="Download Video",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            command=self.start_download,
        )
        self.download_button.grid(row=0, column=0, pady=(0, 20), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.action_frame,
            text="Status: Ready",
            font=ctk.CTkFont(slant="italic")
        )
        self.status_label.grid(row=1, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.action_frame)
        self.progress_bar.grid(row=2, column=0, pady=10, sticky="ew")
        self.progress_bar.set(0)

    def load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_settings(self):
        settings = {"save_path": str(self.save_path)}
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)

    def browse_click(self):
        directory = filedialog.askdirectory(initialdir=self.save_path)
        if directory:
            self.save_path = Path(directory)
            self.path_display.configure(state="normal")
            self.path_display.delete(0, tk.END)
            self.path_display.insert(0, str(self.save_path))
            self.path_display.configure(state="readonly")
            self.save_settings()

    def update_status(self, msg: str, progress: float = None):
        def _update():
            self.status_label.configure(text=f"Status: {msg}")

            if progress is not None:
                # Switch to determinate mode if we have a specific progress
                if self.progress_bar.cget("mode") != "determinate":
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                self.progress_bar.set(progress)
            else:
                # Use indeterminate mode for unknown progress/starting
                if msg == "Ready" or "Complete" in msg or "Error" in msg:
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                    if "Complete" in msg:
                        self.progress_bar.set(1.0)
                    else:
                        self.progress_bar.set(0)
                else:
                    if self.progress_bar.cget("mode") != "indeterminate":
                        self.progress_bar.configure(mode="indeterminate")
                        self.progress_bar.start()

        self.after(0, _update)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0.0%').replace('%','')
            try:
                self.update_status(f"Downloading... {d.get('_percent_str', '')}", float(p) / 100.0)
            except:
                pass
        elif d['status'] == 'finished':
            self.update_status("Processing...", 1.0)

    def download_worker(self, url):
        try:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': str(self.save_path / '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.update_status("Starting download...")
                ydl.download([url])

            self.update_status("Download Complete!", 1.0)
        except Exception as e:
            self.update_status(f"Error: {str(e)}", 0)
        finally:
            self.after(0, lambda: self.download_button.configure(state="normal"))

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self.update_status("Please enter a YouTube URL")
            return

        if not self.save_path.exists():
            self.update_status("Save directory does not exist")
            return

        self.download_button.configure(state="disabled")
        self.progress_bar.set(0)
        threading.Thread(target=self.download_worker, args=(url,), daemon=True).start()

if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
