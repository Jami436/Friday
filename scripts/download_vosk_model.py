"""Download the small English Vosk model for offline wake-word / STT.

Usage:
    python scripts/download_vosk_model.py
"""

import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "models"
EXPECTED_DIR = MODEL_DIR / "vosk-model-small-en-us-0.15"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"Downloading {url} ...")
    with urlopen(url) as response, tmp.open("wb") as out:
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)
    print(f"Downloaded {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    if EXPECTED_DIR.is_dir() and any(EXPECTED_DIR.iterdir()):
        print(f"Model already present at {EXPECTED_DIR}")
        return

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    archive = MODEL_DIR / "vosk-model-small-en-us-0.15.zip"
    _download(MODEL_URL, archive)

    print("Extracting...")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(MODEL_DIR)
    archive.unlink()
    print(f"Model ready at {EXPECTED_DIR}")


if __name__ == "__main__":
    sys.exit(main())
