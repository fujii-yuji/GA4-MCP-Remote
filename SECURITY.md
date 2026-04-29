# Security Policy

Thank you for taking the time to investigate the security of `ga4-remote-mcp`. This project is a community-maintained, non-official fork of Google's [google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp). Issues that live in the upstream Google library should be reported to Google. Issues in *this* fork — the HTTP transport, bearer authentication, property allowlist, deploy scripts, and Docker image — are in scope here.

Both English and Japanese reports are welcome.

## Supported versions

Only the latest commit on `main` is supported. Tagged releases (when available) are supported on a best-effort basis; please retest on `main` before filing if you can.

| Version | Supported |
| --- | --- |
| `main` (latest) | ✅ |
| Older tags | Best-effort; retest on `main` first |

## Reporting a vulnerability

**Please do not open a public GitHub issue or pull request for security problems.**

Use one of the following channels:

1. **GitHub Private Vulnerability Reporting (preferred)** — go to the [Security Advisories tab](https://github.com/fujii-yuji/GA4-MCP-Remote/security/advisories/new) and click *Report a vulnerability*. This creates a private advisory that only the maintainer can see.
2. **Email** — `7122427+fujii-yuji@users.noreply.github.com`. Please prefix the subject with `[ga4-remote-mcp security]`. Encrypted mail is not required; the noreply address forwards to the maintainer.

Please include:

- A clear description of the issue and impact (*what does an attacker gain?*).
- Steps to reproduce, or a proof-of-concept request.
- Affected commit hash or tag.
- Whether you intend to disclose publicly, and on what timeline.

## Response timeline (best effort)

This project is maintained by a single person in their spare time, so timelines are best-effort:

| Stage | Target |
| --- | --- |
| Acknowledge receipt | 7 calendar days |
| Initial triage and severity assessment | 14 calendar days |
| Fix or documented mitigation on `main` | 90 calendar days |

If a fix within that window is not feasible we will coordinate with the reporter on a public advisory and a recommended mitigation.

## In scope

- Authentication bypass against `GA4MCP_AUTH_MODE=bearer` (e.g. constant-time-compare regressions, header-parsing tricks).
- Authorization bypass against `GA4MCP_ALLOWED_PROPERTY_IDS` — i.e. a request for a non-allowlisted property reaching Google Analytics.
- Information disclosure in HTTP responses, logs, or error payloads (stack traces, environment variable names, internal paths leaking to clients).
- The deploy script (`scripts/deploy-cloud-run.sh`) doing something materially less secure than its documentation claims.
- The container image (`Dockerfile`) shipping with secrets baked in, running as root, or otherwise widening the attack surface beyond what is documented.
- DNS-rebinding bypass against `GA4MCP_ALLOWED_HOSTS` in production.

## Out of scope

- Vulnerabilities in upstream dependencies — please report those to their maintainers (Google Analytics MCP, MCP Python SDK, Starlette, Pydantic, etc.). Pull requests bumping affected versions are very welcome.
- Issues that require already holding a valid bearer token *and* having a property in the allowlist; a token holder is, by design, trusted within the allowlist.
- Denial-of-service via legitimate traffic volume. Rate limiting and quota tuning are the deployer's responsibility.
- Self-XSS or social-engineering attacks against the maintainer.
- Brute-forcing weak operator-chosen bearer tokens. Use `./scripts/generate-bearer-token.sh` for an entropy-safe default.

## Disclosure

We prefer **coordinated disclosure**. After a fix lands on `main` we will publish a GitHub security advisory crediting the reporter (unless they prefer to stay anonymous), with a CVE assignment if the impact warrants one.

## Hardening checklist for operators

If you deploy this server, also read the [Security Notice](./README.en.md#security-notice) in the README. The short version:

- Use `GA4MCP_AUTH_MODE=bearer` for any deployment reachable from the internet. The server refuses to start with `GA4MCP_ENV=production` + `GA4MCP_AUTH_MODE=none`.
- Generate the bearer token with `./scripts/generate-bearer-token.sh` and store it in Secret Manager (or an equivalent) — never in git.
- Keep `GA4MCP_ALLOWED_PROPERTY_IDS` as small as the integration actually needs.
- Set `GA4MCP_ALLOWED_HOSTS` in production for DNS-rebinding protection.
- Issue per-tenant bearer tokens — separate Cloud Run services, or at minimum separate property allowlists — when stronger isolation is required. A single shared token is equivalent to giving every holder direct access to every property in the allowlist.
