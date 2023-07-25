import asyncio
import threading
import uuid
from time import sleep

from rakun import rakun
import logging

__doc__ = rakun.__doc__
if hasattr(rakun, "__all__"):
    __all__ = rakun.__all__

logging.basicConfig(level=logging.DEBUG)

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
        evt_processor = rakun.EventProcessor(evt_processor_fnc, rakun.EventType.START)

        self.server.add_event_processor(evt_processor)

    async def __event__processor__(self, data: rakun.Event):
        print(f"Received message: {data.content} {data.creator} {data.event_type} {data.origin_type}")
        # if data and data.publisher == rakun.DataMessagePublisher.System:
        #     print(f"Message From System Service: {data.message}")
        #     if data.message == "Started":
        #         while True:
        #             await asyncio.sleep(5)
        #             print(f"Process {self.id} is starting")
        #             self.server.publish(f"Process {self.id} is starting")
        #
        # self.count += 1

    def __start__(self):
        self.server.start(4)

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

        agents_thread = []
        for agent in self.agents:
            t = threading.Thread(target=agent.start)
            agents_thread.append(t)
            t.start()
            sleep(0.001)

        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Stopping Rakun...")
            for agent in self.agents:
                agent.stop()
