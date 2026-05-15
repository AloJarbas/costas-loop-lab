# QPSK frequency acquisition report

This pass adds a wider receive-chain split: a 4th-power front end now estimates both coarse phase and coarse frequency before the Costas loop takes over.

## Why this matters

Phase-only coarse correction can clean up a static rotation, but it leaves the loop to eat the whole residual frequency ramp by itself.
That is fine near the center. It is much less fine once the offset gets large enough that the loop is always chasing.

The useful boundary here is roughly `|freq_offset| < pi/4`, because the 4th-power frequency estimate wraps beyond that alias limit.

## Sweep summary

- phase-only coarse + Costas stays clean to about ±0.25 rad/sample in this sweep
- freq + phase coarse + Costas stays clean to about ±0.75 rad/sample
- freq + phase coarse + Costas stays at least marginal to about ±0.75 rad/sample

## Per-offset comparison

- -0.750 rad/sample -> phase-only tracked 0.425, freq-acquired tracked 0.058, coarse freq estimate -0.7503
- -0.700 rad/sample -> phase-only tracked 0.426, freq-acquired tracked 0.057, coarse freq estimate -0.6995
- -0.650 rad/sample -> phase-only tracked 0.453, freq-acquired tracked 0.058, coarse freq estimate -0.6499
- -0.600 rad/sample -> phase-only tracked 0.466, freq-acquired tracked 0.057, coarse freq estimate -0.5994
- -0.550 rad/sample -> phase-only tracked 0.459, freq-acquired tracked 0.058, coarse freq estimate -0.5503
- -0.500 rad/sample -> phase-only tracked 0.461, freq-acquired tracked 0.058, coarse freq estimate -0.4998
- -0.450 rad/sample -> phase-only tracked 0.472, freq-acquired tracked 0.058, coarse freq estimate -0.4504
- -0.400 rad/sample -> phase-only tracked 0.470, freq-acquired tracked 0.058, coarse freq estimate -0.3996
- -0.350 rad/sample -> phase-only tracked 0.297, freq-acquired tracked 0.058, coarse freq estimate -0.3503
- -0.300 rad/sample -> phase-only tracked 0.221, freq-acquired tracked 0.058, coarse freq estimate -0.2994
- -0.250 rad/sample -> phase-only tracked 0.059, freq-acquired tracked 0.058, coarse freq estimate -0.2504
- -0.200 rad/sample -> phase-only tracked 0.057, freq-acquired tracked 0.057, coarse freq estimate -0.1997
- -0.150 rad/sample -> phase-only tracked 0.057, freq-acquired tracked 0.057, coarse freq estimate -0.1502
- -0.100 rad/sample -> phase-only tracked 0.058, freq-acquired tracked 0.058, coarse freq estimate -0.0996
- -0.050 rad/sample -> phase-only tracked 0.058, freq-acquired tracked 0.058, coarse freq estimate -0.0505
- +0.000 rad/sample -> phase-only tracked 0.058, freq-acquired tracked 0.058, coarse freq estimate +0.0001
- +0.050 rad/sample -> phase-only tracked 0.058, freq-acquired tracked 0.058, coarse freq estimate +0.0495
- +0.100 rad/sample -> phase-only tracked 0.058, freq-acquired tracked 0.058, coarse freq estimate +0.1002
- +0.150 rad/sample -> phase-only tracked 0.057, freq-acquired tracked 0.057, coarse freq estimate +0.1493
- +0.200 rad/sample -> phase-only tracked 0.057, freq-acquired tracked 0.057, coarse freq estimate +0.2002
- +0.250 rad/sample -> phase-only tracked 0.085, freq-acquired tracked 0.057, coarse freq estimate +0.2498
- +0.300 rad/sample -> phase-only tracked 0.252, freq-acquired tracked 0.058, coarse freq estimate +0.3001
- +0.350 rad/sample -> phase-only tracked 0.299, freq-acquired tracked 0.057, coarse freq estimate +0.3493
- +0.400 rad/sample -> phase-only tracked 0.467, freq-acquired tracked 0.057, coarse freq estimate +0.4003
- +0.450 rad/sample -> phase-only tracked 0.473, freq-acquired tracked 0.057, coarse freq estimate +0.4497
- +0.500 rad/sample -> phase-only tracked 0.459, freq-acquired tracked 0.058, coarse freq estimate +0.5002
- +0.550 rad/sample -> phase-only tracked 0.460, freq-acquired tracked 0.057, coarse freq estimate +0.5495
- +0.600 rad/sample -> phase-only tracked 0.471, freq-acquired tracked 0.057, coarse freq estimate +0.5997
- +0.650 rad/sample -> phase-only tracked 0.476, freq-acquired tracked 0.057, coarse freq estimate +0.6492
- +0.700 rad/sample -> phase-only tracked 0.426, freq-acquired tracked 0.058, coarse freq estimate +0.6995
- +0.750 rad/sample -> phase-only tracked 0.428, freq-acquired tracked 0.058, coarse freq estimate +0.7497

## Read the artifact

Open `assets/qpsk-acquisition-range-map.svg` or the 300 dpi PNG next. The top plot shows the handoff improvement directly, the lower-left panel shows where the coarse estimate stays honest, and the regime bars make the pull-in range visible instead of leaving it as folklore.
