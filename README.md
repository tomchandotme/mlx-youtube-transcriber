# MLX YouTube Transcriber

A lightweight, single-file GUI tool for transcribing YouTube videos using Apple's MLX framework for high-performance inference on Apple Silicon.

## Features

- **Apple Silicon Optimized**: Uses `mlx-whisper` for lightning-fast transcription leveraging the GPU and Neural Engine.
- **Modern GUI**: Built with `customtkinter` for a sleek, dark-themed interface with real-time status updates and a progress indicator.
- **Direct YouTube Integration**: Downloads and extracts audio directly from URLs using `yt-dlp` and `ffmpeg`.
- **Clipboard Ready**: Easily copy the transcribed text to your clipboard with a single click.
- **Single-File Distribution**: Uses PEP 723 script metadata for easy execution without manual dependency management using `uv`.
- **Privacy Focused**: No files are left behind; audio is processed in temporary directories and deleted after transcription.

## Prerequisites

- **macOS**: This tool is specifically designed for Apple Silicon (M1, M2, M3, etc.) to leverage MLX.
- **Python 3.11+**
- **ffmpeg**: Required for audio extraction.
  - Install via [Homebrew](https://brew.sh/): `brew install ffmpeg`
- **uv** (Recommended): The easiest way to run this script with its dependencies.

## Usage

### Using `uv` (Recommended)

You can run the tool directly without setting up a virtual environment manually:

```bash
uv run gui.py
```

### Using `pip`

If you prefer standard pip, install the dependencies first:

```bash
pip install customtkinter yt-dlp mlx-whisper
python gui.py
```

## How it Works

1.  **Audio Retrieval**: It uses `yt-dlp` with `FFmpegExtractAudio` post-processing to extract the audio stream from the provided YouTube URL and convert it to WAV format.
2.  **Temporary Storage**: The audio is saved to a `tempfile.TemporaryDirectory`, ensuring no local storage is cluttered with media files.
3.  **Inference**: `mlx-whisper` loads the `mlx-community/whisper-large-v3-turbo` model.
    - *Note: The model (~1.6GB) will be automatically downloaded from Hugging Face on the first run.*
4.  **Transcription**: The audio is processed using the Apple Silicon GPU/Neural Engine for high-speed transcription.
5.  **Output**: The resulting text is displayed in the GUI and can be copied to your clipboard.

## Dependencies

- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern UI elements.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube video/audio downloader.
- [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) - OpenAI's Whisper implementation for MLX.
- [ffmpeg](https://ffmpeg.org/) - Multimedia framework for audio conversion.
