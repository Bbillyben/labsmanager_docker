"""Stable dates, random streams, and object references for demo generation."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from hashlib import sha256
from random import Random

from . import DEMO_DATA_VERSION


@dataclass
class DemoContext:
    reference_date: date
    seed: int
    people: dict = field(default_factory=dict)
    users: dict = field(default_factory=dict)
    teams: dict = field(default_factory=dict)
    projects: dict = field(default_factory=dict)
    participants: dict = field(default_factory=dict)
    funds: dict = field(default_factory=dict)
    references: dict = field(default_factory=dict)

    def day(self, offset: int) -> date:
        return self.reference_date + timedelta(days=offset)

    def rng_for(self, namespace: str, stable_key: str) -> Random:
        """Derive an independent RNG without Python's process-randomized hash."""
        payload = f"{DEMO_DATA_VERSION}\x00{self.seed}\x00{namespace}\x00{stable_key}".encode()
        return Random(int.from_bytes(sha256(payload).digest(), "big"))
