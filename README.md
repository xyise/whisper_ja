# SenseVoice Subtitle App

A Python-first macOS desktop app that:
- lets you choose a running video app
- captures that app's audio using a small native ScreenCaptureKit helper
- transcribes speech locally with SenseVoice
- shows the subtitles in a separate selectable window

## Requirements

- macOS 13+
- Python 3.11+
- Xcode command line tools (`xcrun swiftc`)

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
whisper-subtitle-app
```

The first capture attempt will require Screen Recording permission.

## Notes

- The native helper currently uses the first available display when building the ScreenCaptureKit filter. This keeps the MVP simple, but multi-display app routing may need refinement.
- Speech recognition runs locally through [FunASR](https://github.com/modelscope/FunASR) using the `iic/SenseVoiceSmall` checkpoint by default. The model is downloaded automatically on first use (from ModelScope/HuggingFace) and cached locally.
- SenseVoice supports `ja`, `zh`, `yue`, `en`, `ko`, and `auto` language detection; unsupported values fall back to `auto`.
