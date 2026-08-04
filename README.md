# FRIDAY

An AI-powered personal assistant inspired by the FRIDAY system from the Avengers.

FRIDAY runs fully hands-free on your PC:
- Wake it with **two claps** or by saying **"Friday"**.
- Talks back to you through ElevenLabs (British female voice by default) and
  addresses you as **"Boss"**.
- Always knows the time (AM/PM), your tasks, deadlines, notes and recent emails.
- Gives a morning briefing on your first wake of the day and nudges you when a
  deadline is approaching.

## Architecture

Hexagonal (Ports & Adapters). Dependencies always point **inward**:

```
entrypoints (main.py, future API/CLI)
        │
        ▼
app/application   use cases (Assistant, Briefing, Reminder, Conversation)
        │
        ▼
app/domain        entities, ports (interfaces), services — pure, no I/O
        │
        ▼
app/infrastructure adapters (Gemini, Vosk, ElevenLabs, Sounddevice, Gmail,
                   SQLite/JSON stores)
        ▲
app/container.py  Composition Root — the only place wiring ports to adapters
```

Rules enforced by structure:
- `application` and `domain` never import `infrastructure`.
- Providers are swappable: `AI_PROVIDER=gemini|local`, `MEMORY_BACKEND=sqlite|json`.
- Every I/O capability sits behind a port (`domain/ports/`), so tests inject fakes
  (`tests/fakes.py`).

```
always-on mic
    │  two-clap detector (local audio analysis)
    │  "Friday" keyword spotter (offline Vosk)
    ▼
wake  ──►  record utterance (VAD) ──► Vosk STT
                                          │  text
                                          ▼
                          FRIDAY brain (Gemini)  persona + "Boss" + AM/PM + daily matters
                                          │  reply
                                          ▼
                          ElevenLabs TTS ──► speaker

persistent store (SQLite at data/memory/friday.db): tasks, deadlines, notes
Gmail over IMAP (App Password): reads & summarizes inbox
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\download_vosk_model.py     # downloads the offline wake/STT model
```

Copy `.env.example` to `.env` and fill in:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Conversation brain (aistudio.google.com/app/apikey) |
| `AI_PROVIDER` | `gemini` (default) or `local` (reserved) |
| `MEMORY_BACKEND` | `sqlite` (default) or `json` |
| `ELEVENLABS_API_KEY` | Voice output (elevenlabs.io/api-keys) |
| `ELEVENLABS_VOICE_ID` | Optional; empty = auto-pick a British female voice |
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | Optional email reading (enable 2FA, create an App Password) |

## Run

```powershell
python -m app.main
```

Then clap twice or say **"Friday"** to talk. Say "goodbye", "stand down", or stay
silent to send FRIDAY back to idle.

Run the tests with:

```powershell
python -m pytest
```

## Notes

- Run with `python -m app.main` from the project root, not `python app/main.py`.
- No ElevenLabs key? FRIDAY falls back to the built-in Windows voice (SAPI,
  female), and finally to console output if speech synthesis is unavailable.
