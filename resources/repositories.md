# Official Repository and Language Hubs

| Title | Provider | URL | Purpose | Version/release | Verified | Learning / application | Local notes |
|---|---|---|---|---|---|---|---|
| Python 3.12 docs | Python Software Foundation | https://docs.python.org/3.12/ | Language, standard library, packaging baseline | 3.12 | 2026-08-23 | `learning/02_python`; platform | Primary Python version |
| ISO C++ getting started | Standard C++ Foundation | https://isocpp.org/get-started | Modern C++ learning/source hub | C++17 platform baseline | 2026-08-23 | `learning/03_cpp`; C++ core | Prefer modern value/RAII practices |
| GitHub Git guide | GitHub | https://docs.github.com/en/get-started/learning-to-code/getting-started-with-git | Git/GitHub onboarding and identity workflow | Current | 2026-08-23 | `learning/01_git`; repository maintenance | Platform remote must remain private |
| NumPy docs | NumPy project | https://numpy.org/doc/stable/ | Array/numerical API used by Python core | Pin environment | 2026-08-23 | Python/math/vision | Public models remain simple value types |
| CMake docs | Kitware | https://cmake.org/documentation/ | C++ configure/build/test reference | CMake 3.28 locally | 2026-08-23 | `learning/03_cpp`; `cpp/` | ROS-independent C++ baseline |

Before adding a repository as a dependency, review release cadence, license,
maintenance, transitive dependencies, platform support, and whether an adapter
can contain it.
