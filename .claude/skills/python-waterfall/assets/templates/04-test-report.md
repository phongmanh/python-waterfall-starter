# Test Report — <Project name>

| Version | Date | Build tested | Status |
|---|---|---|---|
| 1.0 | <YYYY-MM-DD> | <commit / description> | Draft |

## 1. Summary
<!-- 3–5 lines: overall result, open defects, anything not verified. -->

## 2. Results by level
<!-- Paste or summarise actual command output. Never estimate. -->

| Level | Command | Result | Notes |
|---|---|---|---|
| Format + lint | `make lint` | | |
| Types | `make typecheck` | | |
| Unit | `make test-unit` | <n passed / n total> | |
| Integration + E2E | `make test` | <n passed / n total> | external deps used: |
| Coverage | `make coverage` | <total %> | target: |
| Traceability | `make rtm` | <IDs covered / untraced tests> | |
| Dependency audit | `make audit` | | |
| Build + install smoke test | `make build` + <install & run> | | |

## 3. NFR verification

| NFR | Method | Measured | Target | Status |
|---|---|---|---|---|
| NFR-001 | `make check` | | 0 errors | |

<!-- Status: Pass · Fail · Not verified (reason) -->

## 4. Defects

| ID | Severity | Req | Summary | Steps | Status |
|---|---|---|---|---|---|
| | | | | | |

<!-- Severity: Critical / High / Medium / Low (references/testing.md §6). Open Medium/Low defects need explicit user acceptance at the gate. -->

## 5. Requirements Traceability Matrix
<!-- One row per FR and NFR, built from `make rtm` (rtm.json). All Must rows Pass to exit P4. -->

| Req | Priority | Design ref | Implementation | Tests | Status |
|---|---|---|---|---|---|
| FR-001 | Must | | | | |
| NFR-001 | Must | | | | |

## 6. Not verified / limitations
-
