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
    worker = Worker(
        name="worker1",
        admin_port=8000,
        admin_peer="admin",
        workspace_id="admin"
    )
    admin_task = admin.run(pickle.dumps({
        "title": "How to use AI for Machine Learning",
    }))
    worker_task = worker.run(pickle.dumps({
        "title": "How to use AI for Machine Learning",
    }))

    await asyncio.gather(admin_task, worker_task)


if __name__ == '__main__':
    enable_log()
    asyncio.run(main())
