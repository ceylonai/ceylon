# Tutorials

## Introduction

Ceylon is a distributed framework for building multi-agent systems. This guide covers core concepts, best practices, and API usage.

## Core Components

### 1. Agent Types

#### Admin Agent
```python
from ceylon import Admin

class CoordinatorAgent(Admin):
    def __init__(self, name="coordinator", port=8888):
        super().__init__(name=name, port=port)
        
    async def on_agent_connected(self, topic: str, agent: AgentDetail):
        # Handle new agent connections
        pass
```

- Central coordinator for the system
- Manages worker connections
- Handles task distribution
- One admin per system

#### Worker Agent
```python
from ceylon import Worker

class TaskWorker(Worker):
    def __init__(self, name: str):
        super().__init__(name=name, role="worker")
        
    async def on_message(self, agent: AgentDetail, data: bytes, time: int):
        # Process received messages
        pass
```

- Performs specific tasks
- Reports to admin agent
- Multiple workers can run simultaneously

### 2. Message Handling

#### Event Decorators
```python
from ceylon import on, on_run, on_connect

class CustomAgent(Worker):
    @on(MessageType)
    async def handle_message(self, msg: MessageType, time: int, agent: AgentDetail):
        # Process specific message type
        pass
        
    @on_run()
    async def handle_run(self, inputs: bytes):
        # Main execution loop
        pass
        
    @on_connect("*")
    async def handle_connection(self, topic: str, agent: AgentDetail):
        # Handle new connections
        pass
```

#### Message Types
Define message types using dataclasses:
```python
from dataclasses import dataclass

@dataclass
class TaskMessage:
    id: int
    data: str
    priority: int = 1

@dataclass
class ResultMessage:
    task_id: int
    result: str
```

## Best Practices

### 1. Message Design
```python
@dataclass
class Message:
    # Include metadata
    id: str
    timestamp: float
    
    # Add validation
    def validate(self) -> bool:
        return bool(self.id and self.timestamp)
```

- Use dataclasses for message structure
- Include metadata for tracking
- Add validation methods

### 2. Error Handling
```python
class ResilientWorker(Worker):
    async def process_task(self, task):
        try:
            result = await self.execute_task(task)
            await self.send_result(result)
        except Exception as e:
            logger.error(f"Task failed: {e}")
            await self.handle_failure(task)
```

- Catch and log exceptions
- Implement retry mechanisms
- Handle cleanup properly

### 3. State Management
```python
from enum import Enum

class AgentState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"

class StatefulAgent(Worker):
    def __init__(self):
        super().__init__()
        self.state = AgentState.IDLE
        
    async def transition(self, new_state: AgentState):
        old_state = self.state
        self.state = new_state
        logger.info(f"State transition: {old_state} -> {new_state}")
```

### 4. Resource Management
```python
class ResourceAgent(Worker):
    def __init__(self):
        super().__init__()
        self.resources = {}
        
    async def cleanup(self):
        try:
            # Release resources
            for resource in self.resources.values():
                await resource.close()
        finally:
            await self.broadcast_shutdown()
```

## Common Patterns

### 1. Task Distribution
```python
class TaskDistributor(Admin):
    def __init__(self):
        super().__init__()
        self.worker_loads = {}
        
    async def assign_task(self, task):
        available_workers = [w for w in self.worker_loads.items() 
                           if w[1] < self.max_load]
        if not available_workers:
            raise NoAvailableWorkersError()
            
        worker = min(available_workers, key=lambda x: x[1])[0]
        await self.send_message(worker, task)
        self.worker_loads[worker] += 1
```

### 2. Event Processing
```python
class EventProcessor(Worker):
    def __init__(self):
        super().__init__()
        self.handlers = {
            'data': self.handle_data,
            'control': self.handle_control,
            'status': self.handle_status
        }
    
    async def on_message(self, agent: AgentDetail, data: bytes, time: int):
        message = pickle.loads(data)
        handler = self.handlers.get(message.type)
        if handler:
            await handler(message)
```

### 3. Pipeline Processing
```python
class PipelineStage(Worker):
    def __init__(self, next_stage_id: str = None):
        super().__init__()
        self.next_stage = next_stage_id
        
    async def process(self, data):
        result = await self.transform(data)
        if self.next_stage:
            await self.send_message(self.next_stage, result)
        return result
```

## Practical Examples

### 1. Auction System
```python
@dataclass
class Bid:
    bidder: str
    amount: float

class AuctionManager(Admin):
    def __init__(self, item, min_price):
        super().__init__()
        self.item = item
        self.min_price = min_price
        self.bids = []
        
    @on(Bid)
    async def handle_bid(self, bid: Bid, time: int, agent: AgentDetail):
        if bid.amount >= self.min_price:
            self.bids.append(bid)
            await self.broadcast_new_bid(bid)
```

### 2. Task Scheduler
```python
@dataclass
class ScheduledTask:
    id: str
    execute_at: float
    data: Any

class Scheduler(Admin):
    def __init__(self):
        super().__init__()
        self.task_queue = []
        
    async def schedule_task(self, task: ScheduledTask):
        heapq.heappush(self.task_queue, (task.execute_at, task))
        await self.check_queue()
```

## Performance Optimization

### 1. Message Batching
```python
class BatchProcessor(Worker):
    def __init__(self, batch_size=100):
        super().__init__()
        self.batch_size = batch_size
        self.batch = []
        
    async def add_to_batch(self, item):
        self.batch.append(item)
        if len(self.batch) >= self.batch_size:
            await self.process_batch()
```

### 2. Caching
```python
from functools import lru_cache

class CachedWorker(Worker):
    def __init__(self):
        super().__init__()
        self.cache = {}
        
    @lru_cache(maxsize=1000)
    def compute_result(self, input_data):
        return expensive_computation(input_data)
```

## Logging and Monitoring

### 1. Structured Logging
```python
from loguru import logger

class LoggedAgent(Worker):
    async def on_message(self, agent: AgentDetail, data: bytes, time: int):
        logger.info(f"Message received", 
                   agent_id=agent.id,
                   message_size=len(data),
                   timestamp=time)
```

### 2. Metrics Collection
```python
class MetricsAgent(Worker):
    def __init__(self):
        super().__init__()
        self.metrics = {
            'messages_processed': 0,
            'errors': 0,
            'processing_time': []
        }
        
    async def record_metric(self, name, value):
        self.metrics[name] = value
        await self.report_metrics()
```

## Security Considerations

### Message Validation
```python
class SecureAgent(Worker):
    def validate_message(self, message):
        return (
            self.verify_signature(message) and
            self.check_permissions(message.sender)
        )
```

### Access Control
```python
class AuthenticatedAgent(Worker):
    def __init__(self):
        super().__init__()
        self.authorized_peers = set()
        
    async def on_message(self, agent: AgentDetail, data: bytes, time: int):
        if agent.id not in self.authorized_peers:
            logger.warning(f"Unauthorized message from {agent.id}")
            return
```

## Deployment Tips

1. Use environment variables for configuration
2. Implement proper shutdown handlers
3. Monitor system resources
4. Set up logging aggregation
5. Implement health checks

## Common Pitfalls to Avoid

1. Modifying received messages
2. Blocking operations in message handlers
3. Missing error handling
4. Inadequate logging
5. Poor resource cleanup

## Additional Resources

- Ceylon Documentation: [https://docs.ceylon.ai](https://docs.ceylon.ai)
- GitHub Repository: [https://github.com/ceylon-ai/ceylon](https://github.com/ceylon-ai/ceylon)
- API Reference: [https://docs.ceylon.ai/api](https://docs.ceylon.ai/api)