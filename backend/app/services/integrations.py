# backend/app/services/integrations.py
import json
import base64
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Integration

class BaseIntegrationProvider:
    provider_name: str

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Returns JSON schema definitions of tools supported by this integration.
        """
        raise NotImplementedError

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a specific tool action.
        """
        raise NotImplementedError


class SlackProvider(BaseIntegrationProvider):
    provider_name = "slack"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "slack_post_message",
                "description": "Send a notification or task summary to a Slack channel to alert the team.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Slack channel name or ID (e.g. #general, #marketing)."
                        },
                        "message": {
                            "type": "string",
                            "description": "Markdown formatted message to post."
                        }
                    },
                    "required": ["channel", "message"]
                }
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "slack_post_message":
            channel = arguments.get("channel", "#general")
            message = arguments.get("message", "")
            # Simulate posting message
            return {
                "status": "success",
                "message": f"Successfully posted message to Slack channel '{channel}'",
                "posted_at": datetime.utcnow().isoformat(),
                "payload": {
                    "channel": channel,
                    "preview": message[:100] + "..." if len(message) > 100 else message
                }
            }
        raise ValueError(f"Unknown tool '{tool_name}' for provider {self.provider_name}")


class GitHubProvider(BaseIntegrationProvider):
    provider_name = "github"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "github_create_repository",
                "description": "Create a new repository for the project code or documentation on GitHub.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "The name of the new GitHub repository."
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional repository description."
                        },
                        "is_private": {
                            "type": "boolean",
                            "description": "Whether the repository should be private."
                        }
                    },
                    "required": ["repo_name"]
                }
            },
            {
                "name": "github_create_pull_request",
                "description": "Create a new pull request with code reviews or GTM launch plans on GitHub.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "The name of the repository."
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the pull request."
                        },
                        "body": {
                            "type": "string",
                            "description": "Detailed markdown explanation of the PR changes."
                        }
                    },
                    "required": ["repo", "title", "body"]
                }
            },
            {
                "name": "github_push_file",
                "description": "Create or update a single file's contents in a GitHub repository (e.g. to add a generated page, component, or config file).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "The repository name (without owner)."
                        },
                        "path": {
                            "type": "string",
                            "description": "File path within the repo, e.g. 'app/page.tsx' or 'index.html'."
                        },
                        "content": {
                            "type": "string",
                            "description": "Full plain-text content of the file."
                        },
                        "commit_message": {
                            "type": "string",
                            "description": "Commit message for this change."
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch to commit to (defaults to 'main')."
                        }
                    },
                    "required": ["repo_name", "path", "content"]
                }
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        token = self.config.get("access_token") or self.config.get("token")
        owner = self.config.get("owner") or self.config.get("username")

        if not token or not owner:
            return {
                "status": "error",
                "message": "GitHub integration is not fully configured (missing access_token or owner).",
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            if tool_name == "github_create_repository":
                repo_name = arguments.get("repo_name")
                desc = arguments.get("description", "")
                is_private = bool(arguments.get("is_private", False))

                resp = await client.post(
                    "https://api.github.com/user/repos",
                    headers=headers,
                    json={
                        "name": repo_name,
                        "description": desc,
                        "private": is_private,
                        "auto_init": True,
                    },
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "status": "success",
                        "message": f"Created GitHub repository '{repo_name}'",
                        "repo_url": data.get("html_url"),
                        "details": {
                            "name": data.get("name"),
                            "full_name": data.get("full_name"),
                            "default_branch": data.get("default_branch"),
                            "created_at": data.get("created_at"),
                        },
                    }
                if resp.status_code == 422:
                    # Likely already exists - fetch it
                    existing = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo_name}", headers=headers
                    )
                    if existing.status_code == 200:
                        data = existing.json()
                        return {
                            "status": "success",
                            "message": f"Repository '{repo_name}' already exists; reusing it.",
                            "repo_url": data.get("html_url"),
                            "details": {"name": data.get("name"), "default_branch": data.get("default_branch")},
                        }
                return {
                    "status": "error",
                    "message": f"GitHub repo creation failed ({resp.status_code})",
                    "details": resp.text[:500],
                }

            elif tool_name == "github_push_file":
                repo_name = arguments.get("repo_name")
                path = arguments.get("path", "").lstrip("/")
                content = arguments.get("content", "")
                commit_message = arguments.get("commit_message") or f"Update {path}"
                branch = arguments.get("branch", "main")

                url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}"

                # Check if file already exists to get its sha (required for updates)
                sha = None
                existing = await client.get(url, headers=headers, params={"ref": branch})
                if existing.status_code == 200:
                    sha = existing.json().get("sha")

                encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
                payload = {
                    "message": commit_message,
                    "content": encoded_content,
                    "branch": branch,
                }
                if sha:
                    payload["sha"] = sha

                resp = await client.put(url, headers=headers, json=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "status": "success",
                        "message": f"{'Updated' if sha else 'Created'} '{path}' in {owner}/{repo_name}",
                        "file_url": data.get("content", {}).get("html_url"),
                        "commit_sha": data.get("commit", {}).get("sha"),
                    }
                return {
                    "status": "error",
                    "message": f"GitHub file push failed ({resp.status_code})",
                    "details": resp.text[:500],
                }

            elif tool_name == "github_create_pull_request":
                repo = arguments.get("repo")
                title = arguments.get("title")
                body = arguments.get("body", "")
                head = arguments.get("head", "main")
                base = arguments.get("base", "main")

                resp = await client.post(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls",
                    headers=headers,
                    json={"title": title, "body": body, "head": head, "base": base},
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "status": "success",
                        "message": f"Created Pull Request #{data.get('number')} in '{repo}'",
                        "pr_url": data.get("html_url"),
                        "details": {"title": title, "state": data.get("state")},
                    }
                return {
                    "status": "error",
                    "message": f"GitHub PR creation failed ({resp.status_code})",
                    "details": resp.text[:500],
                }

        raise ValueError(f"Unknown tool '{tool_name}' for provider {self.provider_name}")


