from __future__ import annotations

from dataclasses import dataclass
import math

from .loop import LoopTrace, run_qpsk_costas_loop
from .signal import hard_decision_qpsk, qpsk_symbols, rotate_symbols


@dataclass(frozen=True)
class AcquisitionSweepRow:
    freq_offset: float
    raw_rms_error: float
    phase_only_coarse_rms_error: float
    phase_only_tracked_rms_error: float
    freq_acquired_coarse_rms_error: float
    freq_acquired_tracked_rms_error: float
    coarse_frequency_estimate: float


def quality_band(rms_error: float) -> str:
    if rms_error < 0.10:
        return "clean"
    if rms_error < 0.24:
        return "marginal"
    return "failed"


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


def sweep_acquisition_modes(
    offsets: list[float],
    *,
    count: int = 800,
    phase_offset: float = 0.85,
    noise_std: float = 0.04,
    alpha: float = 0.11,
    beta: float = 0.0045,
    coarse_prefix: int = 64,
    seed: int = 7,
    trim: int = 180,
) -> list[AcquisitionSweepRow]:
    symbols = qpsk_symbols(count, seed=seed)
    rows: list[AcquisitionSweepRow] = []
    for offset in offsets:
        received = rotate_symbols(symbols, phase_offset=phase_offset, freq_offset=offset, noise_std=noise_std, seed=seed + 1)
        phase_only = run_qpsk_costas_loop(received, alpha=alpha, beta=beta, coarse_prefix=coarse_prefix, coarse_mode="phase")
        freq_acquired = run_qpsk_costas_loop(received, alpha=alpha, beta=beta, coarse_prefix=coarse_prefix, coarse_mode="freq_phase")
        rows.append(
            AcquisitionSweepRow(
                freq_offset=offset,
                raw_rms_error=rms_decision_error(received, trim=trim),
                phase_only_coarse_rms_error=rms_decision_error(phase_only.coarse_corrected, trim=trim),
                phase_only_tracked_rms_error=rms_decision_error(phase_only.tracked, trim=trim),
                freq_acquired_coarse_rms_error=rms_decision_error(freq_acquired.coarse_corrected, trim=trim),
                freq_acquired_tracked_rms_error=rms_decision_error(freq_acquired.tracked, trim=trim),
                coarse_frequency_estimate=freq_acquired.coarse_frequency,
            )
        )
    return rows
