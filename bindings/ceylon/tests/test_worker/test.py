import asyncio
import pickle

from loguru import logger
from pydantic import BaseModel

from ceylon import on_message, Agent, CoreAdmin


class MessageType1(BaseModel):
    title: str


class MessageType2(BaseModel):
    name: str


class TestAdmin(CoreAdmin):

    @on_message(type=MessageType1)
    async def on_message_type_one(self, message: MessageType1, agent_id: "str", time: "int"):
        logger.info((f"TestAdmin Message type one", message))

    @on_message(type=MessageType2)
    async def on_message_type_two(self, message: MessageType2, agent_id: "str", time: "int"):
        logger.info((f"TestAdmin Message type two", message))

    async def run(self, inputs: "bytes"):
        while True:
            await asyncio.sleep(5)
            await self.broadcast(pickle.dumps(MessageType2(name="Im Admin")))


class TestWorker(Agent):

    @on_message(type=MessageType1)
    async def on_message_type_test_worker(self, message: MessageType1, agent_id: "str", time: "int"):
        logger.info((f"TestWorker {self.details().name} Message type one {self.details().name}", message))

    @on_message(type=MessageType2)
    async def on_message_type_two_test_worker(self, message: MessageType2, agent_id: "str", time: "int"):
        logger.info((f"TestWorker  {self.details().name} Message type two {self.details().name}", message))

    async def run(self, inputs: "bytes"):
        while True:
            await asyncio.sleep(1)
            await self.broadcast(pickle.dumps(MessageType2(name=f"Im Worker {self.details().name}")))


async def main():
    admin = TestAdmin(
        name="admin",
        port=8000
    )
    worker1 = TestWorker(
        name="worker1",
        admin_port=8000,
        admin_peer="admin",
        workspace_id="admin"
    )
    worker2 = TestWorker(
        name="worker2",
        admin_port=8000,
        admin_peer="admin",
        workspace_id="admin"    
    )

    worker3 = TestWorker(
        name="worker3",
        admin_port=8000,
        admin_peer="admin",
        workspace_id="admin"
    )

    await admin.arun_admin(pickle.dumps({
        "title": "How to use AI for Machine Learning",
    }), [
        worker1,
        worker2,
        worker3
    ])


if __name__ == '__main__':
    # enable_log("INFO")
    asyncio.run(main())
