# Multi-Agent Customer Service System (A2A & MCP)

This project implements a distributed, multi-agent architecture to automate complex customer service queries using Google's **Agent-to-Agent (A2A)** protocol for communication and the **Model Context Protocol (MCP)** for secure data access.

The system verifies multi-step coordination, intent negotiation, and structured data handling, meeting all assignment requirements for professional implementation.

## Architecture Overview

The system operates as three independent services coordinating via A2A interfaces:

| Agent Role | Port | Primary Function | Coordination Type |
| :--- | :--- | :--- | :--- |
| **Router Host Agent** | `11000` | Orchestrates the entire workflow, decomposes complex requests, and drives the LLM logic. | Orchestration, Negotiation |
| **Customer Data Agent** | `11001` | Executes all database CRUD operations via internal MCP-style tools. | Data Fetch (Tools) |
| **Support Agent** | `11002` | Generates the final, polite, natural language response for the customer. | Synthesis, Final Output |

## Setup and Installation

### 1. Prerequisites

* Python 3.9+ (A virtual environment is highly recommended.)
* A **Gemini API Key** (set as environment variable `GOOGLE_API_KEY`).

### 2. Local Environment Setup

1.  **Clone the repository:**
    ```bash
    git clone [YOUR_REPO_URL]
    cd [YOUR_REPO_NAME]
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the Database (MCP Data Layer):**
    This script creates the `support.db` file and populates it with test data for customers and tickets.
    ```bash
    python database_setup.py
    ```

## Execution and Testing

### 1. Launch Agent Servers

Run the deployment script to start the three A2A services in the background.

```bash
# This script launches the Router (11000), Data (11001), and Support (11002) Agents.
python run_a2a_servers.py
