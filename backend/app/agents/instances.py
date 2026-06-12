from .base import BaseExecutiveAgent
from .prompts import (
    VISIONARY_CEO_PROMPT,
    OPERATIONS_CEO_PROMPT,
    MARKETING_CEO_PROMPT,
    FINANCE_CEO_PROMPT,
    RISK_ANALYST_PROMPT
)

# Instantiate the agents
visionary_agent = BaseExecutiveAgent("visionary", VISIONARY_CEO_PROMPT)
operations_agent = BaseExecutiveAgent("operations", OPERATIONS_CEO_PROMPT)
marketing_agent = BaseExecutiveAgent("marketing", MARKETING_CEO_PROMPT)
finance_agent = BaseExecutiveAgent("finance", FINANCE_CEO_PROMPT)
risk_agent = BaseExecutiveAgent("risk", RISK_ANALYST_PROMPT)

# Lightweight MVP agents
from .prompts import DEVELOPER_PROMPT, DESIGNER_PROMPT

manager_v2_agent = BaseExecutiveAgent("manager_v2", OPERATIONS_CEO_PROMPT)
developer_agent = BaseExecutiveAgent("developer", DEVELOPER_PROMPT)
designer_agent = BaseExecutiveAgent("designer", DESIGNER_PROMPT)

# Dictionary for dynamic lookup
AGENTS_MAP = {
    "visionary": visionary_agent,
    "operations": operations_agent,
    "marketing": marketing_agent,
    "finance": finance_agent,
    "risk": risk_agent
}

# Add convenience mappings for MVP-specific agents
AGENTS_MAP.update({
    "manager_v2": manager_v2_agent,
    "developer": developer_agent,
    "designer": designer_agent,
})
