# Descope Agentic Crew — MCP Server for Calendar & Contacts

An **MCP (Model Context Protocol) server** that lets any MCP client schedule Google Calendar events and search Google Contacts through natural language. Authentication and Google access are handled by **Descope's Agentic Identity Hub**, and the actual work is done by a **CrewAI** multi-agent crew running on **Claude (Opus 4.8)**.

The server exposes a single MCP tool, `run_crew`, which an authenticated client (e.g. MCP Inspector) calls with a request like _"Schedule a meeting with Kevin tomorrow at 2pm"_.

## 🏗️ Architecture

```
┌──────────────┐   OAuth 2.1 / MCP    ┌────────────────────┐
│  MCP Client  │ ───────────────────► │   MCP Server       │
│ (Inspector,  │ ◄─────────────────── │ (Starlette/uvicorn)│
│  agent, IDE) │   run_crew tool      │   api.py           │
└──────────────┘                      └─────────┬──────────┘
                                                │
            validate agentic token (JWKS)       │  fetch Google token for user
                  ┌─────────────────────────────┴──────────────────────────┐
                  ▼                                                         ▼
       ┌──────────────────────┐                              ┌──────────────────────┐
       │ Descope Agentic Hub  │                              │   CrewAI + Claude     │
       │ • MCP Server (inbound│                              │ • Contacts Finder     │
       │   OAuth, agentic AS) │                              │ • Calendar Manager    │
       │ • Connections        │                              │ • Task Planner        │
       │   (outbound Google   │                              └───────────┬──────────┘
       │    tokens in vault)  │                                          │
       └──────────────────────┘                              ┌───────────▼──────────┐
                                                             │   Google APIs         │
                                                             │ • Calendar v3         │
                                                             │ • People (Contacts)   │
                                                             └──────────────────────┘
```

**How auth works:**
1. The MCP client authenticates to the server via Descope's Agentic Identity Hub (OAuth 2.1). The server validates the resulting agentic access token against Descope's JWKS endpoint.
2. During that consent flow, Descope also provisions **outbound** Google tokens (Calendar + Contacts) into the user's **Connection** vault via an _Agentic Hub / Connect_ flow step.
3. When `run_crew` runs, the tools fetch the user's Google token from the Connection vault (using the agentic token) and call the Google APIs on the user's behalf — no service-account keys required.

## 🛠️ Tech Stack

- **Python 3.10–3.13**
- **MCP** (`mcp` SDK) over Streamable HTTP, served with **Starlette + uvicorn**
- **CrewAI** — multi-agent orchestration
- **Claude Opus 4.8** via **LiteLLM** (`anthropic/claude-opus-4-8`)
- **Descope Agentic Identity Hub** — MCP Server (inbound auth) + Connections (outbound Google tokens)
- **Google API Python Client** — Calendar v3 and People API
- **PyJWT** — agentic token validation against Descope JWKS

## 📋 Prerequisites

