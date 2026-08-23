# Digital Twin Boundary

Digital Twin work maps a governed physical-asset identity to a versioned digital
asset and optional runtime state. It is an adapter/application concern, never a
dependency of `robotics_rnd.core`.

Future modules may cover asset models, physical-to-digital mapping, state,
synchronization, scenarios, validation, and simulator adapters. Add them only
from a concrete experiment with explicit units, frames, timing, ownership, and
failure behavior. Real robot pose, tool, I/O, alarm, camera, and job-state
mappings remain future work; no production mapping is created by the bootstrap.

OpenUSD is the vendor-neutral asset/composition foundation. Isaac Sim, Gazebo,
and visualization tools remain optional adapters with capability gates.
