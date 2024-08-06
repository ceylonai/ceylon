import asyncio
import pickle

from loguru import logger

from ceylon import Agent
from ceylon.ceylon import uniffi_set_event_loop


class WorkerAgent1(Agent):

    async def run(self, inputs: "bytes"):
        logger.info((f"WorkerAgent1 on_run  {self.details().name}", inputs))


worker_1 = WorkerAgent1("worker_2", "server_admin", role="What enver", admin_port=8000,
                        admin_peer="12D3KooWFTTKVN48Ps5DYmUX6YY16Zjo5gm7NbBD65geFohuv5ke")


async def run():
    uniffi_set_event_loop(asyncio.get_event_loop())
    await worker_1.start(pickle.dumps({}))


# enable_log("info")
asyncio.run(run())
