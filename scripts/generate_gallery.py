#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from costaslab.analysis import LoopGainSetting, quality_band, rms_decision_error, study_alias_limit, study_coarse_prefix_budget, study_loop_gains, sweep_acquisition_modes, sweep_frequency_offsets
from costaslab.loop import run_qpsk_costas_loop
from costaslab.render import export_png_from_svg, render_acquisition_range_svg, render_alias_limit_svg, render_coarse_prefix_budget_svg, render_costas_demo_svg, render_loop_gain_tradeoff_svg, render_offset_sweep_svg
from costaslab.signal import qpsk_symbols, rotate_symbols

ASSETS = REPO / "assets"
REPORTS = REPO / "reports"


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    symbols = qpsk_symbols(900, seed=7)
    received = rotate_symbols(symbols, phase_offset=0.85, freq_offset=0.022, noise_std=0.04, seed=8)
    trace = run_qpsk_costas_loop(received, alpha=0.11, beta=0.0045)
    render_costas_demo_svg(trace, output=ASSETS / "qpsk-costas-demo.svg")
    export_png_from_svg(ASSETS / "qpsk-costas-demo.svg", ASSETS / "qpsk-costas-demo.png")

    sweep_rows = sweep_frequency_offsets([(-0.5 + 0.05 * idx) for idx in range(21)])
    render_offset_sweep_svg(sweep_rows, output=ASSETS / "qpsk-costas-offset-sweep.svg")
    export_png_from_svg(ASSETS / "qpsk-costas-offset-sweep.svg", ASSETS / "qpsk-costas-offset-sweep.png")

    acquisition_rows = sweep_acquisition_modes([(-0.75 + 0.05 * idx) for idx in range(31)])
    render_acquisition_range_svg(acquisition_rows, output=ASSETS / "qpsk-acquisition-range-map.svg")
    export_png_from_svg(ASSETS / "qpsk-acquisition-range-map.svg", ASSETS / "qpsk-acquisition-range-map.png")

    gain_settings = [
        LoopGainSetting(label="gentle", alpha=0.05, beta=0.0015),
        LoopGainSetting(label="default", alpha=0.11, beta=0.0045),
        LoopGainSetting(label="aggressive", alpha=0.20, beta=0.0120),
    ]
    gain_studies = study_loop_gains(gain_settings)
    render_loop_gain_tradeoff_svg(gain_studies, output=ASSETS / "qpsk-loop-gain-tradeoffs.svg")
    export_png_from_svg(ASSETS / "qpsk-loop-gain-tradeoffs.svg", ASSETS / "qpsk-loop-gain-tradeoffs.png")

    prefix_rows = study_coarse_prefix_budget([8, 12, 16, 24, 32, 48, 64, 96, 128], [0.02, 0.04, 0.06, 0.08, 0.10])
    render_coarse_prefix_budget_svg(prefix_rows, output=ASSETS / "qpsk-coarse-prefix-budget.svg")
    export_png_from_svg(ASSETS / "qpsk-coarse-prefix-budget.svg", ASSETS / "qpsk-coarse-prefix-budget.png")

    with (ASSETS / "qpsk-coarse-prefix-budget.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "coarse_prefix",
            "noise_std",
            "mean_abs_coarse_frequency_error",
            "mean_coarse_rms_error",
            "mean_tracked_rms_error",
        ])
        for row in prefix_rows:
            writer.writerow(
                [
                    row.coarse_prefix,
                    f"{row.noise_std:.2f}",
                    f"{row.mean_abs_coarse_frequency_error:.8f}",
                    f"{row.mean_coarse_rms_error:.8f}",
                    f"{row.mean_tracked_rms_error:.8f}",
                ]
            )

    lines = [
        "# QPSK carrier-recovery report",
        "",
        "These artifacts were generated locally from the same pure-Python code in this repo.",
        "",
        "## Demo case",
        "",
        f"- coarse fourth-power phase estimate: {trace.coarse_phase:+.3f} rad",
        f"- raw RMS decision error after the transient trim: {rms_decision_error(received, trim=180):.3f}",
        f"- after coarse phase correction only: {rms_decision_error(trace.coarse_corrected, trim=180):.3f}",
        f"- after Costas tracking: {rms_decision_error(trace.tracked, trim=180):.3f}",
        f"- final frequency estimate: {trace.freq_estimates[-1]:+.5f} rad/sample",
        "",
        "## Offset sweep highlights",
        "",
    ]

    best = min(sweep_rows, key=lambda row: row["tracked_rms_error"])
    hardest = max(sweep_rows, key=lambda row: row["tracked_rms_error"])
    stable = [row for row in sweep_rows if row["tracked_rms_error"] < 0.10]
    stable_limit = max(abs(row["freq_offset"]) for row in stable) if stable else 0.0
    lines.append(f"- best tracked RMS error in this sweep: {best['tracked_rms_error']:.3f} at offset {best['freq_offset']:+.3f} rad/sample")
    lines.append(f"- hardest tracked RMS error in this sweep: {hardest['tracked_rms_error']:.3f} at offset {hardest['freq_offset']:+.3f} rad/sample")
    lines.append(f"- with this exact loop tuning, the tracked cloud stays clean out to about ±{stable_limit:.2f} rad/sample before the pull-in range starts to break")
    lines.append("")
    lines.append("## Per-offset summary")
    lines.append("")
    for row in sweep_rows:
        lines.append(f"- {row['freq_offset']:+.3f} rad/sample -> raw {row['raw_rms_error']:.3f}, coarse {row['coarse_rms_error']:.3f}, tracked {row['tracked_rms_error']:.3f}")

    (REPORTS / "qpsk-carrier-recovery.md").write_text("\n".join(lines) + "\n")

    acquisition_lines = [
        "# QPSK frequency acquisition report",
        "",
        "This pass adds a wider receive-chain split: a 4th-power front end now estimates both coarse phase and coarse frequency before the Costas loop takes over.",
        "",
        "## Why this matters",
        "",
        "Phase-only coarse correction can clean up a static rotation, but it leaves the loop to eat the whole residual frequency ramp by itself.",
        "That is fine near the center. It is much less fine once the offset gets large enough that the loop is always chasing.",
        "",
        "The useful boundary here is roughly `|freq_offset| < pi/4`, because the 4th-power frequency estimate wraps beyond that alias limit.",
        "",
        "## Sweep summary",
        "",
    ]

    clean_phase = [abs(row.freq_offset) for row in acquisition_rows if quality_band(row.phase_only_tracked_rms_error) == "clean"]
    clean_freq = [abs(row.freq_offset) for row in acquisition_rows if quality_band(row.freq_acquired_tracked_rms_error) == "clean"]
    marginal_freq = [abs(row.freq_offset) for row in acquisition_rows if quality_band(row.freq_acquired_tracked_rms_error) != "failed"]
    acquisition_lines.append(f"- phase-only coarse + Costas stays clean to about ±{(max(clean_phase) if clean_phase else 0.0):.2f} rad/sample in this sweep")
    acquisition_lines.append(f"- freq + phase coarse + Costas stays clean to about ±{(max(clean_freq) if clean_freq else 0.0):.2f} rad/sample")
    acquisition_lines.append(f"- freq + phase coarse + Costas stays at least marginal to about ±{(max(marginal_freq) if marginal_freq else 0.0):.2f} rad/sample")
    acquisition_lines.append("")
    acquisition_lines.append("## Per-offset comparison")
    acquisition_lines.append("")
    for row in acquisition_rows:
        acquisition_lines.append(
            f"- {row.freq_offset:+.3f} rad/sample -> phase-only tracked {row.phase_only_tracked_rms_error:.3f}, freq-acquired tracked {row.freq_acquired_tracked_rms_error:.3f}, coarse freq estimate {row.coarse_frequency_estimate:+.4f}"
        )

    acquisition_lines.extend(
        [
            "",
            "## Read the artifact",
            "",
            "Open `assets/qpsk-acquisition-range-map.svg` or the 300 dpi PNG next. The top plot shows the handoff improvement directly, the lower-left panel shows where the coarse estimate stays honest, and the regime bars make the pull-in range visible instead of leaving it as folklore.",
        ]
    )
    (REPORTS / "qpsk-frequency-acquisition.md").write_text("\n".join(acquisition_lines) + "\n")

    alias_rows = study_alias_limit([(-1.0 + 0.05 * idx) for idx in range(41)])
    render_alias_limit_svg(alias_rows, output=ASSETS / "qpsk-alias-limit-map.svg")
    export_png_from_svg(ASSETS / "qpsk-alias-limit-map.svg", ASSETS / "qpsk-alias-limit-map.png")

    with (ASSETS / "qpsk-alias-limit-map.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "freq_offset",
                "coarse_frequency_estimate",
                "wrapped_residual_frequency",
                "phase_only_tracked_rms_error",
                "freq_acquired_tracked_rms_error",
                "phase_only_symbol_error_rate",
                "freq_acquired_symbol_error_rate",
            ]
        )
        for row in alias_rows:
            writer.writerow(
                [
                    f"{row.freq_offset:.6f}",
                    f"{row.coarse_frequency_estimate:.6f}",
                    f"{row.wrapped_residual_frequency:.6f}",
                    f"{row.phase_only_tracked_rms_error:.6f}",
                    f"{row.freq_acquired_tracked_rms_error:.6f}",
                    f"{row.phase_only_symbol_error_rate:.6f}",
                    f"{row.freq_acquired_symbol_error_rate:.6f}",
                ]
            )

    alias_lines = [
        "# QPSK alias-limit report",
        "",
        "This sidecar asks a narrower question than the acquisition-range map: **what actually breaks once the 4th-power frequency estimate crosses its `pi/4` alias limit?**",
        "",
        "The useful answer is not just \"the estimate wraps.\" The more interesting failure is that the constellation can still look clean under the old nearest-corner RMS metric even while the symbol labels are wrong.",
        "",
        "## The core identity",
        "",
        "For a QPSK symbol-rate model, the 4th-power front end sees `4 * freq_offset`.",
        "That means the estimate is unique only while `|freq_offset| < pi/4`.",
        "Once the true offset crosses that boundary, the coarse estimate folds onto the wrong branch and leaves a residual close to `±pi/2` rad/sample after coarse correction.",
        "",
        "## Why the old RMS metric can lie",
        "",
        "A residual near `pi/2` rad/sample quarter-turns the constellation from one symbol to the next.",
        "Nearest-corner RMS is blind to that if the cloud still lands on QPSK corners.",
        "So the scatter can look clean while a fixed symbol labeling has already collapsed.",
        "",
        "## Sweep summary",
        "",
    ]

    clean_freq = [abs(row.freq_offset) for row in alias_rows if row.freq_acquired_symbol_error_rate <= 0.01]
    false_clean = [row for row in alias_rows if row.freq_acquired_tracked_rms_error < 0.10 and row.freq_acquired_symbol_error_rate >= 0.70]
    alias_lines.append(f"- freq + phase acquisition keeps best static-quadrant SER near zero out to about ±{(max(clean_freq) if clean_freq else 0.0):.2f} rad/sample")
    if false_clean:
        first_false = min(false_clean, key=lambda row: abs(row.freq_offset))
        alias_lines.append(
            f"- the first false-clean point in this sweep shows up around {first_false.freq_offset:+.2f} rad/sample: tracked RMS still reads {first_false.freq_acquired_tracked_rms_error:.3f}, but best static-quadrant SER is already {first_false.freq_acquired_symbol_error_rate:.2f}"
        )
    pivot = min(alias_rows, key=lambda row: abs(row.freq_offset - 0.85))
    alias_lines.append(
        f"- at {pivot.freq_offset:+.2f} rad/sample, the coarse estimate folds to {pivot.coarse_frequency_estimate:+.3f}, leaving a wrapped residual of {pivot.wrapped_residual_frequency:+.3f} rad/sample while the tracked RMS stays at {pivot.freq_acquired_tracked_rms_error:.3f}"
    )
    alias_lines.append("")
    alias_lines.append("## Per-offset comparison")
    alias_lines.append("")
    for row in alias_rows:
        alias_lines.append(
            f"- {row.freq_offset:+.3f} rad/sample -> estimate {row.coarse_frequency_estimate:+.3f}, wrapped residual {row.wrapped_residual_frequency:+.3f}, phase-only SER {row.phase_only_symbol_error_rate:.2f}, freq-acquired SER {row.freq_acquired_symbol_error_rate:.2f}, freq-acquired tracked RMS {row.freq_acquired_tracked_rms_error:.3f}"
        )

    alias_lines.extend(
        [
            "",
            "## Read the artifact",
            "",
            "Open `assets/qpsk-alias-limit-map.png` next. The top panel shows the coarse estimate folding onto the wrong branch, the lower-left panel shows why nearest-corner RMS still looks deceptively calm, and the lower-right panel shows the real cliff once you measure symbol agreement after the best static quadrant relabeling.",
        ]
    )
    (REPORTS / "qpsk-alias-limit.md").write_text("\n".join(alias_lines) + "\n")

    gain_lines = [
        "# QPSK loop-gain tradeoff report",
        "",
        "This pass keeps the same coarse acquisition logic but changes the Costas loop gains to show the real compromise: hotter gains can pull a rough handoff into place faster, but they leave a noisier residual once the front end has already done its job.",
        "",
        "## Stress cases",
        "",
        "- acquisition panel: phase-only coarse correction, `freq_offset = +0.35 rad/sample`, `noise_std = 0.04`",
        "- tracking panel: frequency-plus-phase coarse correction, `freq_offset = +0.35 rad/sample`, `noise_std = 0.08`",
        "",
        "## Loop settings",
        "",
    ]
    for study in gain_studies:
        settle_text = str(study.acquisition_settle_index) if study.acquisition_settle_index is not None else "no clean settle in 1500 symbols"
        gain_lines.append(
            f"- **{study.label}** (`alpha={study.alpha:.2f}`, `beta={study.beta:.4f}`): phase-only settle = {settle_text}; tracking tail RMS = {study.tracking_tail_rms_error:.3f}; mean |Costas error| = {study.tracking_mean_abs_costas_error:.3f}; frequency jitter = {study.tracking_freq_jitter * 1000.0:.2f} mrad/sample"
        )

    gain_lines.extend(
        [
            "",
            "## Read the result",
            "",
            "The figure splits the problem into two honest regimes instead of pretending one gain setting is simply better:",
            "",
            "- on the harder phase-only handoff, aggressive gains reach the decision-directed sweet spot much sooner",
            "- once the coarse frequency estimate has already done that work, gentler gains leave a quieter steady-state trace",
            "",
            "That is the real tuning trade: rescue margin versus post-lock calm.",
        ]
    )
    (REPORTS / "qpsk-loop-gain-tradeoffs.md").write_text("\n".join(gain_lines) + "\n")

    prefix_lines = [
        "# QPSK coarse-prefix budget report",
        "",
        "This pass asks a narrower front-end question: **once a 4th-power frequency estimate is already inside the Costas loop's pull-in range, how many prefix symbols still matter?**",
        "",
        "The setup stays fixed on purpose:",
        "",
        "- carrier offset: `+0.62 rad/sample`",
        "- same phase offset and loop gains as the rest of the repo",
        "- only the coarse-prefix length and channel noise change",
        "- each grid point averages 24 Monte Carlo trials",
        "",
        "## Main takeaway",
        "",
        "Longer prefixes keep improving the coarse estimate, but the tracked output flattens much sooner.",
        "In this symbol-rate model, the front end gets materially more honest all the way out to 96 or 128 symbols, yet the loop behaves almost the same once the handoff already lands inside its comfort zone.",
        "",
        "That means extra prefix length buys estimator honesty before it buys visible post-lock improvement.",
        "",
        "## Selected checkpoints",
        "",
    ]
    for noise_std in sorted({row.noise_std for row in prefix_rows}):
        band = [row for row in prefix_rows if row.noise_std == noise_std]
        first = band[0]
        mid = next(row for row in band if row.coarse_prefix == 32)
        long = next(row for row in band if row.coarse_prefix == 128)
        threshold = next((row.coarse_prefix for row in band if row.mean_abs_coarse_frequency_error * 1000.0 <= 5.0), None)
        prefix_lines.append(
            f"- noise std {noise_std:.2f}: mean |coarse freq error| drops from {first.mean_abs_coarse_frequency_error * 1000.0:.1f} mrad at prefix 8 to {mid.mean_abs_coarse_frequency_error * 1000.0:.1f} mrad at prefix 32 and {long.mean_abs_coarse_frequency_error * 1000.0:.1f} mrad at prefix 128; tracked RMS only moves from {first.mean_tracked_rms_error:.4f} to {long.mean_tracked_rms_error:.4f}; 5 mrad threshold = {'not reached' if threshold is None else f'prefix {threshold}'}"
        )

    prefix_lines.extend(
        [
            "",
            "## How to read the artifact",
            "",
            "The top panel of `assets/qpsk-coarse-prefix-budget.png` shows the honest front-end story: more symbols make the 4th-power estimate noticeably less noisy, especially once the channel noise rises.",
            "The lower-left panel shows the practical receive-chain story: after the loop takes over, most of that front-end improvement barely changes the post-lock RMS unless the prefix was already too short.",
            "",
            "That is the point of the card. A bigger prefix is not useless. It is just solving a different problem once the handoff is already decent.",
        ]
    )
    (REPORTS / "qpsk-coarse-prefix-budget.md").write_text("\n".join(prefix_lines) + "\n")
    print("generated Costas-loop gallery, alias-limit sidecar, and report")


if __name__ == "__main__":
    main()
