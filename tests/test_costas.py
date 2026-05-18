from __future__ import annotations

import cmath
import unittest

from costaslab.analysis import LoopGainSetting, quality_band, rms_decision_error, study_coarse_prefix_budget, study_loop_gains, sweep_acquisition_modes, sweep_frequency_offsets
from costaslab.loop import coarse_fourth_power_frequency, coarse_fourth_power_phase, run_qpsk_costas_loop
from costaslab.signal import hard_decision_qpsk, qpsk_symbols, rotate_symbols


class CostasLoopTests(unittest.TestCase):
    def test_qpsk_hard_decision_stays_on_constellation(self) -> None:
        out = hard_decision_qpsk(complex(-0.2, 0.8))
        self.assertAlmostEqual(abs(out), 1.0)
        self.assertLess(out.real, 0.0)
        self.assertGreater(out.imag, 0.0)

    def test_coarse_fourth_power_phase_improves_constellation_alignment(self) -> None:
        symbols = qpsk_symbols(256, seed=11)
        rotated = rotate_symbols(symbols, phase_offset=0.7, seed=1)
        estimate = coarse_fourth_power_phase(rotated)
        corrected = [sample * cmath.exp(-1j * estimate) for sample in rotated]
        self.assertLess(rms_decision_error(corrected), rms_decision_error(rotated))

    def test_costas_loop_reduces_decision_error(self) -> None:
        symbols = qpsk_symbols(900, seed=7)
        received = rotate_symbols(symbols, phase_offset=0.85, freq_offset=0.022, noise_std=0.04, seed=8)
        trace = run_qpsk_costas_loop(received)
        raw = rms_decision_error(received, trim=180)
        tracked = rms_decision_error(trace.tracked, trim=180)
        self.assertLess(tracked, 0.55 * raw)

    def test_zero_offset_stays_well_locked(self) -> None:
        symbols = qpsk_symbols(600, seed=3)
        received = rotate_symbols(symbols, phase_offset=0.2, freq_offset=0.0, noise_std=0.02, seed=4)
        trace = run_qpsk_costas_loop(received)
        self.assertLess(rms_decision_error(trace.tracked, trim=120), 0.12)

    def test_offset_sweep_shows_tracking_help_near_center(self) -> None:
        rows = sweep_frequency_offsets([-0.01, 0.0, 0.01], count=700)
        for row in rows:
            self.assertLess(row["tracked_rms_error"], row["raw_rms_error"])
        mean_tracked = sum(row["tracked_rms_error"] for row in rows) / len(rows)
        mean_coarse = sum(row["coarse_rms_error"] for row in rows) / len(rows)
        self.assertLess(mean_tracked, mean_coarse)

    def test_coarse_fourth_power_frequency_tracks_offset(self) -> None:
        symbols = qpsk_symbols(256, seed=12)
        rotated = rotate_symbols(symbols, phase_offset=0.25, freq_offset=0.06, noise_std=0.01, seed=13)
        estimate = coarse_fourth_power_frequency(rotated[:128])
        self.assertAlmostEqual(estimate, 0.06, delta=0.01)

    def test_frequency_acquisition_extends_pull_in_range(self) -> None:
        symbols = qpsk_symbols(900, seed=21)
        received = rotate_symbols(symbols, phase_offset=0.85, freq_offset=0.50, noise_std=0.04, seed=22)
        phase_only = run_qpsk_costas_loop(received, coarse_mode="phase")
        freq_acquired = run_qpsk_costas_loop(received, coarse_mode="freq_phase")
        self.assertLess(rms_decision_error(freq_acquired.tracked, trim=180), 0.65 * rms_decision_error(phase_only.tracked, trim=180))

    def test_acquisition_sweep_shows_broader_clean_band(self) -> None:
        rows = sweep_acquisition_modes([-0.5, -0.3, 0.0, 0.3, 0.5], count=900)
        clean_phase = sum(1 for row in rows if quality_band(row.phase_only_tracked_rms_error) == "clean")
        clean_freq = sum(1 for row in rows if quality_band(row.freq_acquired_tracked_rms_error) == "clean")
        self.assertGreater(clean_freq, clean_phase)

    def test_loop_gain_tradeoff_shows_speed_versus_jitter(self) -> None:
        studies = study_loop_gains(
            [
                LoopGainSetting(label="gentle", alpha=0.05, beta=0.0015),
                LoopGainSetting(label="default", alpha=0.11, beta=0.0045),
                LoopGainSetting(label="aggressive", alpha=0.20, beta=0.0120),
            ]
        )
        by_label = {study.label: study for study in studies}

        self.assertIsNone(by_label["gentle"].acquisition_settle_index)
        self.assertLess(by_label["aggressive"].acquisition_settle_index, by_label["default"].acquisition_settle_index)
        self.assertLess(by_label["gentle"].tracking_freq_jitter, by_label["default"].tracking_freq_jitter)
        self.assertLess(by_label["default"].tracking_freq_jitter, by_label["aggressive"].tracking_freq_jitter)
        self.assertLess(by_label["gentle"].tracking_tail_rms_error, by_label["aggressive"].tracking_tail_rms_error)

    def test_coarse_prefix_budget_shows_honesty_improves_faster_than_post_lock_output(self) -> None:
        rows = study_coarse_prefix_budget([8, 16, 32, 64], [0.08], trials=8)
        by_prefix = {row.coarse_prefix: row for row in rows}

        self.assertGreater(by_prefix[8].mean_abs_coarse_frequency_error, by_prefix[16].mean_abs_coarse_frequency_error)
        self.assertGreater(by_prefix[16].mean_abs_coarse_frequency_error, by_prefix[32].mean_abs_coarse_frequency_error)
        self.assertGreater(by_prefix[8].mean_abs_coarse_frequency_error, by_prefix[64].mean_abs_coarse_frequency_error)

        tracked_span = max(row.mean_tracked_rms_error for row in rows) - min(row.mean_tracked_rms_error for row in rows)
        self.assertLess(tracked_span, 0.002)


if __name__ == "__main__":
    unittest.main()
