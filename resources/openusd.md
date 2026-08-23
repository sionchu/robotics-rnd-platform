# OpenUSD

| Field | Value |
|---|---|
| Title | Universal Scene Description documentation |
| Provider | Pixar Animation Studios / OpenUSD project |
| URL | https://openusd.org/release/ |
| Purpose | Scene description, composition, schemas, asset interchange, and tooling |
| Version/release | Documentation 26.08 when checked |
| Date last checked | 2026-08-24 |
| Why it matters | Vendor-neutral Digital Twin asset and composition foundation |
| Learning module | `learning/openusd` |
| Project/application | `experiments/openusd/create_stage.py` |
| Local notes | Windows PATH had no `usdview`/`usdcat`. The project OpenUSD extra uses `usd-core` 26.8; it supplies `pxr` without coupling the experiment to Isaac. The Isaac distribution retains its own extension-scoped OpenUSD runtime. |

Primary follow-up references:

- Tutorials: <https://openusd.org/release/tut_usd_tutorials.html>
- API documentation: <https://openusd.org/release/api/index.html>
- Specifications: <https://openusd.org/release/spec.html>

Keep OpenUSD experiments useful without Isaac Sim. Record `metersPerUnit`,
`upAxis`, prim hierarchy, composition arcs, asset ownership, version, and
checksums.
