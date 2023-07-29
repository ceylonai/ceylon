import asyncio
import logging

logging.basicConfig(level=logging.INFO)
from rk_core import Event, Processor, EventType, AgentManager, startup, shutdown


# import names


class EchoAgent:
    def __init__(self, name):
        self.name = name
        self.count = 0

    @Processor(event_type=EventType.OnBoot)
    async def on_start(self):
        # while True:
        print(f"EchoAgent Hello, world! {self.count}")
        self.count += 1
        await asyncio.sleep(1)
        print(f"EchoAgent Finished, world! {self.count}")

    @Processor(event_type=EventType.OnShutdown)
    async def on_shutdown(self):
        print(f"EchoAgent Bye, world! {self.count}")

    @Processor(event_type=EventType.Start)
    async def start1(self, event: Event):
        print(f"{self.name} started on {event.creator} {event.event_type}")
        await self.publisher.publish(bytes(f"EchoAgent Hello, world! {self.count}", encoding='utf-8'))

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
        await self.publisher.publish(bytes(message, encoding='utf-8'))
        self.count += 1
        print(f"-------{self.name} received:  ඵ්{event.creator} {event.content}")


if __name__ == "__main__":
    echo_agent = EchoAgent("EchoAgent")
    greeting_agent = GreetingAgent("GreetingAgent")
    agent_manager = AgentManager()
    agent_manager.register(greeting_agent, 1)
    agent_manager.register(echo_agent, 2)
    agent_manager.start()
