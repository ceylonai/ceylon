import asyncio
import logging
import uuid
from multiprocessing import allow_connection_pickling
import random
from threading import Thread

from rakun import rakun

__doc__ = rakun.__doc__
if hasattr(rakun, "__all__"):
    __all__ = rakun.__all__

logging.basicConfig(level=logging.CRITICAL)

rakun_version = rakun.get_version()
logging.info(f"Rakun version: {rakun_version}")


class AgentWrapper:
    def __init__(self, agent):
        self.id = uuid.uuid4()
        self.agent = agent
        self.start_time = None
        self.server = rakun.Server(agent.name)
        self.count = 0
        evt_processor_fnc = rakun.FunctionInfo(self.__event__processor__, True, 1)
        evt_processor = rakun.EventProcessor("__event__processor__", evt_processor_fnc, rakun.EventType.Start)
        self.server.add_event_processor(evt_processor)
        self.publisher = rakun.MessageProcessor()
        self.publisher.start()

    async def publish(self, message):
        rakun.publish(message)

    async def __event__processor__(self, data: rakun.Event):
        if data.event_type == rakun.EventType.Data:
            print(
                f"Received message to {self.agent.name}: {data.content} {data.creator} {data.event_type} {data.origin_type}")

        if data.event_type == rakun.EventType.Start:
            while True:
                self.publisher.publish(f"Greeting from {self.id} {self.agent.name}")
                sleep_time = random.randint(5, 15)
                await asyncio.sleep(sleep_time)

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
