# Camera and AprilTag Conventions

## Units and image coordinates

- Image coordinates and focal/principal-point values: pixels.
- 3D object points, translations, checkerboard squares, and tag sizes: metres.
- Internal angles: radians. Degrees appear only in reports.
- Images use NumPy `(height, width[, channels])`; `ImageSize` stores explicit
  `(width_px, height_px)` fields.
- OpenCV image origin is top-left, +u points right, and +v points down.

No millimetre conversion is implicit anywhere in the vision package.

## Camera model

The pinhole intrinsic matrix is:

```text
K = [fx  0 cx]
    [ 0 fy cy]
    [ 0  0  1]
```

`DistortionCoefficients` follows OpenCV order:
`(k1, k2, p1, p2[, k3[, k4, k5, k6[, s1, s2, s3, s4[, tau_x, tau_y]]]])`.
The v0.2 experiment estimates five coefficients and fixes `k3` to zero.

Calibration observations store `N x 3` object points in metres and matching
`N x 2` image points in pixels. JSON persistence records image size, target
geometry, method, distortion model, timestamp, software version, and metrics.

## Frames and OpenCV pose conversion

The camera frame follows OpenCV: +x right, +y down, +z forward. The AprilTag
frame is centred on the printed square: +x right, +y up, +z out of the printed
front. A physically front-facing tag therefore has an approximately 180-degree
rotation about camera x.

OpenCV PnP returns `rvec` and `tvec` such that:

```text
p_camera = Rodrigues(rvec) @ p_tag + tvec
```

This is object-to-camera and maps directly to platform `T_camera_tag`, because
`T_target_source` maps source coordinates into target. It is not inverted.
`tvec` is interpreted in metres only because tag object points are supplied in
metres.

Public quaternions are normalized `(x, y, z, w)`. Rodrigues vectors and raw
OpenCV arrays are converted at the vision boundary and do not enter
`robotics_rnd.core`.

## Corner order

AprilTag corners are always:

```text
top-left -> top-right -> bottom-right -> bottom-left
```

For `SOLVEPNP_IPPE_SQUARE`, corresponding tag-frame points are:

```text
[-L/2, +L/2, 0]
[+L/2, +L/2, 0]
[+L/2, -L/2, 0]
[-L/2, -L/2, 0]
```

Tests reject reversed corner winding, mismatched image sizes/frames, invalid tag
size, and reversed transform composition.
