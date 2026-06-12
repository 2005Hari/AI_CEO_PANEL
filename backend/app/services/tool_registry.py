from typing import Callable, Dict, Any, List
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

class ToolConfig:
    def __init__(self, requires_approval: bool = False):
        self.requires_approval = requires_approval

class ToolRegistry:
    def __init__(self):
        self.tools: List[BaseTool] = []
        self.tool_configs: Dict[str, ToolConfig] = {}
        
    def register(self, t: BaseTool, requires_approval: bool = False):
        self.tools.append(t)
        self.tool_configs[t.name] = ToolConfig(requires_approval=requires_approval)
        
    def get_tool(self, name: str) -> BaseTool:
        for t in self.tools:
            if t.name == name:
                return t
        return None
        
    def requires_approval(self, name: str) -> bool:
        if name in self.tool_configs:
            return self.tool_configs[name].requires_approval
        return False

registry = ToolRegistry()

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Sends an email to a recipient. Use this for marketing or customer outreach."""
    return f"Sent email to {to} with subject: {subject}"

registry.register(send_email, requires_approval=True)

@tool
def fetch_data(url: str) -> str:
    """Fetches public data from a URL. Useful for competitor research."""
    return f"Successfully fetched and scraped data from {url}"

registry.register(fetch_data, requires_approval=False)

@tool
def github_repo_create(repo_name: str, description: str) -> str:
    """Creates a new GitHub repository."""
    return f"Successfully created GitHub repository: {repo_name}"

registry.register(github_repo_create, requires_approval=True)

@tool
def delegate_task(department: str, title: str, description: str) -> str:
    """Delegates a task to another department. 
    Departments include: product, technology, design, marketing, sales, finance, operations, customer support."""
    # This tool will be handled specially or we can just return a string and let the worker loop intercept
    # Actually, we should just let the worker loop intercept it or do the DB insertion right here.
    # We will do the DB insertion here but we don't have DB session. So let's just return a formatted string
    # and the worker loop will parse it if needed. OR, we can pass it as a regular tool.
    # To keep it simple, we'll just mock it and say the task was delegated.
    return f"DELEGATED_TASK: [{department}] {title} - {description}"

registry.register(delegate_task, requires_approval=False)
