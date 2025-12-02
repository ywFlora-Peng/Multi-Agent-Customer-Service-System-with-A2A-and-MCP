"""
Router (Host) Agent

- Entry point for user queries (via A2A).
- Orchestrates the Customer Data Agent and Support Agent.
- Implements task allocation, negotiation, and multi-step coordination.
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
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# --- Configuration (Must match other agents) ---
ROUTER_AGENT_PORT = 11000
DATA_AGENT_URL = "http://localhost:11001"
SUPPORT_AGENT_URL = "http://localhost:11002"
ROUTER_AGENT_URL = f"http://localhost:{ROUTER_AGENT_PORT}"

# --- Remote Agent Definitions ---
remote_data_agent = RemoteA2aAgent(
    name="customer_data", 
    description="Tool to get customer profiles, lists of IDs, ticket history, and update records via MCP. USE THIS FOR ALL DATA ACCESS.",
    agent_card=f"{DATA_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
)

remote_support_agent = RemoteA2aAgent(
    name="customer_support", 
    description="Tool to generate the final, polite, customer-facing response based on the context provided.",
    agent_card=f"{SUPPORT_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
)

# --- Router Agent Definition ---
router_host_agent = Agent(
    model="gemini-2.5-flash", 
    name="router_host_agent",
    sub_agents=[remote_data_agent, remote_support_agent], 
    
    instruction="""
    You are the Router Host Agent (Orchestrator). Your role is coordination.

    **CRITICAL OUTPUT RULE:** Your ONLY goal is to call the 'customer_support' tool as the final action. You MUST NOT output JSON or raw tool output yourself.

    **TOOL NAMING RULE:** You have two agents: 'customer_data' and 'transfer_to_agent'. The 'customer_support' agent is called via 'transfer_to_agent'.

    **COORDINATION FLOWS:**
    
    1. **Data Fetch & Multi-Intent (MANDATORY CHAIN):**
       * Step 1: Call 'customer_data' to gather facts (e.g., fetch, update, get history).
       * Step 2: Synthesize the raw JSON into concise, actionable TEXT.
       * Step 3 (FINAL ACTION): CALL 'transfer_to_agent' with the synthesized TEXT summary and the original query.

    2. **COMPLEX DECOMPOSITION (Mandatory Chain for Test 3):**
       When a complex report is required, you MUST follow these chained steps and NEVER claim it's impossible:
       * **Step A:** Call 'customer_data' (list_customers) to get ALL required customer IDs.
       * **Step B:** Execute sequential calls to 'customer_data' (get_customer_history) for each ID. You MUST perform the final filtering (e.g., status 'open') yourself.
       * **Step C (FINAL ACTION):** Compile the final report and CALL 'transfer_to_agent'.
    """,
)

router_agent_card = AgentCard(
    name="Router Host Agent",
    url=ROUTER_AGENT_URL,
    description="Orchestrates Customer Data and Support agents using A2A.",
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id="customer_service_router",
            name="Customer Service Orchestrator",
            description="Routes and coordinates customer data and support tasks.",
            tags=["routing", "orchestration", "customer support"],
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
    app = create_agent_a2a_server(router_host_agent, router_agent_card)
    uvicorn.run(app.build(), host='0.0.0.0', port=ROUTER_AGENT_PORT, log_level='info')