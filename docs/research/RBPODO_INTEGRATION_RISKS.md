# rbpodo Integration Risks

Reviewed against rbpodo 0.16.14 at `f6ef41adf629` on 2026-08-23. All mitigation
tests are mock/source verified; no live controller evidence exists.

| Risk | Evidence | Possible failure | Adapter mitigation | Test | Remaining uncertainty |
|---|---|---|---|---|---|
| ACK confused with completion | Official README/getting-started/source | Application reports success while motion continues | Map ACK to `ACCEPTED`; require finish/state evidence for `COMPLETED` | Command lifecycle and fake backend contract | Exact controller event ordering |
| Stale buffered event | README, changelog 0.10.2, PR 6, source | Previous finish event completes a new command | Flush at serialized command boundary; platform command IDs; conservative ambiguity | Experiment 014 stale-response scenario | Flush behavior across controller versions |
| Broadcast multi-client errors | Official README wait warning | Unrelated client error aborts current wait | Single-client assumption; bounded diagnostic; do not equate wait error with motion truth | Unexpected/duplicate response fault cases | Controller behavior with several clients |
| Wait timeout | Source `ReturnType` and timeouts | Motion truth unavailable | Transition to `TIMED_OUT` before acceptance or `UNKNOWN` after accepted/started | Timeout and reconnect tests | Whether motion continues after host timeout |
| Connection loss during motion | Source socket design; ROS issue 6 | Silent completion or automatic replay | Mark pending command `UNKNOWN`; degrade connection; no resume; motion lock after reconnect | Experiment 015 | Controller-side motion/state after link loss |
| Constructor has no connect timeout | Socket source | Application thread blocks at OS connect policy | Document limitation; live backend is explicit/optional; never construct on import; future process isolation if needed | Optional-import and fake connect-timeout tests | Host TCP timeout duration |
| Reconnect unsupported in vendor object | Source API | Stale sockets/state after loss | Recreate backend, re-query state, invalidate commands, require acknowledgment | Reconnect/resync test | Actual controller reconnection limits |
| Thread safety unspecified | No official guarantee; mutable collector/socket | Interleaved sends/responses | Serialize all backend calls; no background vendor call fan-out | Concurrent call serialization test | Vendor internal thread guarantees |
| TCP framing concern | Open issue 20, no resolution | Partial command or parse error | Never reimplement protocol; bound error as communication fault; keep library version recorded | Unexpected-response injection | Whether issue is controller/library/network specific |
| Library/controller version drift | README warning, issue 7, rapid releases | Parsing errors or missing fields | Version range/feature detection, compatibility matrix, LEVEL 1 version capture | Missing-capability fake | Supported firmware matrix unavailable |
| Python/NumPy binding compatibility | Issue 15 and pyproject | Corrupt/duplicated array exposure | Copy and validate exact finite shapes; record versions | Bad-array and missing-field tests | Other ABI combinations |
| IO/model variation | Official model-specific tool docs | Wrong channel semantics | Promote box digital 0–15 only; capability-gate tool/analog IO | Experiment 016 | Model/controller-specific expansion IO |
| Euler ZYX ambiguity | Official rbpodo type docs | Wrong orientation or discontinuous Euler tuple | Convert only in mapping; compare matrices; reject frames/non-finite inputs | Experiment 013 | Physical coordinate alignment |
| Software stop mistaken for E-stop | Official external-script guidance | Unsafe reliance on application command | Name `CONTROLLED_STOP`; document non-safety status; omit emergency-stop API | Read-only/motion lock tests | Actual deceleration/stop response |
| Vendor diagnostic leakage | Response/source fields | Sensitive raw messages/addresses in logs | Bounded sanitized metadata and key-based redaction | Journal redaction test | Novel sensitive content in free text |

## Compatibility strategy

The live backend checks the installed distribution version, discovers the exact
method surface it needs, and rejects unsupported/missing functionality without
breaking mock/replay or read-only state use. No vendor object appears in public
annotations. Default CI never installs rbpodo.
