from __future__ import annotations

from dataclasses import dataclass
import cmath
import math

from .signal import hard_decision_qpsk


@dataclass(frozen=True)
class CoarseAcquisition:
    phase: float
    frequency: float


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
    coarse_frequency: float
    coarse_mode: str


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


def coarse_fourth_power_frequency(samples: list[complex]) -> float:
    if len(samples) < 2:
        raise ValueError("samples must contain at least two symbols")
    acc = sum((samples[idx + 1] ** 4) * (samples[idx].conjugate() ** 4) for idx in range(len(samples) - 1))
    if abs(acc) < 1e-12:
        return 0.0
    return wrap_phase(0.25 * cmath.phase(acc))


def coarse_fourth_power_acquisition(samples: list[complex]) -> CoarseAcquisition:
    if not samples:
        raise ValueError("samples must not be empty")
    freq = coarse_fourth_power_frequency(samples) if len(samples) >= 2 else 0.0
    acc = 0j
    for idx, sample in enumerate(samples):
        acc += (sample**4) * cmath.exp(-1j * 4.0 * freq * idx)
    if abs(acc) < 1e-12:
        phase = 0.0
    else:
        phase = wrap_phase(0.25 * cmath.phase(acc) - 0.25 * math.pi)
    return CoarseAcquisition(phase=phase, frequency=freq)


def qpsk_costas_error(sample: complex) -> float:
    return math.copysign(1.0, sample.real) * sample.imag - math.copysign(1.0, sample.imag) * sample.real


def run_qpsk_costas_loop(
    samples: list[complex],
    *,
    alpha: float = 0.11,
    beta: float = 0.0045,
    coarse_prefix: int = 64,
    coarse_mode: str = "phase",
) -> LoopTrace:
    if not samples:
        raise ValueError("samples must not be empty")
    if coarse_prefix < 8:
        raise ValueError("coarse_prefix must be at least 8")
    if coarse_mode not in {"phase", "freq_phase"}:
        raise ValueError("coarse_mode must be 'phase' or 'freq_phase'")

    prefix = samples[: min(coarse_prefix, len(samples))]
    if coarse_mode == "freq_phase":
        coarse = coarse_fourth_power_acquisition(prefix)
        coarse_phase = coarse.phase
        coarse_frequency = coarse.frequency
    else:
        coarse_phase = coarse_fourth_power_phase(prefix)
        coarse_frequency = 0.0
    coarse_corrected = [sample * cmath.exp(-1j * (coarse_phase + coarse_frequency * idx)) for idx, sample in enumerate(samples)]

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
        coarse_frequency=coarse_frequency,
        coarse_mode=coarse_mode,
    )
