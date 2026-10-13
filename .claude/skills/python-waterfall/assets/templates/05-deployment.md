# Deployment — <Project name>

| Version | Date | Status |
|---|---|---|
| 1.0 | <YYYY-MM-DD> | Draft |

## 1. Target
<!-- Keep what applies: PyPI package · `uv tool install` from Git · container image + host · serverless · internal artifact. -->
- **Distribution / host:**
- **Environments:** <production; staging?>
- **URL(s) / package name:**

## 2. Build
- Command: `make build` → `dist/*.whl`, `dist/*.tar.gz` <and/or `docker build -t <image>:<version> .`>
- Python: per `.python-version` / `requires-python`
- Image: <base image, non-root user, size>

## 3. Configuration

| Name | Purpose | Secret? | Where set |
|---|---|---|---|
| `APP_DATABASE_URL` | database connection | Yes | host secret store |

<!-- Secrets come from the environment / secret store only. `.env.example` lists names with dummy values. -->

## 4. Security
- Runs as: <non-root user / sandbox>
- Exposed ports / endpoints: <…>
- HTTP: <TLS termination, CORS origins, security headers, rate limits — or N/A>
- Supply chain: `uv sync --locked`, `make audit` in CI, <trusted publishing to PyPI via OIDC, no long-lived tokens>

## 5. CI/CD
- Workflow: `.github/workflows/ci.yml`: lint → types → tests + coverage → RTM → audit → build
- Release trigger: <manual / tag `v*` / merge to main>
- Last run: <link or local result>

## 6. Release checklist
- [ ] P4 approved; RTM all Must = Pass
- [ ] Version bumped to <x.y.z> (`uv version <x.y.z>`); CHANGELOG.md updated
- [ ] Config/secrets set in the target environment
- [ ] CI green on the release commit
- [ ] Published / deployed (confirmed with the user before running)
- [ ] Smoke test on the released artifact: <commands / endpoints>

## 7. Rollback
<!-- Exact steps: redeploy the previous image tag, `uv tool install <pkg>==<prev>`, yank a PyPI release, DB migration downgrade policy. -->
