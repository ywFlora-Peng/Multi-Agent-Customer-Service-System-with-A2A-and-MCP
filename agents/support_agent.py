"""
Support Agent

- Handles customer-facing responses.
- Uses context from Data Agent (customer profile, tickets, etc.).
"""

import asyncio
import logging
import os
import threading
import time
from typing import Any
import uvicorn
import nest_asyncio

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, TransportProtocol
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor, A2aAgentExecutorConfig
from google.adk.agents import Agent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# --- Configuration ---
SUPPORT_AGENT_PORT = 11002
SUPPORT_AGENT_URL = f"http://localhost:{SUPPORT_AGENT_PORT}"

# --- Agent Definition ---
support_agent = Agent(
    model="gemini-2.5-flash",
    name="support_agent",
    instruction="""
    You are the Support Agent. You receive the customer's original query AND a data summary (TEXT format) from the Router Agent.

    Your task is to convert ALL received structured data or JSON into a polite, concise, and actionable natural language response. Do not output any raw JSON or code blocks.

    If the data summary contains customer details, use the customer's NAME in the greeting (e.g., "Hello [Name]").
    """,
    tools=[],
)

support_agent_card = AgentCard(
    name="Support Agent",
    url=SUPPORT_AGENT_URL,
    description="Customer-facing support agent; uses context from the data agent.",
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id="customer_support_skill",
            name="Customer Support Skill",
            description="Handles customer issues, escalation, and general assistance.",
            tags=["support", "escalation", "explanations"],
        )
    ],
)

# --- Server Utilities ---
def create_agent_a2a_server(agent: Agent, agent_card: AgentCard):
    """Create an A2A server for any ADK agent using the quickstart pattern."""
    runner = Runner(
        app_name=agent.name,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    config = A2aAgentExecutorConfig()
    executor = A2aAgentExecutor(runner=runner, config=config)

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)


if __name__ == "__main__":
    nest_asyncio.apply()
    app = create_agent_a2a_server(support_agent, support_agent_card)
    uvicorn.run(app.build(), host='0.0.0.0', port=SUPPORT_AGENT_PORT, log_level='info')