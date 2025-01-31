# Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
# Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
import asyncio
import inspect
import pickle
import traceback
from typing import Dict, Callable, Optional, Any
from loguru import logger

from ceylon import AgentDetail

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
    return param in sig.parameters


class AgentCommon:
    def __init__(self):
        self._handlers = {}
        self._run_handlers = {}
        self._connection_handlers = {}
        logger.info(f"AgentCommon initialized for {self.__class__.__name__}")

    def on(self, data_type):
        def decorator(func):
            self._handlers[data_type] = func
            return func

        return decorator

    def on_run(self):
        def decorator(func):
            self._run_handlers[func.__name__] = func
            return func

        return decorator

    def on_connect(self, topic: str):
        def decorator(func):
            self._connection_handlers[topic] = func
            return func

        return decorator

    def _matches_pattern(self, pattern: str, topic: str, agent_role: str) -> bool:
        if pattern == '*':
            return True
        if ':' in pattern:
            pattern_topic, pattern_role = pattern.split(':')
            return (pattern_topic == '*' or pattern_topic == topic) and \
                (pattern_role == '*' or pattern_role == agent_role)
        return pattern == topic

    async def onmessage_handler(self, agent: AgentDetail, data: bytes, time: int):
        message = pickle.loads(data)
        message_type = type(message)
        for cls in inspect.getmro(self.__class__):
            method_key = f"{cls.__name__}.{message_type}"
            if method_key in message_handlers:
                handler = message_handlers[method_key]
                kwargs = {}
                if has_param(handler, "agent"): kwargs["agent"] = agent
                if has_param(handler, "time"): kwargs["time"] = time
                await handler(self, message, **kwargs)
                break

    async def onrun_handler(self, inputs: Optional[bytes] = None):
        decoded_input = pickle.loads(inputs) if inputs else None
        for cls in inspect.getmro(self.__class__):
            if cls.__name__ in run_handlers:
                await run_handlers[cls.__name__](self, decoded_input)

    async def onconnect_handler(self, topic: str, agent_detail: Any):
        for cls in inspect.getmro(self.__class__):
            if cls.__name__ in connect_handlers:
                topic_handlers = connect_handlers[cls.__name__]
                if '*' in topic_handlers:
                    await topic_handlers['*'](self, topic, agent_detail)
                for pattern, handler in topic_handlers.items():
                    if pattern != '*' and self._matches_pattern(pattern, topic, agent_detail.role):
                        await handler(self, topic, agent_detail)

    async def common_on_message(self, agent: AgentDetail, data: bytes, time: int):
        try:
            tasks = [self.onmessage_handler(agent, data, time)]

            decoded_data = pickle.loads(data)
            if type(decoded_data) in self._handlers:
                tasks.append(self._handlers[type(decoded_data)](decoded_data, agent, time))

            await asyncio.gather(*tasks)
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error processing message: {e}")

    async def common_on_agent_connected(self, topic: str, agent: AgentDetail):
        try:
            tasks = [self.onconnect_handler(topic, agent)]

            if '*' in self._connection_handlers:
                tasks.append(self._connection_handlers['*'](topic, agent))

            for pattern, handler in self._connection_handlers.items():
                if pattern != '*' and self._matches_pattern(pattern, topic, agent.role):
                    tasks.append(handler(topic, agent))

            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error handling connection: {e}")

    async def common_on_run(self, inputs: bytes):
        try:
            tasks = [self.onrun_handler(inputs)]

            decoded_input = pickle.loads(inputs) if inputs else None
            for handler in self._run_handlers.values():
                tasks.append(handler(decoded_input))

            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in run method: {e}")
