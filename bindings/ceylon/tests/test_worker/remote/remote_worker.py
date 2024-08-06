import asyncio
import pickle

from loguru import logger

from ceylon import Agent
from ceylon.ceylon import uniffi_set_event_loop


class WorkerAgent1(Agent):

    async def run(self, inputs: "bytes"):
        logger.info((f"WorkerAgent1 on_run  {self.details().name}", inputs))


worker_1 = WorkerAgent1("worker_2", "server_admin", role="What enver", admin_port=8000,
                        admin_peer="12D3KooWCLKVyiM5VkwYYAaDKL5rMW4WnSbMcVicMDqy23inFz3K")


worker_1.run_worker(pickle.dumps({}))
