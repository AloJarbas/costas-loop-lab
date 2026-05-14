from __future__ import annotations

import cmath
import math
import random

QPSK_POINTS = (
    complex(1.0, 1.0),
    complex(-1.0, 1.0),
    complex(-1.0, -1.0),
    complex(1.0, -1.0),
)
NORM = math.sqrt(2.0)


def qpsk_symbols(count: int, *, seed: int = 0) -> list[complex]:
    if count < 1:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    return [rng.choice(QPSK_POINTS) / NORM for _ in range(count)]


def rotate_symbols(
    symbols: list[complex],
    *,
    phase_offset: float = 0.0,
    freq_offset: float = 0.0,
    noise_std: float = 0.0,
    seed: int = 0,
) -> list[complex]:
    rng = random.Random(seed)
    out: list[complex] = []
    for idx, symbol in enumerate(symbols):
        phase = phase_offset + freq_offset * idx
        noise = complex(rng.gauss(0.0, noise_std), rng.gauss(0.0, noise_std)) if noise_std > 0.0 else 0j
        out.append(symbol * cmath.exp(1j * phase) + noise)
    return out


def hard_decision_qpsk(sample: complex) -> complex:
    i = 1.0 if sample.real >= 0.0 else -1.0
    q = 1.0 if sample.imag >= 0.0 else -1.0
    return complex(i, q) / NORM
