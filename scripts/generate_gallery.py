#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from costaslab.analysis import rms_decision_error, sweep_frequency_offsets
from costaslab.loop import run_qpsk_costas_loop
from costaslab.render import render_costas_demo_svg, render_offset_sweep_svg
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

    sweep_rows = sweep_frequency_offsets([(-0.5 + 0.05 * idx) for idx in range(21)])
    render_offset_sweep_svg(sweep_rows, output=ASSETS / "qpsk-costas-offset-sweep.svg")

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
    print("generated Costas-loop gallery and report")


if __name__ == "__main__":
    main()
