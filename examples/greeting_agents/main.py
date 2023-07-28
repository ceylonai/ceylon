import logging

logging.basicConfig(level=logging.INFO)
from rk_core import Event, Processor, EventType, AgentManager


# import names


class EchoAgent:
    def __init__(self, name):
        self.name = name
        self.count = 0

    @Processor(event_type=EventType.Start)
    async def start1(self, event: Event):
        print(f"{self.name} started on {event.creator} {event.event_type}")
        await self.publisher.publish(f"EchoAgent Hello, world! {self.count}")
        self.count += 1

    @Processor(event_type=EventType.Data)
    async def act1(self, event: Event):
        print(f"-------{self.name} ඈඇ received: {event.content}")


class GreetingAgent:
    def __init__(self, name):
        self.name = name
        self.count = 0

    @Processor(event_type=EventType.Start)
    async def start2(self, event: Event):
        print(f"-------{self.name} started on {event.creator} {event.event_type}")

    @Processor(event_type=EventType.Data)
    async def act2(self, event: Event):
        message = f"GreetingAgent Say Hi How Are you doing? {self.count}"
        await self.publisher.publish(message)
        self.count += 1
        print(f"-------{self.name} received:  ඵ්{event.creator} {event.content}")


if __name__ == "__main__":
    echo_agent = EchoAgent("EchoAgent")
    greeting_agent = GreetingAgent("GreetingAgent")
    # greeting_agent2 = GreetingAgent("GreetingAgent2")

    agent_manager = AgentManager()
    agent_manager.register_agent(echo_agent)
    agent_manager.register_agent(greeting_agent)
    # agent_manager.register_agent(greeting_agent2)
    agent_manager.start()
