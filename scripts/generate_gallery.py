#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from costaslab.analysis import LoopGainSetting, quality_band, rms_decision_error, study_loop_gains, sweep_acquisition_modes, sweep_frequency_offsets
from costaslab.loop import run_qpsk_costas_loop
from costaslab.render import export_png_from_svg, render_acquisition_range_svg, render_costas_demo_svg, render_loop_gain_tradeoff_svg, render_offset_sweep_svg
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
    print("generated Costas-loop gallery and report")


if __name__ == "__main__":
    main()
