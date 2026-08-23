# Isaac Sim on RTX 4070 Ti 12 GB

The Windows desktop contains Isaac Sim `6.0.1-rc.7+release.42383.32955d8d.gl`
under `C:/isaacsim` and
an RTX 4070 Ti with 12,282 MiB VRAM. Isaac Sim 6.0 documents a GeForce RTX 4080
and 16 GB VRAM as the x86_64 minimum. This workstation is therefore below the
official minimum and the platform must remain useful without Isaac Sim.

Use `scripts/windows/check_isaac_readiness.ps1` to record the OS, GPU, VRAM,
driver, installed distribution/version, and availability of the packaged
compatibility checker. The script is read-only unless `-RunCompatibilityChecker`
is explicitly supplied.

On 2026-08-24 the packaged compatibility-checker application completed with exit
code 0. This proves that the checker launched and exited; it does not demonstrate
scene stability, sensor capacity, training capacity, or compliance with the
documented minimum. No Isaac scene workload was launched by the bootstrap.

If a local smoke run is attempted:

1. close competing GPU workloads;
2. start with the smallest packaged scene and conservative resolution;
3. avoid multiple RTX sensors, large textures, and heavy synthetic-data graphs;
4. record peak VRAM, launch stability, driver errors, and scene parameters;
5. stop on repeated OOM or driver-reset behavior;
6. keep Isaac adapters outside `robotics_rnd.core`.

An OOM is a workload/capability result, not a reason to couple the platform core
to Isaac or rewrite the generic architecture.

Official reference: <https://docs.isaacsim.omniverse.nvidia.com/6.0.0/installation/requirements.html>
