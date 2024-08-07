import inspect
import pickle
from typing import Dict, Callable

from loguru import logger

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


def has_param(func, param):
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    return param in params


class AgentCommon:

    async def _on_message_handler(self, agent_id: "str", data: "bytes", time: "int"):
        # Deserialize the message
        message = pickle.loads(data)
        message_type = type(message)
        class_name = self.__class__.__qualname__.split(".")[0]
        method_key = f"{class_name}.{message_type}"
        # Trigger the appropriate handler if one is registered
        if method_key in message_handlers:
            func = message_handlers[method_key]
            if has_param(func, "agent_id") and has_param(func, "time"):
                await message_handlers[method_key](self, message, agent_id=agent_id, time=time)
            elif has_param(func, "agent_id"):
                await message_handlers[method_key](self, message, agent_id=agent_id)
            elif has_param(func, "time"):
                await message_handlers[method_key](self, message, time=time)
            else:
                await message_handlers[method_key](self, message)
        else:
            logger.warning(f"No handler registered ({self.__class__.__qualname__}) for message type: {message_type}")
