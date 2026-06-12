# backend/app/services/integrations.py
import json
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
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "github_create_repository":
            repo_name = arguments.get("repo_name")
            desc = arguments.get("description", "")
            return {
                "status": "success",
                "message": f"Created GitHub repository '{repo_name}' successfully",
                "repo_url": f"https://github.com/mock-org/{repo_name}",
                "details": {
                    "name": repo_name,
                    "description": desc,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
        elif tool_name == "github_create_pull_request":
            repo = arguments.get("repo")
            title = arguments.get("title")
            return {
                "status": "success",
                "message": f"Created Pull Request #{101} in '{repo}'",
                "pr_url": f"https://github.com/mock-org/{repo}/pull/101",
                "details": {
                    "title": title,
                    "state": "open"
                }
            }
        raise ValueError(f"Unknown tool '{tool_name}' for provider {self.provider_name}")


class VercelProvider(BaseIntegrationProvider):
    provider_name = "vercel"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "vercel_trigger_deploy",
                "description": "Deploy a branch or project to Vercel.",
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
        if tool_name == "vercel_trigger_deploy":
            project = arguments.get("project_name")
            branch = arguments.get("branch", "main")
            return {
                "status": "success",
                "message": f"Triggered deployment build for Vercel project '{project}' from branch '{branch}'",
                "deployment_id": "dpl_mock123abc789",
                "url": f"https://{project}-git-{branch}-mock.vercel.app",
                "triggered_at": datetime.utcnow().isoformat()
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


# Registry mapping provider keys to classes
PROVIDER_CLASS_MAP = {
    "slack": SlackProvider,
    "github": GitHubProvider,
    "vercel": VercelProvider,
    "google": GoogleWorkspaceProvider,
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
