# Tutorial: Setting Up Remote Admin and Worker Agents

This tutorial will guide you through setting up a remote admin agent and a worker agent on separate computers using the
Ceylon framework. We'll explain the process step-by-step and provide insights into how the system works.

## Overview

In this setup, we have two main components:

1. **Server Admin (Admin Computer)**: This is the central control point that manages worker agents.
2. **Worker Agent (Worker Computer)**: This is a separate computer that connects to the admin and performs tasks.

The goal is to establish communication between these two computers over a network.

## Step 1: Setting Up the Server Admin

### 1.1 Prepare the Admin Script

On the computer that will act as the server admin:

1. Create a new file called `remote_admin.py`.
2. Copy the following code into `remote_admin.py`:

```python
import pickle
from loguru import logger
from ceylon import CoreAdmin, Agent
from ceylon.ceylon import AgentDetail


class ServerAdminAgent(CoreAdmin):
    async def on_agent_connected(self, topic: "str", agent: AgentDetail):
        logger.info(f"ServerAdminAgent on_agent_connected {self.details().name}", agent.id, agent.name, agent.role)


class WorkerAgent1(Agent):
    async def run(self, inputs: "bytes"):
        logger.info(f"WorkerAgent1 on_run  {self.details().name}", inputs)


worker_1 = WorkerAgent1("worker_1", "server_admin", admin_port=8000)
server_admin = ServerAdminAgent("server_admin", 8000, workers=[worker_1])
server_admin.run_admin(pickle.dumps({}), [worker_1])
```

### 1.2 Understanding the Admin Script

- We define two classes: `ServerAdminAgent` (which extends `CoreAdmin`) and `WorkerAgent1` (which extends `Agent`).
- The `ServerAdminAgent` has a method to handle when an agent connects.
- We create instances of both `WorkerAgent1` and `ServerAdminAgent`.
- The admin is set to listen on port 8000.

### 1.3 Run the Admin Script

1. Open a terminal or command prompt.
2. Navigate to the directory containing `remote_admin.py`.
3. Run the script:

```bash
python remote_admin.py
```

4. The script will start and display a peer ID. It will look something like this:

```
ServerAdmin peer ID: 12D3KooWCLKVyiM5VkwYYAaDKL5rMW4WnSbMcVicMDqy23inFz3K
```

**Important:** Note down this peer ID. You'll need it for the worker script.

## Step 2: Setting Up the Worker Agent

### 2.1 Prepare the Worker Script

On a different computer that will act as the worker:

1. Create a new file called `remote_worker.py`.
2. Copy the following code into `remote_worker.py`:

```python
import asyncio
import pickle
from loguru import logger
from ceylon import Agent
from ceylon.ceylon import uniffi_set_event_loop


class WorkerAgent1(Agent):
    async def run(self, inputs: "bytes"):
        logger.info(f"WorkerAgent1 on_run  {self.details().name}", inputs)


# Replace these with the actual values from your admin computer
admin_peer_id = "12D3KooWCLKVyiM5VkwYYAaDKL5rMW4WnSbMcVicMDqy23inFz3K"
admin_ip = "192.168.1.100"
admin_port = 8000

worker_1 = WorkerAgent1("worker_2", "server_admin", role="Whatever",
                        admin_port=admin_port,
                        admin_peer=f"{admin_peer_id}@{admin_ip}:{admin_port}")
worker_1.run_worker(pickle.dumps({}))
```

### 2.2 Understanding the Worker Script

- We define a `WorkerAgent1` class similar to the admin script.
- The crucial part is setting up the `worker_1` instance with the correct `admin_peer` parameter.
- The `admin_peer` parameter combines the peer ID, IP address, and port of the admin computer.

### 2.3 Configuring the Worker Script

Before running the worker script, you need to update three key pieces of information:

1. `admin_peer_id`: Replace this with the peer ID you noted from the admin script.
2. `admin_ip`: Replace this with the IP address of the computer running the admin script.
3. `admin_port`: This should match the port the admin is listening on (8000 in our example).

### 2.4 Run the Worker Script

1. Open a terminal or command prompt on the worker computer.
2. Navigate to the directory containing `remote_worker.py`.
3. Run the script:

```bash
python remote_worker.py
```

## Step 3: Verifying the Connection

If everything is set up correctly:

1. On the admin computer, you should see a log message indicating that a worker agent has connected.
2. On the worker computer, you should see log messages about task execution and successful connection to the admin.

## Troubleshooting

If the connection isn't working:

1. **Check Network Connectivity**: Ensure both computers can reach each other over the network.
2. **Firewall Settings**: Make sure the necessary ports (e.g., 8000) are open on both computers.
3. **Double-check Configuration**: Verify that the peer ID, IP address, and port in the worker script match the admin's
   details.

## How It Works

1. The admin script starts and generates a unique peer ID.
2. The worker script uses this peer ID, along with the admin's IP and port, to establish a connection.
3. Once connected, the admin can assign tasks to the worker, and the worker can execute these tasks and report back.

This setup allows for distributed computing, where tasks can be offloaded to worker agents running on different
machines, all coordinated by a central admin agent.