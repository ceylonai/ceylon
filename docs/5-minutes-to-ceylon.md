# Ceylon Minimal Playground Tutorial

## Installation

First, install Ceylon and its dependencies:

```bash
pip install ceylon loguru
```

## Basic Concepts

Ceylon is a framework for building distributed systems. The minimal approach uses:

1. **BasePlayground**: Coordinates message passing between agents
2. **Worker**: An agent that can send and receive messages
3. **Message Handlers**: Functions that process specific types of messages

## Simple Example

Here's a minimal example showing the core functionality:

```python
import asyncio
from dataclasses import dataclass

from loguru import logger
from ceylon import Worker, AgentDetail
from ceylon.base.playground import BasePlayGround


# Define a message type
@dataclass
class SimpleMessage:
    content: str


# Create playground and agent
playground = BasePlayGround(name="minimal_demo")
agent = Worker("worker1")


# Define message handler
@agent.on(SimpleMessage)
async def handle_message(message: SimpleMessage, sender: AgentDetail, time: int):
    logger.info(f"From {sender.name} received: {message.content}")


async def main():
    async with playground.play(workers=[agent]) as active_playground:
        message = SimpleMessage(content="Hello from worker1!")
        await active_playground.broadcast_message(message)


if __name__ == "__main__":
    asyncio.run(main())
```

## Breaking Down the Components

### 1. Message Types

Messages are defined using dataclasses:

```python
@dataclass
class SimpleMessage:
    content: str
```

### 2. Playground and Agent

Create instances at module level:

```python
playground = BasePlayGround(name="minimal_demo")
agent = Worker("worker1")
```

### 3. Message Handler

Use the `@agent.on` decorator to handle specific message types:

```python
@agent.on(SimpleMessage)
async def handle_message(message: SimpleMessage, sender: AgentDetail, time: int):
    logger.info(f"From {sender.name} received: {message.content}")
```

### 4. Message Broadcasting

Send messages through the playground:

```python
await active_playground.broadcast_message(message)
```

## Common Use Cases

1. **System Monitoring**
    - Agents sending status updates
    - Collecting metrics

2. **Event Processing**
    - Handling events in distributed systems
    - Event broadcasting

3. **Simple Communication**
    - Message passing between components
    - Basic coordination

## Best Practices

1. **Message Design**
    - Keep message classes simple
    - Use dataclasses for message definitions
    - Include only necessary fields

2. **Handler Organization**
    - One handler per message type
    - Clear handler naming
    - Focused handler functionality

3. **Resource Management**
    - Use async context managers
    - Proper cleanup in handlers
    - Handle errors appropriately

## Common Extensions

1. Add multiple message types:

```python
@dataclass
class StatusMessage:
    status: str


@agent.on(StatusMessage)
async def handle_status(message: StatusMessage, sender: AgentDetail, time: int):
    logger.info(f"Status from {sender.name}: {message.status}")
```

2. Add multiple agents:

```python
agent1 = Worker("worker1")
agent2 = Worker("worker2")

async with playground.play(workers=[agent1, agent2]) as active_playground:
# Your code here
```

## Troubleshooting

1. **Messages not being received**
    - Check handler decorator matches message type
    - Verify playground has started properly
    - Ensure agent is in workers list

2. **Type errors**
    - Verify message class matches handler
    - Check dataclass field types
    - Ensure proper async/await usage

## Next Steps

1. Explore more complex message types
2. Add multiple agents
3. Implement different message patterns
4. Add error handling
5. Explore other Ceylon features

## Resources

- Ceylon Documentation: https://docs.ceylon.ai
- GitHub Repository: https://github.com/ceylon-ai/ceylon