- Python 3.10–3.13 and [`uv`](https://docs.astral.sh/uv/)
- An **Anthropic API key**
- A **Descope** project with the Agentic Identity Hub enabled
- A **Google Cloud** project with the **Calendar API** and **People API** enabled, and an OAuth 2.0 Client

## ⚙️ One-time setup

### 1. Google Cloud
1. Enable the **Google Calendar API** and **Google People API**.
2. Create an **OAuth 2.0 Client ID** (Web application).
3. Add the redirect URI: `https://api.descope.com/v1/outbound/oauth/callback`
4. Add your account as a **Test user** (or publish the consent screen). Calendar/Contacts are restricted scopes.

### 2. Descope — Connections
Create two **Connections** under Agentic Identity Hub:

| Connection ID      | Google scope                                       |
| ------------------ | -------------------------------------------------- |
| `google-calendar`  | `https://www.googleapis.com/auth/calendar`         |
| `google-contacts`  | `https://www.googleapis.com/auth/contacts.readonly`|

For each, set the Google **Client ID** and **Client Secret** from step 1.

### 3. Descope — MCP Server
1. Create an **MCP Server** with URL `http://localhost:5001/mcp`.
2. Add two scopes, each **linked to its Connection** and marked **mandatory**:
   - `google-calendar` → `google-calendar` connection
   - `google-contacts` → `google-contacts` connection

### 4. Descope — consent flow (important)
The inbound consent flow (e.g. `inbound-apps-user-consent`) must provision the outbound tokens, or the Google vault stays empty (`E152102`). In the flow editor, after user consent and before `END`, add an **Agentic Hub / Connect** step for each connection:
- one with default outbound app `google-calendar`, scope `https://www.googleapis.com/auth/calendar`
- one with default outbound app `google-contacts`, scope `https://www.googleapis.com/auth/contacts.readonly`

## 🔑 Environment configuration

```bash
cp .env.example .env
```

Fill in `.env`:

```bash
# Descope
DESCOPE_PROJECT_ID=your_descope_project_id
DESCOPE_MANAGEMENT_KEY=your_management_key
MCP_SERVER_ID=your_mcp_server_id

# MCP Server
MCP_SERVER_URL=http://localhost:5001

# Google
GOOGLE_CALENDAR_ID=primary

# AI Model
MODEL=anthropic/claude-opus-4-8
ANTHROPIC_API_KEY=your_anthropic_api_key
```

> `.env` is gitignored — never commit it.

## 🚀 Run

```bash
# Install dependencies
uv sync

# Start the MCP server (port 5001)
uv run python src/descope_agentic_crew/api.py
```

Connect an MCP client. With the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector@latest \
  --transport http --server-url http://localhost:5001/mcp
```

Open the printed `?MCP_PROXY_AUTH_TOKEN=...` URL, click **Connect**, complete the Descope login and Google consent (Calendar + Contacts), then call the **`run_crew`** tool:

```
user_request: Schedule a meeting with Kevin tomorrow at 2pm
```

The crew searches your contacts for "Kevin", creates the event on your calendar, and emails the invite.

## 🧰 MCP Tool

### `run_crew`
| Param          | Type   | Description                                                  |
| -------------- | ------ | ------------------------------------------------------------ |
| `user_request` | string | Natural-language calendar/contacts request                   |

Returns the crew's final result (event confirmation, attendees invited, assumptions made).

## 🤖 Agents

- **Task Planner** — breaks the request into an execution plan.
- **Contacts Finder** — searches Google Contacts (lists + filters connections for reliability) and returns only real, tool-sourced contact data.
- **Calendar Manager** — parses date/time (relative dates resolved against today's date, times in `America/Los_Angeles`) and creates the event, inviting the contact when an email was found.

## 📁 Project Structure

```
crewai-app/
├── src/descope_agentic_crew/
│   ├── api.py              # MCP server: auth (JWKS), run_crew tool, Starlette app
│   ├── crew.py             # CrewAI crew, agents, Claude LLM config
│   ├── config/
│   │   ├── agents.yaml     # Agent roles/goals/backstories
│   │   └── tasks.yaml      # Task definitions
│   └── tools/
│       └── custom_tool.py  # Google Calendar + Contacts tools (Descope Connection tokens)
├── .env.example
├── pyproject.toml
└── README.md
```

## 🐛 Troubleshooting

- **`E152102 Outbound app token not found`** — the Google token isn't in the Connection vault. Make sure the consent flow has the **Agentic Hub / Connect** steps (setup §4) and re-run the connect flow.
- **`Token signature verification failure` / key not found** — stale cached OAuth client in the MCP client. Clear the client's local storage and reconnect with a fresh session.
- **`This model does not support assistant message prefill`** — Opus 4.8 rejects CrewAI's prefill; handled in `crew.py` (a LiteLLM patch ensures requests end with a user message).
- **`ACCESS_TOKEN_SCOPE_INSUFFICIENT` on directory search** — harmless; the tool lists/filters personal contacts via the `contacts.readonly` scope.
- **Event lands at the wrong hour** — times use `America/Los_Angeles` in `tools/custom_tool.py`; change the `timeZone` there for a different zone.

## 📚 References

- [Model Context Protocol](https://modelcontextprotocol.io)
- [Descope Agentic Identity Hub](https://docs.descope.com)
- [CrewAI](https://docs.crewai.com)
- [Claude API](https://docs.anthropic.com)
- [Google Calendar API](https://developers.google.com/calendar) · [People API](https://developers.google.com/people)
```
