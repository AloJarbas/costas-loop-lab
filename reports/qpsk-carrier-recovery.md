# QPSK carrier-recovery report

These artifacts were generated locally from the same pure-Python code in this repo.

## Demo case

- coarse fourth-power phase estimate: -0.084 rad
- raw RMS decision error after the transient trim: 0.448
- after coarse phase correction only: 0.447
- after Costas tracking: 0.057
- final frequency estimate: +0.02209 rad/sample

## Offset sweep highlights

- best tracked RMS error in this sweep: 0.057 at offset +0.150 rad/sample
- hardest tracked RMS error in this sweep: 0.473 at offset +0.450 rad/sample
- with this exact loop tuning, the tracked cloud stays clean out to about ±0.25 rad/sample before the pull-in range starts to break

## Per-offset summary

- -0.500 rad/sample -> raw 0.451, coarse 0.449, tracked 0.461
- -0.450 rad/sample -> raw 0.448, coarse 0.450, tracked 0.472
- -0.400 rad/sample -> raw 0.449, coarse 0.447, tracked 0.470
- -0.350 rad/sample -> raw 0.446, coarse 0.452, tracked 0.297
- -0.300 rad/sample -> raw 0.450, coarse 0.450, tracked 0.221
- -0.250 rad/sample -> raw 0.449, coarse 0.448, tracked 0.059
- -0.200 rad/sample -> raw 0.447, coarse 0.450, tracked 0.057
- -0.150 rad/sample -> raw 0.448, coarse 0.448, tracked 0.057
- -0.100 rad/sample -> raw 0.448, coarse 0.451, tracked 0.058
- -0.050 rad/sample -> raw 0.453, coarse 0.444, tracked 0.058
- +0.000 rad/sample -> raw 0.707, coarse 0.056, tracked 0.058
- +0.050 rad/sample -> raw 0.450, coarse 0.449, tracked 0.058
- +0.100 rad/sample -> raw 0.447, coarse 0.449, tracked 0.058
- +0.150 rad/sample -> raw 0.449, coarse 0.447, tracked 0.057
- +0.200 rad/sample -> raw 0.447, coarse 0.447, tracked 0.057
- +0.250 rad/sample -> raw 0.448, coarse 0.447, tracked 0.085
- +0.300 rad/sample -> raw 0.446, coarse 0.450, tracked 0.252
- +0.350 rad/sample -> raw 0.450, coarse 0.449, tracked 0.299
- +0.400 rad/sample -> raw 0.447, coarse 0.444, tracked 0.467
- +0.450 rad/sample -> raw 0.449, coarse 0.447, tracked 0.473
- +0.500 rad/sample -> raw 0.450, coarse 0.447, tracked 0.459
