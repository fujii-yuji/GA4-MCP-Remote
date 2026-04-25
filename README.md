**English** | **[日本語](./README.ja.md)**

# ga4-remote-mcp

An **unofficial** Remote MCP (HTTP) server forked from Google's official GA4 MCP ([google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp)).

The official GA4 MCP provides a set of tools that let AI agents interact with Google Analytics naturally — not just raw API calls, but intelligently selected tools for the task at hand. This project wraps those tools as a **Remote MCP over Streamable HTTP**, enabling server-to-server and cross-tool usage that the local-only official MCP cannot support.

As a Remote MCP, it enables use cases like:

- Calling GA4 MCP tools from **Dify**, **n8n**, or other AI workflow platforms
- Invoking GA4 analysis from your own apps (e.g. posting automated reports to Slack)
- Sharing a single GA4 MCP instance across a team — no per-user local setup required

> **stdio (standard I/O) connections are not supported.** This server is designed for HTTP connections from browsers and cloud services only.

## Why Remote MCP?

**By making GA4 MCP remote, AI-powered analytics become easier to use across systems and teams.**

The official GA4 MCP is a local MCP — it must be installed on each PC, making it unsuitable for calling from other systems.

Think: automatically sending AI analysis to Slack every Monday morning, or letting someone without GA4 property access ask "What's the recent trend?" via Slack using natural language.

---

## What You Need to Prepare

**This is a Remote MCP server (externally callable).** You need to set up **hosting** and **authentication**.

### MCP Server URL

Prepare a server accessible from Dify / n8n, start the MCP server there, and determine the URL.

