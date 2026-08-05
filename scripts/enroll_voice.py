"""Enroll the local machine owner's voice for speaker verification.

Usage:
    python scripts/enroll_voice.py [--samples 5]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings
from app.infrastructure.audio.vad import SounddeviceVoiceActivityDetector
from app.infrastructure.security.vosk_speaker import VoskSpeakerVerifier


def main() -> int:
    parser = argparse.ArgumentParser(description="Enroll the owner's voice profile.")
    parser.add_argument("--samples", type=int, default=5, help="Utterances to capture (default 5).")
    args = parser.parse_args()

    settings = Settings()
    verifier = VoskSpeakerVerifier()
    vad = SounddeviceVoiceActivityDetector(
        device=settings.audio_input_device,
        default_max_sec=settings.listen_max_sec,
        default_silence_sec=settings.listen_silence_sec,
    )

    samples = []
    for i in range(1, args.samples + 1):
        print(f"\nSay a short phrase (e.g. 'I am {settings.owner_name}') for sample {i}/{args.samples}...")
        audio = vad.record_utterance()
        if audio.size == 0:
            print("No speech detected; skipping this sample.")
            continue
        samples.append(audio)
        print(f"Captured {len(audio) / 16000:.1f}s.")

    if not samples:
        print("No samples captured; enrollment aborted.")
        return 1

    verifier.enroll(samples)
    print(f"Owner voice enrolled from {len(samples)} sample(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
