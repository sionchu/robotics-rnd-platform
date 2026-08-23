# External Research Intake

## Purpose

The intake system turns public repositories, SDKs, papers, algorithms,
standards, and vendor documentation into traceable engineering decisions rather
than unreviewed dependencies. It applies to every platform area, not only RB
control.

```text
QUESTION -> SEARCH -> SOURCE TRIAGE -> REPRODUCE -> MEASURE
         -> COMPARE -> DECIDE -> INTEGRATE -> TRACK
```

## 1. Question

Write the engineering question, expected decision, required evidence, and scope
exclusions first. Examples include command completion semantics, IO indexing,
pose units, or whether ROS belongs in a direct driver. A technology name alone
is not a research question.

## 2. Search and source priority

Use sources in this order:

1. Vendor official documentation
2. Vendor official source repositories
3. Upstream library documentation and package metadata
4. Standards and specifications
5. Peer-reviewed papers or authoritative preprints
6. Established open-source projects
7. Issue trackers and discussions
8. Community material only as secondary evidence

Record retrieval date, exact URL, repository commit/tag, document version, and
whether the source is official. Cross-check issue claims against source or
documentation; an issue is evidence of a reported failure, not proof that every
version behaves that way.

## 3. GitHub and repository triage

For each repository inspect README, LICENSE, changelog/releases/tags, build and
package metadata, examples, public API/source, tests/CI, recent commits, and
narrowly relevant issues. Record language/OS/ROS support, dependency footprint,
warnings, maintenance state, and API stability.

Use `scripts/research/intake_repo.sh` for an inspectable shallow clone into
ignored `.external/intake/`. The script never executes external code. For a
one-off review, `/tmp/robotics-rnd-intake/` is preferred. Never use `curl | sh`,
run a third-party setup script before inspection, or commit the clone.

When an authenticated GitHub/MCP connector is available, use it read-only for
repository metadata, commits, releases, files, and issue/PR retrieval. Otherwise
use the official GitHub web/API/CLI and the bounded clone helper. Connector
availability never changes the evidence requirements: exact URL/revision,
license text, primary-source cross-check, retrieval date, and public issue status
must still be recorded. Never grant write scope merely to perform intake.

## 4. License and provenance gate

Identify license text at the reviewed revision, not only a badge. A missing root
license or conflicting package licenses is recorded as `NOASSERTION` until
resolved. This is an engineering provenance inventory, not legal advice.

For influenced implementation record:

- source, tag/commit, and license;
- what was learned;
- whether code was copied;
- what was independently implemented;
- redistribution implications known to the project.

Platform generic logic should normally record `code_copied: false`.

## 5. Reproduction and measurement

Inspect build/test commands before execution. Use an isolated scratch
environment and a bounded minimal reproduction. Do not provide hardware
addresses, credentials, vendor binaries, or production data. Record the exact
environment, input, command, result, limitation, and evidence class:

```text
OFFICIAL_DOC  SOURCE_INSPECTION  ISSUE_EVIDENCE  MOCK_TEST  REPLAY_TEST
LIVE_READ_ONLY  LIVE_NON_MOTION  LIVE_MOTION
```

Mock latency is labelled `SOFTWARE_ONLY` and cannot predict controller latency.

## 6. Compare and decide

Every evaluated technology ends in exactly one status:

- `REFERENCE_ONLY`: useful evidence, no dependency.
- `EVALUATE`: more evidence is required.
- `USE_AS_DEPENDENCY`: a bounded direct dependency is justified.
- `WRAP_WITH_ADAPTER`: useful vendor/framework API must remain isolated.
- `REIMPLEMENT_GENERIC`: independently implement a neutral concept.
- `REJECT`: risk/coupling/license/fitness makes adoption inappropriate.

Record the problem, candidates, evidence, license, maintenance, API stability,
performance evidence, platform coupling, reason, and revisit trigger in
`TECHNOLOGY_DECISIONS.md`.

## 7. Integrate and track

Before integration, define the adapter boundary, optional dependency behavior,
version strategy, contract/architecture tests, and failure behavior. Update the
registries, third-party inventory, experiment link, roadmap, and devlog. Review
records again when a pinned/reviewed version changes or a revisit trigger fires.

## Paper and algorithm routing

Papers use `experiments/_paper_reproduction_template/` and the paper registry.
Algorithms use `research/evaluations/_algorithm_template.md`. Every entry must
connect to a question, platform decision, experiment, or explicit roadmap item;
uncurated reading lists are rejected.

## Intake completion checklist

- Question and exclusions are explicit.
- Official source identity and exact revision are recorded.
- License and provenance are verified or uncertainty is explicit.
- Maintenance, releases, warnings, compatibility, and issues are reviewed.
- Reproduction is bounded and evidence-labelled.
- Decision and revisit trigger are recorded.
- Dependency/adapter and architecture tests are defined.
- No external clone, credential, binary, private address, or production asset is tracked.
