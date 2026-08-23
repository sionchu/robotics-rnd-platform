# Vision pose boundary

The v0.2 planar AprilTag solver produces `T_camera_tag`, following the platform
rule `T_target_source`. OpenCV's `rvec/tvec` satisfy
`p_camera = R * p_tag + t`, so they map directly to that transform; they are
converted at the package boundary and never leak into the robotics core.

Tag geometry uses metres. Image observations and reprojection error use pixels.
`SOLVEPNP_IPPE_SQUARE` is the default because its required four-point ordering
matches the documented tag corners: top-left, top-right, bottom-right,
bottom-left. The tag frame is +x right, +y up, +z out of the printed front.

Experiment 003 validated the default against mathematical ground truth and
experiment 005 records its planar ambiguity and noise limitations.
