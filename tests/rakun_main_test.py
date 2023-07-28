import asyncio
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
        logging.info(f"{self.name} started on {event.creator} {event.event_type}")
        while True:
            await self.publisher.publish(f"EchoAgent Hello, world! {self.count}")
            self.count += 1
            await asyncio.sleep(5)

    @Processor(event_type=EventType.Data)
    async def act1(self, event: Event):
        logging.info(f"-------{self.name} ඈඇ received: {event.content}")


class GreetingAgent:
    def __init__(self, name):
        self.name = name
        self.count = 0

    @Processor(event_type=EventType.Start)
    async def start2(self, event: Event):
        logging.info(f"-------{self.name} started on {event.creator} {event.event_type}")

    @Processor(event_type=EventType.Data)
    async def act2(self, event: Event):
        message = f"GreetingAgent Say Hi How Are you doing? {self.count}"
        await self.publisher.publish(message)
        self.count += 1
        logging.info(f"-------{self.name} received:  ඵ්{event.creator} {event.content}")


if __name__ == "__main__":
    echo_agent = EchoAgent("EchoAgent")
    greeting_agent = GreetingAgent("GreetingAgent")
    agent_manager = AgentManager()
    agent_manager.register(greeting_agent, 1)
    agent_manager.register(echo_agent, 2)
    agent_manager.start()
