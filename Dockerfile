# FRIDAY development / CI image.
#
# NOTE: FRIDAY is a desktop voice assistant that needs your physical
# microphone and speakers (PortAudio/sounddevice). A container cannot access
# host audio, so this image is intended for running the test suite and
# configuration smoke checks, NOT for the interactive voice experience.
#
# Build:    docker build -t friday .
# Run tests: docker run --rm friday python -m pytest -q
# Smoke:     docker run --rm -e LOG_LEVEL=INFO friday python -c "import app.main; print('ok')"
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MEMORY_BACKEND=sqlite \
    AI_PROVIDER=gemini \
    DEBUG=False

WORKDIR /srv/friday

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Headless targets only (see note above). No PortAudio / Vosk model download.
RUN useradd -m friday
USER friday

CMD ["python", "-m", "pytest", "-q"]