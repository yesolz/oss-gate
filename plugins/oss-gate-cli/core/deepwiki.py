"""Lazy DeepWiki connection with the same optional outbound policy as collection."""

import asyncio
import json
from datetime import datetime, timezone
from functools import partial

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .transport import BoundedAsyncTransport
from .repository import parse_repository
from .settings import PolicyBlocked, check, identifier, load_policy, policy_scope
from .tls import build_context, TLSConfigurationError

ENDPOINT = "https://mcp.deepwiki.com/mcp"
QUESTIONS = {
    "overview": "What does this public project do, who uses it, and how does a typical request flow through it? Cite sources and version limitations.",
    "communication": "What information leaves the environment? Describe destinations, telemetry, credentials, defaults, disabling options and configuration. Cite sources; missing evidence is not proof of no external communication.",
    "dependencies": "Why are the direct dependencies used? Which optional extras and platform-specific dependencies are outside the default graph? Cite sources and version limitations.",
    "maintenance": "Who maintains this project? Describe its release, support and vulnerability-reporting practices with sources.",
}


def client_factory(headers=None, timeout=None, auth=None, *, verify=True):
    return httpx.AsyncClient(
        headers=headers,
        timeout=timeout or 30,
        auth=auth,
        transport=BoundedAsyncTransport(verify=verify),
        follow_redirects=False,
        trust_env=False,
    )


async def request(repo, action="ask_question", topic="overview", policy_path=None):
    """Record capture metadata for both remote responses and local failures."""
    result = await _request(repo, action, topic, policy_path)
    return {
        **result,
        "schema": "oss-gate.explanation/1",
        "repository": result.get("repository", repo),
        "action": action,
        "topic": topic if action == "ask_question" else None,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "capture_kind": "local_failure" if "error" in result else "tool_response",
    }


async def _request(repo, action, topic, policy_path):
    """Only public owner/repo identifiers and fixed topic questions can leave here."""
    try:
        config = load_policy(policy_path)
        host, path = parse_repository(repo)
        if action not in ("ask_question", "read_wiki_structure", "read_wiki_contents") or topic not in QUESTIONS:
            raise ValueError("unknown DeepWiki action or topic")
        args = {"repoName": path}
        if action == "ask_question":
            args["question"] = QUESTIONS[topic]
        with policy_scope(config):
            check("deepwiki", [identifier("repo", f"{host}/{path}")])
            if host != "github.com":
                return {
                    "error": "DeepWiki supports public GitHub repositories only",
                    "code": "unsupported_repository_host",
                }
            repo = path
            verify, evidence = build_context(config)
            result = await asyncio.wait_for(_call(repo, action, topic, args, verify), timeout=120)
            if evidence is not None:
                result["tls_trust"] = evidence
            return result
    except PolicyBlocked as exc:
        return {"error": "DeepWiki request blocked by selected policy", "code": "policy_blocked", "reason": exc.code}
    except asyncio.TimeoutError:
        return {"error": "DeepWiki timed out", "code": "upstream_timeout"}
    except TLSConfigurationError:
        return {"error": "cannot load selected additional CA certificates", "code": "tls_configuration_invalid"}
    except (ValueError, OSError) as exc:
        return {"error": "invalid DeepWiki input or policy", "code": "invalid_input", "error_type": type(exc).__name__}
    except Exception as exc:
        # SDK transport failures can arrive wrapped in task-group exceptions.
        return {"error": "DeepWiki unavailable", "code": "upstream_unavailable", "error_type": type(exc).__name__}


async def _call(repo, action, topic, args, verify=True):
    async with streamablehttp_client(
        ENDPOINT, timeout=30, sse_read_timeout=90, httpx_client_factory=partial(client_factory, verify=verify)
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            remote_action = "ask_wiki_question" if action == "ask_question" else action
            result = await session.call_tool(remote_action, args)
            return {
                "repository": repo,
                "action": action,
                "topic": topic if action == "ask_question" else None,
                "question": args.get("question"),
                "isError": result.isError,
                "content": [item.model_dump(mode="json", exclude_none=True) for item in result.content],
                "source": "DeepWiki AI-generated content; not version-pinned or independently verified",
            }


async def invoke(repo, action="ask_question", topic="overview"):
    return json.dumps(await request(repo, action, topic), ensure_ascii=False)
