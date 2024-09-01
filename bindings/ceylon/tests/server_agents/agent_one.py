import asyncio
import pickle
import random
import time
from typing import Any

from loguru import logger
from pydantic import BaseModel

from ceylon import on_message
from ceylon.ceylon import enable_log
from ceylon.task import TaskOperator

enable_log("INFO")


class SubTaskMessage(BaseModel):
    message: str
    time: float


class SubTaskWorkingAgent(TaskOperator):
    async def get_result(self, task) -> Any:
        return "done"

    @on_message(type=SubTaskMessage)
    async def on_sub_task_message(self, data: SubTaskMessage):
        logger.info(f"Got message: {data}")

    async def run(self, inputs: "bytes"):
        while True:
            await self.broadcast_data(SubTaskMessage(message="hello", time=time.time()))
            logger.info("done")
            random_number = random.randint(1, 10)
            await asyncio.sleep(random_number)


worker_1 = SubTaskWorkingAgent("worker_2", "server_admin",
                               admin_port=8888,
                               workspace_id="ceylon_agent_stack",
                               admin_ip="23.94.182.52",
                               # admin_ip="127.0.0.1",
                               admin_peer="12D3KooWEUH7vcsHUQ72xfExPZLHawWiYZrybZL5Hj9t6RvkcHpX")

asyncio.run(worker_1.arun_worker(pickle.dumps({})))
