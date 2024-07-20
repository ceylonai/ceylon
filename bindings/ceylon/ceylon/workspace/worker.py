import asyncio
import pickle

from ceylon.ceylon import WorkerAgent, WorkerAgentConfig, Processor, \
    MessageHandler


class Worker(WorkerAgent, Processor, MessageHandler):

    def __init__(self, name="admin", workspace_id="admin", admin_peer=None, admin_port=8888,role="worker"):
        super().__init__(config=WorkerAgentConfig(name=name,
                                                  role=role,
                                                  admin_peer=admin_peer,
                                                  admin_port=admin_port,
                                                  work_space_id=workspace_id), processor=self, on_message=self)

    async def run(self, inputs: "bytes"):
        print(f"Worker  received: {inputs}")
        try:
            while True:
                await self.broadcast(pickle.dumps({
                    "hello": f"world from worker  {self.details().name}"
                }))
                await asyncio.sleep(1)
                print(f"Worker broadcasted: {pickle.dumps({'hello': 'world from worker'})}")
        except Exception as e:
            print(f"Worker error: {e}")
        print(f"Worker {self.details().name} finished")

    def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(f"Worker on_message  {self.details().name}", agent_id, data, time)

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(f"Worker on_message  {self.details().name}", agent_id, data, time)
