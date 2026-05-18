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


@dataclass(frozen=True)
class LoopGainSetting:
    label: str
    alpha: float
    beta: float


@dataclass(frozen=True)
class LoopGainStudy:
    label: str
    alpha: float
    beta: float
    acquisition_trace: LoopTrace
    tracking_trace: LoopTrace
    acquisition_settle_index: int | None
    acquisition_tail_rms_error: float
    tracking_tail_rms_error: float
    tracking_mean_abs_costas_error: float
    tracking_freq_jitter: float


@dataclass(frozen=True)
class CoarsePrefixBudgetRow:
    coarse_prefix: int
    noise_std: float
    mean_abs_coarse_frequency_error: float
    mean_coarse_rms_error: float
    mean_tracked_rms_error: float


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


def decision_error_series(samples: list[complex]) -> list[float]:
    return [abs(sample - hard_decision_qpsk(sample)) for sample in samples]


def moving_average(values: list[float], window: int) -> list[float]:
    if window <= 1 or not values:
        return list(values)
    out: list[float] = []
    total = 0.0
    for idx, value in enumerate(values):
        total += value
        if idx >= window:
            total -= values[idx - window]
        out.append(total / min(idx + 1, window))
    return out


def settle_index(samples: list[complex], *, threshold: float = 0.14, hold: int = 64) -> int | None:
    if hold < 1:
        raise ValueError("hold must be at least 1")
    errors = decision_error_series(samples)
    if len(errors) < hold:
        return None
    for idx in range(len(errors) - hold + 1):
        if max(errors[idx : idx + hold]) < threshold:
            return idx
    return None


def mean_abs(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(abs(value) for value in values) / len(values)


def population_std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


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


def study_loop_gains(
    settings: list[LoopGainSetting],
    *,
    count: int = 1500,
    phase_offset: float = 0.85,
    acquisition_offset: float = 0.35,
    acquisition_noise_std: float = 0.04,
    tracking_offset: float = 0.35,
    tracking_noise_std: float = 0.08,
    coarse_prefix: int = 64,
    seed: int = 7,
) -> list[LoopGainStudy]:
    if not settings:
        raise ValueError("settings must not be empty")

    symbols = qpsk_symbols(count, seed=seed)
    acquisition_received = rotate_symbols(
        symbols,
        phase_offset=phase_offset,
        freq_offset=acquisition_offset,
        noise_std=acquisition_noise_std,
        seed=seed + 1,
    )
    tracking_received = rotate_symbols(
        symbols,
        phase_offset=phase_offset,
        freq_offset=tracking_offset,
        noise_std=tracking_noise_std,
        seed=seed + 2,
    )

    studies: list[LoopGainStudy] = []
    for setting in settings:
        acquisition_trace = run_qpsk_costas_loop(
            acquisition_received,
            alpha=setting.alpha,
            beta=setting.beta,
            coarse_prefix=coarse_prefix,
            coarse_mode="phase",
        )
        tracking_trace = run_qpsk_costas_loop(
            tracking_received,
            alpha=setting.alpha,
            beta=setting.beta,
            coarse_prefix=coarse_prefix,
            coarse_mode="freq_phase",
        )
        acquisition_settled = settle_index(acquisition_trace.tracked)
        acquisition_tail_start = max(300, ((acquisition_settled + 100) if acquisition_settled is not None else 300))
        tracking_tail_start = 300
        studies.append(
            LoopGainStudy(
                label=setting.label,
                alpha=setting.alpha,
                beta=setting.beta,
                acquisition_trace=acquisition_trace,
                tracking_trace=tracking_trace,
                acquisition_settle_index=acquisition_settled,
                acquisition_tail_rms_error=rms_decision_error(acquisition_trace.tracked, trim=acquisition_tail_start),
                tracking_tail_rms_error=rms_decision_error(tracking_trace.tracked, trim=tracking_tail_start),
                tracking_mean_abs_costas_error=mean_abs(tracking_trace.error_signal[tracking_tail_start:]),
                tracking_freq_jitter=population_std(tracking_trace.freq_estimates[tracking_tail_start:]),
            )
        )
    return studies


def study_coarse_prefix_budget(
    prefixes: list[int],
    noise_levels: list[float],
    *,
    freq_offset: float = 0.62,
    count: int = 900,
    phase_offset: float = 0.85,
    alpha: float = 0.11,
    beta: float = 0.0045,
    trim: int = 180,
    trials: int = 24,
    base_seed: int = 41,
) -> list[CoarsePrefixBudgetRow]:
    if not prefixes:
        raise ValueError("prefixes must not be empty")
    if not noise_levels:
        raise ValueError("noise_levels must not be empty")
    if trials < 1:
        raise ValueError("trials must be at least 1")

    rows: list[CoarsePrefixBudgetRow] = []
    for noise_std in noise_levels:
        for coarse_prefix in prefixes:
            freq_errors: list[float] = []
            coarse_rms_errors: list[float] = []
            tracked_rms_errors: list[float] = []
            for trial in range(trials):
                symbol_seed = base_seed + 17 * trial
                channel_seed = base_seed + 1000 + 29 * trial
                symbols = qpsk_symbols(count, seed=symbol_seed)
                received = rotate_symbols(
                    symbols,
                    phase_offset=phase_offset,
                    freq_offset=freq_offset,
                    noise_std=noise_std,
                    seed=channel_seed,
                )
                trace = run_qpsk_costas_loop(
                    received,
                    alpha=alpha,
                    beta=beta,
                    coarse_prefix=coarse_prefix,
                    coarse_mode="freq_phase",
                )
                freq_errors.append(abs(trace.coarse_frequency - freq_offset))
                coarse_rms_errors.append(rms_decision_error(trace.coarse_corrected, trim=trim))
                tracked_rms_errors.append(rms_decision_error(trace.tracked, trim=trim))

            rows.append(
                CoarsePrefixBudgetRow(
                    coarse_prefix=coarse_prefix,
                    noise_std=noise_std,
                    mean_abs_coarse_frequency_error=sum(freq_errors) / len(freq_errors),
                    mean_coarse_rms_error=sum(coarse_rms_errors) / len(coarse_rms_errors),
                    mean_tracked_rms_error=sum(tracked_rms_errors) / len(tracked_rms_errors),
                )
            )
    return rows
