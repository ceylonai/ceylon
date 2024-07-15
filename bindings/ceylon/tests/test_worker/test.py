import asyncio
import pickle

from ceylon.ceylon import enable_log
from ceylon.workspace.admin import Admin
from ceylon.workspace.worker import Worker


async def main():
    admin = Admin(
        name="admin",
        port=8000
    )
    worker1 = Worker(
        name="worker1",
        admin_port=8000,
        admin_peer="admin",
        workspace_id="admin"
    )
    worker2 = Worker(
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
    enable_log("ERROR")
    asyncio.run(main())
