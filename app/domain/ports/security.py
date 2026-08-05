"""Ports for owner authentication: voice verification and passphrase gating."""
from typing import Protocol

import numpy as np


class SpeakerVerifier(Protocol):
    """Verifies that a speech sample belongs to the enrolled owner.

    Enrollment is per-installation: the owner records voice samples locally
    and FRIDAY stores the resulting speaker profile in that machine's data.
    """

    def is_enrolled(self) -> bool: ...

    def enroll(self, samples: list[np.ndarray]) -> None:
        """Record the owner's voice from one or more utterances."""
        ...

    def verify(self, audio: np.ndarray) -> float:
        """Return a similarity score in [0, 1] for the given utterance.

        A value at/above the configured threshold means 'owner'.
        """
        ...


class PassphraseStore(Protocol):
    """Stores/retrieves the owner's spoken passphrase for a machine."""

    def get(self) -> str: ...

    def set(self, passphrase: str) -> None: ...
