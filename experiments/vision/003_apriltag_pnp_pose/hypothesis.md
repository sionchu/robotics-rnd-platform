# Question and Hypothesis

## Question

Can four exact tag corners recover known object-to-camera poses and map them to
`T_camera_tag` without an inverse-direction error?

## Hypothesis

Four no-noise cases will have translation error below `1e-8 m`, orientation
error below `1e-5 deg`, and mean reprojection below `1e-7 px`; every result will
be named `T_camera_tag`.
