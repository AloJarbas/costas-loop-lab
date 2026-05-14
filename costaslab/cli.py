from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import rms_decision_error, sweep_frequency_offsets
from .loop import run_qpsk_costas_loop
from .render import render_costas_demo_svg, render_offset_sweep_svg
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