class VercelProvider(BaseIntegrationProvider):
    provider_name = "vercel"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "vercel_deploy_site",
                "description": "Deploy a small static or Next.js site to Vercel directly from file contents (no GitHub repo required) and get a live URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Vercel project name (used to generate the deployment URL)."
                        },
                        "files": {
                            "type": "array",
                            "description": "List of files to deploy, each {\"path\": str, \"content\": str}.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string"},
                                    "content": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["project_name", "files"]
                }
            },
            {
                "name": "vercel_trigger_deploy",
                "description": "Trigger a redeploy of an existing Vercel project (uses latest linked Git branch).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Vercel project name."
                        },
                        "branch": {
                            "type": "string",
                            "description": "Git branch to build and deploy (defaults to 'main')."
                        }
                    },
                    "required": ["project_name"]
                }
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        token = self.config.get("access_token") or self.config.get("token")
        team_id = self.config.get("team_id")

        if not token:
            return {
                "status": "error",
                "message": "Vercel integration is not configured (missing access_token).",
            }

        headers = {"Authorization": f"Bearer {token}"}
        params = {"teamId": team_id} if team_id else {}

        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "vercel_deploy_site":
                project = arguments.get("project_name")
                files = arguments.get("files", [])

                deploy_files = [
                    {"file": f["path"].lstrip("/"), "data": f["content"]} for f in files
                ]

                resp = await client.post(
                    "https://api.vercel.com/v13/deployments",
                    headers=headers,
                    params=params,
                    json={
                        "name": project,
                        "files": deploy_files,
                        "target": "production",
                        "projectSettings": {"framework": None},
                    },
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    url = data.get("url")
                    return {
                        "status": "success",
                        "message": f"Deployed '{project}' to Vercel",
                        "deployment_id": data.get("id"),
                        "url": f"https://{url}" if url else None,
                        "triggered_at": datetime.utcnow().isoformat(),
                    }
                return {
                    "status": "error",
                    "message": f"Vercel deployment failed ({resp.status_code})",
                    "details": resp.text[:500],
                }

            elif tool_name == "vercel_trigger_deploy":
                project = arguments.get("project_name")
                branch = arguments.get("branch", "main")

                resp = await client.post(
                    "https://api.vercel.com/v13/deployments",
                    headers=headers,
                    params=params,
                    json={
                        "name": project,
                        "gitSource": {
                            "type": "github",
                            "ref": branch,
                        },
                        "target": "production",
                    },
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    url = data.get("url")
                    return {
                        "status": "success",
                        "message": f"Triggered deployment for '{project}' on branch '{branch}'",
                        "deployment_id": data.get("id"),
                        "url": f"https://{url}" if url else None,
                        "triggered_at": datetime.utcnow().isoformat(),
                    }
                return {
                    "status": "error",
                    "message": f"Vercel deploy trigger failed ({resp.status_code})",
                    "details": resp.text[:500],
                }

        raise ValueError(f"Unknown tool '{tool_name}' for provider {self.provider_name}")


class GoogleWorkspaceProvider(BaseIntegrationProvider):
    provider_name = "google"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "google_create_doc",
                "description": "Write a document, report, or pitch memo to Google Docs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Google Doc title."
                        },
                        "content": {
                            "type": "string",
                            "description": "Document body text in markdown or plain text."
                        }
                    },
                    "required": ["title", "content"]
                }
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "google_create_doc":
            title = arguments.get("title")
            return {
                "status": "success",
                "message": f"Successfully created Google Doc '{title}'",
                "doc_id": "doc_mock_987xyz",
                "doc_url": f"https://docs.google.com/document/d/mock_987xyz/edit",
                "created_at": datetime.utcnow().isoformat()
            }
        raise ValueError(f"Unknown tool '{tool_name}' for provider {self.provider_name}")


