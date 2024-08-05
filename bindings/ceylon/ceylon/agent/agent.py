from typing import Dict, Callable

from ceylon.workspace.worker import Worker

message_handlers: Dict[str, Callable] = {}


def on_message(type):
    def decorator(method):
        class_name = method.__qualname__.split(".")[0]
        method_key = f"{class_name}.{type}"
        message_handlers[method_key] = method

        def wrapper(*args, **kwargs):
            return method(*args, **kwargs)

        return wrapper

    return decorator


class Agent(Worker):
    history_responses = []

    def __init__(self, name: str, workspace_id: str, admin_port: int, admin_peer: str, role: str = None):
        super().__init__(
            name=name,
            workspace_id=workspace_id,
            admin_port=admin_port,
            admin_peer=admin_peer,
            role=role if role else name,
        )

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        pass
