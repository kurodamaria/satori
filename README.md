# Satori (悟り)

Screenshot OCR + translation for reading Japanese manga on screen. Captures a
screen area, recognizes the Japanese text with a manga-specialized OCR model,
and translates it via a cloud API (DeepL by default).

## Features

- `watch` — watches the clipboard; use Windows' own **Win+Shift+S** (Snipping
  Tool: rectangle, freehand, window) and the new screenshot is OCR'd and
  translated automatically
- `capture` — built-in fullscreen overlay with freehand lasso selection,
  OCR + translate
- `file <path>` — OCR + translate an image file
- `file <path> --ocr-only` — OCR only, no translation

## Install

1. Python 3.11–3.13 recommended (PyTorch wheels). First run downloads the
   ~400MB manga-ocr model.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and add your `DEEPL_API_KEY`.

## Usage

```powershell
# Listen to the clipboard (recommended): open a terminal, then use Win+Shift+S anytime
python -m satori listen --source clipboard

# Listen to a screen region: lasso one area, then it re-translates whenever the
# content changes (scroll, new page, next anime frame). First poll translates immediately.
python -m satori listen --source region

# Same, but for a fixed rectangle without the lasso: x, y, w, h
python -m satori listen --source region --x 100 --y 50 --w 400 --h 200

# Region poll interval (default 1.0s)
python -m satori listen --source region --interval 0.5

# Diagnostics (shows each new image detected)
python -m satori listen --verbose

# `watch` is an alias for `listen --source clipboard`
python -m satori watch

# Manual one-shot: lasso an area on screen, OCR + translate, copy to clipboard
python -m satori capture

# Translate an image file
python -m satori file page.png

# Only OCR, no translation
python -m satori file page.png --ocr-only

# LLM tutor mode (chat2api or any OpenAI-compatible server): instead of a
# plain translation you get the reading in hiragana chunks, the meaning,
# and two similar sentences that share the sentence's structure
python -m satori listen --provider llm
python -m satori file page.png --provider llm --llm-model deepseek-v4-flash

# Speak the OCR'd Japanese aloud with an anime voice (requires VOICEVOX engine)
python -m satori listen --tts --tts-voice ずんだもん
python -m satori set --tts on --tts-voice 四国めたん   # persist it
python -m satori voices                              # list available characters
```

Satori only reacts to *new* content: a clipboard image already there when it
starts is ignored, and a region is only OCR'd when its pixels change. The
translation is copied to the clipboard (overwriting the screenshot) — copy
something else before taking the next screenshot.

### Text-to-speech (VOICEVOX)

Satori can read the OCR'd Japanese aloud with free, local, anime-style
[VOICEVOX](https://voicevox.hiroshiba.jp/) voices (ずんだもん, 四国めたん, ...).

1. Install VOICEVOX (the engine runs as `http://127.0.0.1:50021`):
   - GUI app from <https://voicevox.hiroshiba.jp/> (launches the engine), or
   - the engine alone from
     <https://github.com/VOICEVOX/voicevox_engine/releases>.
2. Enable it in Satori: `python -m satori set --tts on --tts-voice ずんだもん`
3. Any `listen`/`capture`/`file` run now speaks the OCR text. List characters
   with `python -m satori voices`.

No API key and no internet needed for TTS; synthesis is async so listening
never blocks.

> **Note:** prefer `python -m satori` (or `.venv\Scripts\python.exe -m satori`) over
> the `satori` console-script. The pip-generated `.exe` wrapper can stall when its
> output is redirected (`satori ... > log.txt`); the module invocation is stable.
> If OCR ever stalls on a high-core CPU, pass `--threads 8`.

## Configuration

Stored in `%APPDATA%\satori\config.json` (Windows) or
`~/.config/satori/config.json`. Override from CLI:

```powershell
satori set --provider google --target-lang EN
```

## How it works

1. **Capture** — from a source: the Windows clipboard (Snipping Tool) or a
   polled screen region (`mss` grabs the region directly). One-shot lasso
   capture is also available.
2. **OCR** — `manga-ocr` (kha-white/manga-ocr-base), purpose-built for Japanese
   manga: vertical and horizontal text, furigana, stylized fonts.
3. **Translate** — DeepL (free tier) or Google via the `GOOGLE_API_KEY` or the
   free `deep-translator` endpoint.

### LLM tutor mode (`--provider llm`)

With `--provider llm`, Satori sends the OCR'd Japanese to an OpenAI-compatible
endpoint (default `http://127.0.0.1:8080`, e.g.
[chat2api](https://github.com/lanqian528/chat2api)) and asks it for a
structured mini-lesson:

- **Reading** — the whole sentence rewritten in pure hiragana, chunk by chunk
- **Meaning** — translation in your `--target-lang`
- **Similar sentences** — two sentences reusing the same grammar so you can
  see the structure

Configure with `--llm-url` / `--llm-model`, or persist with
`satori set --provider llm --llm-url ... --llm-model ...`; auth is taken from
`LLM_API_KEY` or `OPENAI_API_KEY` in `.env` if set (chat2api on localhost
usually needs none).
