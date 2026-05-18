from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .analysis import LoopGainSetting, rms_decision_error, study_coarse_prefix_budget, study_loop_gains, sweep_acquisition_modes, sweep_frequency_offsets
from .loop import run_qpsk_costas_loop
from .render import (
    export_png_from_svg,
    render_acquisition_range_svg,
    render_costas_demo_svg,
    render_loop_gain_tradeoff_svg,
    render_coarse_prefix_budget_svg,
    render_offset_sweep_svg,
)
from .signal import qpsk_symbols, rotate_symbols


def main() -> None:
    parser = argparse.ArgumentParser(description="QPSK carrier recovery lab with coarse phase acquisition and Costas tracking")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="run one QPSK carrier-recovery demo")
    demo.add_argument("--count", type=int, default=900)
    demo.add_argument("--seed", type=int, default=7)
    demo.add_argument("--phase-offset", type=float, default=0.85)
    demo.add_argument("--freq-offset", type=float, default=0.022)
    demo.add_argument("--noise-std", type=float, default=0.04)
    demo.add_argument("--alpha", type=float, default=0.11)
    demo.add_argument("--beta", type=float, default=0.0045)
    demo.add_argument("--output", type=Path, default=None)

    sweep = sub.add_parser("sweep", help="sweep carrier offsets and optionally render a figure")
    sweep.add_argument("--min-offset", type=float, default=-0.5)
    sweep.add_argument("--max-offset", type=float, default=0.5)
    sweep.add_argument("--steps", type=int, default=21)
    sweep.add_argument("--count", type=int, default=800)
    sweep.add_argument("--seed", type=int, default=7)
    sweep.add_argument("--phase-offset", type=float, default=0.85)
    sweep.add_argument("--noise-std", type=float, default=0.04)
    sweep.add_argument("--alpha", type=float, default=0.11)
    sweep.add_argument("--beta", type=float, default=0.0045)
    sweep.add_argument("--output", type=Path, default=None)

    acquisition = sub.add_parser("acquisition-sweep", help="compare phase-only acquisition against 4th-power frequency acquisition")
    acquisition.add_argument("--min-offset", type=float, default=-0.75)
    acquisition.add_argument("--max-offset", type=float, default=0.75)
    acquisition.add_argument("--steps", type=int, default=31)
    acquisition.add_argument("--count", type=int, default=900)
    acquisition.add_argument("--seed", type=int, default=7)
    acquisition.add_argument("--phase-offset", type=float, default=0.85)
    acquisition.add_argument("--noise-std", type=float, default=0.04)
    acquisition.add_argument("--alpha", type=float, default=0.11)
    acquisition.add_argument("--beta", type=float, default=0.0045)
    acquisition.add_argument("--coarse-prefix", type=int, default=64)
    acquisition.add_argument("--output", type=Path, default=None)
    acquisition.add_argument("--png-output", type=Path, default=None)

    gain_study = sub.add_parser("gain-study", help="compare loop-gain settings on acquisition speed versus tracking jitter")
    gain_study.add_argument("--count", type=int, default=1500)
    gain_study.add_argument("--seed", type=int, default=7)
    gain_study.add_argument("--phase-offset", type=float, default=0.85)
    gain_study.add_argument("--acquisition-offset", type=float, default=0.35)
    gain_study.add_argument("--acquisition-noise-std", type=float, default=0.04)
    gain_study.add_argument("--tracking-offset", type=float, default=0.35)
    gain_study.add_argument("--tracking-noise-std", type=float, default=0.08)
    gain_study.add_argument("--coarse-prefix", type=int, default=64)
    gain_study.add_argument("--output", type=Path, default=None)
    gain_study.add_argument("--png-output", type=Path, default=None)

    prefix_study = sub.add_parser("prefix-budget-study", help="measure how coarse-prefix length changes front-end honesty versus post-loop output")
    prefix_study.add_argument("--prefixes", type=str, default="8,12,16,24,32,48,64,96,128")
    prefix_study.add_argument("--noise-levels", type=str, default="0.02,0.04,0.06,0.08,0.10")
    prefix_study.add_argument("--freq-offset", type=float, default=0.62)
    prefix_study.add_argument("--count", type=int, default=900)
    prefix_study.add_argument("--phase-offset", type=float, default=0.85)
    prefix_study.add_argument("--alpha", type=float, default=0.11)
    prefix_study.add_argument("--beta", type=float, default=0.0045)
    prefix_study.add_argument("--trim", type=int, default=180)
    prefix_study.add_argument("--trials", type=int, default=24)
    prefix_study.add_argument("--base-seed", type=int, default=41)
    prefix_study.add_argument("--output", type=Path, default=None)
    prefix_study.add_argument("--png-output", type=Path, default=None)

    args = parser.parse_args()

    if args.command == "demo":
        symbols = qpsk_symbols(args.count, seed=args.seed)
        received = rotate_symbols(
            symbols,
            phase_offset=args.phase_offset,
            freq_offset=args.freq_offset,
            noise_std=args.noise_std,
            seed=args.seed + 1,
        )
        trace = run_qpsk_costas_loop(received, alpha=args.alpha, beta=args.beta)
        if args.output is not None:
            render_costas_demo_svg(trace, output=args.output)
        payload = {
            "count": args.count,
            "coarse_phase": trace.coarse_phase,
            "raw_rms_error": rms_decision_error(received, trim=180),
            "coarse_rms_error": rms_decision_error(trace.coarse_corrected, trim=180),
            "tracked_rms_error": rms_decision_error(trace.tracked, trim=180),
            "final_freq_estimate": trace.freq_estimates[-1],
        }
        print(json.dumps(payload, indent=2))
        return

    if args.command == "acquisition-sweep":
        offsets = [args.min_offset + idx * (args.max_offset - args.min_offset) / (args.steps - 1) for idx in range(args.steps)]
        rows = sweep_acquisition_modes(
            offsets,
            count=args.count,
            phase_offset=args.phase_offset,
            noise_std=args.noise_std,
            alpha=args.alpha,
            beta=args.beta,
            coarse_prefix=args.coarse_prefix,
            seed=args.seed,
        )
        if args.output is not None:
            render_acquisition_range_svg(rows, output=args.output)
        if args.png_output is not None and args.output is not None:
            export_png_from_svg(args.output, args.png_output)
        print(json.dumps([asdict(row) for row in rows], indent=2))
        return

    if args.command == "gain-study":
        settings = [
            LoopGainSetting(label="gentle", alpha=0.05, beta=0.0015),
            LoopGainSetting(label="default", alpha=0.11, beta=0.0045),
            LoopGainSetting(label="aggressive", alpha=0.20, beta=0.0120),
        ]
        studies = study_loop_gains(
            settings,
            count=args.count,
            phase_offset=args.phase_offset,
            acquisition_offset=args.acquisition_offset,
            acquisition_noise_std=args.acquisition_noise_std,
            tracking_offset=args.tracking_offset,
            tracking_noise_std=args.tracking_noise_std,
            coarse_prefix=args.coarse_prefix,
            seed=args.seed,
        )
        if args.output is not None:
            render_loop_gain_tradeoff_svg(studies, output=args.output)
        if args.png_output is not None and args.output is not None:
            export_png_from_svg(args.output, args.png_output)
        payload = [
            {
                "label": study.label,
                "alpha": study.alpha,
                "beta": study.beta,
                "acquisition_settle_index": study.acquisition_settle_index,
                "acquisition_tail_rms_error": study.acquisition_tail_rms_error,
                "tracking_tail_rms_error": study.tracking_tail_rms_error,
                "tracking_mean_abs_costas_error": study.tracking_mean_abs_costas_error,
                "tracking_freq_jitter": study.tracking_freq_jitter,
            }
            for study in studies
        ]
        print(json.dumps(payload, indent=2))
        return

    if args.command == "prefix-budget-study":
        prefixes = [int(chunk) for chunk in args.prefixes.split(",") if chunk.strip()]
        noise_levels = [float(chunk) for chunk in args.noise_levels.split(",") if chunk.strip()]
        rows = study_coarse_prefix_budget(
            prefixes,
            noise_levels,
            freq_offset=args.freq_offset,
            count=args.count,
            phase_offset=args.phase_offset,
            alpha=args.alpha,
            beta=args.beta,
            trim=args.trim,
            trials=args.trials,
            base_seed=args.base_seed,
        )
        if args.output is not None:
            render_coarse_prefix_budget_svg(rows, output=args.output)
        if args.png_output is not None and args.output is not None:
            export_png_from_svg(args.output, args.png_output)
        payload = [asdict(row) for row in rows]
        print(json.dumps(payload, indent=2))
        return

    offsets = [args.min_offset + idx * (args.max_offset - args.min_offset) / (args.steps - 1) for idx in range(args.steps)]
    rows = sweep_frequency_offsets(
        offsets,
        count=args.count,
        phase_offset=args.phase_offset,
        noise_std=args.noise_std,
        alpha=args.alpha,
        beta=args.beta,
        seed=args.seed,
    )
    if args.output is not None:
        render_offset_sweep_svg(rows, output=args.output)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
