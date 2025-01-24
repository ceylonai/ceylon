# Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
# Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).

import inspect
import pickle
from typing import Dict, Callable, Optional, Any
from loguru import logger

message_handlers: Dict[str, Callable] = {}
run_handlers: Dict[str, Callable] = {}
connect_handlers: Dict[str, Dict[str, Callable]] = {}


def on(type):
    def decorator(method):
        class_name = method.__qualname__.split(".")[0]
        method_key = f"{class_name}.{type}"
        message_handlers[method_key] = method
        return method

    return decorator


def on_run():
    def decorator(method):
        class_name = method.__qualname__.split(".")[0]
        run_handlers[class_name] = method
        return method

    return decorator


def on_connect(topic: str):
    def decorator(method):
        class_name = method.__qualname__.split(".")[0]
        if class_name not in connect_handlers:
            connect_handlers[class_name] = {}
        connect_handlers[class_name][topic] = method
        return method

    return decorator


def has_param(func, param):
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    return param in params


class AgentCommon:
    async def onmessage_handler(self, agent_id: str, data: bytes, time: int):
        message = pickle.loads(data)
        message_type = type(message)
        class_hierarchy = inspect.getmro(self.__class__)

        handler = None
        for cls in class_hierarchy:
            method_key = f"{cls.__name__}.{message_type}"
            if method_key in message_handlers:
                handler = message_handlers[method_key]
                break

        if handler:
            if has_param(handler, "agent_id") and has_param(handler, "time"):
                await handler(self, message, agent_id=agent_id, time=time)
            elif has_param(handler, "agent_id"):
                await handler(self, message, agent_id=agent_id)
            elif has_param(handler, "time"):
                await handler(self, message, time=time)
            else:
                await handler(self, message)

    async def onrun_handler(self, inputs: Optional[bytes] = None):
        decoded_input = pickle.loads(inputs) if inputs else None
        class_hierarchy = inspect.getmro(self.__class__)

        for cls in class_hierarchy:
            if cls.__name__ in run_handlers:
                await run_handlers[cls.__name__](self, decoded_input)

    async def onconnect_handler(self, topic: str, agent_detail: Any):
        class_hierarchy = inspect.getmro(self.__class__)

        for cls in class_hierarchy:
            if cls.__name__ in connect_handlers:
                topic_handlers = connect_handlers[cls.__name__]

                if '*' in topic_handlers:
                    await topic_handlers['*'](self, topic, agent_detail)

                for pattern, handler in topic_handlers.items():
                    if pattern == '*':
                        continue

                    if ':' in pattern:
                        pattern_topic, pattern_role = pattern.split(':')
                        if (pattern_topic == '*' or pattern_topic == topic) and \
                                (pattern_role == '*' or pattern_role == agent_detail.role):
                            await handler(self, topic, agent_detail)
                    elif pattern == topic:
                        await handler(self, topic, agent_detail)
