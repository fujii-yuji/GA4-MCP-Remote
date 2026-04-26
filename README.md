English | [日本語](./README.ja.md)

# ga4-remote-mcp

An unofficial Remote MCP (HTTP) server forked from Google's official GA4 MCP ([google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp)).


## What You Can Do

Build AI chatbots and automated reports using your GA4 data, combined with tools like Dify, n8n, and Slack.

| What you can do | Example |
| --- | --- |
| Share across your team | Set up one server and everyone shares the same AI analytics environment — no per-PC installation |
| Automate recurring reports | Build a workflow that posts "AI-generated weekly comparison report" to Slack |
| Analytics without GA4 access | Team members can ask questions via a Slack bot or internal chat — no GA4 login required. You can also mask sensitive data via system prompts |
| Ask GA4 questions in natural language | Just ask "Analyze by traffic source" or "Analyze the past 6 months excluding seasonal trends" and get answers |


### How This Differs from the Official MCP

| | Google Official GA4 MCP | ga4-remote-mcp (this project) |
| --- | --- | --- |
| Connection | Local (stdio) | Remote (HTTP) |
| Where you can use it | Runs on the PC where it's installed | Anywhere HTTP can reach — Dify, n8n, Slack bots, etc. |
| Team use | Each person installs separately | One server shared by the whole team |
| Automation | Possible within the installed PC | Runs from the cloud, so you can use it with n8n or Dify workflows |

> stdio (standard I/O) connections are not supported. This server is HTTP-only.


---

## How to Read This README

Which sections to read depends on your role.

| Your role | What to read |
| --- | --- |
| User (marketer, director, etc.) You received a URL and token; you're setting up Dify / n8n | [User Guide](#user-guide) → [Dify Setup](#dify-setup) or [n8n Setup](#n8n-setup) |
| Admin (engineer) You're deploying the server and issuing URLs and tokens | [Admin Guide](#admin-guide-server-setup) → also review the User Guide |


---

## User Guide

> An admin (engineer) sets up the server and gives you the info below. The setup steps may look complex, but you can work through them one by one with help from AI assistants like ChatGPT or Gemini.

### What You Need to Prepare

| What to prepare | Description | Who provides it |
| --- | --- | --- |
| MCP Server URL | The connection URL for Dify / n8n. | Get from your admin |
| Bearer Token | An authentication string (like a password) | Get from your admin |
| GA4 Property ID | The numeric ID of your analytics property. | Check in GA4 |
| AI Model API Key | You need an AI available via API to analyze data retrieved from MCP. Prepare whichever is easiest to use — Gemini, Claude, GPT, etc. | Sign up and obtain yourself, or ask your admin. Free APIs may use your data for training, so they are not recommended for business use. |


---

## Dify Setup

Register via Tools → MCP → Add MCP Server (HTTP) in Dify.

![Dify — Add MCP Server (HTTP)](./docs/images/dify-add-mcp-server.png)

### Steps

