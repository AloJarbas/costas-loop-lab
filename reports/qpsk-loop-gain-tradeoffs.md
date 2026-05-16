# QPSK loop-gain tradeoff report

This pass keeps the same coarse acquisition logic but changes the Costas loop gains to show the real compromise: hotter gains can pull a rough handoff into place faster, but they leave a noisier residual once the front end has already done its job.

## Stress cases

- acquisition panel: phase-only coarse correction, `freq_offset = +0.35 rad/sample`, `noise_std = 0.04`
- tracking panel: frequency-plus-phase coarse correction, `freq_offset = +0.35 rad/sample`, `noise_std = 0.08`

## Loop settings

- **gentle** (`alpha=0.05`, `beta=0.0015`): phase-only settle = no clean settle in 1500 symbols; tracking tail RMS = 0.113; mean |Costas error| = 0.093; frequency jitter = 0.47 mrad/sample
- **default** (`alpha=0.11`, `beta=0.0045`): phase-only settle = 422; tracking tail RMS = 0.114; mean |Costas error| = 0.095; frequency jitter = 0.98 mrad/sample
- **aggressive** (`alpha=0.20`, `beta=0.0120`): phase-only settle = 88; tracking tail RMS = 0.117; mean |Costas error| = 0.099; frequency jitter = 2.04 mrad/sample

## Read the result

The figure splits the problem into two honest regimes instead of pretending one gain setting is simply better:

- on the harder phase-only handoff, aggressive gains reach the decision-directed sweet spot much sooner
- once the coarse frequency estimate has already done that work, gentler gains leave a quieter steady-state trace

That is the real tuning trade: rescue margin versus post-lock calm.
