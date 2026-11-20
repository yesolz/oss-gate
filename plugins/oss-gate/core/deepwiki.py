"""Lazy DeepWiki connection with the same optional outbound policy as collection."""

import json

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .repository import parse_repository
from .settings import PolicyBlocked, check, identifier, load_policy, policy_scope

ENDPOINT = "https://mcp.deepwiki.com/mcp"
QUESTIONS = {
    "overview": "What does this public project do, who uses it, and how does a typical request flow through it? Cite sources and version limitations.",
    "communication": "What information leaves the environment? Describe destinations, telemetry, credentials, defaults, disabling options and configuration. Cite sources; missing evidence is not proof of no external communication.",
    "dependencies": "Why are the direct dependencies used? Which optional extras and platform-specific dependencies are outside the default graph? Cite sources and version limitations.",
    "maintenance": "Who maintains this project? Describe its release, support and vulnerability-reporting practices with sources.",
}


def client_factory(headers=None, timeout=None, auth=None):
    return httpx.AsyncClient(headers=headers, timeout=timeout or 30, auth=auth, follow_redirects=False, trust_env=False)


async def request(repo, action="ask_question", topic="overview", policy_path=None):
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
            async with streamablehttp_client(
                ENDPOINT, timeout=30, sse_read_timeout=90, httpx_client_factory=client_factory
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
    except PolicyBlocked as exc:
        return {"error": "DeepWiki request blocked by selected policy", "code": "policy_blocked", "reason": exc.code}
    except (ValueError, OSError) as exc:
        return {"error": "invalid DeepWiki input or policy", "code": "invalid_input", "error_type": type(exc).__name__}
    except Exception as exc:
        # SDK transport failures can arrive wrapped in task-group exceptions.
        return {"error": "DeepWiki unavailable", "code": "upstream_unavailable", "error_type": type(exc).__name__}


async def invoke(repo, action="ask_question", topic="overview"):
    return json.dumps(await request(repo, action, topic), ensure_ascii=False)
