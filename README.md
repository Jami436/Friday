# FRIDAY

An AI-powered personal assistant inspired by the FRIDAY system from the Avengers.

FRIDAY runs fully hands-free on your PC:
- Wake it with **two claps** or by saying **"Friday"**.
- Talks back to you through ElevenLabs (British female voice by default) and
  addresses you as **"Boss"**.
- Always knows the time (AM/PM), your tasks, deadlines, notes and recent emails.
- Gives a morning briefing on your first wake of the day and nudges you when a
  deadline is approaching.
- **Owner-locked**: only the person who set it up can control it, verified by
  voice biometrics and/or a spoken passphrase.
- **By voice you can add, complete, delete, reschedule and list** your tasks and
  deadlines, and jot notes.

## Architecture

Hexagonal (Ports & Adapters). Dependencies always point **inward**:

```
entrypoints (main.py, scripts/enroll_voice.py, future API/CLI)
        │
        ▼
app/application   use cases (Assistant, Briefing, Reminder, Conversation, AccessControl)
        │
        ▼
app/domain        entities, ports (interfaces), services — pure, no I/O
        │
        ▼
app/infrastructure adapters (Gemini, Vosk, ElevenLabs, Sounddevice, Gmail,
                   SQLite/JSON stores, speaker verification, passphrase store)
        ▲
app/container.py  Composition Root — the only place wiring ports to adapters
```

Rules enforced by structure:
- `application` and `domain` never import `infrastructure`.
- Providers are swappable: `AI_PROVIDER=gemini|local`, `MEMORY_BACKEND=sqlite|json`.
- Every I/O capability sits behind a port (`domain/ports/`), so tests inject fakes
  (`tests/fakes.py`). Owner auth uses `SpeakerVerifier` and `PassphraseStore` ports.

```
always-on mic
    │  two-clap detector (local audio analysis)
    │  "Friday" keyword spotter (offline Vosk)
    ▼
wake  ──►  owner verification (voice biometrics / passphrase)  ──►  denied? back to idle
            │
            ▼
        record utterance (VAD) ──► Vosk STT
                                          │  text
                                          ▼
                          FRIDAY brain (Gemini)  persona + "Boss" + AM/PM + daily matters
                                          │  reply
                                          ▼
                          ElevenLabs TTS (→ Windows SAPI fallback) ──► speaker

persistent store (SQLite at data/memory/friday.db): tasks, deadlines, notes, owner profile
Gmail over IMAP (App Password): reads & summarizes inbox
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\download_vosk_model.py --speaker   # offline wake/STT model + speaker model
```

Copy `.env.example` to `.env` and fill in:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Conversation brain (aistudio.google.com/app/apikey) |
| `AI_PROVIDER` | `gemini` (default) or `local` (reserved) |
| `MEMORY_BACKEND` | `sqlite` (default) or `json` |
| `ELEVENLABS_API_KEY` | Voice output (elevenlabs.io/api-keys) |
| `ELEVENLABS_VOICE_ID` | Optional; empty = auto-pick a British female voice |
| `ELEVENLABS_STABILITY` / `ELEVENLABS_SIMILARITY_BOOST` | Optional voice tuning (0.0–1.0) |
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | Optional email reading (enable 2FA, create an App Password) |
| `OWNER_NAME` | The owner FRIDAY addresses (default `Boss`) |
| `SECURITY_ENABLED` | Gate the assistant behind owner verification (`True`/`False`) |
| `SECURITY_MODE` | `voice` (biometrics), `passphrase`, or `both` |
| `SECURITY_PASSPHRASE` | Spoken passphrase for `passphrase`/`both` mode |
| `SPEAKER_THRESHOLD` | Voice-match strictness (0.0–1.0, default `0.72`) |

### Owner security (per-installation)

Only the person who set up this machine can control it. On your machine you are
the owner; anyone else who clones this project on their own machine becomes the
owner of that copy. Ownership is bound to local data: a voice profile and/or
passphrase stored under `data/memory/`, plus your `.env` credentials.

```powershell
python scripts\download_vosk_model.py --speaker   # fetch the speaker model (~14MB)
python scripts\enroll_voice.py --samples 5        # enroll your voice
```

With `SECURITY_ENABLED=True`, FRIDAY verifies the speaker after every wake
before the briefing or any conversation, and says "Access denied" otherwise.

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
