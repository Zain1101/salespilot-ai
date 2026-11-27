from .opportunity_tools import register_opportunity_tools
from .lead_tools import register_lead_tools
from .task_tools import register_task_tools


def register_ai_tools():
    register_opportunity_tools()
    register_lead_tools()
    register_task_tools()