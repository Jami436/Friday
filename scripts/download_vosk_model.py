"""Download the small English Vosk model (wake-word / STT) and the speaker model.

Usage:
    python scripts/download_vosk_model.py            # ASR model only
    python scripts/download_vosk_model.py --speaker  # also fetch the speaker model
"""

import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "models"
EXPECTED_DIR = MODEL_DIR / "vosk-model-small-en-us-0.15"

SPK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip"
SPK_EXPECTED_DIR = MODEL_DIR / "vosk-model-spk-0.4"


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


def _ensure_dir_from_zip(archive_url: str, expected_dir: Path, name: str) -> None:
    if expected_dir.is_dir() and any(expected_dir.iterdir()):
        print(f"{name} already present at {expected_dir}")
        return
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    archive = MODEL_DIR / (name + ".zip")
    _download(archive_url, archive)
    print("Extracting...")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(MODEL_DIR)
    archive.unlink()
    print(f"{name} ready at {expected_dir}")


def main() -> None:
    _ensure_dir_from_zip(MODEL_URL, EXPECTED_DIR, "vosk-model-small-en-us-0.15")
    if "--speaker" in sys.argv[1:]:
        _ensure_dir_from_zip(SPK_MODEL_URL, SPK_EXPECTED_DIR, "vosk-model-spk-0.4")


if __name__ == "__main__":
    sys.exit(main())
