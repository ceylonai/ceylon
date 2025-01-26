# Best Practices Guide

## Core Design Principles

### 1. Single Responsibility

- Each agent should handle one primary function
- Break complex behaviors into specialized agents
- Keep message handlers focused and specific

```python
# Good
class DataValidator(Worker):
    async def validate(self, data): pass


class DataProcessor(Worker):
    async def process(self, data): pass


# Avoid
class DataHandler(Worker):
    async def validate_and_process(self, data): pass
```

### 2. Message Immutability

- Define messages using dataclasses
- Never modify received messages
- Create new instances for changes

```python
@dataclass(frozen=True)  # Enforces immutability
class TaskMessage:
    id: str
    data: Any
    timestamp: float = field(default_factory=time.time)
```

### 3. Event-Driven Architecture

- Use decorators for message handling
- Implement asynchronous communication
- Handle events independently

```python
class EventDrivenAgent(Worker):
    @on(TaskMessage)
    async def handle_task(self, msg: TaskMessage):
        await self.process_task(msg)

    @on_connect("*")
    async def handle_connection(self, topic: str, agent: AgentDetail):
        await self.initialize_connection(agent)
```

## Architecture Patterns

### 1. Layered Communication

```python
class SystemArchitecture:
    def __init__(self):
        self.layers = {
            'coordination': AdminAgent(),
            'processing': [WorkerAgent() for _ in range(3)],
            'storage': StorageAgent()
        }
```

### 2. State Management

```python
class StatefulAgent(Worker):
    def __init__(self):
        self.state = AgentState.IDLE
        self._transitions = {
            AgentState.IDLE: [AgentState.PROCESSING],
            AgentState.PROCESSING: [AgentState.COMPLETED, AgentState.ERROR]
        }

    async def transition(self, new_state: AgentState):
        if new_state in self._transitions[self.state]:
            self.state = new_state
```

### 3. Resource Management

```python
class ResourceAwareAgent(Worker):
    async def __aenter__(self):
        await self.initialize_resources()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup_resources()
```

## Error Handling and Resilience

### 1. Graceful Error Recovery

```python
class ResilientAgent(Worker):
    async def execute_with_retry(self, task, max_retries=3):
        for attempt in range(max_retries):
            try:
                return await self.process(task)
            except Exception as e:
                if attempt == max_retries - 1:
                    await self.handle_failure(task, e)
                await asyncio.sleep(2 ** attempt)
```

### 2. Circuit Breaking

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = 'closed'

    async def call(self, func, *args):
        if self.state == 'open':
            raise CircuitBreakerOpen()

        try:
            result = await func(*args)
            self.failures = 0
            return result
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = 'open'
                asyncio.create_task(self.reset_timer())
            raise
```

## Performance Optimization

### 1. Message Batching

```python
class BatchProcessor(Worker):
    def __init__(self, batch_size=100):
        self.batch = []
        self.batch_size = batch_size

    async def process(self, item):
        self.batch.append(item)
        if len(self.batch) >= self.batch_size:
            await self.process_batch(self.batch)
            self.batch = []
```

### 2. Resource Pooling

```python
class ResourcePool:
    def __init__(self, pool_size):
        self.pool = asyncio.Queue(pool_size)
        self.semaphore = asyncio.Semaphore(pool_size)

    async def acquire(self):
        async with self.semaphore:
            return await self.pool.get()

    async def release(self, resource):
        await self.pool.put(resource)
```

## Security Best Practices

### 1. Message Authentication

```python
class SecureAgent(Worker):
    def authenticate_message(self, message, signature):
        return hmac.verify(
            message.content,
            signature,
            self.secret_key
        )
```

### 2. Access Control

```python
class SecureWorker(Worker):
    async def on_message(self, agent: AgentDetail, data: bytes, time: int):
        if not self.authorize_peer(agent.id):
            logger.warning(f"Unauthorized message from {agent.id}")
            return
        await self.process_message(data)
```

## Monitoring and Observability

### 1. Structured Logging

```python
class ObservableAgent(Worker):
    async def log_event(self, event_type, **kwargs):
        logger.info(
            f"{event_type}",
            agent_id=self.id,
            timestamp=time.time(),
            **kwargs
        )
```

### 2. Metrics Collection

```python
class MetricsCollector:
    def __init__(self):
        self.metrics = {
            'messages_processed': Counter(),
            'processing_time': Histogram(),
            'error_rate': Gauge()
        }

    async def record(self, metric, value):
        self.metrics[metric].record(value)
```

## Implementation Guidelines

### 1. Message Design

- Include metadata for tracking
- Add validation methods
- Use clear naming conventions

```python
@dataclass
class Message:
    id: str = field(default_factory=uuid.uuid4)
    timestamp: float = field(default_factory=time.time)
    payload: Any
    metadata: Dict = field(default_factory=dict)

    def validate(self) -> bool:
        return bool(self.payload)
```

### 2. Communication Patterns

- Use broadcast for system-wide messages
- Direct messages for point-to-point
- Topic-based for selective communication

```python
class CommunicationPatterns:
    async def broadcast_update(self, update):
        await self.broadcast_message(update)

    async def direct_message(self, peer_id, message):
        await self.send_message(peer_id, message)

    async def topic_message(self, topic, message):
        await self.publish(topic, message)
```

### 3. State Transitions

- Define clear state machines
- Validate transitions
- Log state changes

```python
class WorkflowAgent(Worker):
    async def transition_state(self, new_state):
        if new_state not in self.valid_transitions[self.current_state]:
            raise InvalidTransition(f"{self.current_state} -> {new_state}")

        self.current_state = new_state
        await self.log_event("state_change", new_state=new_state)
```

## Common Pitfalls

1. Race Conditions

- Use synchronization primitives
- Implement proper locking
- Handle concurrent access

2. Memory Leaks

- Clean up resources properly
- Implement context managers
- Monitor memory usage

3. Message Overflow

- Implement backpressure
- Use flow control
- Handle queue limits

4. Error Propagation

- Define error boundaries
- Implement recovery strategies
- Log error contexts

## Best Practices Checklist

### Design

- [ ] Single responsibility per agent
- [ ] Clear message contracts
- [ ] Proper state management
- [ ] Error handling strategy

### Implementation

- [ ] Immutable messages
- [ ] Resource cleanup
- [ ] Proper logging
- [ ] Security measures

### Operation

- [ ] Monitoring setup
- [ ] Performance metrics
- [ ] Error tracking
- [ ] Resource monitoring

## Deployment Considerations

### Configuration

```python
class ConfigurableAgent(Worker):
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.validate_config()
```

### Resource Limits

```python
class ResourceLimits:
    def __init__(self):
        self.max_connections = int(os.getenv('MAX_CONNECTIONS', 100))
        self.message_timeout = int(os.getenv('MESSAGE_TIMEOUT', 30))
```

### Health Checks

```python
class HealthCheck(Worker):
    async def check_health(self):
        return {
            'status': 'healthy',
            'connections': len(self.connections),
            'message_rate': self.message_counter.rate()
        }
```