**English** | **[日本語](./README.ja.md)**

# ga4-remote-mcp

An **unofficial** Remote MCP (HTTP) server forked from Google's official GA4 MCP ([google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp)).

## What You Can Do

Build **AI chatbots and automated reports** using your GA4 data, combined with tools like Dify, n8n, and Slack.

| Use case | Example |
|---|---|
| **Ask GA4 questions in natural language** | Ask a Dify chatbot "How many sessions last week?" or "Show me traffic sources" and get instant answers |
| **Automate recurring reports** | Build an n8n workflow that posts key metrics to Slack every Monday morning |
| **Analytics without GA4 access** | Team members can ask questions via a Slack bot or internal chat — no GA4 login required |
| **Share across your team** | Set up one server and everyone shares the same AI analytics environment — no per-PC installation |

### How This Differs from the Official MCP

| | Google Official GA4 MCP | ga4-remote-mcp (this project) |
|---|---|---|
| Connection | Local (stdio) | Remote (HTTP) |
| Where you can use it | Only on the PC where it's installed | Anywhere HTTP can reach — Dify, n8n, Slack bots, etc. |
| Team use | Each person installs separately | One server shared by the whole team |
| Automation | Difficult | Schedule with n8n or Dify workflows |

> **stdio (standard I/O) connections are not supported.** This server is HTTP-only.

---

## How to Read This README

**Which sections to read depends on your role.**

| Your role | What to read |
|---|---|
| **User** (marketer, director, etc.)<br>You received a URL and token; you're setting up Dify / n8n | [User Guide](#user-guide) → [Dify Setup](#dify-setup) or [n8n Setup](#n8n-setup) → [Common Issues](#common-issues) |
| **Admin** (engineer)<br>You're deploying the server and issuing URLs and tokens | [Admin Guide](#admin-guide-server-setup) → also review the User Guide |

---

## User Guide

> **An admin (engineer) sets up the server and gives you the info below. The setup steps may look complex, but you can work through them one by one with help from AI assistants like ChatGPT or Gemini.**

### What You Need to Prepare

| What to prepare | Description | Who provides it |
|---|---|---|
| **MCP Server URL** | The connection URL for Dify / n8n. e.g. `https://analytics-mcp.example.com/mcp` | Get from your admin |
| **Bearer Token** | An authentication string (like a password) | Get from your admin |
| **GA4 Property ID** | The numeric ID of your analytics property. e.g. `123456789` | Get from your admin |
| **AI Model API Key** | The AI that powers the chatbot's reasoning. Choose from OpenAI (GPT), Google (Gemini), Anthropic (Claude), etc. | Sign up and obtain yourself (or ask your admin) |

Once you have all four, you're ready to configure Dify or n8n.

> **AI Model API**: In Dify, configure it under "Model Provider"; in n8n, use an LLM node. The AI model decides which tools to call and how to explain results.

---

## Dify Setup

Register via **Tools → MCP → Add MCP Server (HTTP)** in Dify.