| Step | Details |
|------|---------|
| 1. Hosting | On-premise server, cloud container (Cloud Run recommended), etc. Must be reachable from Dify / n8n. |
| 2. Deploy | Build from source or use the [Dockerfile](./Dockerfile). See [Server Setup](#server-setup-for-admins). |
| 3. URL format | `https://<hostname>/mcp` |

### Where to Configure Authentication

You need separate auth for: client → MCP server, and MCP server → GA4.
You also need LLM API credentials (e.g. **Gemini**, **GPT**) configured in Dify / n8n for the AI agent.

| Auth purpose | Where to set | Example |
|---|---|---|
| **MCP server → GA4** | **MCP server** | `GOOGLE_APPLICATION_CREDENTIALS` env var pointing to a service account JSON. See [.env.example](./.env.example). |
| **Dify / n8n → MCP server** | **Both server and client** with the **same token** | **Server**: `GA4MCP_AUTH_MODE=bearer` + `GA4MCP_BEARER_TOKEN` (env var or `.env` — **never commit**). **Dify**: Add `Authorization` / `Bearer <token>` in the MCP HTTP Header ([instructions](#dify-setup)). **n8n**: Set via MCP Client Tool Credentials ([instructions](#n8n-setup)). Bearer is recommended. Set `GA4MCP_AUTH_MODE=none` only for trusted networks. |

---

## Table of Contents

1. [What You Need to Prepare](#what-you-need-to-prepare)
2. [Prerequisites](#prerequisites) ([Agent LLM API](#agent-llm-api) included)
3. [Server Setup (for Admins)](#server-setup-for-admins) ([Cloud Run Requirements](#cloud-run-deploy-prereqs))
4. [Dify Setup](#dify-setup) ([System Prompt Example](#dify-system-prompt-ga4))
5. [n8n Setup](#n8n-setup)
6. [Official Documentation Reference](#official-documentation-reference)
7. [Common Issues](#common-issues)
8. [License & Developer Info](#license--developer-info)

---

## Prerequisites

If you **don't have a URL yet**, read [What You Need to Prepare](#what-you-need-to-prepare) first.

| Item | Details |
|------|---------|
| **MCP Server URL** | e.g. `https://analytics-mcp.example.com/mcp` (**keep `/mcp` at the end**) |
| **Google Auth** | A **service account** (or equivalent cloud auth) with access to GA4 and Google Analytics Admin API. Must be active in the server environment. |
| **GA4 Property ID** | Numeric ID (e.g. `123456789`). Must match the server's allowlist. |
| **Bearer Token** | Required between Dify/n8n and MCP server. Can be disabled for trusted networks. |
| **Agent LLM API** | The **inference API** used by Dify / n8n for chat/agent (OpenAI, Vertex AI, Anthropic, etc.) |

**Allowlist**: Property IDs not in the server's allowlist will be rejected for report tools. Tell the admin which property IDs you'll use.

### Agent LLM API (Dify / n8n side)

The **LLM** connected to Dify or n8n decides **which tools to call and how to explain results**.

- **LLM credentials**: API key / Vertex auth / endpoint configured in Dify's "Model Provider" or n8n's LLM node — for **inference and planning**.
- Mixed cloud setups (e.g. Vertex AI for Dify's LLM + Cloud Run for this MCP in a different GCP project) are common. Check **billing and IAM** per provider's docs.

---

## Server Setup (for Admins)

Before clients connect from Dify / n8n:

1. **Start the server** and make it reachable via **HTTPS (recommended) or HTTP**.
2. **Set environment variables** for Google auth, allowlist, and **Bearer (recommended for production)**. See [.env.example](./.env.example) and `src/ga4_remote_mcp/config/settings.py`. Generate a token with `./scripts/generate-bearer-token.sh`. Start with `cp .env.example .env` and **fill in `GA4MCP_BEARER_TOKEN`** (server won't start with bearer mode and empty token). **For Dify, `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` is recommended** (`deploy-cloud-run.sh` sets this by default for bearer).
3. **For production DNS rebinding protection**, set **`GA4MCP_ALLOWED_HOSTS`** matching the client's `Host` header. Without it, all connections may fail.

**Health checks (optional)**

- `GET https://<host>/health` → success if server is alive
- `GET https://<host>/ready` → confirms **config loaded OK only**. Does **not** verify GA4 API connectivity (that's only known on first tool execution).

**Docker example** (see `Dockerfile` for details)

```bash
docker build -t ga4-remote-mcp .
docker run --rm -p 8080:8080 \
  -e GA4MCP_ENV=production \
  -e GA4MCP_AUTH_MODE=bearer \
  -e GA4MCP_BEARER_TOKEN=<output of ./scripts/generate-bearer-token.sh> \
  -e GA4MCP_BEARER_FAILURE_HTTP_STATUS=403 \
  -e GA4MCP_ALLOWED_HOSTS=<Host value clients send> \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa.json \
  -v /path/to/sa.json:/secrets/sa.json:ro \
  ga4-remote-mcp
```

### Cloud Run Deploy Prerequisites

Full instructions: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) and [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh). Key requirements:

| Category | Requirement |
|----------|-------------|
| **GCP** | Target **project**, **billing** enabled, APIs (Cloud Run, Cloud Build for `--source`, Artifact Registry, Secret Manager if using secrets). |
| **Runtime SA** | Service account attached to Cloud Run. Must have **GA4 property read access** and Analytics Admin API if needed. Prefer **Workload Identity / ADC** over JSON keys. |
| **Env vars** | `GA4MCP_ENV=production`, `GA4MCP_ALLOWED_PROPERTY_IDS` (comma-separated), `GA4MCP_ALLOWED_HOSTS` for DNS protection. See [.env.example](./.env.example). |
| **Bearer (recommended)** | `GA4MCP_AUTH_MODE=bearer` + token in **Secret Manager**. See [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md). **`GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` recommended for Dify**. |
| **Deploy** | Run `./scripts/deploy-cloud-run.sh` with `GCP_PROJECT_ID`, `GA4MCP_ALLOWED_PROPERTY_IDS`, `CLOUD_RUN_SERVICE_ACCOUNT` (recommended), and `GA4MCP_BEARER_SECRET_NAME` for bearer. |

After deploy, get the **public URL** via console or `gcloud run services describe` and set `https://<host>/mcp` as the MCP Server URL in Dify / n8n.

---

## Dify Setup

In Dify, go to **Tools → MCP** and select **Add MCP Server (HTTP)**. In the Japanese UI, look for "ツール" → "MCP" → "MCP サーバーを追加".

> Dify currently supports **HTTP transport MCP servers only**. This server is compatible.
> Reference: [Using MCP Tools (Dify official)](https://docs.dify.ai/en/use-dify/build/mcp)

### Agent System Prompt (for GA4 analysis)

Adding a system prompt with this MCP's **tool names, argument format (snake_case), and guardrails** reduces errors and hallucination.

- **Copy-ready prompt (Markdown)**: [docs/dify-system-prompt-ga4-mcp-tools.md](./docs/dify-system-prompt-ga4-mcp-tools.md)
  - Covers role, common rules, tool selection, post-analysis guidance, and Dify-specific notes.
  - Customize **property IDs and organization-specific wording** on the Dify side.

### Steps

1. Go to **Tools → MCP** → **Add MCP Server (HTTP)**.
2. Enter the **Server URL**: `https://<your-domain>/mcp`
3. Fill in **Name**, **Server ID** (don't change after creation), etc.
4. If using **Bearer auth** (`GA4MCP_AUTH_MODE=bearer`), add a **custom HTTP header**:
   - Name: `Authorization`
   - Value: `Bearer <token from admin>` (note the space after `Bearer`)
   - The header field in Dify was [merged in Sep 2025](https://github.com/langgenius/dify/pull/24760). If you don't see it, **update Dify**.
5. Verify: tool list appears, and agent/workflow can call tools.
6. On errors, check [Common Issues](#common-issues).

### "Failed to discover OAuth metadata from server" (Dify)

Dify tries to fetch OAuth metadata (`/.well-known/...`) when it receives **HTTP 401**. This server uses **shared Bearer only** (no OAuth), so metadata doesn't exist.

**Root cause is usually "Bearer not reaching / not matching the server"** (typo, trailing space, wrong `Authorization` format). Check:

1. `Authorization` value is **`Bearer ` + token** (one space after `Bearer`, no extra whitespace).
2. Turn **off** dynamic client registration if possible.
3. Set **`GA4MCP_BEARER_FAILURE_HTTP_STATUS=403`** on the server to prevent Dify from entering the OAuth flow.

### Bearer Returns 403 (Dify / Client-Side)

- Value must be **`Bearer ` + space + token** (not `Bearer` alone or token alone).
- Terminal copy: the trailing **`%` is a zsh display artifact**, not part of the token. Base64 trailing **`=` IS part of the token**.
- Re-fetch token with `gcloud secrets versions access ... | tr -d '\n\r'` to strip newlines.
- When testing with `curl`, add **`Accept: application/json, text/event-stream`** (without it you'll get **406**, which looks like a Bearer problem but isn't).

---

## n8n Setup

n8n provides these nodes for external MCP servers:

- **MCP Client node** — execute tools as workflow steps
- **MCP Client Tool node** — provide tools to an AI agent

Both support **Bearer**, **Generic Header**, and **OAuth2** credentials.
Reference: [MCP Client node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcpClient/) / [MCP Client Tool node](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/)

### Steps

1. Add **MCP Client** or **MCP Client Tool** to your workflow.
2. Set **Server URL**: `https://<your-domain>/mcp`
3. For **Bearer auth**: select Bearer in Credentials and enter the token, or use header auth with `Authorization: Bearer <token>`.
4. Verify: tool list loads and agent can call GA4 tools.
5. On failure, share the **HTTP status code** and message with the admin.

### Notes

- This server responds on `/mcp` using **Streamable HTTP** transport. MCP is transitioning from SSE; **keep n8n updated** if connection errors persist.
- Avoid using **HTTP Request node alone** to mimic MCP JSON-RPC — use **MCP Client (Tool) nodes** instead.
- If using an **AI agent with LLM**, you need separate **LLM Credentials/API** (OpenAI, Azure, Vertex, etc.) in addition to MCP. The [Dify system prompt example](./docs/dify-system-prompt-ga4-mcp-tools.md) can be adapted for n8n.

---

## Official Documentation Reference

| Item | Details |
|------|---------|
| **Dify menu** | **Tools → MCP** → **Add MCP Server (HTTP)**. Matches this README. |
| **Dify URL format** | Official examples use `https://api.notion.com/mcp`. The `/mcp` path is correct. |
| **Dify & HTTP** | Dify officially supports "HTTP transport MCP only". This server is HTTP-only, so it's compatible. |
| **Dify & Bearer** | Custom HTTP headers for MCP were **merged Sep 2025**. Older Dify versions may lack this feature → **update recommended**. |
| **n8n nodes** | **MCP Client** / **MCP Client Tool** documented officially with Bearer/Header/OAuth2 support. |
| **n8n & transport** | Streamable HTTP support is evolving in n8n. If connections fail, try a **newer stable version**. |

---

## Common Issues

| Symptom | Check |
|---------|-------|
| **401 Unauthorized** | Bearer matches server? Format is `Authorization: Bearer <token>`? |
| **403 (Dify etc.)** | `Authorization: Bearer …` format, token match, no extra chars (newlines, `%`). See Dify section above. |
| **Dify: Failed to discover OAuth metadata** | See [Dify Setup](#dify-setup). Usually Bearer not reaching server. Try `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403`. |
| **421 or connection refused (production)** | `GA4MCP_ALLOWED_HOSTS` matches the **Host** header sent by the client? (admin issue) |
| **Tools appear but property rejected** | Is the property ID in the server's **allowlist**? |
| **ready OK but GA4 fails** | Google auth, API enablement, and SA permissions are server-side issues. `/ready` doesn't check these. |
| **n8n + Vertex (Gemini): `zod_to_gemini_parameters` / `anyOf` error** | JSON Schema union types cause Gemini conversion failures. This repo uses **string-only `property_id`**. **Update the server** and pass `property_id` as a **JSON string** `"123456789"`. If errors persist for specific tools, temporarily exclude them via **Tools to Include**. |

---

## License & Developer Info

- **License**: Apache License 2.0 ([LICENSE](./LICENSE)). Code derived from [google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp) is noted in [NOTICE](./NOTICE).
- **Cloud Run deployment**: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) and [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh)
- **Local development**: Python 3.10+. `pip install -e ".[dev]"`, then use `pytest` / `ruff` (see `pyproject.toml`).

### Operations Notes (Shutdown & Logging)

- **Graceful shutdown**: Uvicorn is started with **`timeout_graceful_shutdown=30`** (seconds). In-flight requests get up to 30s to complete. For Kubernetes, set **`terminationGracePeriodSeconds`** to at least **45–60** and coordinate with PreStop hooks.
- **Logging & personal data**: Structured logs on the `/mcp` path may include **client IP** (or trusted `X-Forwarded-For`). **Retention, access control, and GDPR compliance are the deployer's responsibility.** Configure masking and retention policies in your logging infrastructure as needed.

---

*Improvements are welcome via Issues and Pull Requests.*
