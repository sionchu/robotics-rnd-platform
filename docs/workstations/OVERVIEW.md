# Dual-Workstation Overview

The platform uses one private GitHub repository and three independent clones:

```text
GitHub origin/main
├── Ubuntu laptop clone       real robotics and ROS 2 lab
├── Windows native clone      GPU, OpenUSD, Digital Twin, and Windows SDK lab
└── Windows WSL2 clone        Linux build and CUDA-support environment
```

Git is the synchronization boundary for code and small configuration. Dataset,
model, capture, and large asset bytes use the governed external-data workflow in
`docs/data/DATA_POLICY.md`.

Windows and WSL never share a virtual environment or build directory. The WSL
clone lives in the Linux filesystem, not under `/mnt/c`. Real RB robot motion,
real industrial camera acquisition, and field network validation remain
Ubuntu-first and require an explicit safety procedure.

Read `SYNC_WORKFLOW.md`, `CAPABILITY_MATRIX.md`, and the workstation-specific
page before starting a task.
