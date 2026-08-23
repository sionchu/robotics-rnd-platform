# Robotics Data Policy

Git synchronizes source code, small configuration examples, schemas, and
manifests. It does not synchronize camera captures, point clouds, bags, trained
weights, large USD/CAD assets, synthetic datasets, caches, or benchmark media.

## Storage model

| Content | Storage | Git content |
|---|---|---|
| Source and small configuration | private repository | files |
| Dataset/model/asset identity | private repository | manifest and checksums |
| Large personal research data | workstation data root or approved private storage | metadata only |
| Company or production data | company-approved systems only | nothing |

Default workstation data roots are examples, not hard-coded application paths:

- Ubuntu and WSL2: `~/robotics-data`
- Windows native: `D:/robotics-data` when the dedicated drive is available

Local paths belong in ignored `config/workstations/local.toml` or environment
variables. A manifest records ownership, license, sensitivity, version, format,
coordinate/scale conventions, content checksums, and approved locations without
embedding personal paths.

## Transfer gate

Before copying data between workstations:

1. establish ownership and redistribution rights;
2. reject company, customer, plant, production, credential, and vendor-license material;
3. generate a content manifest and checksums;
4. use an explicitly approved transfer mechanism;
5. validate the destination checksum and access controls;
6. keep the bytes outside the repository.

Git LFS, DVC with object storage, a private NAS, S3-compatible private storage,
or manual verified copy may be selected when dataset scale and access patterns
justify it. None is installed or enabled by the bootstrap.

See `COMPANY_DATA_BOUNDARY.md`, `data/README.md`, `models/README.md`, and
`assets/README.md`.
