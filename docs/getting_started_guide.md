# Ceylon Agent Framework - Getting Started Guide

## Installation

```bash
pip install ceylon
```

## Core Concepts

- **Admin Agent**: Central coordinator for the agent network
- **Worker Agent**: Client agents that connect to the admin
- **Handlers**: Functions that process messages and events

## Basic Usage

### 1. Create Agents

```python
from ceylon.base.agents import Admin, Worker

# Create admin agent
admin = Admin(
    name="admin",
    port=8888,
    role="admin"
)

# Create worker agent
worker = Worker(
    name="worker1",
    role="worker",
    admin_peer="admin"  # Optional: specify admin to connect to
)
```

### 2. Define Message Types

```python
from pydantic.dataclasses import dataclass


@dataclass
class Message:
    content: str
```

### 3. Add Message Handlers

```python
@admin.on(Message)
async def handle_message(data: Message, time: int, agent: AgentDetail):
    print(f"Received: {data.content} from {agent.name}")
```

### 4. Add Connection Handlers

```python
@worker.on_connect("*")  # Handle all connections
async def on_connect(topic: str, agent: AgentDetail):
    print(f"Connected to {agent.name} with role {agent.role}")


@worker.on_connect("*:worker")  # Handle specific role connections
async def on_worker_connect(topic: str, agent: AgentDetail):
    print(f"Worker connected: {agent.name}")
```

### 5. Add Run Handlers

```python
@worker.on_run()
async def run_worker(inputs: bytes):
    while True:
        await worker.broadcast_message(Message(content="Hello"))
        await asyncio.sleep(1)
```

### 6. Start the Network

```python
import asyncio

if __name__ == '__main__':
    asyncio.run(admin.start_agent(workers=[worker]))
```

## Key Features

- Automatic message serialization/deserialization
- Built-in event handling
- Role-based connection management
- Async communication patterns
- Pattern-based message routing

## Best Practices

1. Use dataclasses for message types
2. Handle connection events for network awareness
3. Implement error handling in message processors
4. Use meaningful agent names and roles
5. Structure long-running tasks in run handlers