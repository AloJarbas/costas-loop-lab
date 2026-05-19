# QPSK alias-limit report

This sidecar asks a narrower question than the acquisition-range map: **what actually breaks once the 4th-power frequency estimate crosses its `pi/4` alias limit?**

The useful answer is not just "the estimate wraps." The more interesting failure is that the constellation can still look clean under the old nearest-corner RMS metric even while the symbol labels are wrong.

## The core identity

For a QPSK symbol-rate model, the 4th-power front end sees `4 * freq_offset`.
That means the estimate is unique only while `|freq_offset| < pi/4`.
Once the true offset crosses that boundary, the coarse estimate folds onto the wrong branch and leaves a residual close to `±pi/2` rad/sample after coarse correction.

## Why the old RMS metric can lie

A residual near `pi/2` rad/sample quarter-turns the constellation from one symbol to the next.
Nearest-corner RMS is blind to that if the cloud still lands on QPSK corners.
So the scatter can look clean while a fixed symbol labeling has already collapsed.

## Sweep summary

- freq + phase acquisition keeps best static-quadrant SER near zero out to about ±0.75 rad/sample
- the first false-clean point in this sweep shows up around -0.80 rad/sample: tracked RMS still reads 0.057, but best static-quadrant SER is already 0.75
- at +0.85 rad/sample, the coarse estimate folds to -0.722, leaving a wrapped residual of +1.572 rad/sample while the tracked RMS stays at 0.057

## Per-offset comparison

- -1.000 rad/sample -> estimate +0.571, wrapped residual -1.571, phase-only SER 0.67, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057
- -0.950 rad/sample -> estimate +0.621, wrapped residual -1.571, phase-only SER 0.75, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057
- -0.900 rad/sample -> estimate +0.671, wrapped residual -1.571, phase-only SER 0.75, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057
- -0.850 rad/sample -> estimate +0.721, wrapped residual -1.571, phase-only SER 0.75, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057
- -0.800 rad/sample -> estimate +0.771, wrapped residual -1.571, phase-only SER 0.75, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057
- -0.750 rad/sample -> estimate -0.750, wrapped residual +0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.700 rad/sample -> estimate -0.700, wrapped residual -0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.650 rad/sample -> estimate -0.650, wrapped residual -0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.600 rad/sample -> estimate -0.599, wrapped residual -0.001, phase-only SER 0.74, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.550 rad/sample -> estimate -0.550, wrapped residual +0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.500 rad/sample -> estimate -0.500, wrapped residual -0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.450 rad/sample -> estimate -0.450, wrapped residual +0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.400 rad/sample -> estimate -0.400, wrapped residual -0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.350 rad/sample -> estimate -0.350, wrapped residual +0.000, phase-only SER 0.18, freq-acquired SER 0.00, freq-acquired tracked RMS 0.058
- -0.300 rad/sample -> estimate -0.299, wrapped residual -0.001, phase-only SER 0.08, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.250 rad/sample -> estimate -0.250, wrapped residual +0.000, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.058
- -0.200 rad/sample -> estimate -0.200, wrapped residual -0.000, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.150 rad/sample -> estimate -0.150, wrapped residual +0.000, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- -0.100 rad/sample -> estimate -0.100, wrapped residual -0.000, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.058
- -0.050 rad/sample -> estimate -0.050, wrapped residual +0.000, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.000 rad/sample -> estimate +0.000, wrapped residual -0.000, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.050 rad/sample -> estimate +0.049, wrapped residual +0.001, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.100 rad/sample -> estimate +0.100, wrapped residual -0.000, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.150 rad/sample -> estimate +0.149, wrapped residual +0.001, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.200 rad/sample -> estimate +0.200, wrapped residual -0.000, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.250 rad/sample -> estimate +0.250, wrapped residual +0.000, phase-only SER 0.00, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.300 rad/sample -> estimate +0.300, wrapped residual -0.000, phase-only SER 0.13, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.350 rad/sample -> estimate +0.349, wrapped residual +0.001, phase-only SER 0.19, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.400 rad/sample -> estimate +0.400, wrapped residual -0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.450 rad/sample -> estimate +0.450, wrapped residual +0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.500 rad/sample -> estimate +0.500, wrapped residual -0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.550 rad/sample -> estimate +0.550, wrapped residual +0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.600 rad/sample -> estimate +0.600, wrapped residual +0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.650 rad/sample -> estimate +0.649, wrapped residual +0.001, phase-only SER 0.72, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.700 rad/sample -> estimate +0.700, wrapped residual +0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.750 rad/sample -> estimate +0.750, wrapped residual +0.000, phase-only SER 0.75, freq-acquired SER 0.00, freq-acquired tracked RMS 0.057
- +0.800 rad/sample -> estimate -0.771, wrapped residual +1.571, phase-only SER 0.75, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057
- +0.850 rad/sample -> estimate -0.722, wrapped residual +1.572, phase-only SER 0.75, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057
- +0.900 rad/sample -> estimate -0.671, wrapped residual +1.571, phase-only SER 0.74, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057
- +0.950 rad/sample -> estimate -0.622, wrapped residual +1.572, phase-only SER 0.75, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057
- +1.000 rad/sample -> estimate -0.571, wrapped residual +1.571, phase-only SER 0.67, freq-acquired SER 0.75, freq-acquired tracked RMS 0.057

## Read the artifact

Open `assets/qpsk-alias-limit-map.png` next. The top panel shows the coarse estimate folding onto the wrong branch, the lower-left panel shows why nearest-corner RMS still looks deceptively calm, and the lower-right panel shows the real cliff once you measure symbol agreement after the best static quadrant relabeling.
