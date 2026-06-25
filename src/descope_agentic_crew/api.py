#!/usr/bin/env python
import asyncio
import contextlib
import os
import sys
import warnings
from datetime import date

import jwt as pyjwt
import requests as req_lib
import uvicorn
from jwt.algorithms import RSAAlgorithm
from mcp.server import Server
from mcp.server.auth.middleware.auth_context import AuthContextMiddleware, get_access_token
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend, RequireAuthMiddleware
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.routes import build_resource_metadata_url, create_protected_resource_routes
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
sys.path.insert(0, os.path.dirname(__file__))

from crew import DescopeAgenticCrew

DESCOPE_PROJECT_ID = os.getenv("DESCOPE_PROJECT_ID")
MCP_SERVER_ID = os.getenv("MCP_SERVER_ID")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:5001")

DESCOPE_MANAGEMENT_KEY = os.getenv("DESCOPE_MANAGEMENT_KEY")
DESCOPE_AS_URL = (
    f"https://api.descope.com/v1/apps/agentic/{DESCOPE_PROJECT_ID}/{MCP_SERVER_ID}"
)
RESOURCE_URL = f"{MCP_SERVER_URL}/mcp"

# The agentic AS OIDC discovery doc returns this as jwks_uri — it's the correct
# endpoint for validating agentic OAuth tokens (not /v1/keys or /v2/keys which
# the Descope SDK uses for standard session tokens).
_JWKS_CANDIDATES = [
    f"https://api.descope.com/{DESCOPE_PROJECT_ID}/.well-known/jwks.json",
    f"https://api.descope.com/v2/keys/{DESCOPE_PROJECT_ID}",
]
_kid_cache: dict[str, object] = {}  # kid → RSA public key


def _fetch_keys(url: str) -> list[dict]:
    """Try fetching JWKS without auth, then with management key."""
    for label, headers in [("no-auth", {}), ("mgmt-key", {"Authorization": f"Bearer {DESCOPE_PROJECT_ID}:{DESCOPE_MANAGEMENT_KEY}"})]:
        try:
            resp = req_lib.get(url, headers=headers, timeout=10)
            print(f"[JWKS] GET {url} ({label}) → {resp.status_code}")
            if resp.ok:
                keys = resp.json().get("keys", [])
                print(f"[JWKS]   kids: {[k.get('kid') for k in keys]}")
                return keys
        except Exception as e:
            print(f"[JWKS] GET {url} ({label}) → ERROR: {e}")
    return []


def _find_public_key(kid: str):
    if kid in _kid_cache:
        return _kid_cache[kid]
    for url in _JWKS_CANDIDATES:
        for jwk in _fetch_keys(url):
            k = RSAAlgorithm.from_jwk(jwk)
            _kid_cache[jwk.get("kid", "")] = k
        if kid in _kid_cache:
            print(f"[TokenVerifier] Found key {kid} at {url}")
            return _kid_cache[kid]
    return None


class DescopeTokenVerifier:
    """Validates Descope agentic AS tokens by searching known JWKS endpoints."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            header = pyjwt.get_unverified_header(token)
            kid = header.get("kid", "")
            alg = header.get("alg", "RS256")
            print(f"[TokenVerifier] kid={kid}, alg={alg}")

            public_key = await asyncio.to_thread(_find_public_key, kid)
            if public_key is None:
                print(f"[TokenVerifier] FAILED — key {kid!r} not found in any JWKS")
                return None

            payload = pyjwt.decode(
                token,
                public_key,
                algorithms=[alg, "RS256", "RS512"],
                options={"verify_aud": False},
            )
            user_id = payload.get("sub") or payload.get("userId")
            iss = payload.get("iss", "")
            print(f"[TokenVerifier] Success — user={user_id}, iss={iss}")
            raw_client_id = payload.get("azp") or payload.get("aud") or DESCOPE_PROJECT_ID
            client_id = raw_client_id[0] if isinstance(raw_client_id, list) else str(raw_client_id)
            scope_raw = payload.get("scope", "")
            scopes = scope_raw.split() if isinstance(scope_raw, str) else list(scope_raw or [])
            exp = payload.get("exp")
            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=scopes,
                expires_at=int(exp) if exp else None,
                subject=user_id,
                claims={k: v for k, v in payload.items() if k != "scope"},
            )
        except Exception as e:
            print(f"[TokenVerifier] FAILED — {type(e).__name__}: {e}")
            return None


mcp_server = Server("crewai-calendar-contacts")


@mcp_server.list_tools()
async def list_tools():
    return [
        Tool(
            name="run_crew",
            description=(
                "Run the CrewAI crew to handle Google Calendar and Contacts tasks. "
                "Supports creating calendar events and searching contacts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "Natural language request for calendar or contacts operations",
                    }
                },
                "required": ["user_request"],
            },
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "run_crew":
        raise ValueError(f"Unknown tool: {name}")

    access_token_obj = get_access_token()
    if access_token_obj is None:
        return [TextContent(type="text", text="Error: Missing authentication")]

    raw_token = access_token_obj.token
    user_id = access_token_obj.subject
    if not user_id:
        return [TextContent(type="text", text="Error: Could not determine user ID from token")]

    user_request = arguments.get("user_request", "").strip()
    if not user_request:
        return [TextContent(type="text", text="Error: user_request is required")]

    # Give the agents today's date so relative dates like "tomorrow" resolve
    # correctly (the model otherwise guesses the year).
    dated_request = f"Today's date is {date.today().isoformat()}. {user_request}"

    crew_instance = DescopeAgenticCrew(user_id=user_id, access_token=raw_token)

    try:
        result = await asyncio.to_thread(
            lambda: crew_instance.crew().kickoff(inputs={"user_request": dated_request})
        )
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        return [TextContent(type="text", text=f"Crew execution failed: {str(e)}")]


def create_app() -> Starlette:
    token_verifier = DescopeTokenVerifier()
    session_manager = StreamableHTTPSessionManager(app=mcp_server, stateless=False)

    resource_url = AnyHttpUrl(RESOURCE_URL)
    as_url = AnyHttpUrl(DESCOPE_AS_URL)
    resource_metadata_url = build_resource_metadata_url(resource_url)

    class MCPApp:
        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            await session_manager.handle_request(scope, receive, send)

    mcp_asgi = MCPApp()
    protected_mcp = RequireAuthMiddleware(mcp_asgi, [], resource_metadata_url)

    protected_resource_routes = create_protected_resource_routes(
        resource_url=resource_url,
        authorization_servers=[as_url],
        scopes_supported=["google-calendar", "google-contacts"],
        resource_name="CrewAI Calendar & Contacts Server",
    )

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            yield

    return Starlette(
        debug=False,
        routes=[
            Route("/mcp", endpoint=protected_mcp),
            *protected_resource_routes,
        ],
        middleware=[
            Middleware(AuthenticationMiddleware, backend=BearerAuthBackend(token_verifier)),
            Middleware(AuthContextMiddleware),
        ],
        lifespan=lifespan,
    )


if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=5001)
