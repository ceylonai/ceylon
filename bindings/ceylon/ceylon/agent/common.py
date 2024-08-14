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

        # Get the class hierarchy
        class_hierarchy = inspect.getmro(self.__class__)

        # Find the most specific handler in the class hierarchy
        handler = None
        for cls in class_hierarchy:
            class_name = cls.__name__
            method_key = f"{class_name}.{message_type}"
            if method_key in message_handlers:
                handler = message_handlers[method_key]
                break

        # Trigger the appropriate handler if one is registered
        if handler:
            if has_param(handler, "agent_id") and has_param(handler, "time"):
                await handler(self, message, agent_id=agent_id, time=time)
            elif has_param(handler, "agent_id"):
                await handler(self, message, agent_id=agent_id)
            elif has_param(handler, "time"):
                await handler(self, message, time=time)
            else:
                await handler(self, message)
        else:
            logger.warning(f"No handler registered in the class hierarchy for message type: {message_type}")