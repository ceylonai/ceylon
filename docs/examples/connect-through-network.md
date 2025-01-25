# Remote Agents

## System Components

### 1. Server (server.py)

```python
from ceylon import Admin

app = Admin(name="admin", port=8888, role="admin")


@app.on_run()
async def run_worker(inputs: bytes):
    while True:
        await app.broadcast_message("Hello World from Server")
```

The server broadcasts messages continuously to all connected workers.

### 2. Worker (worker_agent.py)

```python
from ceylon import Worker

worker = Worker(name="worker", port=8888, role="worker")


@worker.on(str)
async def on_message(agent_id: str, data: str, time: int):
    print(f"Received message from {agent_id}: {data} at {time}")
```

The worker listens for and processes messages from the server.

### 3. Configuration (.ceylon_network)

```
WORKSPACE_ID=default
WORKSPACE_IP=127.0.0.1
WORKSPACE_PEER=12D3KooWMrqMLuYL3vExw7qaBJRzjN43kkkZwqSxUog7oaQCmnFE
WORKSPACE_PORT=8888
```

## Setup Instructions

1. Start the Server:
   ```bash
   python server.py
   ```
   - Server creates .ceylon_network file with connection details
   - WORKSPACE_PEER is auto-generated unique identifier

2. Start Worker(s):
   ```bash
   python worker_agent.py
   ```
   - Worker reads .ceylon_network file
   - Connects to server using WORKSPACE_PEER

## Remote Connection Setup

1. Copy .ceylon_network to remote machine
2. Update WORKSPACE_IP if needed
3. Run worker_agent.py on remote machine

## Network Configuration

- Default port: 8888
- Local IP: 127.0.0.1
- For remote connections:
   - Update WORKSPACE_IP to server's IP
   - Ensure port 8888 is accessible

## Common Issues

1. Connection Failures
   - Verify .ceylon_network file exists
   - Check WORKSPACE_IP and port accessibility
   - Ensure WORKSPACE_PEER matches server

2. Network Constraints
   - Configure firewalls to allow port 8888
   - Use correct IP for non-local connections

## Security Notes

- WORKSPACE_PEER acts as unique identifier
- Keep .ceylon_network secure for controlled access
- Update configuration for production environments