class WebSearchProvider(BaseIntegrationProvider):
    """Lightweight web search provider for lead-gen / research tasks.

    Uses Serper.dev (Google Search API) if configured via
    Integration.config = {"provider": "serper", "api_key": "..."}.
    Add other providers by extending execute_tool.
    """
    provider_name = "web_search"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "web_search",
                "description": "Search the web for companies, people, or businesses matching a query. Use this for lead generation and market research.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query, e.g. 'boutique fitness studios in Austin TX'."
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return (default 10, max 20)."
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name != "web_search":
            raise ValueError(f"Unknown tool '{tool_name}' for provider {self.provider_name}")

        api_key = self.config.get("api_key")
        provider = self.config.get("provider", "serper")
        query = arguments.get("query", "")
        num_results = min(int(arguments.get("num_results", 10)), 20)

        if not api_key:
            return {
                "status": "error",
                "message": "Web search is not configured (missing api_key for provider).",
            }

        async with httpx.AsyncClient(timeout=20.0) as client:
            if provider == "serper":
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": num_results},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("organic", [])[:num_results]:
                        results.append({
                            "title": item.get("title"),
                            "link": item.get("link"),
                            "snippet": item.get("snippet"),
                        })
                    return {"status": "success", "query": query, "results": results}
                return {
                    "status": "error",
                    "message": f"Search failed ({resp.status_code})",
                    "details": resp.text[:300],
                }

        return {"status": "error", "message": f"Unsupported search provider '{provider}'"}


# Registry mapping provider keys to classes
PROVIDER_CLASS_MAP = {
    "slack": SlackProvider,
    "github": GitHubProvider,
    "vercel": VercelProvider,
    "google": GoogleWorkspaceProvider,
    "web_search": WebSearchProvider,
}

class IntegrationManager:
    @staticmethod
    async def get_active_providers(project_id: str, db: AsyncSession) -> List[BaseIntegrationProvider]:
        """
        Fetches all connected integrations for a project and instantiates their provider instances.
        """
        result = await db.execute(
            select(Integration)
            .where(Integration.project_id == project_id)
            .where(Integration.status == "connected")
        )
        db_integrations = result.scalars().all()
        
        providers = []
        for db_int in db_integrations:
            provider_cls = PROVIDER_CLASS_MAP.get(db_int.provider)
            if provider_cls:
                providers.append(provider_cls(config=db_int.config or {}))
        return providers

    @staticmethod
    async def execute_tool_call(project_id: str, tool_name: str, arguments: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """
        Finds the active provider corresponding to a tool name and executes the tool action.
        """
        providers = await IntegrationManager.get_active_providers(project_id, db)
        for provider in providers:
            # Check if this provider owns the tool
            for tool in provider.get_tools():
                if tool["name"] == tool_name:
                    return await provider.execute_tool(tool_name, arguments)
        
        raise ValueError(f"No active integration supports the tool '{tool_name}'")

# Global singleton
integration_manager = IntegrationManager()
