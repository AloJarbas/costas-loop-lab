from __future__ import annotations

from dataclasses import dataclass
import cmath
import math

from .signal import hard_decision_qpsk


@dataclass(frozen=True)
class LoopTrace:
    received: list[complex]
    coarse_corrected: list[complex]
    tracked: list[complex]
    decisions: list[complex]
    error_signal: list[float]
    phase_estimates: list[float]
    freq_estimates: list[float]
    coarse_phase: float


def wrap_phase(value: float) -> float:
    while value > math.pi:
        value -= 2.0 * math.pi
    while value <= -math.pi:
        value += 2.0 * math.pi
    return value


def coarse_fourth_power_phase(samples: list[complex]) -> float:
    if not samples:
        raise ValueError("samples must not be empty")
    acc = sum(sample**4 for sample in samples)
    if abs(acc) < 1e-12:
        return 0.0
    # Our Gray-style QPSK points sit on the diagonals, so s^4 contributes a constant
    # phase bias of pi. Subtracting pi/4 removes that fixed bias while leaving the
    # expected 90-degree ambiguity intact.
    return wrap_phase(0.25 * cmath.phase(acc) - 0.25 * math.pi)


def qpsk_costas_error(sample: complex) -> float:
    return math.copysign(1.0, sample.real) * sample.imag - math.copysign(1.0, sample.imag) * sample.real


def run_qpsk_costas_loop(
    samples: list[complex],
    *,
    alpha: float = 0.11,
    beta: float = 0.0045,
    coarse_prefix: int = 64,
) -> LoopTrace:
    if not samples:
        raise ValueError("samples must not be empty")
    if coarse_prefix < 8:
        raise ValueError("coarse_prefix must be at least 8")

    prefix = samples[: min(coarse_prefix, len(samples))]
    coarse_phase = coarse_fourth_power_phase(prefix)
    coarse_corrected = [sample * cmath.exp(-1j * coarse_phase) for sample in samples]

    phase_hat = 0.0
    freq_hat = 0.0
    tracked: list[complex] = []
    decisions: list[complex] = []
    error_signal: list[float] = []
    phase_estimates: list[float] = []
    freq_estimates: list[float] = []

    for sample in coarse_corrected:
        rotated = sample * cmath.exp(-1j * phase_hat)
        error = qpsk_costas_error(rotated)
        freq_hat += beta * error
        phase_hat = wrap_phase(phase_hat + freq_hat + alpha * error)

        tracked.append(rotated)
        decisions.append(hard_decision_qpsk(rotated))
        error_signal.append(error)
        phase_estimates.append(phase_hat)
        freq_estimates.append(freq_hat)

    return LoopTrace(
        received=list(samples),
        coarse_corrected=coarse_corrected,
        tracked=tracked,
        decisions=decisions,
        error_signal=error_signal,
        phase_estimates=phase_estimates,
        freq_estimates=freq_estimates,
        coarse_phase=coarse_phase,
    )
