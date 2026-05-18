# QPSK coarse-prefix budget report

This pass asks a narrower front-end question: **once a 4th-power frequency estimate is already inside the Costas loop's pull-in range, how many prefix symbols still matter?**

The setup stays fixed on purpose:

- carrier offset: `+0.62 rad/sample`
- same phase offset and loop gains as the rest of the repo
- only the coarse-prefix length and channel noise change
- each grid point averages 24 Monte Carlo trials

## Main takeaway

Longer prefixes keep improving the coarse estimate, but the tracked output flattens much sooner.
In this symbol-rate model, the front end gets materially more honest all the way out to 96 or 128 symbols, yet the loop behaves almost the same once the handoff already lands inside its comfort zone.

That means extra prefix length buys estimator honesty before it buys visible post-lock improvement.

## Selected checkpoints

- noise std 0.02: mean |coarse freq error| drops from 3.1 mrad at prefix 8 to 0.6 mrad at prefix 32 and 0.2 mrad at prefix 128; tracked RMS only moves from 0.0290 to 0.0290; 5 mrad threshold = prefix 8
- noise std 0.04: mean |coarse freq error| drops from 6.7 mrad at prefix 8 to 1.5 mrad at prefix 32 and 0.7 mrad at prefix 128; tracked RMS only moves from 0.0580 to 0.0580; 5 mrad threshold = prefix 12
- noise std 0.06: mean |coarse freq error| drops from 11.2 mrad at prefix 8 to 2.8 mrad at prefix 32 and 1.4 mrad at prefix 128; tracked RMS only moves from 0.0871 to 0.0871; 5 mrad threshold = prefix 24
- noise std 0.08: mean |coarse freq error| drops from 16.8 mrad at prefix 8 to 4.7 mrad at prefix 32 and 2.6 mrad at prefix 128; tracked RMS only moves from 0.1161 to 0.1161; 5 mrad threshold = prefix 32
- noise std 0.10: mean |coarse freq error| drops from 24.0 mrad at prefix 8 to 7.4 mrad at prefix 32 and 4.1 mrad at prefix 128; tracked RMS only moves from 0.1451 to 0.1451; 5 mrad threshold = prefix 96

## How to read the artifact

The top panel of `assets/qpsk-coarse-prefix-budget.png` shows the honest front-end story: more symbols make the 4th-power estimate noticeably less noisy, especially once the channel noise rises.
The lower-left panel shows the practical receive-chain story: after the loop takes over, most of that front-end improvement barely changes the post-lock RMS unless the prefix was already too short.

That is the point of the card. A bigger prefix is not useless. It is just solving a different problem once the handoff is already decent.
