# Ceylon Framework Core Concepts Guide

## Agent System Architecture

### Admin Agent
The central coordinator in a Ceylon system.

```python
from ceylon import Admin

class CoordinatorAdmin(Admin):
    def __init__(self, name="coordinator", port=8888):
        super().__init__(name=name, port=port)
```

Key characteristics:
- One admin per system
- Manages worker connections
- Coordinates task distribution
- Handles system-wide state

### Worker Agent
Performs specific tasks within the system.

```python
from ceylon import Worker

class TaskWorker(Worker):
    def __init__(self, name: str, role: str):
        super().__init__(name=name, role=role)
```

Key characteristics:
- Multiple workers per system
- Specialized task execution
- Reports to admin agent
- Independent operation

## Message System

### Message Types
```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Message:
    id: str
    content: Any
    timestamp: float
```

Core message principles:
- Immutable data structures
- Type-safe communication
- Metadata inclusion
- Serializable format

### Message Handlers
```python
from ceylon import on, on_run, on_connect

class MessageHandling:
    @on(MessageType)
    async def handle_specific(self, msg: MessageType):
        # Handle specific message type
        pass
    
    @on_run()
    async def handle_run(self, inputs: bytes):
        # Main execution loop
        pass
    
    @on_connect("*")
    async def handle_connection(self, topic: str, agent: AgentDetail):
        # Connection handling
        pass
```

## Communication Patterns

### Direct Communication
```python
class DirectCommunication(Worker):
    async def send_to_peer(self, peer_id: str, data: Any):
        await self.send_message(peer_id, data)
```

### Broadcast Communication
```python
class BroadcastCommunication(Admin):
    async def notify_all(self, data: Any):
        await self.broadcast_message(data)
```

## State Management

### Agent State
```python
from enum import Enum

class AgentState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"

class StateManagement(Worker):
    def __init__(self):
        super().__init__()
        self.state = AgentState.IDLE
```

### State Transitions
```python
class StatefulAgent(Worker):
    async def transition_state(self, new_state: AgentState):
        old_state = self.state
        self.state = new_state
        await self.notify_state_change(old_state, new_state)
```

## Event Processing

### Event Handling
```python
class EventProcessor(Worker):
    @on(Event)
    async def process_event(self, event: Event):
        if self.can_handle(event):
            await self.handle_event(event)
        else:
            await self.forward_event(event)
```

### Event Flow
```python
class EventFlow(Admin):
    async def manage_event_flow(self, event: Event):
        # Preprocessing
        processed_event = await self.preprocess(event)
        
        # Distribution
        await self.distribute_event(processed_event)
        
        # Monitoring
        await self.monitor_event_processing(processed_event)
```

## Resource Management

### Resource Lifecycle
```python
class ResourceManager(Worker):
    async def __aenter__(self):
        await self.acquire_resources()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release_resources()
```

### Resource Pooling
```python
class ResourcePool:
    def __init__(self, size: int):
        self.pool = asyncio.Queue(size)
        self.in_use = set()
    
    async def acquire(self):
        resource = await self.pool.get()
        self.in_use.add(resource)
        return resource
    
    async def release(self, resource):
        self.in_use.remove(resource)
        await self.pool.put(resource)
```

## Error Handling

### Basic Error Handling
```python
class ErrorHandler(Worker):
    async def safe_execute(self, task):
        try:
            return await self.execute_task(task)
        except Exception as e:
            await self.handle_error(task, e)
            raise
```

### Retry Mechanism
```python
class RetryMechanism(Worker):
    async def with_retry(self, operation, max_retries=3):
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
```

## System Integration

### External Service Integration
```python
class ServiceIntegrator(Worker):
    async def interact_with_service(self, service_request):
        # Convert to external format
        external_request = self.convert_request(service_request)
        
        # Make external call
        response = await self.call_service(external_request)
        
        # Convert response back
        return self.convert_response(response)
```

### Data Flow
```python
class DataFlowManager(Admin):
    async def manage_data_flow(self, data):
        # Input validation
        validated_data = await self.validate(data)
        
        # Processing
        processed_data = await self.process(validated_data)
        
        # Distribution
        await self.distribute(processed_data)
```

## Core Utilities

### Message Conversion
```python
class MessageConverter:
    @staticmethod
    def to_bytes(message: Any) -> bytes:
        return pickle.dumps(message)
        
    @staticmethod
    def from_bytes(data: bytes) -> Any:
        return pickle.loads(data)
```

### Agent Identification
```python
class AgentIdentification:
    @staticmethod
    def create_agent_id(name: str, role: str) -> str:
        return f"{name}_{role}_{uuid.uuid4()}"
```

## System Lifecycle

### Initialization
```python
async def initialize_system():
    # Create admin
    admin = AdminAgent(port=8888)
    
    # Create workers
    workers = [
        WorkerAgent(f"worker_{i}")
        for i in range(3)
    ]
    
    # Start system
    await admin.start_agent(b"", workers)
```

### Shutdown
```python
async def shutdown_system(admin: Admin, workers: List[Worker]):
    # Stop workers
    for worker in workers:
        await worker.stop()
    
    # Stop admin
    await admin.stop()
```

## Key Concepts Summary

1. **Agent Hierarchy**
    - Admin agents coordinate
    - Worker agents execute
    - Clear responsibility separation

2. **Message-Based Communication**
    - Type-safe messages
    - Asynchronous processing
    - Event-driven architecture

3. **State Management**
    - Clear state definitions
    - Controlled transitions
    - State monitoring

4. **Resource Handling**
    - Proper initialization
    - Clean cleanup
    - Resource pooling

5. **Error Management**
    - Graceful error handling
    - Retry mechanisms
    - Error reporting

These core concepts provide the foundation for building robust distributed systems with Ceylon.