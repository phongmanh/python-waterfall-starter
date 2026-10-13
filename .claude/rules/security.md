# Security & secrets (always applies)

- Never read, print, copy or commit secrets: `.env` / `.env.*` (except `.env.example`), `*.pem`, `*.key`, SSH keys, `credentials.json`, service-account files, `~/.pypirc`, `~/.netrc`. The permission rules and the phase-gate hook block them. If a task needs a secret value, ask the user to set it in the environment themselves.
- Secrets reach the program only through environment variables or a secret manager, read by `Settings` as `SecretStr`. Never hard-code them, give them realistic defaults, log them, or put them in test fixtures. `.env.example` holds names and dummy values only.
- Validate all untrusted input at the boundary (CLI args, HTTP, env, files, queue messages, third-party responses) with Pydantic or the framework.
- No `shell=True` with interpolated input, no string-built SQL, no `eval`/`exec`/`pickle`/`yaml.load` on untrusted data. Every network call has a timeout.
- Keep ruff's bandit rules (`S`) clean. Suppress a finding only with a specific code and a written reason, logged in the implementation log.
- Dependencies: add only what the design names or an approved CR adds. Keep `uv.lock` committed and `make audit` clean.
- Outward-facing actions (push, publish, deploy, creating remote resources, setting CI secrets) need the user's confirmation every time.
