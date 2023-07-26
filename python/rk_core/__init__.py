import asyncio
import logging
import uuid
from multiprocessing import allow_connection_pickling
import random
from threading import Thread

from rk_core import rk_core
from rk_core.rk_core import FunctionInfo, EventProcessor, MessageProcessor, Server, EventType, Event

__doc__ = rk_core.__doc__
if hasattr(rk_core, "__all__"):
    __all__ = rk_core.__all__

logging.basicConfig(level=logging.CRITICAL)

rakun_version = rk_core.get_version()
logging.info(f"Rakun version: {rakun_version}")


class AgentWrapper:
    def __init__(self, agent):
        self.id = uuid.uuid4()
        self.agent = agent
        self.start_time = None
        self.server = Server(agent.name)
        self.count = 0
        self.server.add_event_processor(
            EventProcessor("__event__processor__",
                           FunctionInfo(self.__event__processor__, True, 1),
                           EventType.Start))
        self.server.add_event_processor(
            EventProcessor("__data__processor__",
                           FunctionInfo(self.__data__processor__, True, 1),
                           EventType.Data))
        self.publisher = MessageProcessor()
        self.publisher.start()

    async def __event__processor__(self, data: Event):
        print(
            f"Received message to {self.agent.name}: {data.content} {data.creator} {data.event_type} {data.origin_type}")

        while True:
            self.publisher.publish(f"Greeting from {self.id} {self.agent.name}")
            sleep_time = random.randint(5, 15)
            await asyncio.sleep(sleep_time)

    async def __data__processor__(self, data: Event):
        print(
            f"Received message to Data Processor {self.agent.name}: {data.content} {data.creator} {data.event_type} {data.origin_type}")

    def __start__(self):
        self.server.start()

    def start(self):
        self.__start__()
        # asyncio.run(self.__start__())

    def stop(self):
        evt = asyncio.get_event_loop()

        async def stop():
            await self.agent.__state__("stop")
            exit(-1)

        evt.call_soon_threadsafe(stop)


class AgentManager:

    def __init__(self):
        self.agents = []

    def register_agent(self, agent):
        self.agents.append(AgentWrapper(agent))

    def unregister_agent(self, agent):
        # using id remove the agent
        self.agents = [agent for agent in self.agents if agent.id != agent.id]

    def get_agents(self):
        return [agent.agent for agent in self.agents]

    def start(self):
        logging.info("Starting Rakun.")
        allow_connection_pickling()

        agents_thread = []
        for agent in self.agents:
            # agent.start()
            t = Thread(target=agent.start)
            t.start()
            agents_thread.append(t)

        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Stopping Rakun...")
            for agent in self.agents:
                agent.stop()
