"""
Demo script: run A2A scenarios against the Router Host Agent.

Assumes:
- MCP server is running on http://localhost:8000/mcp (for DB tools).
- A2A agents are running:
    Router Host Agent    -> http://localhost:11000
    Customer Data Agent  -> http://localhost:11001
    Support Agent        -> http://localhost:11002
"""

# run_scenarios.py
import asyncio
import logging
import os
import sys
from typing import Any

# Import client components
import httpx
from a2a.client.client_factory import ClientFactory, ClientConfig
from a2a.types import TransportProtocol, AgentCard
from a2a.client import create_text_message_object
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

# --- Configuration (Must match the agents' setup) ---
ROUTER_AGENT_URL = "http://localhost:11000"
# Add other necessary constants defined in Cell 4
DATA_AGENT_URL = "http://localhost:11001"
SUPPORT_AGENT_URL = "http://localhost:11002"


# --- A2A Simple Client (Final Working Version) ---
class A2ASimpleClient:
    """A minimal client to send text requests to the A2A Router."""

    def __init__(self):
        # Initialize Async Client
        self._async_client = httpx.AsyncClient(timeout=60.0)
        
        # 1. Create ClientConfig instance
        config = ClientConfig(
            httpx_client=self._async_client,
            supported_transports=[
                TransportProtocol.jsonrpc,
                TransportProtocol.http_json,
            ],
            use_client_preference=True,
        )
        
        # 2. Use config to initialize ClientFactory
        self._client_factory = ClientFactory(config)
        self._resolver = None 

    async def _get_client(self, agent_base_url: str) -> Any:
        card_url = f"{agent_base_url}{AGENT_CARD_WELL_KNOWN_PATH}"
        
        # FIX: Manually fetch the card data to bypass unstable resolver methods
        response = await self._async_client.get(card_url)
        response.raise_for_status() 
        
        # Deserialize the JSON response into the required AgentCard object
        card_data = response.json()
        card = AgentCard(**card_data)

        # FIX: Use the correct method name 'create'
        client = self._client_factory.create(card) 
        return client

    async def create_task(self, agent_base_url: str, text: str) -> str:
        """Sends the message and extracts the final text response."""
        client = await self._get_client(agent_base_url)
        message_obj = create_text_message_object(content=text)
        
        responses = []
        # Note: The 'await' block in the loop is essential for streaming
        async for response in client.send_message(message_obj):
            responses.append(response)

        # Extract final text, robustly handling failed tasks
        if responses and responses[0] is not None and isinstance(responses[0], tuple) and len(responses[0]) > 0:
            task = responses[0][0]
            
            if task is None or not getattr(task, 'artifacts', None):
                 return f"Task failed or returned empty: {str(task)}"

            try:
                # Success path
                return task.artifacts[0].parts[0].root.text
            except (AttributeError, IndexError, TypeError):
                # Fallback for unexpected structure (e.g., if LLM outputs only JSON code block)
                return f"Task completed, but output structure failed. Raw Task: {str(task)}"
                
        return 'No response received'

a2a_client = A2ASimpleClient()


# --- Scenario Execution Functions ---

async def scenario_simple_query() -> None:
    print("\n" + "="*80)
    print("=== TEST 1: Simple Query (ID 5 Fetch) ===")
    print("================================================================================\n")
    query = "Get customer information for ID 5"
    print(f"QUERY: {query}")
    response = await a2a_client.create_task(ROUTER_AGENT_URL, query)
    print("\n--- Router Final Response ---")
    print(response)
    print("-----------------------------\n")

async def scenario_coordinated_query() -> None:
    print("\n" + "="*80)
    print("=== TEST 2: Coordinated Query (Upgrade Request) ===")
    print("================================================================================\n")
    query = "I'm customer 1 and need help upgrading my account"
    print(f"QUERY: {query}")
    response = await a2a_client.create_task(ROUTER_AGENT_URL, query)
    print("\n--- Router Final Response ---")
    print(response)
    print("-----------------------------\n")

async def scenario_complex_aggregation() -> None:
    print("\n" + "="*80)
    print("=== TEST 3: Complex Aggregation (Open Tickets for Active Customers) ===")
    print("================================================================================\n")
    query = "Show me all active customers who have open tickets"
    print(f"QUERY: {query}")
    response = await a2a_client.create_task(ROUTER_AGENT_URL, query)
    print("\n--- Router Final Response ---")
    print(response)
    print("-----------------------------\n")

async def scenario_escalation() -> None:
    print("\n" + "="*80)
    print("=== TEST 4: Escalation (High Priority Ticket Creation) ===")
    print("================================================================================\n")
    query = "I'm customer 2 and I've been charged twice, please refund immediately!"
    print(f"QUERY: {query}")
    response = await a2a_client.create_task(ROUTER_AGENT_URL, query)
    print("\n--- Router Final Response ---")
    print(response)
    print("-----------------------------\n")

async def scenario_multi_intent() -> None:
    print("\n" + "="*80)
    print("=== TEST 5: Multi-Intent (Update Email + Show History) ===")
    print("================================================================================\n")
    query = "Update my email to alice.new@corp.com for customer 4 and show my ticket history"
    print(f"QUERY: {query}")
    response = await a2a_client.create_task(ROUTER_AGENT_URL, query)
    print("\n--- Router Final Response ---")
    print(response)
    print("-----------------------------\n")


async def main():
    """Runs all scenarios with delays to respect API quotas."""
    
    print("\n--- Starting all scenarios ---")
    
    await scenario_simple_query()
    print("--- Waiting 30 seconds for quota reset... ---")
    await asyncio.sleep(30)
    
    await scenario_coordinated_query()
    print("--- Waiting 30 seconds for quota reset... ---")
    await asyncio.sleep(30)

    await scenario_complex_aggregation()
    print("--- Waiting 30 seconds for quota reset... ---")
    await asyncio.sleep(30)

    await scenario_escalation()
    print("--- Waiting 30 seconds for quota reset... ---")
    await asyncio.sleep(30)

    await scenario_multi_intent()
    print("\n--- All Scenarios Complete ---")

if __name__ == "__main__":
    # The client must be run in an event loop
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot run" in str(e):
            # This handles the "cannot run an event loop" error common in environments 
            # where the loop is already running (like Colab or jupyter)
            import nest_asyncio
            nest_asyncio.apply()
            asyncio.run(main())
        else:
            raise