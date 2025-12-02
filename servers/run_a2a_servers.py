"""
Utility script to start all three A2A agent servers:

- Router Host Agent
- Customer Data Agent
- Support Agent

You can also run each agent individually:
    python -m agents.data_agent
    python -m agents.support_agent
    python -m agents.router_agent
"""

# run_a2a_servers.py
import os
import subprocess
import sys
import time
import signal
from pathlib import Path

# Define the Agent module paths
AGENT_MODULES = {
    "router": "agents.router_agent",
    "data": "agents.data_agent",
    "support": "agents.support_agent",
}

def start_agent(name, module_path) -> subprocess.Popen:
    """Start an agent module as a background subprocess."""
    print(f"Starting {name} agent...")
    
    # We use -m to run the module, assuming the files are in the 'agents' directory
    # and contain the 'if __name__ == "__main__":' block for Uvicorn startup.
    process = subprocess.Popen(
        [sys.executable, "-m", module_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        # Use a new process group to manage cleanup gracefully
        preexec_fn=os.setsid 
    )
    return process

def main():
    processes = []
    
    # 1. Start all agents
    data_proc = start_agent("Customer Data", AGENT_MODULES["data"])
    processes.append(data_proc)
    
    support_proc = start_agent("Support", AGENT_MODULES["support"])
    processes.append(support_proc)
    
    router_proc = start_agent("Router Host", AGENT_MODULES["router"])
    processes.append(router_proc)
    
    # 2. Wait for a moment to ensure agents have time to boot and bind ports
    print("Waiting 10 seconds for servers to initialize...")
    time.sleep(10)
    
    print("\n All agents running in background.")
    print("   Run 'python run_scenarios.py' in a separate terminal to test.")
    print("   Press Ctrl+C to stop all servers.")
    
    # 3. Keep the main process alive to prevent subprocesses from being killed
    try:
        while True:
            time.sleep(1)
            # Check if any agent crashed
            if any(p.poll() is not None for p in processes):
                print("\nError: One or more agent processes crashed unexpectedly!")
                break
                
    except KeyboardInterrupt:
        print("\nStopping agents...")
        
    finally:
        # 4. Terminate all subprocesses gracefully
        for proc in processes:
            if proc.poll() is None:
                # Send signal to process group to ensure Uvicorn threads are killed
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=5)
        print("Shutdown complete.")

if __name__ == "__main__":
    # The -m ensures Python finds modules correctly inside the virtual environment
    # Note: You may need to run 'pip install uvicorn' etc. if running outside a venv
    main()