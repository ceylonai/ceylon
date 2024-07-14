import asyncio
import pickle

from ceylon.ceylon import AdminAgent, AdminAgentConfig, enable_log


class Admin(AdminAgent):

    def __init__(self, name="admin", port=8888):
        super().__init__(config=AdminAgentConfig(name=name, port=port))


async def main():
    admin = Admin()
    await admin.run(pickle.dumps({
        "title": "How to use AI for Machine Learning",
    }))


if __name__ == '__main__':
    enable_log()
    asyncio.run(main())
