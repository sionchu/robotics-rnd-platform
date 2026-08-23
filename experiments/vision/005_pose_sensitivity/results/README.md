# Results

- At 0.5 px corner noise, increasing distance from 0.5 m (215 px edge) to 1.6 m
  (67 px edge) increased mean translation error from `0.866` to `9.419 mm` and
  mean orientation error from `0.681` to `3.420 deg`.
- At 0.8 m, increasing corner noise from 0 to 2 px increased mean translation
  error from numerical zero to `9.651 mm`; mean orientation reached `7.810 deg`
  with a `36.600 deg` p95 tail.
- A 2% synthetic intrinsic perturbation produced `18.484 mm` mean translation
  and `5.138 deg` orientation error despite only `0.469 px` reprojection error.
- A near-frontal 5 deg view produced `4.866 deg` mean orientation error at 0.5
  px noise versus `0.316 deg` at 60 deg, demonstrating planar ambiguity.
- At approximately 76 px tag edge and image-noise standard deviation 8, blur
  sigma 5 reduced detection/PnP success from `100%` to `25%`.

Complete rows are in `sensitivity.csv` and `metrics.json`.
