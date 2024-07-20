import asyncio
import pickle

from ceylon.ceylon import enable_log
from ceylon.workspace.admin import Admin
from ceylon.workspace.worker import Worker


class TestAdmin(Admin):

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(f"Admin on_message  {self.details().name}", agent_id, data, time)
        await self.broadcast(pickle.dumps({
            "title": "Im Admin " + self.details().name + " on message",
        }))

    async def run(self, inputs: "bytes"):
        while True:
            await asyncio.sleep(1)
            await self.broadcast(pickle.dumps({
                "title": "Im Admin",
            }))


class TestWorker(Worker):

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(f"Agent on_message  {self.details().name}", agent_id, data, time)
        await self.broadcast(pickle.dumps({
            "title": "Im Agent " + self.details().name + " on message",
        }))

    async def run(self, inputs: "bytes"):
        while True:
            await asyncio.sleep(2)
            await self.broadcast(pickle.dumps({
                "title": "Im Agent " + self.details().name,
            }))


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

    await admin.run_admin(pickle.dumps({
        "title": "How to use AI for Machine Learning",
    }), [
        worker1,
        worker2
    ])


if __name__ == '__main__':
    enable_log("INFO")
    asyncio.run(main())
