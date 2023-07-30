# RAKUN: A Rust-Python Multi-Agent System Framework with Plugable Communication

RAKUN is a robust multi-agent system framework developed with the Python programming language, fused with the efficiency
and safety of Rust via the PyO3 project. This unique combination ensures high performance and superior safety standards
for your Python development projects.

One of the core strengths of RAKUN is its pluggable communication feature. This means the framework is designed to work
with various communication protocols, based on user requirements. Its built-in libp2p integration facilitates
peer-to-peer (P2P) communication between agents, making the system highly decentralized and scalable. However, should
the project requirements change, the communication protocol can be easily swapped out to match your specific needs,
removing the dependency on a specific third-party message-passing library. This flexibility is what sets RAKUN apart and
ensures the framework can adapt to a wide range of scenarios.

## Overview

In the RAKUN framework, an agent is defined as a discrete unit that independently performs tasks in an asynchronous
manner while communicating with its fellow agents. These agents are constructed as Python classes, encapsulating the
specific actions and behaviors they're responsible for. The orchestration of these agents, including their lifecycle
management and communication handling, is overseen by a specialized component known as the `AgentManager`. This means
the `AgentManager` is responsible for initiating, supervising, and terminating the agents, as well as facilitating their
interactions.

## Key Features

- **Rust-PyO3 Bridge**: The framework amalgamates the robustness and speed of Rust with Python's versatility and
  simplicity through the PyO3 interface. This innovative blend allows developers to leverage the strengths of both
  languages.

- **Pluggable Communication**: While it natively incorporates the libp2p library for decentralized, peer-to-peer
  communication among agents, it also supports the flexibility to plug-in different communication protocols as per
  project requirements, ensuring a scalable and resilient networking setup.

- **Asynchronous Operations**: RAKUN enables defining and handling of asynchronous tasks, thereby significantly
  enhancing the system's performance and responsiveness.

- **Modular Design**: RAKUN's agent-centric model fosters a modular approach, encouraging the development of reusable
  and maintainable code segments.

## Usage

RAKUN's potential can be best understood through real-world applications. Consider the design of an advanced smart home
system. In this scenario, multiple agents can each manage a unique aspect of the smart home.

- **TemperatureAgent**: Monitors the ambient temperature and communicates with other agents to ensure the home stays
  comfortable. For instance, if the temperature rises above a certain level, the TemperatureAgent could send a signal to
  the AirConditioningAgent.

- **AirConditioningAgent**: Receives signals from the TemperatureAgent or HumidityAgent and accordingly controls the air
  conditioning system to maintain optimal conditions.

- **LightingAgent**: Responds to light conditions outside and within the home, time of the day, or direct instructions
  from the homeowner, and communicates with individual LightAgents.

- **LightAgent**: Each light in the home could be managed by its own agent, taking instructions from the LightingAgent
  to dim, brighten, switch on, or switch off.

- **SecurityAgent**: Manages the overall security of the home, communicating with DoorAgents and WindowAgents to ensure
  the home is secure.

- **DoorAgent and WindowAgent**: Monitor the status of each door and window, respectively, sending status updates to the
  SecurityAgent.

In this multi-agent setup, each agent independently manages its assigned task, but through effective communication, they
operate collectively as an intelligent smart home system. This is just one example of how RAKUN can be used. The
framework is versatile enough to support a broad range of scenarios and use cases, from managing infrastructure systems
to coordinating activities in a warehouse or factory.

### Defining an Agent

Each agent is a Python class where you define the tasks that the agent should perform. The `@Processor` decorator is
used to associate an event type that triggers a function.

```python
class EchoAgent:
    def __init__(self, name):
        self.name = name
        self.count = 0

    @Processor(event_type=EventType.OnBoot)
    async def on_start(self):
        while True:
            self.count += 1
            await asyncio.sleep(1)
            print(f"{self.name} on_start")
```

### Registering and Running Agents

After defining the agents, they are registered with the `AgentManager`, which manages their execution and communication.

```python
if __name__ == "__main__":
    echo_agent = EchoAgent("EchoAgent")
    greeting_agent = GreetingAgent("GreetingAgent")
    agent_manager = AgentManager()
    agent_manager.register(greeting_agent, 1)
    agent_manager.register(echo_agent, 2)
    agent_manager.start()
```

### Inter-Agent Communication

For communication, the framework leverages libp2p for inter-agent messaging. Agents can publish messages using
the `publish` method, which are then propagated to other agents. The messages can be any byte or bytearray type, making
it possible to send a variety of data types and structures.

```python
await self.publisher.publish(byte_message)
```

## Conclusion

The rk_core framework opens up new avenues for efficient, scalable, and robust multi-agent system development in Python.
With the powerful combination of Rust and PyO3 at its core and the decentralized communication capabilities offered by
libp2p, rk_core stands out from traditional Python-based agent frameworks. Whether designing a small system with few
agents or a large-scale complex multi-agent system, rk_core offers the flexibility and performance you need.

```
