"""
Customer Data Agent

- Specialist agent for customer & ticket data.
- It does NOT talk directly to users; it serves other agents via A2A.
- For the assignment, this agent should eventually call MCP tools internally.
"""

# agents/data_agent.py
import os
import uvicorn
from datetime import datetime
from typing import Any
import asyncio
import nest_asyncio

from google.adk.agents import Agent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, TransportProtocol
from a2a.a2a.executor.a2a_agent_executor import A2aAgentExecutor, A2aAgentExecutorConfig
from mcp_server import get_customer, list_customers, update_customer, create_ticket, get_customer_history

# Global Config (ensure these match your run_a2a_servers.py)
DATA_AGENT_PORT = 11001
DATA_AGENT_URL = f"http://localhost:{DATA_AGENT_PORT}"

data_agent = Agent(
    model="gemini-2.5-flash",
    name="customer_data_agent",
    instruction="""
    You are the Customer Data Agent in a multi-agent customer support system.
    You DO NOT talk directly to end users; you serve other agents (Router/Support) via A2A.
    CRITICAL: Use your provided tools (get_customer, list_customers, etc.) to fulfill the data request from the calling agent.
    When you reply: Return the raw output from the tool call. Be concise, providing only the necessary data.
    """,
    tools=[get_customer, list_customers, update_customer, create_ticket, get_customer_history],
)

data_agent_card = AgentCard(
    name="Customer Data Agent",
    url=DATA_AGENT_URL,
    description="Specialist agent for customer and ticket data operations",
    version="1.0",
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[AgentSkill(id="customer_data_skill", name="Customer Data Operations", description="Fetches and updates customer and ticket data", tags=["customer", "tickets", "database"])],
)

def create_agent_a2a_server(agent: Agent, agent_card: AgentCard):
    runner = Runner(
        app_name=agent.name, agent=agent, 
        artifact_service=InMemoryArtifactService(), session_service=InMemorySessionService(), 
        memory_service=InMemoryMemoryService()
    )
    executor = A2aAgentExecutor(runner=runner, config=A2aAgentExecutorConfig())
    request_handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

if __name__ == "__main__":
    nest_asyncio.apply()
    app = create_agent_a2a_server(data_agent, data_agent_card)
    uvicorn.run(app.build(), host='0.0.0.0', port=DATA_AGENT_PORT, log_level='info')