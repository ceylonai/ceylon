import logging

from rk_core import Event, Processor, EventType, AgentManager


# import names

# logging.basicConfig(level=logging.INFO)


class EchoAgent:
    def __init__(self, name):
        self.name = name

    @Processor(event_type=EventType.Start)
    async def start1(self, event: Event):
        print(f"{self.name} started on {event.creator} {event.event_type}")
        await self.publisher.publish("Hello, world!")

    @Processor(event_type=EventType.Data)
    async def act1(self, event: Event):
        print(f"-------{self.name} received: {event.content}")


class GreetingAgent:
    def __init__(self, name):
        self.name = name

    @Processor(event_type=EventType.Start)
    async def start2(self, event: Event):
        print(f"-------{self.name} started on {event.creator} {event.event_type}")

    @Processor(event_type=EventType.Data)
    async def act2(self, event: Event):
        print(f"-------{self.name} received: {event.content}")
        message = "GreetingAgent Say Hi How Are you doing?"
        await self.publisher.publish(message)


if __name__ == "__main__":
    echo_agent = EchoAgent("EchoAgent")
    greeting_agent = GreetingAgent("GreetingAgent")

    agent_manager = AgentManager()
    agent_manager.register_agent(echo_agent)
    agent_manager.register_agent(greeting_agent)
    agent_manager.start()
