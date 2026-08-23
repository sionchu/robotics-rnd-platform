# OpenUSD Learning Path

1. Create a stage and choose `metersPerUnit` and `upAxis` deliberately.
2. Define stable prim paths and distinguish transforms from geometry.
3. Compose assets using references and payloads instead of copying prim trees.
4. Use variants for reviewed alternatives such as tools or sensor mounts.
5. Record coordinate conventions, scale, ownership, version, and checksums.
6. Keep runtime state separate from asset identity and composition.
7. Validate a generic stage with `usdchecker`, `usdcat`, or `usdview` when available.

Start with `experiments/openusd/create_stage.py`. Isaac Sim may consume OpenUSD,
but Isaac packages are not a dependency of this learning path or the platform
core.

Install the lightweight Python bindings into a project environment with:

```bash
python -m pip install -e ".[openusd]"
```
