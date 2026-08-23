# Conclusion

## Question

Are Pi and laptop replay results equivalent, and what is the CPU cost difference?

## Hypothesis

Detection and pose will agree within declared tolerances on identical decoded
frames, while the laptop will have lower latency than the Pi 4.

## Hardware

`NOT_RUN_HARDWARE_UNAVAILABLE`; Pi CPU/memory and camera dataset are unavailable.

## Software

The v0.2 benchmark schema, v0.2.1 replay pipeline, version capture, and pose-run
comparison metrics are prepared. Pi OpenCV/Python versions remain unknown.

## Method

Prepared same-dataset CPU execution on each host, separate pose-run outputs,
latency/FPS/resource fields, and numerical equivalence comparison.

## Ground truth class

`ALGORITHM_GROUND_TRUTH` for cross-host equivalence; this is not physical pose truth.

## Measurement uncertainty

Uncontrolled process scheduling, thermals, warm-up, library versions, and CPU
load must be recorded. One timing run is not a controlled benchmark.

## Results

`NOT_RUN_HARDWARE_UNAVAILABLE`; measurements are intentionally null.

## Failure cases

Different image decode, OpenCV configuration, dataset, calibration, tag size,
thermal state, or background load invalidates direct comparison.

## Limitations

The study excludes GPU, network streaming, and production real-time guarantees.

## Conclusion

Cross-host performance and equivalence remain unmeasured until one real dataset
can run on the Pi and laptop.

## Decision

`CONTINUE_RESEARCH`
