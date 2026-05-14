from __future__ import annotations

import math

from .loop import LoopTrace, run_qpsk_costas_loop
from .signal import hard_decision_qpsk, qpsk_symbols, rotate_symbols


def rms_decision_error(samples: list[complex], *, trim: int = 0) -> float:
    view = samples[trim:] if trim else samples
    if not view:
        return 0.0
    mse = 0.0
    for sample in view:
        mse += abs(sample - hard_decision_qpsk(sample)) ** 2
    return math.sqrt(mse / len(view))


def sweep_frequency_offsets(
    offsets: list[float],
    *,
    count: int = 800,
    phase_offset: float = 0.85,
    noise_std: float = 0.04,
    alpha: float = 0.11,
    beta: float = 0.0045,
    seed: int = 7,
    trim: int = 180,
) -> list[dict[str, float]]:
    symbols = qpsk_symbols(count, seed=seed)
    rows: list[dict[str, float]] = []
    for offset in offsets:
        received = rotate_symbols(symbols, phase_offset=phase_offset, freq_offset=offset, noise_std=noise_std, seed=seed + 1)
        trace = run_qpsk_costas_loop(received, alpha=alpha, beta=beta)
        rows.append(
            {
                "freq_offset": offset,
                "raw_rms_error": rms_decision_error(received, trim=trim),
                "tracked_rms_error": rms_decision_error(trace.tracked, trim=trim),
                "coarse_rms_error": rms_decision_error(trace.coarse_corrected, trim=trim),
            }
        )
    return rows
