import asyncio
import pickle
import random
import time
from typing import Any

from loguru import logger
from pydantic import BaseModel

from ceylon import on_message
from ceylon.ceylon import enable_log
from ceylon.static_val import DEFAULT_CONF_FILE
from ceylon.task import TaskOperator

# enable_log("INFO")


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

    async def on_agent_connected(self, topic: "str", agent: "AgentDetail"):
        logger.info(f"Agent {agent.name} connected to {topic}")
        await super().on_agent_connected(topic, agent)


worker_1 = SubTaskWorkingAgent("worker_2", "server_admin",
                               conf_file=DEFAULT_CONF_FILE)

asyncio.run(worker_1.arun_worker(pickle.dumps({})))