> Dify supports HTTP transport MCP servers only. This server is compatible.
> Reference: [Using MCP Tools (Dify official)](https://docs.dify.ai/en/use-dify/build/mcp)

### Steps

1. Go to **Tools → MCP** → **Add MCP Server (HTTP)**
2. Enter the **Server URL** from your admin
   - Example: `https://analytics-mcp.example.com/mcp`
   - Make sure it ends with `/mcp`
3. Fill in **Name** and **Server ID** (don't change the Server ID after creation)
4. **Set the Bearer auth header** (if you received a token from the admin)
   - Name: `Authorization`
   - Value: `Bearer <token>` (one space after `Bearer`, then the token)
   - If you don't see a header field, your Dify version may be too old. This feature was [merged in Sep 2025](https://github.com/langgenius/dify/pull/24760) — consider updating
5. Save and verify that the tool list appears
6. Test calling tools from an agent or workflow

### Agent System Prompt (Recommended)

To improve AI accuracy, set up a **system prompt**:

- Copy-ready prompt: [docs/dify-system-prompt-ga4-mcp-tools.md](./docs/dify-system-prompt-ga4-mcp-tools.md)
- Includes tool names, argument formats, and guardrails to reduce errors and hallucination
- Customize property IDs and organization-specific wording on the Dify side

### Common Dify Errors

#### "Failed to discover OAuth metadata from server"

When Dify receives HTTP 401 from a Bearer mismatch, it tries to discover OAuth metadata. This server uses Bearer only (no OAuth), so this error appears.

**Usually caused by the token not reaching the server correctly.**

1. Check that `Authorization` value is `Bearer <token>` (one space after `Bearer`)
2. Ask your admin to set `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` to prevent Dify from entering the OAuth flow

#### Bearer Returns 403

- Format must be `Bearer ` + one space + token (not `Bearer` alone or token alone)
- When copying from terminal, the trailing `%` is a zsh display artifact — don't include it
- Base64 trailing `=` IS part of the token — don't remove it

---

## n8n Setup

In n8n, connect an **AI Model (Chat Model)** and **MCP Client** to the **AI Agent node**.

![n8n AI Agent + MCP Client setup](./docs/images/n8n-ai-agent-mcp-client.png)

- **MCP Client node** — execute tools as workflow steps
- **MCP Client Tool node** — provide tools to an AI agent

Reference: [MCP Client node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcpClient/) / [MCP Client Tool node](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/)

### Steps

1. Add **MCP Client** or **MCP Client Tool** to your workflow
2. Set **Server URL** to the URL from your admin
   - Example: `https://analytics-mcp.example.com/mcp`
3. **Set Bearer auth**: select Bearer in Credentials and enter the token, or use header auth with `Authorization: Bearer <token>`
4. Verify that the tool list loads and the agent can call GA4 tools
5. On failure, share the HTTP status code and error message with your admin

### Notes

- If connection errors persist, try **updating n8n** to the latest stable version (Streamable HTTP support is evolving)
- Use **MCP Client (Tool) nodes** — don't try to replicate MCP JSON-RPC with the HTTP Request node
- When using an AI agent, you need **AI model API credentials** (OpenAI, Vertex AI, etc.) in addition to MCP

---

## Common Issues

| Symptom | What to check |
|---|---|
| **401 Unauthorized** | Does your Bearer token match the server? Is the format `Authorization: Bearer <token>`? |
| **403** | Token format error (extra newlines, `%`). See [Common Dify Errors](#common-dify-errors) above |
| **Dify: Failed to discover OAuth metadata** | Bearer not reaching the server. See [Common Dify Errors](#common-dify-errors) above |
| **421 or connection refused** | `GA4MCP_ALLOWED_HOSTS` misconfiguration → ask your admin |
| **Tools appear but property is rejected** | Your property ID may not be in the server's allowlist → ask your admin |
| **ready OK but GA4 fails** | Google auth, API enablement, or SA permissions → ask your admin |
| **n8n + Gemini: `zod_to_gemini_parameters` error** | Update n8n and the server. Pass `property_id` as a JSON string `"123456789"` |

---

## Admin Guide (Server Setup)

> This section is for engineers who deploy and operate the server.

### Authentication Overview

| Auth purpose | Where to set | How |
|---|---|---|
| **MCP server → GA4** | MCP server env vars | `GOOGLE_APPLICATION_CREDENTIALS` pointing to a service account JSON. On Cloud Run, prefer Workload Identity / ADC |
| **Dify / n8n → MCP server** | Both server and client | Server: `GA4MCP_AUTH_MODE=bearer` + `GA4MCP_BEARER_TOKEN`. Client: `Authorization: Bearer <same token>`. `GA4MCP_AUTH_MODE=none` for trusted networks only |
| **AI model (LLM)** | Dify / n8n side | API keys in Dify's "Model Provider" or n8n's LLM node (independent from this server) |

### Before Starting the Server

1. **Start the server** and make it reachable via HTTPS (recommended) or HTTP
2. **Set environment variables**. Copy `.env.example` to `.env` and fill in values
   - `GA4MCP_BEARER_TOKEN`: generate with `./scripts/generate-bearer-token.sh` (server won't start with bearer mode and empty token)
   - `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403`: recommended for Dify integration
   - `GA4MCP_ALLOWED_PROPERTY_IDS`: allowed property IDs (comma-separated)
3. **In production, set `GA4MCP_ALLOWED_HOSTS`** to match the Host header sent by clients (DNS rebinding protection; without it, all connections may fail)

### Health Checks

- `GET /health` → success if server is alive
- `GET /ready` → confirms config loaded OK only (does not verify GA4 API connectivity — that's only known on first tool execution)

### Docker Example

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

### Cloud Run Deployment

Full instructions: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) / [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh)

| Category | Requirement |
|---|---|
| **GCP** | Target project, billing enabled, APIs (Cloud Run, Cloud Build, Artifact Registry, Secret Manager) |
| **Runtime SA** | Service account for Cloud Run with GA4 property read access. Prefer Workload Identity / ADC over JSON keys |
| **Env vars** | `GA4MCP_ENV=production`, `GA4MCP_ALLOWED_PROPERTY_IDS`, `GA4MCP_ALLOWED_HOSTS` for production |
| **Bearer (recommended)** | `GA4MCP_AUTH_MODE=bearer` + token in Secret Manager. `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` recommended for Dify |
| **Deploy** | Run `./scripts/deploy-cloud-run.sh` with `GCP_PROJECT_ID`, `GA4MCP_ALLOWED_PROPERTY_IDS`, `CLOUD_RUN_SERVICE_ACCOUNT` (recommended), and `GA4MCP_BEARER_SECRET_NAME` for bearer |

After deployment, get the public URL via `gcloud run services describe` and share `https://<host>/mcp` with users.

---

## Official Documentation Reference

| Item | Details |
|---|---|
| **Dify menu** | **Tools → MCP → Add MCP Server (HTTP)**. Matches this README |
| **Dify & HTTP** | Dify supports HTTP transport MCP only. This server is HTTP-only, so it's compatible |
| **Dify & Bearer** | Custom HTTP headers for MCP were merged Sep 2025. Older Dify versions may lack this feature → update recommended |
| **n8n nodes** | MCP Client / MCP Client Tool documented with Bearer/Header/OAuth2 support |
| **n8n & transport** | Streamable HTTP support is evolving. If connections fail, try a newer stable version |

---

## License & Developer Info

- **License**: Apache License 2.0 ([LICENSE](./LICENSE)). Code derived from [google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp) is noted in [NOTICE](./NOTICE)
- **Cloud Run deployment**: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) / [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh)
- **Local development**: Python 3.10+. `pip install -e ".[dev]"`, then use `pytest` / `ruff` (see `pyproject.toml`)

### Operations Notes

- **Graceful shutdown**: Uvicorn starts with `timeout_graceful_shutdown=30` seconds. For Kubernetes, set `terminationGracePeriodSeconds` to at least 45–60
- **Logging & personal data**: Structured logs may include client IP. Retention, access control, and GDPR compliance are the deployer's responsibility

---

*Improvements are welcome via Issues and Pull Requests.*
