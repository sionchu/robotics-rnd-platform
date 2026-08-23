# Conclusion

## Question

How does real tag performance change with viewing angle?

## Hypothesis

Strong perspective and reduced projected tag area will increase corner/pose
jitter and detection dropouts, while near-frontal planar ambiguity may increase
orientation instability.

## Hardware

`NOT_RUN_HARDWARE_UNAVAILABLE`; no angle fixture or sensor is assumed.

## Software

The same v0.2 detector/PnP and v0.2.1 study metrics are prepared.

## Method

Prepared rigid 100-frame sequences at reproducible positive/negative nominal
angles with one fixed distance and camera configuration.

## Ground truth class

`NOMINAL_PHYSICAL_REFERENCE` unless a measured angle tool and uncertainty are
recorded; repeatability remains valid without exact angle truth.

## Measurement uncertainty

Manual protractor/fixture alignment, target flatness, and camera optical-axis
definition limit angular truth.

## Results

`NOT_RUN_HARDWARE_UNAVAILABLE`; measurements are intentionally null.

## Failure cases

Unrepeatable angle placement, target motion, clipped tags, calibration mismatch,
and ambiguity-tainted orientation estimates must be reported.

## Limitations

Nominal manual angles cannot support precise orientation-accuracy claims.

## Conclusion

Angle characterization remains pending physical fixtures and data.

## Decision

`CONTINUE_RESEARCH`