1. In Dify's Tools → MCP → select Add MCP Server (HTTP)
2. Enter the Server URL from your admin
3. Fill in Name and Server ID (you can freely choose the name, but don't change the Server ID after creation)
4. Select Auth → Header and set the following:
   - Name: `Authorization`
   - Value: `Bearer <token>` (the string `Bearer` followed by one space before the token value)
5. Save and verify that the tool list appears
6. Try calling tools from a chat or workflow

### Agent System Prompt (Recommended)

To improve AI accuracy, set up a system prompt.

- System prompt example: [docs/dify-system-prompt-ga4-mcp-tools.md](./docs/dify-system-prompt-ga4-mcp-tools.md)
- You can customize it freely, but use the example as a reference.
- We recommend adding information specific to your property or organization so the AI can answer relevant questions.

### Common Dify Errors

#### "Failed to discover OAuth metadata from server"

Check that `Authorization` value is `Bearer <token>`.

#### Bearer Returns 403

- Check that `Authorization` value is `Bearer <token>`
- If there's a `%` at the end, it's a copy error. The trailing `%` is not part of the token
- The trailing `=` IS part of the token — don't remove it


---

## n8n Setup

![n8n AI Agent + MCP Client setup](./docs/images/n8n-ai-agent-mcp-client.png)

Node names and settings may change over time — check the latest information.

### Steps

1. Set up Credentials with Bearer and enter the token.
2. Set up Credentials for the AI API connection.
3. Connect MCP Client and an AI model (Chat Model) to an AI Agent node and place them in the workflow.
4. Configure MCP Client with Credentials from step 1, and enter the Server URL from your admin.
5. Configure the AI model (Chat Model) with Credentials from step 2.
6. Set up user prompt and system prompt on the AI Agent node.
   System prompt example: [docs/dify-system-prompt-ga4-mcp-tools.md](./docs/dify-system-prompt-ga4-mcp-tools.md)
7. Configure other nodes as needed (e.g., receiving input from Slack) and test.


---

## Admin Guide (Server Setup)

> This section is for engineers who deploy and operate the server.
> If you're a marketer or PdM rather than an engineer, you can still accomplish this by having AI read this content and collaborating with it. No specialized knowledge is required.

### Authentication Overview

| Auth purpose | Where to set | How |
| --- | --- | --- |
| MCP server → GA4 | MCP server env vars | `GOOGLE_APPLICATION_CREDENTIALS` pointing to a service account JSON. On Cloud Run, prefer Workload Identity / ADC |
| Dify / n8n → MCP server | Both server and client | Server: `GA4MCP_AUTH_MODE=bearer` + `GA4MCP_BEARER_TOKEN`. Client: `Authorization: Bearer <same token>`. |
| AI model (LLM) | Dify / n8n side | API keys in Dify's "Model Provider" or n8n's LLM node |

### Before Starting the Server

1. Start the server and make it reachable via HTTPS (recommended) or HTTP
2. Set environment variables.
   - `GA4MCP_BEARER_TOKEN`: generate with `./scripts/generate-bearer-token.sh` (server won't start with bearer mode and empty token)
   - `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403`: recommended for Dify integration
   - `GA4MCP_ALLOWED_PROPERTY_IDS`: allowed property IDs (comma-separated)
3. In production, set `GA4MCP_ALLOWED_HOSTS` (DNS rebinding protection; without it, all connections may fail)

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

### Cloud Run Example

Full instructions: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) / [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh)

| Category | Requirement |
| --- | --- |
| GCP | Target project, billing enabled, APIs (Cloud Run, Cloud Build, Artifact Registry, Secret Manager) |
| Runtime SA | Service account for Cloud Run with GA4 property read access. Prefer Workload Identity / ADC over JSON keys |
| Env vars | `GA4MCP_ENV=production`, `GA4MCP_ALLOWED_PROPERTY_IDS`, `GA4MCP_ALLOWED_HOSTS` for production |
| Bearer (recommended) | `GA4MCP_AUTH_MODE=bearer` + token in Secret Manager. `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` recommended for Dify |
| Deploy | Run `./scripts/deploy-cloud-run.sh` with `GCP_PROJECT_ID`, `GA4MCP_ALLOWED_PROPERTY_IDS`, `CLOUD_RUN_SERVICE_ACCOUNT` (recommended), and `GA4MCP_BEARER_SECRET_NAME` for bearer |

After deployment, get the public URL via `gcloud run services describe` and share `https://<host>/mcp` with users.


---

## License & Developer Info

- License: Apache License 2.0 ([LICENSE](./LICENSE)). Code derived from [google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp) is noted in [NOTICE](./NOTICE)
- Cloud Run deployment: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) / [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh)
- Local development: Python 3.10+. `pip install -e ".[dev]"`, then use `pytest` / `ruff` (see `pyproject.toml`)

### Operations Notes

- Graceful shutdown: Uvicorn starts with `timeout_graceful_shutdown=30` seconds. For Kubernetes, set `terminationGracePeriodSeconds` to at least 45–60
- Logging & personal data: Structured logs may include client IP. Retention, access control, and GDPR compliance are the deployer's responsibility

---

*Improvements are welcome via Issues and Pull Requests.*
