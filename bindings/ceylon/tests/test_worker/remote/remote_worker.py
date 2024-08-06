import asyncio
import pickle

from loguru import logger

from ceylon import Agent
from ceylon.ceylon import uniffi_set_event_loop, enable_log


class WorkerAgent1(Agent):

    async def run(self, inputs: "bytes"):
        logger.info((f"WorkerAgent1 on_run  {self.details().name}", inputs))


worker_1 = WorkerAgent1("worker_2", "server_admin", admin_port=8000,
                        admin_peer="12D3KooWJCAL6SbHPLdyga6ENyvr7M1WpEhcBWEqDs5xFzA1BNq3")


async def run():
    uniffi_set_event_loop(asyncio.get_event_loop())
    await worker_1.start(pickle.dumps({}))


enable_log("info")
asyncio.run(run())
