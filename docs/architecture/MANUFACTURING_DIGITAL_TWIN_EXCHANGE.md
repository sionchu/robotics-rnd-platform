# Future Manufacturing Digital Twin Exchange

## Repository boundary

The future `manufacturing-digital-twin-rnd` repository will remain a separate
consumer and producer of the Workcell Exchange Schema. It must not copy this
repository's source tree, vendor adapters, Git history, private data, or runtime
environment. Integration should use a reviewed version/tag of the Python package
and the matching `workcell-exchange-v1.schema.json` artifact.

## Consumption flow

1. Receive a JSON or YAML manifest plus its declared schema version.
2. Validate the document against the matching JSON Schema.
3. Parse it with `robotics_rnd.exchange.workcell`, which validates the frame tree
   through `robotics_rnd.core.geometry.Transform`.
4. Resolve required `T_target_source` transforms by frame role.
5. Map those transforms into the digital-twin repository's scene or application
   layer. Simulator, renderer, CAD, and manufacturing-domain objects remain on
   that repository's side of the boundary.
6. Keep referenced/generated assets and production data outside this platform's
   Git repository under their own reviewed storage policy.

The consumer must reject unknown roles, duplicate edges, non-normalized
quaternions, unsupported major versions, and unit/convention mismatches. It must
not infer millimetres, Euler-angle ordering, WXYZ ordering, or transform
direction.

## Production flow

When `manufacturing-digital-twin-rnd` exports a workcell update, it should:

1. convert its internal transforms into metres and normalized XYZW quaternions;
2. emit explicit frame IDs, roles, parents, and `T_parent_child` records;
3. retain `T_target_source` direction in names and values;
4. validate the output against the schema and parser;
5. round-trip the document through JSON before exchange;
6. optionally generate a generic USD stage as an interoperability artifact; and
7. record provenance and timestamps in its own repository or data catalog, not
   by adding private operational metadata to this generic schema.

## Ownership

`robotics-rnd-platform` owns units, frame semantics, schema compatibility,
transform validation, and the generic OpenUSD mapping. The future digital-twin
repository owns manufacturing concepts, process behavior, simulation, scene
assets, and product-specific import/export orchestration. Changes affecting both
repositories require a schema version decision and contract tests on each side.
