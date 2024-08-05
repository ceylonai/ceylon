import asyncio
import pickle
from typing import Type, Dict, Callable

from loguru import logger
from pydantic import BaseModel

from ceylon.workspace.admin import Admin
from ceylon.workspace.worker import Worker

message_handlers: Dict[str, Callable] = {}


def on_message(type: Type[BaseModel]):
    def decorator(method):
        class_name = method.__qualname__.split(".")[0]
        method_key = f"{class_name}.{type}"
        message_handlers[method_key] = method

        def wrapper(*args, **kwargs):
            return method(*args, **kwargs)

        return wrapper

    return decorator


class MessageType1(BaseModel):
    title: str


class MessageType2(BaseModel):
    name: str


class TestAdmin(Admin):

    @on_message(type=MessageType1)
    async def on_message_type_one(self, message: MessageType1, agent_id: "str", time: "int"):
        logger.info((f"Message type one", message))

    @on_message(type=MessageType2)
    async def on_message_type_two(self, message: MessageType2, agent_id: "str", time: "int"):
        logger.info((f"Message type two", message))

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        # Deserialize the message
        message = pickle.loads(data)
        message_type = type(message)
        class_name = self.__class__.__qualname__.split(".")[0]
        method_key = f"{class_name}.{message_type}"
        # Trigger the appropriate handler if one is registered
        if method_key in message_handlers:
            await message_handlers[method_key](self, message, agent_id, time)
        else:
            logger.warning("No handler registered for message type: %s", message_type)

        await self.broadcast(pickle.dumps(MessageType1(title=f"Im Admin on message {self.details().name}")))

    async def run(self, inputs: "bytes"):
        while True:
            await asyncio.sleep(5)
            await self.broadcast(pickle.dumps(MessageType2(name="Im Admin")))


class TestWorker(Worker):

    @on_message(type=MessageType1)
    async def on_message_type_test_worker(self, message: MessageType1, agent_id: "str", time: "int"):
        logger.info((f"Message type one {self.details().name}", message))

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        # logger.info((f"Admin on_message  {self.details().name}", agent_id, data, time))
        await self.broadcast(pickle.dumps(MessageType1(title=f"Im Worker on message  {self.details().name}")))

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

    await admin.arun_admin(pickle.dumps({
        "title": "How to use AI for Machine Learning",
    }), [
        worker1,
        worker2
    ])


if __name__ == '__main__':
    # enable_log("INFO")
    asyncio.run(main())
