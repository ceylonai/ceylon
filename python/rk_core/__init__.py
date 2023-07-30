import logging

from rk_core import rk_core

__doc__ = rk_core.__doc__
if hasattr(rk_core, "__all__"):
    __all__ = rk_core.__all__

rakun_version = rk_core.get_version()
logging.info(f"Rakun version: {rakun_version}")

import tracemalloc

tracemalloc.start()

from .__agent_manager import AgentManager
from .__agent_func import EventProcessorWrapper, Processor, startup, shutdown
from .__agent_wrapper import AgentWrapper
from rk_core.rk_core import Event, EventType
