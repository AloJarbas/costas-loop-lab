# Costas Loop Lab

A tiny pure-Python lab for one specific receive-side job: stop a QPSK constellation from spinning after timing is already good enough.

This repo is about the handoff between a coarse carrier estimate and fine Costas-loop tracking.
Not a full modem. Not a grab bag of SDR buzzwords. Just the carrier-recovery part, made visible.

## What is here

- deterministic QPSK symbol generator and carrier-offset channel
- coarse 4th-power phase estimate for QPSK, with the expected quadrant ambiguity
- coarse 4th-power frequency estimate so the front end can remove a real carrier ramp before the loop takes over
- Costas-loop tracker with recorded phase and frequency traces
- generated figures for the baseline demo, the original offset sweep, the acquisition-range map that compares phase-only correction against phase-plus-frequency acquisition, and a new loop-gain tradeoff study that makes pull-in speed fight steady-state calm in one view
- a companion notebook and small tests that check the acquisition chain actually helps

## Gallery

### QPSK carrier-recovery demo

![QPSK carrier-recovery demo](assets/qpsk-costas-demo.png)

### Carrier-offset sweep

![Carrier-offset sweep](assets/qpsk-costas-offset-sweep.png)

### Acquisition range map

![Acquisition range map](assets/qpsk-acquisition-range-map.png)

This is the new spine of the repo. It shows the actual handoff: phase-only coarse correction stays clean only near the center, while a 4th-power frequency estimate keeps the Costas loop inside a much wider pull-in window until the `\pi/4` alias limit shows up.

### Loop-gain tradeoff study

![Loop gain tradeoffs](assets/qpsk-loop-gain-tradeoffs.png)

This follow-up pass answers a different question: once the front end is fixed, how hard should the loop push? The figure separates two regimes instead of mushing them together: on a rough phase-only handoff, hotter gains pull in faster; once coarse frequency help already landed near lock, gentler gains leave a quieter residual.

## Why this repo is worth opening

Carrier recovery often gets explained as if one loop does everything.
That is the mushy version.

The useful version is narrower:

- timing recovery tells you when to sample,
- coarse carrier logic gets the constellation into the right neighborhood, even if quadrant labeling is still ambiguous,
- a Costas loop keeps it from drifting away again.

This repo opens with that split made explicit.
It now ships code, figures, a notebook, a range map that shows exactly when the front end has done enough work for the loop to finish the job, and a gain-tradeoff pass that shows why tuning still matters after acquisition is already in place.

## Quick start

Generate the gallery and reports:

```bash
python3 scripts/generate_gallery.py
```

Run the tests:

```bash
python3 -m unittest discover -s tests
```

Run one demo and emit a JSON summary:

```bash
python3 -m costaslab.cli demo --freq-offset 0.022 --output assets/qpsk-costas-demo.svg
```

Sweep offsets and render the comparison figure:

```bash
python3 -m costaslab.cli sweep --min-offset -0.5 --max-offset 0.5 --steps 21 --output assets/qpsk-costas-offset-sweep.svg
```

Compare phase-only coarse acquisition against the 4th-power frequency-assisted chain:

```bash
python3 -m costaslab.cli acquisition-sweep --min-offset -0.75 --max-offset 0.75 --steps 31 --output assets/qpsk-acquisition-range-map.svg --png-output assets/qpsk-acquisition-range-map.png
```

Compare gentle, default, and aggressive loop gains under one acquisition stress case and one tracking stress case:

```bash
python3 -m costaslab.cli gain-study --output assets/qpsk-loop-gain-tradeoffs.svg --png-output assets/qpsk-loop-gain-tradeoffs.png
```

## Repo layout

- `costaslab/signal.py`: QPSK source and channel rotation
- `costaslab/loop.py`: coarse phase and coarse frequency estimates plus the Costas tracking loop
- `costaslab/analysis.py`: RMS decision-error metrics, offset sweeps, acquisition-mode comparisons, and loop-gain studies
- `costaslab/render.py`: SVG figure generation plus PNG export helper for GitHub previews
- `costaslab/cli.py`: demo, sweep, acquisition-sweep, and gain-study commands
- `scripts/generate_gallery.py`: reproducible asset build
- `reports/qpsk-carrier-recovery.md`: generated baseline summary for the original figures
- `reports/qpsk-frequency-acquisition.md`: generated summary for the new acquisition-range pass
- `reports/qpsk-loop-gain-tradeoffs.md`: generated summary for the speed-versus-jitter pass
- `notebooks/frequency_acquisition_and_pull_in.ipynb`: slower technical walkthrough with equations, caveats, and problems
- `tests/test_costas.py`: verification layer for phase estimation, frequency estimation, pull-in improvements, and the new gain tradeoff

## Scope boundary

This stays in the receive-study lane.
No live-emission procedures, no hardware control, no giant SDR framework.

## Next good moves

- add one sidecar note on why decision-directed tracking alone is fragile when the slicer is still wrong
- add one bounded note on what breaks once the offset crosses the `\pi/4` alias limit of the 4th-power estimate
- sweep one or two coarse-prefix lengths so the repo can show how much work the front end has to do before gain tuning even becomes the main question

That is enough for this repo to open as a real lab instead of a single neat picture.

— Jarbas
