"""Tests for owner access control (voice + passphrase)."""
import numpy as np

from app.application.access_control import (
    SECURITY_MODE_BOTH,
    SECURITY_MODE_PASSPHRASE,
    SECURITY_MODE_VOICE,
    AccessControlService,
    _normalize,
)
from tests.fakes import FakeClock, FakePassphraseStore, FakeSpeakerVerifier, FakeSTT, FakeTTS, FakeVAD


def make_access_control(
    *,
    enabled=True,
    mode=SECURITY_MODE_VOICE,
    threshold=0.72,
    passphrase="",
    verifier=None,
    passphrase_store=None,
    stt_texts=None,
):
    tts = FakeTTS()
    return AccessControlService(
        verifier=verifier or FakeSpeakerVerifier(),
        passphrase_store=passphrase_store or FakePassphraseStore(),
        vad=FakeVAD(),
        stt=FakeSTT(stt_texts or ["hello"]),
        tts=tts,
        clock=FakeClock(),
        enabled=enabled,
        mode=mode,
        threshold=threshold,
        passphrase=passphrase,
        owner_name="Boss",
    ), tts


def test_disabled_security_always_grants():
    gate, _ = make_access_control(enabled=False)
    assert gate.authorize() is True


def test_voice_grants_when_score_above_threshold():
    gate, tts = make_access_control(threshold=0.72, verifier=FakeSpeakerVerifier(score=0.9))
    assert gate.authorize() is True
    assert tts.spoken[0] == "Voice check, Boss."
    assert "Welcome back" in tts.spoken[-1]


def test_voice_denies_when_score_below_threshold():
    gate, tts = make_access_control(threshold=0.72, verifier=FakeSpeakerVerifier(score=0.3))
    assert gate.authorize() is False
    assert tts.spoken[-1] == "Access denied, Boss."


def test_voice_denies_when_not_enrolled():
    gate, tts = make_access_control(verifier=FakeSpeakerVerifier(enrolled=False))
    assert gate.authorize() is False
    assert "enrolled" in tts.spoken[0]


def test_passphrase_grants_on_exact_normalized_match():
    store = FakePassphraseStore(passphrase="Iron Man")
    gate, _ = make_access_control(mode=SECURITY_MODE_PASSPHRASE, passphrase_store=store, stt_texts=["iron man"])
    assert gate.authorize() is True


def test_passphrase_denies_on_mismatch():
    store = FakePassphraseStore(passphrase="Iron Man")
    gate, _ = make_access_control(mode=SECURITY_MODE_PASSPHRASE, passphrase_store=store, stt_texts=["hulk"])
    assert gate.authorize() is False


def test_passphrase_falls_back_to_configured_default():
    gate, _ = make_access_control(
        mode=SECURITY_MODE_PASSPHRASE, passphrase="Avengers", stt_texts=["avengers"]
    )
    assert gate.authorize() is True


def test_both_mode_grants_via_voice():
    gate, _ = make_access_control(mode=SECURITY_MODE_BOTH, verifier=FakeSpeakerVerifier(score=0.95))
    assert gate.authorize() is True


def test_both_mode_falls_back_to_passphrase():
    store = FakePassphraseStore(passphrase="winter soldier")
    gate, tts = make_access_control(
        mode=SECURITY_MODE_BOTH,
        verifier=FakeSpeakerVerifier(score=0.1),
        passphrase_store=store,
        stt_texts=["winter soldier"],
    )
    assert gate.authorize() is True
    assert "Passphrase" in tts.spoken[1]


def test_both_mode_denies_when_both_fail():
    store = FakePassphraseStore(passphrase="winter soldier")
    gate, _ = make_access_control(
        mode=SECURITY_MODE_BOTH,
        verifier=FakeSpeakerVerifier(score=0.1),
        passphrase_store=store,
        stt_texts=["hulk"],
    )
    assert gate.authorize() is False


def test_normalize_ignores_case_punctuation_spaces():
    assert _normalize("Access Granted!") == "access granted"
    assert _normalize("  Iron-Man, 42  ") == "ironman 42"
    assert _normalize("  Access  Granted  ") == "access granted"


def test_enroll_accepts_samples():
    verifier = FakeSpeakerVerifier(enrolled=False)
    samples = [np.zeros(1600, dtype=np.int16) for _ in range(3)]
    verifier.enroll(samples)
    assert verifier.is_enrolled() is True
    assert len(verifier.enrolled_samples) == 3
