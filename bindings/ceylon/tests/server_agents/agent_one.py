import asyncio
import pickle
from typing import Any

from ceylon.ceylon import enable_log
from ceylon.task import TaskOperator


class SubTaskWorkingAgent(TaskOperator):
    async def get_result(self, task) -> Any:
        return "done"


worker_1 = SubTaskWorkingAgent("worker_2", "server_admin",
                               admin_port=8888,
                               workspace_id="ceylon_agent_stack",
                               admin_ip="127.0.0.1",
                               admin_peer="12D3KooWQ4h86VMba9PG4mhQRMszkFM5wNAhnUC9rpWNmSzroHsh")

enable_log("INFO")
asyncio.run(worker_1.arun_worker(pickle.dumps({})))
