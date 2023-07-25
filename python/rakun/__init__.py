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

        async def start():
            logging.info(f"Agent:{self.id} Start Process")
            print("Start Process")
            return 0

        async def stop():
            logging.info(f"Agent:{self.id} Stop Process")
            print("Stop Process")
            return 0

        start_func = rakun.FunctionInfo(start, True, 0)
        stop_func = rakun.FunctionInfo(stop, True, 0)

        self.server.add_startup_handler(start_func)
        self.server.add_shutdown_handler(stop_func)

        message_processor_fnc = rakun.FunctionInfo(self.__process_message__, True, 1)
        message_processor = rakun.MessageProcessor(message_processor_fnc, "ALL")

        self.server.add_message_handler(message_processor)

    async def __process_message__(self, message):
        logging.info(f"Agent:{self.id} Messagssse: {message} {self.count}")
        self.count += 1

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
